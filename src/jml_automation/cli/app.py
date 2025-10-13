#!/usr/bin/env python3
"""
JML Automation CLI - Main command line interface for employee lifecycle management.
Supports onboarding and termination workflows with various execution modes.
"""

import click
import sys
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

@click.group(help="JML Automation CLI (onboarding & termination)")
def cli():
    """JML Automation CLI - Employee lifecycle management automation."""
    pass

@cli.group(help="Onboarding workflows")
def onboard():
    """Employee onboarding automation commands."""
    pass

@cli.group(help="Termination workflows") 
def terminate():
    """Employee termination automation commands."""
    pass

# ========== ONBOARDING COMMANDS ==========

@onboard.command("run")
@click.option("--ticket-id", required=True, help="SolarWinds ticket ID(s) - can be single ticket or comma-separated list")
@click.option("--dry-run/--no-dry-run", default=True, help="Dry run mode (default: True)")
def onboard_run(ticket_id, dry_run):
    """Run onboarding for one or more tickets (comma-separated)."""
    
    # Parse ticket IDs (support both single and comma-separated)
    ticket_ids = [tid.strip() for tid in ticket_id.split(',')]
    
    if len(ticket_ids) == 1:
        click.echo(f" Running onboarding for ticket {ticket_ids[0]} (dry_run={dry_run})")
    else:
        click.echo(f" Running onboarding for {len(ticket_ids)} tickets (dry_run={dry_run})")
        click.echo(f" Tickets: {', '.join(ticket_ids)}")
    
    overall_success = True
    results = []
    
    try:
        from jml_automation.workflows.onboarding import run
        
        for i, tid in enumerate(ticket_ids, 1):
            if len(ticket_ids) > 1:
                click.echo(f"\n{'='*60}")
                click.echo(f" PROCESSING TICKET {i}/{len(ticket_ids)}: {tid}")
                click.echo(f"{'='*60}")
            
            try:
                result = run(
                    ticket_id=tid,
                    ticket_raw=None,
                    dry_run=dry_run,
                    push_domo=False
                )
                
                if result == 0:
                    click.echo(f"SUCCESS: Onboarding completed successfully for ticket {tid}")
                    results.append({'ticket': tid, 'success': True, 'result': result})
                else:
                    click.echo(f"ERROR: Onboarding failed for ticket {tid} with code {result}")
                    results.append({'ticket': tid, 'success': False, 'result': result})
                    overall_success = False
                    
            except Exception as e:
                click.echo(f"ERROR: Fatal error in onboarding for ticket {tid}: {e}")
                results.append({'ticket': tid, 'success': False, 'error': str(e)})
                overall_success = False
        
        # Summary for multiple tickets
        if len(ticket_ids) > 1:
            click.echo(f"\n{'='*60}")
            click.echo(f" BATCH ONBOARDING SUMMARY")
            click.echo(f"{'='*60}")
            
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            click.echo(f"Total tickets processed: {len(ticket_ids)}")
            click.echo(f"Successful: {len(successful)}")
            click.echo(f"Failed: {len(failed)}")
            
            if successful:
                click.echo(f"\nSuccessful tickets:")
                for r in successful:
                    click.echo(f"  SUCCESS: {r['ticket']}")
            
            if failed:
                click.echo(f"\nFailed tickets:")
                for r in failed:
                    error_info = r.get('error', f"Exit code {r.get('result', 'unknown')}")
                    click.echo(f"  ERROR: {r['ticket']} - {error_info}")
            
            click.echo(f"\nOverall result: {'SUCCESS' if overall_success else 'PARTIAL_SUCCESS'}")
        
        return 0 if overall_success else 1
        
    except Exception as e:
        click.echo(f"ERROR: Fatal error in batch onboarding: {e}")
        return 1

# ========== TERMINATION COMMANDS ==========

