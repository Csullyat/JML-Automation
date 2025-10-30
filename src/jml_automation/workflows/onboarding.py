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
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any


from jml_automation.parsers import parse_ticket, fetch_ticket
from jml_automation.models.ticket import OnboardingTicket
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim

log = logging.getLogger("jml_automation")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = RotatingFileHandler("logs/jml_automation.log", maxBytes=1048576, backupCount=3)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)

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

        profile = {
            "firstName": u.first_name,
            "lastName":  u.last_name,
            "email":     u.email,
            "login":     u.email,
            "displayName": f"{u.first_name} {u.last_name}",
            "title":       u.title,
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
        print(f"DEBUG: User exists with ID: {user_id}, updating...")
        okta.update_profile(user_id, {k:v for k,v in {
            "mobilePhone": u.phone_mobile,
            "department":  u.department,
            "title":       u.title,
        }.items() if v})
        print(f"DEBUG: Updated user {u.email} (id={user_id})")
        log.info(f"Updated Okta user: {u.email} (id={user_id})")

    # 2) Groups
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

    # 3) Microsoft 365 group assignment
    try:
        from jml_automation.services.microsoft import MicrosoftService
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

    # Update SolarWinds ticket state and add comment (direct API style)
    try:
        from jml_automation.services.solarwinds import update_ticket_status_direct, add_ticket_comment_direct
        sw_ticket_id = str(ticket.ticket_id)
        sw_ticket_number = sw_ticket_id  # OnboardingTicket does not have display_number
        update_ticket_status_direct(sw_ticket_id, sw_ticket_number, "In Progress")
        add_ticket_comment_direct(sw_ticket_id, sw_ticket_number, "User account has been created.")
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

    # TODO: call real adapters (downstream services)
    # if push_domo: DomoService(...).send_metrics(...)
    return 0