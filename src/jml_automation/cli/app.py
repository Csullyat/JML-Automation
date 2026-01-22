#!/usr/bin/env python3
"""
JML Automation CLI - Employee lifecycle management.

Commands:
    jml onboard <ticket_id>     Onboard new employee(s)
    jml terminate <ticket_id>   Terminate employee(s)
    jml partner <ticket_id>     Onboard partner
"""

import click
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

def _find_project_root() -> Path:
    """Find project root by looking for pyproject.toml"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return Path(__file__).parent.parent.parent.parent.resolve()

# Resolve paths relative to project root, not cwd
PROJECT_ROOT = _find_project_root()

logger = logging.getLogger(__name__)


@click.group(help="""
JML Automation - Filevine Employee Lifecycle Management

\b
Quick Start:
  jml onboard 78513              Onboard (dry-run)
  jml onboard 78513 --live       Onboard (execute)
  jml terminate 78500            Terminate (dry-run)
  jml terminate 78500 --live     Terminate (execute)
  jml partner 78600              Partner onboard (dry-run)

\b
Batch Operations:
  jml onboard 78513,78514,78515  Multiple tickets
  jml terminate batch            All pending terminations
""")
@click.version_option(version="1.0.0", prog_name="jml")
def cli():
    pass


# ========== ONBOARD ==========

@cli.command("onboard")
@click.argument("ticket_id")
@click.option("--live", is_flag=True, help="Execute for real (default is dry-run)")
def onboard(ticket_id: str, live: bool):
    """
    Onboard new employee(s) from SolarWinds ticket.

    \b
    Examples:
      jml onboard 78513              # Dry-run single ticket
      jml onboard 78513 --live       # Execute single ticket
      jml onboard 78513,78514        # Multiple tickets (comma-separated)
    """
    dry_run = not live
    ticket_ids = [tid.strip() for tid in ticket_id.split(',')]
    
    mode = "DRY-RUN" if dry_run else "LIVE"
    if len(ticket_ids) == 1:
        click.echo(f"[{mode}] Onboarding ticket {ticket_ids[0]}")
    else:
        click.echo(f"[{mode}] Onboarding {len(ticket_ids)} tickets: {', '.join(ticket_ids)}")
    
    try:
        from jml_automation.workflows.onboarding import run
        
        results = []
        for i, tid in enumerate(ticket_ids, 1):
            if len(ticket_ids) > 1:
                click.echo(f"\n{'='*50}")
                click.echo(f"[{i}/{len(ticket_ids)}] Ticket {tid}")
                click.echo('='*50)
            
            try:
                result = run(ticket_id=tid, ticket_raw=None, dry_run=dry_run, push_domo=False)
                success = result == 0
                results.append({'ticket': tid, 'success': success})
                
                if success:
                    click.echo(click.style(f"✓ Ticket {tid} completed", fg="green"))
                else:
                    click.echo(click.style(f"✗ Ticket {tid} failed (code {result})", fg="red"))
            except Exception as e:
                click.echo(click.style(f"✗ Ticket {tid} error: {e}", fg="red"))
                results.append({'ticket': tid, 'success': False})
        
        # Summary for batch
        if len(ticket_ids) > 1:
            _print_batch_summary(results, "Onboarding")
        
        return 0 if all(r['success'] for r in results) else 1
        
    except Exception as e:
        click.echo(click.style(f"Fatal error: {e}", fg="red"))
        return 1


# ========== TERMINATE ==========

@cli.command("terminate")
@click.argument("ticket_id", required=False)
@click.option("--live", is_flag=True, help="Execute for real (default is dry-run)")
@click.option("--user", "user_email", help="Terminate by email instead of ticket")
@click.option("--manager", "manager_email", help="Manager email for delegation")
@click.option("--phases", help="Specific phases: okta,microsoft,google,zoom")
def terminate(ticket_id: Optional[str], live: bool, user_email: Optional[str], 
              manager_email: Optional[str], phases: Optional[str]):
    """
    Terminate employee(s) from SolarWinds ticket.

    \b
    Examples:
      jml terminate 78500                    # Dry-run from ticket
      jml terminate 78500 --live             # Execute from ticket  
      jml terminate --user jane@company.com  # Direct termination
      jml terminate 78500,78501 --live       # Multiple tickets
    """
    if not ticket_id and not user_email:
        click.echo(click.style("Error: Provide ticket_id or --user email", fg="red"))
        sys.exit(1)
    
    dry_run = not live
    mode = "DRY-RUN" if dry_run else "LIVE"
    phase_list = [p.strip() for p in phases.split(',')] if phases else None
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        workflow = TerminationWorkflow()
        
        # Direct user termination
        if user_email:
            click.echo(f"[{mode}] Terminating {user_email}")
            if dry_run:
                _print_termination_plan(user_email, manager_email, None)
                return 0
            
            results = workflow.execute_multi_phase_termination(
                user_email=user_email,
                manager_email=manager_email,
                phases=phase_list,
                ticket_id=ticket_id
            )
            return _handle_termination_result(results)
        
        # Ticket-based termination
        ticket_ids = [tid.strip() for tid in ticket_id.split(',')]
        
        if len(ticket_ids) == 1:
            click.echo(f"[{mode}] Terminating from ticket {ticket_ids[0]}")
            return _terminate_single_ticket(workflow, ticket_ids[0], manager_email, phase_list, dry_run)
        else:
            click.echo(f"[{mode}] Terminating {len(ticket_ids)} tickets")
            return _terminate_multiple_tickets(workflow, ticket_ids, phase_list, dry_run)
            
    except Exception as e:
        click.echo(click.style(f"Fatal error: {e}", fg="red"))
        logger.error(f"Termination error: {e}")
        return 1


@cli.command("terminate-batch")
@click.option("--live", is_flag=True, help="Execute for real (default is dry-run)")
def terminate_batch(live: bool):
    """
    Process all pending termination tickets.

    \b
    Examples:
      jml terminate-batch          # Dry-run first ticket
      jml terminate-batch --live   # Process all tickets
    """
    dry_run = not live
    mode = "DRY-RUN (first ticket only)" if dry_run else "LIVE (all tickets)"
    click.echo(f"[{mode}] Batch termination")
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, extract_manager_email_from_ticket
        
        workflow = TerminationWorkflow()
        tickets = workflow.solarwinds.fetch_termination_tickets()
        
        if not tickets:
            click.echo("No termination tickets found.")
            return 0
        
        click.echo(f"Found {len(tickets)} termination ticket(s)")
        
        if dry_run:
            ticket = tickets[0]
            user_email = extract_user_email_from_ticket(ticket)
            manager_email = extract_manager_email_from_ticket(ticket)
            ticket_id = ticket.get('ticket_id')
            
            click.echo(f"\nProcessing first ticket: {ticket_id}")
            _print_termination_plan(user_email, manager_email, ticket_id)
            return 0
        else:
            workflow.run_batch_processing()
            click.echo(click.style("✓ Batch processing complete", fg="green"))
            return 0
            
    except Exception as e:
        click.echo(click.style(f"Fatal error: {e}", fg="red"))
        return 1


# ========== PARTNER ==========

@cli.command("partner")
@click.argument("ticket_id")
@click.option("--live", is_flag=True, help="Execute for real (default is dry-run)")
def partner(ticket_id: str, live: bool):
    """
    Onboard partner from SolarWinds ticket.

    \b
    Examples:
      jml partner 78600          # Dry-run
      jml partner 78600 --live   # Execute
    """
    dry_run = not live
    mode = "DRY-RUN" if dry_run else "LIVE"
    click.echo(f"[{mode}] Partner onboarding for ticket {ticket_id}")
    
    try:
        from jml_automation.workflows.partner_onboarding import run
        
        result = run(ticket_id=ticket_id, ticket_raw=None, dry_run=dry_run)
        
        if result == 0:
            click.echo(click.style(f"✓ Partner onboarding completed", fg="green"))
            return 0
        else:
            click.echo(click.style(f"✗ Partner onboarding failed (code {result})", fg="red"))
            return result
            
    except Exception as e:
        click.echo(click.style(f"Fatal error: {e}", fg="red"))
        return 1


# ========== HELPERS ==========

def _print_batch_summary(results: list, operation: str):
    """Print summary for batch operations."""
    click.echo(f"\n{'='*50}")
    click.echo(f"{operation} Summary")
    click.echo('='*50)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    click.echo(f"Total: {len(results)} | Success: {len(successful)} | Failed: {len(failed)}")
    
    if failed:
        click.echo("\nFailed tickets:")
        for r in failed:
            click.echo(f"  ✗ {r['ticket']}")


def _print_termination_plan(user_email: str, manager_email: Optional[str], ticket_id: Optional[str]):
    """Print what would happen in a termination."""
    click.echo("\n=== Termination Plan ===")
    click.echo(f"User: {user_email}")
    if ticket_id:
        click.echo(f"Ticket: {ticket_id}")
    if manager_email:
        click.echo(f"Manager: {manager_email}")
    click.echo("\nPhases:")
    click.echo("  1. Okta: Clear sessions & deactivate")
    click.echo("  2. Google: Suspend & transfer data")
    click.echo("  3. Microsoft 365: Convert mailbox & remove licenses")
    click.echo("  4. Adobe: Remove licenses")
    click.echo("  5. Zoom: Remove user")
    click.echo("  6. Domo: Remove user")
    click.echo("  7. Lucidchart: Remove user")
    click.echo("  8. Workato: Remove user")
    click.echo("  9. SynQ Prox: Remove user")
    click.echo(" 10. Remove from app-specific Okta groups")
    click.echo(" 11. Update SolarWinds ticket")
    click.echo("\nRun with --live to execute.")


def _terminate_single_ticket(workflow, ticket_id: str, manager_email: Optional[str], 
                             phase_list: Optional[list], dry_run: bool) -> int:
    """Handle single ticket termination."""
    from jml_automation.parsers.solarwinds_parser import fetch_ticket, parse_ticket
    
    raw_ticket = fetch_ticket(ticket_id)
    ticket = parse_ticket(raw_ticket)
    
    if hasattr(ticket, 'user') and ticket.user and ticket.user.email:
        user_email = ticket.user.email
    else:
        user_email = workflow.resolve_user_email_from_ticket(raw_ticket)
    
    if not manager_email:
        manager_email = workflow.resolve_manager_email_from_ticket(raw_ticket)
    
    if not user_email:
        click.echo(click.style("Error: Could not extract user email", fg="red"))
        return 1
    
    click.echo(f"User: {user_email}")
    click.echo(f"Manager: {manager_email or 'Not specified'}")
    
    if dry_run:
        _print_termination_plan(user_email, manager_email, ticket_id)
        return 0
    
    results = workflow.execute_multi_phase_termination(
        user_email=user_email,
        manager_email=manager_email,
        phases=phase_list,
        ticket_id=ticket_id
    )
    return _handle_termination_result(results)


def _terminate_multiple_tickets(workflow, ticket_ids: list, phase_list: Optional[list], dry_run: bool) -> int:
    """Handle multiple ticket termination."""
    from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, extract_manager_email_from_ticket
    import time
    
    if dry_run:
        click.echo(f"\nWould process {len(ticket_ids)} tickets:")
        for tid in ticket_ids:
            click.echo(f"  • {tid}")
        _print_termination_plan("<user_from_ticket>", "<manager_from_ticket>", "each ticket")
        return 0
    
    results = []
    for i, tid in enumerate(ticket_ids, 1):
        click.echo(f"\n{'='*50}")
        click.echo(f"[{i}/{len(ticket_ids)}] Ticket {tid}")
        click.echo('='*50)
        
        try:
            raw_ticket = workflow.solarwinds.fetch_ticket(tid)
            if not raw_ticket:
                raise Exception(f"Ticket not found")
            
            user_email = extract_user_email_from_ticket(raw_ticket)
            manager_email = extract_manager_email_from_ticket(raw_ticket)
            
            if not user_email:
                raise Exception("Could not extract user email")
            
            click.echo(f"User: {user_email}")
            
            result = workflow.execute_multi_phase_termination(
                user_email=user_email,
                manager_email=manager_email,
                phases=phase_list,
                ticket_id=tid
            )
            
            success = result.get('overall_success', False)
            results.append({'ticket': tid, 'success': success})
            
            if success:
                click.echo(click.style(f"✓ Ticket {tid} completed", fg="green"))
            else:
                click.echo(click.style(f"✗ Ticket {tid} had issues", fg="yellow"))
            
            if i < len(ticket_ids):
                time.sleep(3)
                
        except Exception as e:
            click.echo(click.style(f"✗ Ticket {tid} error: {e}", fg="red"))
            results.append({'ticket': tid, 'success': False})
    
    _print_batch_summary(results, "Termination")
    return 0 if all(r['success'] for r in results) else 1


def _handle_termination_result(results: dict) -> int:
    """Handle and display termination results."""
    if not results:
        click.echo(click.style("✗ No results returned", fg="red"))
        return 1
    
    click.echo("\n=== Results ===")
    for phase in ["okta", "google", "microsoft", "adobe", "zoom", "domo", "lucidchart", "workato", "synqprox"]:
        if phase in results.get("phase_success", {}):
            success = results["phase_success"][phase]
            icon = click.style("✓", fg="green") if success else click.style("✗", fg="red")
            click.echo(f"{icon} {phase.title()}")
    
    if results.get("errors"):
        click.echo("\nErrors:")
        for error in results["errors"]:
            click.echo(f"  • {error}")
    
    if results.get('overall_success'):
        click.echo(click.style("\n✓ Termination completed successfully", fg="green"))
        return 0
    else:
        click.echo(click.style("\n⚠ Termination completed with issues", fg="yellow"))
        return 1


def get_project_root() -> Path:
    """Get the project root directory."""
    return PROJECT_ROOT


if __name__ == "__main__":
    cli()