@terminate.command("run")
@click.option("--ticket-id", help="SolarWinds ticket ID(s) to process (single ticket or comma-separated list)")
@click.option("--user-email", help="Email of user to terminate directly")
@click.option("--manager-email", help="Email of manager for delegation")
@click.option("--phases", help="Comma-separated phases to run (okta,microsoft,google,zoom)")
@click.option("--test-mode/--production-mode", default=True, help="Test mode (default: True)")
def terminate_run(ticket_id: Optional[str], user_email: Optional[str], manager_email: Optional[str], phases: Optional[str], test_mode: bool):
    """Run termination for a ticket or user with multi-phase support."""
    
    # Validate input
    if not ticket_id and not user_email:
        click.echo("ERROR: Error: Must provide either --ticket-id or --user-email")
        sys.exit(1)
    
    # Parse phases if provided
    phase_list = None
    if phases:
        phase_list = [p.strip() for p in phases.split(',')]
        click.echo(f" Phases to execute: {', '.join(phase_list)}")
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        
        workflow = TerminationWorkflow()
        
        if test_mode:
            click.echo("TEST: TEST MODE: Multi-phase termination")
        else:
            click.echo(" PRODUCTION MODE: Multi-phase termination")
        
        if user_email:
            # Direct user termination
            click.echo(f" Running multi-phase termination for {user_email}")
            results = workflow.execute_multi_phase_termination(
                user_email=user_email,
                manager_email=manager_email,
                phases=phase_list,
                ticket_id=ticket_id
            )
            
                        if results and results.get('overall_success'):
                click.echo("SUCCESS: Termination completed successfully")
                return 0
            else:
                click.echo("WARNING: Termination completed with issues")
                return 1
        else:
            # Ticket-based termination - support multiple tickets
            # Check if multiple tickets provided (comma-separated)
            if ',' in ticket_id:
                # Multiple tickets mode
                click.echo(f" Running full multi-phase termination for multiple tickets: {ticket_id}")
                
                from jml_automation.workflows.termination import TerminationWorkflow
                workflow = TerminationWorkflow()
                
                if test_mode:
                    click.echo("TEST: TEST MODE: Multiple ticket termination (showing plan only)")
                    ticket_list = [tid.strip() for tid in ticket_id.split(',')]
                    print("=== Multiple Ticket Termination Plan ===")
                    print(f"Tickets: {', '.join(ticket_list)}")
                    print(f"Total tickets: {len(ticket_list)}")
                    print("\nFor each ticket, will execute:")
                    print(" 1. Fetch ticket from SolarWinds")
                    print(" 2. Extract user and manager emails")
                    print(" 3. Run full 9-step termination workflow")
                    print(" 4. Update ticket status")
                    print("\nPhases per ticket:")
                    print(" - Okta: Clear sessions & deactivate user")
                    print(" - Google Workspace: Suspend user & transfer data")
                    print(" - Microsoft 365: Convert mailbox & remove licenses")
                    print(" - Zoom: Remove user")
                    print(" - Domo: Remove user (if in groups)")
                    print(" - Lucidchart: Remove user (if in groups)")
                    print(" - Workato: Remove user (if in groups)")
                    print(" - SynQ Prox: Remove user")
                    print(" - Remove from app-specific Okta groups")
                    return 0
                else:
                    click.echo(" PRODUCTION MODE: Multiple ticket termination")
                    click.echo("WARNING: This will perform actual termination for ALL tickets!")
                    
                    results = workflow.execute_multiple_ticket_terminations(ticket_id)
                    
                    # Display results
                    click.echo("\n=== MULTIPLE TICKET TERMINATION RESULTS ===")
                    click.echo(f"Total tickets: {results['total_tickets']}")
                    click.echo(f"Successful: {results['successful_tickets']}")
                    click.echo(f"Failed: {results['failed_tickets']}")
                    click.echo(f"Success rate: {results.get('success_rate', 0):.1f}%")
                    click.echo(f"Duration: {results.get('duration', 0):.1f} seconds")
                    
                    click.echo("\nIndividual results:")
                    for tid, result in results['ticket_results'].items():
                        status = "SUCCESS" if result.get('overall_success') else "FAILED"
                        user = result.get('user_email', 'Unknown')
                        error_count = len(result.get('errors', []))
                        click.echo(f"  {status}: Ticket {tid} - {user} ({error_count} errors)")
                    
                    if results.get('success'):
                        click.echo("\nSUCCESS: Multiple ticket termination completed successfully")
                        return 0
                    else:
                        click.echo("\nWARNING: Multiple ticket termination completed with issues")
                        return 1
            else:
                # Single ticket mode (existing functionality)
                click.echo(f" Running full multi-phase termination for ticket {ticket_id}")
                from jml_automation.workflows.termination import TerminationWorkflow
                
                workflow = TerminationWorkflow()
            
            # Parse ticket to get user details
            from jml_automation.parsers.solarwinds_parser import fetch_ticket, parse_ticket
            try:
                raw_ticket = fetch_ticket(ticket_id)
                ticket = parse_ticket(raw_ticket)
                
                if hasattr(ticket, 'user') and ticket.user:
                    user_email = ticket.user.email
                else:
                    # Extract email from raw ticket if parsing fails
                    from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket
                    user_email = extract_user_email_from_ticket(raw_ticket)
                
                if hasattr(ticket, 'manager') and ticket.manager:
                    manager_email = ticket.manager.email
                else:
                    # Extract manager email from raw ticket if parsing fails
                    from jml_automation.parsers.solarwinds_parser import extract_manager_email_from_ticket
                    manager_email = extract_manager_email_from_ticket(raw_ticket)
                
                if not user_email:
                    click.echo("ERROR: Could not extract user email from ticket")
                    return 1
                
                click.echo(f" User: {user_email}")
                click.echo(f" Manager: {manager_email or 'Not specified'}")
                
                # Run full multi-phase termination with all services
                if test_mode:
                    click.echo(" Running dry run of full 9-step termination workflow")
                    # Show the plan but don't execute
                    print("=== Full Termination Plan ===")
                    print(f"User: {user_email}")
                    print(f"Ticket: {ticket_id}")
                    print(f"Manager: {manager_email or 'Not specified'}")
                    print("\nPhases:")
                    print(" 1. Okta: Clear sessions & deactivate user")
                    print(" 2. Google Workspace: Suspend user & transfer data")
                    print(" 3. Microsoft 365: Convert mailbox & remove licenses")
                    print(" 4. Adobe: Remove licenses")
                    print(" 5. Zoom: Remove user")
                    print(" 6. Domo: Remove user")
                    print(" 7. Lucidchart: Remove user")
                    print(" 8. Workato: Remove user")
                    print(" 9. SynQ Prox: Remove user")
                    print("10. Remove from app-specific Okta groups")
                    print("11. SolarWinds: Update ticket to 'In Progress'")
                    return 0
                else:
                    click.echo(" Running LIVE multi-phase termination")
                    click.echo("")
                    
                    # Run with progress callback
                    def progress_callback(step: str, status: str, details: str = ""):
                        if status == "starting":
                            click.echo(f"{step}...")
                        elif status == "success":
                            click.echo(f"{step} - SUCCESS")
                            if details:
                                click.echo(f"   -> {details}")
                        elif status == "error":
                            click.echo(f"{step} - ERROR")
                            if details:
                                click.echo(f"   -> {details}")
                        elif status == "warning":
                            click.echo(f"{step} - WARNING")
                            if details:
                                click.echo(f"   -> {details}")
                        elif status == "skipped":
                            click.echo(f"{step} - SKIPPED")
                            if details:
                                click.echo(f"   -> {details}")
                    
                    results = workflow.execute_multi_phase_termination(
                        user_email=user_email,
                        manager_email=manager_email,
                        ticket_id=ticket_id,
                        progress_callback=progress_callback
                    )
                    
                    click.echo("")
                    click.echo("=== TERMINATION SUMMARY ===")
                    
                    if results:
                        # Show phase results
                        for phase in ["okta", "google", "microsoft", "adobe", "zoom", "domo", "lucidchart", "workato", "synqprox"]:
                            if phase in results.get("phase_success", {}):
                                success = results["phase_success"][phase]
                                icon = "PASS" if success else "FAIL"
                                click.echo(f"{icon} {phase.title()}: {'SUCCESS' if success else 'FAILED'}")
                        
                        # Show errors if any
                        if results.get("errors"):
                            click.echo("")
                            click.echo("ERRORS ENCOUNTERED:")
                            for error in results["errors"]:
                                click.echo(f"   • {error}")
                        
                        # Show warnings if any  
                        if results.get("warnings"):
                            click.echo("")
                            click.echo("WARNINGS:")
                            for warning in results["warnings"]:
                                click.echo(f"   • {warning}")
                        
                        click.echo("")
                        if results.get('overall_success'):
                            click.echo("SUCCESS: Multi-phase termination completed successfully")
                            return 0
                        else:
                            click.echo("WARNING: Multi-phase termination completed with issues")
                            return 1
                    else:
                        click.echo("ERROR: Multi-phase termination failed to return results")
                        return 1
                        
            except Exception as parse_error:
                click.echo(f"ERROR: Failed to parse ticket: {parse_error}")
                return 1
            
    except Exception as e:
        click.echo(f"ERROR: Fatal error in termination: {e}")
        logger.error(f"Termination CLI error: {e}")
        return 1

