#!/usr/bin/env python3
"""
JML Automation CLI - Main command line interface for employee lifecycle management.
Supports onboarding and termination workflows with various execution modes.
"""

import click
import sys
import logging
import time
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
@click.option("--ticket-id", help="SolarWinds ticket ID(s) to process (single or comma-separated)")
@click.option("--user-email", help="Email of user to terminate directly")
@click.option("--manager-email", help="Email of manager for delegation")
@click.option("--phases", help="Comma-separated phases to run (okta,microsoft,google,zoom)")
@click.option("--test-mode/--production-mode", default=True, help="Test mode (default: True)")
def terminate_run(ticket_id: Optional[str], user_email: Optional[str], manager_email: Optional[str], phases: Optional[str], test_mode: bool):
    """Run termination for a ticket or user with multi-phase support."""
    
    # Validate input
    if not ticket_id and not user_email:
        click.echo("ERROR: Must provide either --ticket-id or --user-email")
        sys.exit(1)
    
    # Parse phases if provided
    phase_list = None
    if phases:
        phase_list = [p.strip() for p in phases.split(',')]
        click.echo(f" Phases to execute: {', '.join(phase_list)}")
    
    # Import TerminationWorkflow
    from jml_automation.workflows.termination import TerminationWorkflow
    workflow = TerminationWorkflow()
    
    # Print mode
    if test_mode:
        click.echo("TEST MODE: Multi-phase termination")
    else:
        click.echo("PRODUCTION MODE: Multi-phase termination")
    
    # Handle user email direct termination
    if user_email:
        click.echo(f" Running multi-phase termination for {user_email}")
        
        results = workflow.execute_multi_phase_termination(
            user_email=user_email,
            manager_email=manager_email,
            phases=phase_list,
            ticket_id=ticket_id
        )
        
        success = results and results.get('overall_success', False)
        click.echo("SUCCESS: Termination completed successfully" if success else "WARNING: Termination completed with issues")
        return 0 if success else 1
    
    # Handle ticket-based termination
    # Check for multiple tickets
    if ticket_id and ',' in ticket_id:
        # Parse comma-separated tickets
        ticket_list = [t.strip() for t in ticket_id.split(',') if t.strip()]
        click.echo(f" Processing {len(ticket_list)} tickets: {', '.join(ticket_list)}")
        
        if test_mode:
            # Show plan for multiple tickets
            click.echo("\nTEST MODE: Multiple ticket termination plan")
            click.echo(f"Tickets to process: {', '.join(ticket_list)}")
            click.echo("\nFor each ticket, would execute:")
            click.echo("1. Fetch ticket data from SolarWinds")
            click.echo("2. Extract user and manager emails")
            click.echo("3. Run complete multi-phase termination workflow")
            click.echo("4. Update ticket status")
            return 0
        
        # Production mode - actually process all tickets
        click.echo("\nPRODUCTION MODE: Processing multiple tickets")
        click.echo("WARNING: This will execute actual termination for all tickets!")
        
        # Process each ticket
        results = []
        success_count = 0
        failure_count = 0
        
        for i, tid in enumerate(ticket_list, 1):
            click.echo(f"\n{'='*60}")
            click.echo(f" PROCESSING TICKET {i}/{len(ticket_list)}: {tid}")
            click.echo(f"{'='*60}")
            
            try:
                # Fetch ticket info
                from jml_automation.parsers.solarwinds_parser import fetch_ticket, extract_user_email_from_ticket, extract_manager_email_from_ticket
                
                # Fetch the ticket
                ticket_data = fetch_ticket(tid)
                if not ticket_data:
                    click.echo(f"ERROR: Could not fetch ticket {tid}")
                    results.append({"ticket": tid, "success": False, "error": "Ticket not found"})
                    failure_count += 1
                    continue
                
                # Extract user and manager emails
                user_email = extract_user_email_from_ticket(ticket_data)
                manager_email = extract_manager_email_from_ticket(ticket_data)
                
                if not user_email:
                    click.echo(f"ERROR: Could not extract user email from ticket {tid}")
                    results.append({"ticket": tid, "success": False, "error": "User email not found"})
                    failure_count += 1
                    continue
                
                click.echo(f" User to terminate: {user_email}")
                click.echo(f" Manager: {manager_email or 'Not specified'}")
                
                # Define progress callback
                def progress_callback(step: str, status: str, details: str = ""):
                    if status == "starting":
                        click.echo(f"{step}...")
                    elif status == "success":
                        click.echo(f"{step} - SUCCESS")
                        if details:
                            click.echo(f"   └─ {details}")
                    elif status == "error":
                        click.echo(f"{step} - ERROR")
                        if details:
                            click.echo(f"   └─ {details}")
                    elif status == "warning":
                        click.echo(f"{step} - WARNING")
                        if details:
                            click.echo(f"   └─ {details}")
                    elif status == "skipped":
                        click.echo(f"{step} - SKIPPED")
                        if details:
                            click.echo(f"   └─ {details}")
                
                # Execute termination for this ticket
                termination_result = workflow.execute_multi_phase_termination(
                    user_email=user_email,
                    manager_email=manager_email,
                    ticket_id=tid,
                    progress_callback=progress_callback
                )
                
                # Track result
                ticket_success = termination_result and termination_result.get('overall_success', False)
                if ticket_success:
                    success_count += 1
                    click.echo(f"SUCCESS: Termination completed successfully for ticket {tid}")
                    results.append({"ticket": tid, "user": user_email, "success": True})
                else:
                    failure_count += 1
                    errors = termination_result.get('errors', [])
                    error_count = len(errors)
                    click.echo(f"WARNING: Termination completed with {error_count} issues for ticket {tid}")
                    results.append({"ticket": tid, "user": user_email, "success": False, "errors": errors})
                
                # Pause between tickets
                if i < len(ticket_list):
                    click.echo(f"Pausing 3 seconds before next ticket...")
                    time.sleep(3)
                
            except Exception as e:
                click.echo(f"ERROR: Fatal error processing ticket {tid}: {e}")
                results.append({"ticket": tid, "success": False, "error": str(e)})
                failure_count += 1
        
        # Show summary for multiple tickets
        click.echo(f"\n{'='*60}")
        click.echo(f" MULTIPLE TICKET TERMINATION SUMMARY")
        click.echo(f"{'='*60}")
        click.echo(f"Total tickets processed: {len(ticket_list)}")
        click.echo(f"Successful: {success_count}")
        click.echo(f"Failed: {failure_count}")
        
        # Show detailed results
        if results:
            successful = [r for r in results if r.get('success')]
            failed = [r for r in results if not r.get('success')]
            
            if successful:
                click.echo(f"\nSuccessful tickets:")
                for r in successful:
                    click.echo(f"  SUCCESS: Ticket {r['ticket']} - {r.get('user', 'Unknown user')}")
            
            if failed:
                click.echo(f"\nFailed tickets:")
                for r in failed:
                    error_info = r.get('error', 'Unknown error')
                    click.echo(f"  FAILED: Ticket {r['ticket']} - {r.get('user', 'Unknown user')} - {error_info}")
        
        # Return success if at least one ticket succeeded
        return 0 if success_count > 0 else 1
    
    # Process single ticket
    click.echo(f" Processing single ticket: {ticket_id}")
    
    # Process the single ticket
    try:
        # Fetch ticket info
        from jml_automation.parsers.solarwinds_parser import fetch_ticket, parse_ticket, extract_user_email_from_ticket, extract_manager_email_from_ticket
        
        ticket_data = fetch_ticket(ticket_id)
        if not ticket_data:
            click.echo(f"ERROR: Could not fetch ticket {ticket_id}")
            return 1
        
        # Try to parse ticket object
        ticket = None
        try:
            ticket = parse_ticket(ticket_data)
        except Exception as parse_error:
            click.echo(f"WARNING: Could not parse ticket object: {parse_error}")
        
        # Get user and manager emails
        if ticket and hasattr(ticket, 'user') and ticket.user:
            user_email = ticket.user.email
        else:
            user_email = extract_user_email_from_ticket(ticket_data)
        
        if ticket and hasattr(ticket, 'manager') and ticket.manager:
            manager_email = ticket.manager.email
        else:
            manager_email = extract_manager_email_from_ticket(ticket_data)
        
        if not user_email:
            click.echo(f"ERROR: Could not extract user email from ticket {ticket_id}")
            return 1
        
        click.echo(f" User to terminate: {user_email}")
        click.echo(f" Manager: {manager_email or 'Not specified'}")
        
        if test_mode:
            # Show plan
            click.echo("\nTEST MODE: Termination plan")
            click.echo(f"User: {user_email}")
            click.echo(f"Ticket: {ticket_id}")
            click.echo(f"Manager: {manager_email or 'Not specified'}")
            click.echo("\nWould execute:")
            click.echo("1. Okta: Clear sessions & deactivate user")
            click.echo("2. Google Workspace: Suspend user & transfer data")
            click.echo("3. Microsoft 365: Convert mailbox & remove licenses")
            click.echo("4. Zoom: Remove user")
            click.echo("5. SynQ Prox: Remove user")
            click.echo("6. Domo/Lucid/Workato: Remove if in groups")
            click.echo("7. Remove from app-specific Okta groups")
            return 0
        
        # Production mode - execute termination
        click.echo("\nPRODUCTION MODE: Executing termination")
        
        # Define progress callback
        def progress_callback(step: str, status: str, details: str = ""):
            if status == "starting":
                click.echo(f"{step}...")
            elif status == "success":
                click.echo(f"{step} - SUCCESS")
                if details:
                    click.echo(f"   └─ {details}")
            elif status == "error":
                click.echo(f"{step} - ERROR")
                if details:
                    click.echo(f"   └─ {details}")
            elif status == "warning":
                click.echo(f"{step} - WARNING")
                if details:
                    click.echo(f"   └─ {details}")
            elif status == "skipped":
                click.echo(f"{step} - SKIPPED")
                if details:
                    click.echo(f"   └─ {details}")
        
        # Execute termination
        results = workflow.execute_multi_phase_termination(
            user_email=user_email,
            manager_email=manager_email,
            ticket_id=ticket_id,
            progress_callback=progress_callback
        )
        
        # Show summary
        click.echo("\n=== TERMINATION SUMMARY ===")
        
        # Show phase results
        if results:
            for phase in ["okta", "microsoft", "google", "zoom", "synqprox", "domo", "lucidchart", "workato"]:
                if phase in results.get("phase_success", {}):
                    success = results["phase_success"][phase]
                    icon = "PASS" if success else "FAIL"
                    click.echo(f"{icon} {phase.title()}: {'SUCCESS' if success else 'FAILED'}")
            
            # Show errors if any
            if results.get("errors"):
                click.echo("\nERRORS ENCOUNTERED:")
                for error in results["errors"]:
                    click.echo(f"   • {error}")
            
            # Show warnings if any  
            if results.get("warnings"):
                click.echo("\nWARNINGS:")
                for warning in results["warnings"]:
                    click.echo(f"   • {warning}")
            
            # Overall result
            click.echo("")
            if results.get('overall_success'):
                click.echo("SUCCESS: Termination completed successfully")
                return 0
            else:
                click.echo("WARNING: Termination completed with issues")
                return 1
        else:
            click.echo("ERROR: Termination failed to return results")
            return 1
            
    except Exception as e:
        click.echo(f"ERROR: Fatal error in termination: {e}")
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

if __name__ == "__main__":
    cli()