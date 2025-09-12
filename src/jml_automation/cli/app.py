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
@click.option("--ticket-id", required=True, help="SolarWinds ticket ID")
@click.option("--dry-run/--no-dry-run", default=True, help="Dry run mode (default: True)")
def onboard_run(ticket_id, dry_run):
    """Run onboarding for a specific ticket."""
    click.echo(f"🚀 Running onboarding for ticket {ticket_id} (dry_run={dry_run})")
    
    try:
        from jml_automation.workflows.onboarding import run
        result = run(
            ticket_id=ticket_id,
            ticket_raw=None,
            dry_run=dry_run,
            push_domo=False
        )
        if result == 0:
            click.echo("✅ Onboarding completed successfully")
        else:
            click.echo(f"❌ Onboarding failed with code {result}")
        return result
    except Exception as e:
        click.echo(f"❌ Fatal error in onboarding: {e}")
        return 1

# ========== TERMINATION COMMANDS ==========

@terminate.command("run")
@click.option("--ticket-id", help="SolarWinds ticket ID to process")
@click.option("--user-email", help="Email of user to terminate directly")
@click.option("--manager-email", help="Email of manager for delegation")
@click.option("--phases", help="Comma-separated phases to run (okta,microsoft,google,zoom)")
@click.option("--test-mode/--production-mode", default=True, help="Test mode (default: True)")
def terminate_run(ticket_id: Optional[str], user_email: Optional[str], manager_email: Optional[str], phases: Optional[str], test_mode: bool):
    """Run termination for a ticket or user with multi-phase support."""
    
    # Validate input
    if not ticket_id and not user_email:
        click.echo("❌ Error: Must provide either --ticket-id or --user-email")
        sys.exit(1)
    
    # Parse phases if provided
    phase_list = None
    if phases:
        phase_list = [p.strip() for p in phases.split(',')]
        click.echo(f"📋 Phases to execute: {', '.join(phase_list)}")
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        
        workflow = TerminationWorkflow()
        
        if test_mode:
            click.echo("🧪 TEST MODE: Multi-phase termination")
        else:
            click.echo("🚀 PRODUCTION MODE: Multi-phase termination")
        
        if user_email:
            # Direct user termination
            click.echo(f"🚀 Running multi-phase termination for {user_email}")
            results = workflow.execute_multi_phase_termination(
                user_email=user_email,
                manager_email=manager_email,
                phases=phase_list,
                ticket_id=ticket_id
            )
            
            if results and results.get('overall_success'):
                click.echo("✅ Termination completed successfully")
                return 0
            else:
                click.echo("⚠️ Termination completed with issues")
                return 1
        else:
            # Ticket-based termination
            click.echo(f"🚀 Running termination for ticket {ticket_id}")
            from jml_automation.workflows.termination import run
            result = run(
                ticket_id=ticket_id,
                ticket_raw=None,
                dry_run=test_mode
            )
            
            if result == 0:
                click.echo("✅ Termination completed successfully")
                return 0
            else:
                click.echo("⚠️ Termination completed with issues")
                return result
            
    except Exception as e:
        click.echo(f"❌ Fatal error in termination: {e}")
        logger.error(f"Termination CLI error: {e}")
        return 1

@terminate.command("test")
@click.argument("user_email")
@click.option("--manager-email", help="Email of manager for delegation")
def terminate_test(user_email: str, manager_email: Optional[str]):
    """Test termination readiness for a specific user."""
    click.echo(f"🧪 Running termination readiness test for {user_email}")
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        
        workflow = TerminationWorkflow()
        results = workflow.test_termination(user_email, manager_email)
        
        click.echo(f"\n🧪 TEST MODE RESULTS for {user_email}")
        click.echo(f"Overall Ready: {'✅ YES' if results['overall_ready'] else '❌ NO'}")
        click.echo(f"\nWould Execute:")
        for action in results['would_execute']:
            click.echo(f"  ✅ {action}")
        click.echo(f"\nPotential Issues:")
        for issue in results['potential_issues']:
            click.echo(f"  ⚠️ {issue}")
        
        sys.exit(0 if results['overall_ready'] else 1)
        
    except Exception as e:
        click.echo(f"❌ Fatal error in test mode: {e}")
        logger.error(f"Termination test error: {e}")
        sys.exit(1)

@terminate.command("synqprox")
@click.argument("ticket_id")
def terminate_synqprox(ticket_id: str):
    """Test SYNQ Prox deletion for a specific ticket."""
    click.echo(f"🧪 Testing SYNQ Prox deletion for ticket {ticket_id}")
    
    try:
        # Fetch the ticket to get user email
        from jml_automation.services.solarwinds import SolarWindsService
        from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket
        from jml_automation.services.synqprox import SynqProxService
        
        solarwinds = SolarWindsService.from_config()
        ticket = solarwinds.fetch_ticket(ticket_id)
        
        if not ticket:
            click.echo(f"❌ Ticket {ticket_id} not found")
            sys.exit(1)
        
        user_email = extract_user_email_from_ticket(ticket)
        if not user_email:
            click.echo(f"❌ Could not extract user email from ticket {ticket_id}")
            sys.exit(1)
        
        click.echo(f"✅ Found user email: {user_email}")
        click.echo(f"🚀 Testing SYNQ Prox deletion...")
        
        # Test SYNQ Prox deletion
        synqprox = SynqProxService()
        result = synqprox.execute_termination(user_email)
        
        if result:
            click.echo(f"✅ SYNQ Prox deletion test successful for {user_email}")
            click.echo("🎉 User deleted successfully from SYNQ Prox")
            sys.exit(0)
        else:
            click.echo(f"❌ SYNQ Prox deletion test failed for {user_email}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Fatal error in SYNQ Prox test: {e}")
        logger.error(f"SYNQ Prox test error: {e}")
        sys.exit(1)

@terminate.command("batch")
@click.option("--test-mode/--production-mode", default=True, help="Test mode processes only first ticket")
def terminate_batch(test_mode: bool):
    """Process all termination tickets in batch mode."""
    
    if test_mode:
        click.echo("🧪 TEST MODE: Processing first termination ticket only")
    else:
        click.echo("🚀 PRODUCTION MODE: Processing all termination tickets")
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
                click.echo(f"❌ Could not extract user email from ticket {ticket_id}")
                return 1
            
            click.echo(f"🧪 TEST MODE: Processing multi-phase termination for {user_email}")
            results = workflow.execute_multi_phase_termination(user_email, manager_email, ticket_id=ticket_id)
            
            if results['overall_success']:
                click.echo(f"✅ TEST termination successful for {user_email}")
                click.echo("\n🧪 Test mode completed. Review logs and results.")
                click.echo("💡 To run in production mode, use --production-mode")
                return 0
            else:
                click.echo(f"⚠️ TEST termination had issues for {user_email}")
                return 1
        else:
            # Production mode - process all tickets
            workflow.run_batch_processing()
            click.echo("✅ Batch termination processing completed")
            return 0
            
    except KeyboardInterrupt:
        click.echo("\n⚠️ Termination automation interrupted by user")
        return 1
    except Exception as e:
        click.echo(f"❌ Fatal error in batch processing: {e}")
        logger.error(f"Batch termination error: {e}")
        return 1

if __name__ == "__main__":
    cli()
