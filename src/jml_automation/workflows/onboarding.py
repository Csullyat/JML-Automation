"""
Onboarding workflow for JML Automation.

This module orchestrates the complete onboarding process:
1. Fetch tickets from SolarWinds
2. Create users in Okta
3. Send Slack notifications
4. Update ticket status
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any


from jml_automation.parsers import parse_ticket, fetch_ticket
from jml_automation.models.ticket import OnboardingTicket
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim

# Use the centralized logger instead of setting up our own
log = logging.getLogger("jml_automation")

def _plan_from_ticket(ticket: OnboardingTicket) -> list[str]:
    user = ticket.user
    email = user.email if user else "<unknown>"
    name = f"{user.first_name} {user.last_name}".strip() if user else "<unknown>"
    steps = [
        f"Okta: create/upsert {email} ({name})",
        "Okta: add baseline groups (Filevine Employees, dept groups, Zoom basic/pro)",
        "M365/Google: provision mailbox/license per mappings",
        "Zoom: assign license (AE → Pro if applicable)",
    # "Domo/Lucid/Adobe/Workato: provision as needed",
    # "Assets: record laptop style / create inventory (Kandji/Intune as needed)",
    ]
    return steps

def run(
    *,
    ticket_id: Optional[str] = None,
    ticket_raw: Optional[Dict[str, Any]] = None,
    dry_run: bool = True,
    push_domo: bool = False,
) -> int:
    """
    Execute the onboarding workflow.
    - If ticket_raw is provided, use it (tests/smoke).
    - Else fetch by ticket_id (when fetch_ticket is wired).
    """

    print("DEBUG: Entered onboarding run() function")
    print(f"DEBUG: ticket_id={ticket_id}, ticket_raw is None? {ticket_raw is None}")

    if ticket_raw is None:
        if not ticket_id:
            log.error("Either ticket_raw or ticket_id must be provided.")
            print("ERROR: No ticket_id or ticket_raw provided.")
            return 2
        print(f"DEBUG: Fetching ticket {ticket_id}...")
        raw = fetch_ticket(ticket_id)
        print(f"DEBUG: Got raw ticket: {raw}")
    else:
        print("DEBUG: Using provided ticket_raw.")
        raw = ticket_raw
        print(f"DEBUG: Got raw ticket: {raw}")

    print("DEBUG: Parsing ticket...")
    ticket = parse_ticket(raw)
    print(f"DEBUG: Parsed ticket: {ticket}")
    if not isinstance(ticket, OnboardingTicket):
        log.error("Parsed ticket is not an OnboardingTicket (id=%s)", raw.get("id"))
        print(f"ERROR: Parsed ticket is not an OnboardingTicket (id={raw.get('id')})")
        return 3

    print("DEBUG: Building onboarding plan...")
    plan = _plan_from_ticket(ticket)
    print(f"DEBUG: Onboarding plan: {plan}")

    # Safety: Only allow live runs for test user
    u = ticket.user

    print(f"DEBUG: dry_run value is: {dry_run}")
    if dry_run:
        print("=== Onboarding plan ===")
        for s in plan:
            print(" -", s)
        return 0

    # --- LIVE ONBOARDING LOGIC ---

    from jml_automation.services.okta import OktaService
    from pathlib import Path
    import yaml

    print("DEBUG: Creating OktaService...")
    okta = OktaService.from_env()
    print("DEBUG: OktaService created successfully")

    # 1) Upsert user
    u = ticket.user
    assert u and u.email, "Cannot onboard without email"
    print(f"DEBUG: Looking for existing user: {u.email}")

    user_id = okta.find_user_by_email(u.email)
    if not user_id:
        print(f"DEBUG: User not found, creating new user: {u.email}")
        # Calculate timezone based on location
        timezone = "America/Denver"  # Default fallback
        common_locations = {
            ("Salt Lake City", "UT", "US"): "America/Denver",
            ("London", None, "GB"): "Europe/London",
            ("Tokyo", None, "JP"): "Asia/Tokyo",
            # Czech Republic locations
            ("Prague", "Czech Republic", "CZ"): "Europe/Prague",
            ("Brno", "Czech Republic", "CZ"): "Europe/Prague",
            ("Rajhrad", "Czech Republic", "CZ"): "Europe/Prague",
            # Add more as needed
        }
        key = (u.city, u.state if u.state else None, u.country_code)
        if key in common_locations:
            timezone = common_locations[key]
            print(f"DEBUG: Used fallback timezone {timezone} for {key}")
        elif u.city and u.country_code:
            try:
                geolocator = Nominatim(user_agent="jml_automation", timeout=10)
                # Try multiple location string formats for better geocoding
                location_strings = []
                if u.state and u.state != u.country_code:
                    location_strings.append(f"{u.city}, {u.state}, {u.country_code}")
                    location_strings.append(f"{u.city}, {u.state}")
                location_strings.append(f"{u.city}, {u.country_code}")
                location_strings.append(u.city)
                
                location = None
                for location_str in location_strings:
                    print(f"DEBUG: Trying to geocode: '{location_str}'")
                    try:
                        location = geolocator.geocode(location_str)
                        if location and hasattr(location, "latitude") and hasattr(location, "longitude"):
                            print(f"DEBUG: Successfully geocoded '{location_str}' to {location.latitude}, {location.longitude}")
                            break
                    except Exception as geo_e:
                        print(f"DEBUG: Geocoding failed for '{location_str}': {geo_e}")
                        continue
                
                if location and hasattr(location, "latitude") and hasattr(location, "longitude"):
                    tf = TimezoneFinder()
                    detected_timezone = tf.timezone_at(lat=location.latitude, lng=location.longitude)
                    if detected_timezone:
                        timezone = detected_timezone
                        print(f"DEBUG: Detected timezone {timezone} for coordinates {location.latitude}, {location.longitude}")
                    else:
                        print(f"DEBUG: TimezoneFinder returned None for coordinates {location.latitude}, {location.longitude}")
                else:
                    print(f"DEBUG: Could not geocode any location string for {u.city}, {u.state}, {u.country_code}")
            except Exception as e:
                print(f"DEBUG: Error detecting timezone: {e}, using default")

        # Modify title for contractors
        title = u.title or ""
        if ticket.hire_type and ticket.hire_type.strip().lower() == "contractor":
            if title and not title.lower().endswith("contractor"):
                title = f"{title} - Contractor"
            elif not title:
                title = "Contractor"
            print(f"DEBUG: Modified title for contractor: '{title}'")
        
        profile = {
            "firstName": u.first_name,
            "lastName":  u.last_name,
            "email":     u.email,
            "login":     u.email,
            "displayName": f"{u.first_name} {u.last_name}",
            "title":       title,
            "department":  u.department,
            "manager":     u.manager_display,  # The "Lastname, Firstname" format
            # Additional mappings
            "secondEmail": u.personal_email,  # From "New Employee Personal Email Address"
            "mobilePhone": u.phone_mobile,
            "streetAddress": u.street_address,  # From "streetAddress" in ticket
            "city": u.city,
            "state": u.state,  # From "state - Formatted (UT)"
            "zipCode": u.zip_code,
            "countryCode": u.country_code,  # From "countryCode - Formatted (US)"
            "organization": "Filevine",  # Always Filevine
            "managerId": u.manager_email,  # The manager's email address
            "swrole": "Requester",  # Always Requester
            "preferredLanguage": "en",  # Always hardcoded to English
            "timezone": timezone,
            "primary": True,  # Always set primary to true
        }
        print(f"DEBUG: Creating with profile: {profile}")
        user_id = okta.create_user(profile, activate=True)
        print(f"DEBUG: Created user with ID: {user_id}")
        log.info(f"Created Okta user: {u.email} (id={user_id})")
    else:
        print(f"ERROR: User {u.email} already exists in Okta with ID: {user_id}")
        print(f"MANUAL ACTION REQUIRED: Please check the user's status in Okta and handle manually")
        log.error(f"User {u.email} already exists in Okta (ID: {user_id}). Manual intervention required.")
        raise Exception(f"User {u.email} already exists in Okta. Please handle manually and re-run onboarding.")

    # 2) Groups - Check if partner user and skip baseline groups
    # Check if this user was just created as a partner user
    is_partner_user = okta.is_partner_user(user_id)
    
    if is_partner_user:
        print(f"DEBUG: Partner user {u.email} detected - skipping baseline group assignment")
        log.info(f"Partner user {u.email} detected - groups managed by partner assignment rules only")
    else:
        # Standard employee group assignment
        cfg = yaml.safe_load((Path("config")/"groups.yaml").read_text())
        group_names = set(cfg.get("baseline", []))

        dept_map = (cfg.get("dept") or {})
        
        # Map department names to config keys
        department_key = u.department
        if u.department == "AE - Account Executives":
            department_key = "Sales"
        elif u.department == "SDR - Sales Development Reps":
            department_key = "Sales"
        
        if department_key in dept_map:
            group_names.update(dept_map[department_key])

        # Zoom license group
        zoom = cfg.get("zoom", {})
        if (u.title or "").strip().lower().startswith("account executive"):
            group_names.add(zoom.get("ae", zoom.get("default")))
        else:
            if zoom.get("default"): group_names.add(zoom["default"])

        # Resolve to IDs and assign
        print(f"DEBUG: Resolving group names: {sorted(group_names)}")
        gids = []
        for name in sorted(n for n in group_names if n):
            gid = okta.find_group_id(name)
            if gid:
                gids.append(gid)
                print(f"DEBUG: Resolved group '{name}' to id {gid}")
                log.info(f"Resolved group '{name}' to id {gid}")
            else:
                print(f"DEBUG: Group '{name}' not found in Okta")
                log.warning(f"Group '{name}' not found in Okta")
        if gids:
            print(f"DEBUG: Adding user {u.email} (id={user_id}) to groups: {gids}")
            okta.add_to_groups(user_id, gids)
            print(f"DEBUG: Added user {u.email} (id={user_id}) to groups: {gids}")
            log.info(f"Added user {u.email} (id={user_id}) to groups: {gids}")
        else:
            print(f"DEBUG: No valid groups to add for user {u.email} (id={user_id})")
            log.warning(f"No valid groups to add for user {u.email} (id={user_id})")

    # 3) Microsoft 365 group assignment - Skip for partner users
    # Check if this is a partner user (should skip standard provisioning)
    is_partner = okta.is_partner_user(user_id)
    
    if is_partner:
        print(f"DEBUG: Detected partner user {u.email}, skipping standard Microsoft 365/Google provisioning")
        log.info(f"Skipping standard provisioning for partner user {u.email} - access limited to partner groups only")
    else:
        try:
            from jml_automation.services.microsoft import MicrosoftService
            import time
            
            # Wait for user propagation from Okta to Exchange Online
            print(f"DEBUG: Waiting 90 seconds for {u.email} to propagate from Okta to Exchange Online...")
            log.info(f"Waiting 90 seconds for user {u.email} to propagate from Okta to Exchange Online")
            time.sleep(90)
            
            print(f"DEBUG: Adding Microsoft 365 groups for user {u.email} in department {u.department}")
            
            ms = MicrosoftService()
            m365_results = ms.add_user_to_groups_by_department(u.email, u.department or "")
            
            if m365_results['success']:
                groups_added = m365_results['groups_added']
                print(f"DEBUG: Successfully added {u.email} to Microsoft 365 groups: {groups_added}")
                log.info(f"Added user {u.email} to Microsoft 365 groups: {groups_added}")
            else:
                groups_failed = m365_results['groups_failed']
                errors = m365_results['errors']
                print(f"DEBUG: Microsoft 365 group assignment failed for {u.email}: {errors}")
                log.warning(f"Microsoft 365 group assignment failed for {u.email}: {groups_failed}")
                # Don't fail the entire onboarding process for M365 group issues
                for error in errors:
                    log.warning(f"M365 group error: {error}")
                    
        except Exception as e:
            print(f"DEBUG: Microsoft 365 group assignment failed for {u.email}: {e}")
            log.warning(f"Microsoft 365 group assignment failed (non-fatal): {e}")
            # Continue with onboarding even if M365 groups fail

    # Update SolarWinds ticket state, add comment, and reassign to Laptop Setup
    try:
        from jml_automation.services.solarwinds import update_ticket_status_direct, add_ticket_comment_direct, SolarWindsService
        sw_ticket_id = str(ticket.ticket_id)
        sw_ticket_number = sw_ticket_id  # OnboardingTicket does not have display_number
        
        # Update status and add comment
        update_ticket_status_direct(sw_ticket_id, sw_ticket_number, "In Progress")
        add_ticket_comment_direct(sw_ticket_id, sw_ticket_number, "User account has been created.")
        
        # Reassign from "New Users" to "Laptop Setup" group
        sw_service = SolarWindsService.from_config()
        reassign_success = sw_service.reassign_ticket_to_group(sw_ticket_id, "Laptop Setup")
        
        if reassign_success:
            print(f"DEBUG: Successfully reassigned ticket {sw_ticket_id} to Laptop Setup group")
            log.info(f"Ticket {sw_ticket_id} reassigned to Laptop Setup group")
        else:
            print(f"DEBUG: Failed to reassign ticket {sw_ticket_id} to Laptop Setup group")
            log.warning(f"Failed to reassign ticket {sw_ticket_id} to Laptop Setup group")
        
        print(f"DEBUG: Updated ticket {sw_ticket_id} state and added comment.")
    except Exception as e:
        log.warning(f"SolarWinds ticket update failed (non-fatal): {e}")
        print(f"DEBUG: SolarWinds ticket update failed: {e}")

    # Send Slack notification after group assignment
    try:
        from jml_automation.services.slack import SlackService
        from jml_automation.config import Config
        slack = SlackService(config=Config())
        display_num = str(ticket_id) if ticket_id else None
        slack.send_onboarding_notification(
            user=u,
            ticket=ticket,
            okta_user_id=user_id,
            display_number=display_num
        )
        print(f"DEBUG: Slack notification sent for {u.email}")
    except Exception as e:
        log.warning(f"Slack notification failed (non-fatal): {e}")
        print(f"DEBUG: Slack notification failed: {e}")

    # 4) Handle contractor-specific logic
    if ticket.hire_type and ticket.hire_type.strip().lower() == "contractor":
        try:
            print(f"DEBUG: Detected contractor hire type for {u.email}, adding to Contractors group")
            log.info(f"Processing contractor-specific logic for {u.email}")
            
            # Wait a bit for user to propagate in Okta before attempting group operations
            print(f"DEBUG: Waiting 10 seconds for user propagation before Contractors group addition...")
            time.sleep(10)
            
            # Add contractor to the Contractors group
            contractors_group_id = okta.find_group_id("Contractors")
            
            if contractors_group_id:
                print(f"DEBUG: Found Contractors group ID: {contractors_group_id}")
                okta.add_to_groups(user_id, [contractors_group_id])
                print(f"DEBUG: Successfully added contractor {u.email} to Contractors Okta group")
                log.info(f"Successfully added contractor {u.email} to Contractors Okta group")
            else:
                print(f"DEBUG: Contractors group not found in Okta")
                log.warning(f"Contractors group not found in Okta for contractor {u.email}")
                
        except Exception as e:
            print(f"DEBUG: Contractor Okta group operations failed for {u.email}: {e}")
            log.warning(f"Contractor Okta group operations failed (non-fatal): {e}")
            # Continue anyway - don't fail onboarding for this
    else:
        hire_type_display = ticket.hire_type or "Not specified"
        print(f"DEBUG: Hire type is '{hire_type_display}', no contractor-specific actions needed")

    # TODO: call real adapters (downstream services)
    # if push_domo: DomoService(...).send_metrics(...)
    return 0