@terminate.command("test")
@click.argument("user_email")
@click.option("--manager-email", help="Email of manager for delegation")
def terminate_test(user_email: str, manager_email: Optional[str]):
    """Test termination readiness for a specific user."""
    click.echo(f"TEST: Running termination readiness test for {user_email}")
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        
        workflow = TerminationWorkflow()
        results = workflow.test_termination(user_email, manager_email)
        
        click.echo(f"\nTEST: TEST MODE RESULTS for {user_email}")
        click.echo(f"Overall Ready: {'SUCCESS: YES' if results['overall_ready'] else 'ERROR: NO'}")
        click.echo(f"\nWould Execute:")
        for action in results['would_execute']:
            click.echo(f"  SUCCESS: {action}")
        click.echo(f"\nPotential Issues:")
        for issue in results['potential_issues']:
            click.echo(f"  WARNING: {issue}")
        
        sys.exit(0 if results['overall_ready'] else 1)
        
    except Exception as e:
        click.echo(f"ERROR: Fatal error in test mode: {e}")
        logger.error(f"Termination test error: {e}")
        sys.exit(1)

@terminate.command("synqprox")
@click.argument("ticket_id")
def terminate_synqprox(ticket_id: str):
    """Test SYNQ Prox deletion for a specific ticket."""
    click.echo(f"TEST: Testing SYNQ Prox deletion for ticket {ticket_id}")
    
    try:
        # Fetch the ticket to get user email
        from jml_automation.services.solarwinds import SolarWindsService
        from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket
        from jml_automation.services.synqprox import SynqProxService
        
        solarwinds = SolarWindsService.from_config()
        ticket = solarwinds.fetch_ticket(ticket_id)
        
        if not ticket:
            click.echo(f"ERROR: Ticket {ticket_id} not found")
            sys.exit(1)
        
        user_email = extract_user_email_from_ticket(ticket)
        if not user_email:
            click.echo(f"ERROR: Could not extract user email from ticket {ticket_id}")
            sys.exit(1)
        
        click.echo(f"SUCCESS: Found user email: {user_email}")
        click.echo(f" Testing SYNQ Prox deletion...")
        
        # Test SYNQ Prox deletion
        synqprox = SynqProxService()
        result = synqprox.execute_termination(user_email)
        
        if result:
            click.echo(f"SUCCESS: SYNQ Prox deletion test successful for {user_email}")
            click.echo(" User deleted successfully from SYNQ Prox")
            sys.exit(0)
        else:
            click.echo(f"ERROR: SYNQ Prox deletion test failed for {user_email}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"ERROR: Fatal error in SYNQ Prox test: {e}")
        logger.error(f"SYNQ Prox test error: {e}")
        sys.exit(1)

@terminate.command("batch")
@click.option("--test-mode/--production-mode", default=True, help="Test mode processes only first ticket")
def terminate_batch(test_mode: bool):
    """Process all termination tickets in batch mode."""
    
    if test_mode:
        click.echo("TEST: TEST MODE: Processing first termination ticket only")
    else:
        click.echo(" PRODUCTION MODE: Processing all termination tickets")
        click.echo("Phases: Okta → Microsoft → Google → Zoom → Notifications")
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        
        workflow = TerminationWorkflow()
        
        if test_mode:
            # Test mode - process only first ticket
            tickets = workflow.solarwinds.fetch_termination_tickets()
            if not tickets:
                click.echo("No termination tickets found.")
                return 0
            
            ticket = tickets[0]
            from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, extract_manager_email_from_ticket
            
            user_email = extract_user_email_from_ticket(ticket)
            manager_email = extract_manager_email_from_ticket(ticket)
            ticket_id = ticket.get('ticket_id')
            
            if not user_email:
                click.echo(f"ERROR: Could not extract user email from ticket {ticket_id}")
                return 1
            
            click.echo(f"TEST: TEST MODE: Processing multi-phase termination for {user_email}")
            results = workflow.execute_multi_phase_termination(user_email, manager_email, ticket_id=ticket_id)
            
            if results['overall_success']:
                click.echo(f"SUCCESS: TEST termination successful for {user_email}")
                click.echo("\nTEST: Test mode completed. Review logs and results.")
                click.echo(" To run in production mode, use --production-mode")
                return 0
            else:
                click.echo(f"WARNING: TEST termination had issues for {user_email}")
                return 1
        else:
            # Production mode - process all tickets
            workflow.run_batch_processing()
            click.echo("SUCCESS: Batch termination processing completed")
            return 0
            
    except KeyboardInterrupt:
        click.echo("\nWARNING: Termination automation interrupted by user")
        return 130
    except Exception as e:
        click.echo(f"ERROR: Fatal error in batch termination: {e}")
        logger.error(f"Batch termination error: {e}")
        return 1

@terminate.command("ticket")
@click.argument("ticket_id")
@click.option("--dry-run/--execute", default=True, help="Dry run mode (default) vs actual execution")
@click.option("--confirm", is_flag=True, help="Confirm actual termination (required for --execute)")
def terminate_ticket(ticket_id: str, dry_run: bool, confirm: bool):
    """Process a single termination ticket with dry-run or execution mode."""
    
    if not dry_run and not confirm:
        click.echo("ERROR: Actual termination requires --confirm flag for safety!")
        click.echo("Examples:")
        click.echo(f"  jml terminate ticket {ticket_id}                    # Dry run (safe)")
        click.echo(f"  jml terminate ticket {ticket_id} --execute --confirm # Actual termination")
        return 1
    
    try:
        from jml_automation.workflows.single_ticket import SingleTicketWorkflow
        workflow = SingleTicketWorkflow()
        
        if dry_run:
            # DRY RUN MODE
            click.echo(f"DRY RUN: Testing connectivity for ticket {ticket_id}")
            click.echo("(No actual termination will occur)")
            
            results = workflow.execute_single_ticket_dry_run(ticket_id)
            workflow.print_dry_run_summary(results)
            
            return 0 if results['overall_success'] else 1
        else:
            # PRODUCTION MODE
            click.echo(f"PRODUCTION: Executing termination for ticket {ticket_id}")
            click.echo("WARNING: This will perform actual user termination!")
            
            # Double confirmation for safety
            confirm_input = click.prompt("Type 'TERMINATE' to confirm", type=str)
            if confirm_input != 'TERMINATE':
                click.echo("Termination cancelled.")
                return 1
            
            results = workflow.execute_single_ticket_production(ticket_id)
            workflow.print_production_summary(results)
            
            return 0 if results['overall_success'] else 1
        
    except Exception as e:
        mode = "dry run" if dry_run else "production termination"
        click.echo(f"ERROR: Fatal error in {mode}: {e}")
        logger.error(f"Single ticket {mode} error: {e}")
        return 1

if __name__ == "__main__":
    cli()
