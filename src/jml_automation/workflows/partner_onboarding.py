"""
Partner onboarding workflow for JML Automation.

This module orchestrates the complete partner onboarding process:
1. Fetch partner tickets from SolarWinds
2. Create partner organizations in Okta (if new)
3. Create partner users in Okta
4. Send notifications
5. Update ticket status
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

from jml_automation.parsers import parse_ticket, fetch_ticket
from jml_automation.models.ticket import PartnerTicket

log = logging.getLogger("jml_automation")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = RotatingFileHandler("logs/jml_automation.log", maxBytes=1048576, backupCount=3)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)


def _plan_from_ticket(ticket: PartnerTicket) -> list[str]:
    """Generate a plan for partner onboarding based on the ticket."""
    company = ticket.partner_company or "<unknown company>"
    name = ticket.partner_name or "<unknown name>"
    is_new_org = ticket.is_new_partner_org
    needs_knowbe4 = ticket.needs_knowbe4
    
    steps = []
    
    # Microsoft steps first
    steps.extend([
        f"Microsoft: create shared mailbox {ticket.filevine_email}",
        f"Microsoft: set up email forwarding to {ticket.partner_email}",
    ])
    
    # Then Okta steps
    if is_new_org:
        steps.extend([
            f"Okta: create partner organization '{company}'",
            f"Okta: create Partner - {company} group",
            f"Okta: create SSO-Zscaler_ZPA_Partner_{company.replace(' ', '')} group",
            f"Okta: assign Zscaler group to Zscaler ZPA application",
            f"Okta: create assignment rule for partner groups{'(include KnowBe4)' if needs_knowbe4 else ''}",
        ])
    
    steps.extend([
        f"Okta: create partner user {name} ({ticket.filevine_email})",
        f"Okta: add user to Partner - {company} group",
    ])
    
    return steps


def run(
    *,
    ticket_id: Optional[str] = None,
    ticket_raw: Optional[Dict[str, Any]] = None,
    dry_run: bool = True,
) -> int:
    """
    Execute the partner onboarding workflow.
    - If ticket_raw is provided, use it (tests/smoke).
    - Else fetch by ticket_id.
    """

    print("DEBUG: Entered partner onboarding run() function")
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

    print("DEBUG: Parsing ticket...")
    ticket = parse_ticket(raw)
    print(f"DEBUG: Parsed ticket: {ticket}")
    
    if not isinstance(ticket, PartnerTicket):
        log.error("Parsed ticket is not a PartnerTicket (id=%s)", raw.get("id"))
        print(f"ERROR: Parsed ticket is not a PartnerTicket (id={raw.get('id')})")
        return 3

    print("DEBUG: Building partner onboarding plan...")
    plan = _plan_from_ticket(ticket)
    print(f"DEBUG: Partner onboarding plan: {plan}")

    print(f"DEBUG: dry_run value is: {dry_run}")
    if dry_run:
        print("=== Partner Onboarding Plan ===")
        for s in plan:
            print(" -", s)
        return 0

    # --- LIVE PARTNER ONBOARDING LOGIC ---

    from jml_automation.services.okta import OktaService

    print("DEBUG: Creating OktaService...")
    okta = OktaService.from_env()
    print("DEBUG: OktaService created successfully")

    # Validate required fields
    if not ticket.partner_company:
        log.error("Partner company is required for onboarding")
        print("ERROR: Partner company is required")
        return 4
    
    if not ticket.partner_name:
        log.error("Partner name is required for onboarding")
        print("ERROR: Partner name is required")
        return 4
        
    if not ticket.filevine_email:
        log.error("Filevine email is required for onboarding")
        print("ERROR: Filevine email is required")
        return 4

    # Step 1: Create Microsoft shared mailbox with email forwarding FIRST (for ALL partner users)
    print(f"DEBUG: Creating Microsoft shared mailbox with forwarding: {ticket.filevine_email} -> {ticket.partner_email}")
    
    try:
        from jml_automation.services.microsoft import MicrosoftService
        microsoft = MicrosoftService()
        
        mailbox_result = microsoft.create_partner_mailbox_with_forwarding(
            partner_name=ticket.partner_name,
            filevine_email=ticket.filevine_email,
            partner_email=ticket.partner_email or ""
        )
        
        if mailbox_result["success"]:
            print(f"SUCCESS: Created shared mailbox with forwarding for {ticket.partner_name}")
            print(f"Mailbox: {ticket.filevine_email} -> {ticket.partner_email}")
        else:
            log.error(f"Failed to create shared mailbox for {ticket.partner_name}: {mailbox_result.get('error')}")
            print(f"ERROR: Failed to create shared mailbox: {mailbox_result.get('error')}")
            return 7
    except Exception as e:
        log.error(f"Error creating shared mailbox for {ticket.partner_name}: {e}")
        print(f"ERROR: Error creating shared mailbox: {e}")
        return 7

    # Step 2: Create partner organization if it's a new one
    if ticket.is_new_partner_org:
        print(f"DEBUG: Creating new partner organization: {ticket.partner_company}")
        
        org_result = okta.create_partner_organization(
            partner_name=ticket.partner_company,
            needs_knowbe4=ticket.needs_knowbe4 or False
        )
        
        if org_result['success']:
            print(f"SUCCESS: Created partner organization '{ticket.partner_company}'")
            print(f"Groups created: {[g['name'] for g in org_result['groups_created']]}")
            if org_result['rule_created']:
                print(f"Assignment rule created: {org_result['rule_created']['name']}")
            if org_result['app_assignment_created']:
                print("Zscaler ZPA application assignment created")
        else:
            log.error(f"Failed to create partner organization: {org_result['errors']}")
            print(f"ERROR: Failed to create partner organization: {org_result['errors']}")
            return 5
    else:
        print(f"DEBUG: Using existing partner organization: {ticket.partner_company}")

    # Step 3: Create partner user
    print(f"DEBUG: Creating partner user: {ticket.partner_name}")
    
    user_id = okta.create_partner_user(
        partner_email=ticket.partner_email or "",
        partner_name=ticket.partner_name,
        filevine_email=ticket.filevine_email,
        partner_company=ticket.partner_company
    )
    
    if user_id:
        print(f"SUCCESS: Created partner user {ticket.partner_name} ({ticket.filevine_email}) with ID {user_id}")
        
        # Step 4: Assign ticket to Cody Atkinson and mark as resolved
        try:
            from jml_automation.services.solarwinds import SolarWindsService
            sw_service = SolarWindsService.from_config()
            
            # Use the original ticket ID from the ticket data
            ticket_id = ticket.ticket_id if hasattr(ticket, 'ticket_id') else raw.get('id')
            
            if ticket_id:
                success = sw_service.assign_and_resolve_ticket(str(ticket_id))
                if success:
                    print(f"SUCCESS: Assigned ticket {ticket_id} to Cody Atkinson and marked resolved")
                    log.info(f"Ticket {ticket_id} assigned and resolved successfully")
                else:
                    print(f"WARNING: Failed to assign/resolve ticket {ticket_id} - please do manually")
                    log.warning(f"Failed to assign/resolve ticket {ticket_id}")
            else:
                print(f"WARNING: No ticket ID available for assignment")
                log.warning(f"No ticket ID available for assignment")
        except Exception as e:
            print(f"WARNING: Error assigning ticket: {e} - please assign manually")
            log.warning(f"Error assigning ticket: {e}")
        
        log.info(f"Partner onboarding completed for {ticket.partner_name} at {ticket.partner_company}")
        return 0
    else:
        log.error(f"Failed to create partner user {ticket.partner_name}")
        print(f"ERROR: Failed to create partner user {ticket.partner_name}")
        return 6


if __name__ == "__main__":
    # Basic test
    run(ticket_id="test", dry_run=True)