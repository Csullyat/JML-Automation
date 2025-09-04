from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from jml_automation.parsers import parse_ticket, fetch_ticket
from jml_automation.models.ticket import TerminationTicket

log = logging.getLogger(__name__)


def _plan_from_ticket(ticket: TerminationTicket) -> list[str]:
    email = ticket.user.email if ticket.user else "<unknown>"
    transfer = ticket.transfer_to_email or "<missing>"
    steps = [
        f"Okta: clear sessions for {email}",
        f"Okta: deactivate user {email}",
        "Okta: remove SSO groups (Zoom, M365, Google, Domo, Lucid, Adobe, Workato)",
        f"Zoom: transfer recordings/data to {transfer}",
        "Google/M365: convert mailbox / delegate / license removal per SOP",
        "Domo/Lucid/Adobe/Workato: remove license or delete account",
        "Assets: Kandji/Intune inventory updates; SolarWinds asset status",
        "Security: rotate shared/group authenticators if applicable",
    ]
    # CJIS variants
    if ticket.cjis_cleared:
        steps.append("CJIS: ensure CJIS-related access removed within 24 hours")
    return steps


def run(
    *,
    ticket_id: Optional[str] = None,
    ticket_raw: Optional[Dict[str, Any]] = None,
    dry_run: bool = True,
    push_domo: bool = False,
) -> int:
    """
    Execute the termination workflow.
    - If ticket_raw is provided, use it (tests/smoke).
    - Else fetch by ticket_id (when fetch_ticket is wired).
    """
    if ticket_raw is None:
        if not ticket_id:
            log.error("Either ticket_raw or ticket_id must be provided.")
            return 2
        # TODO: wire API call in fetch_ticket
        raw = fetch_ticket(ticket_id)
    else:
        raw = ticket_raw

    ticket = parse_ticket(raw)
    if not isinstance(ticket, TerminationTicket):
        log.error("Parsed ticket is not a TerminationTicket (id=%s)", raw.get("id"))
        return 3

    plan = _plan_from_ticket(ticket)

    if dry_run:
        print("=== Termination plan ===")
        for s in plan:
            print(" -", s)
        return 0

    # TODO: call real adapters in order; collect results and handle errors.
    # Example skeleton:
    # okta = OktaService.from_config(...)
    # okta.clear_sessions(email)
    # okta.deactivate_user(email)
    # okta.remove_from_groups(email, groups=...)
    # ...
    # if push_domo: DomoService(...).send_metrics(...)
    return 0
