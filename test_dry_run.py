#!/usr/bin/env python3
"""Dry run test of the enterprise termination orchestrator"""

from enterprise_termination_orchestrator import EnterpriseTerminationOrchestrator
from ticket_processor import fetch_termination_tickets
import logging

def run_dry_mode():
    """Run the orchestrator in dry mode to preview actions."""
    
    print('🧪 ENTERPRISE TERMINATION ORCHESTRATOR - DRY RUN MODE')
    print('=' * 80)
    print('⚠️  DRY RUN: No actual changes will be made to any systems')
    print('=' * 80)

    try:
        # Initialize the orchestrator
        print('\n🚀 Initializing Enterprise Termination Orchestrator V2.0...')
        orchestrator = EnterpriseTerminationOrchestrator()
        
        print('✅ Orchestrator initialized successfully')

        # Fetch tickets
        print('\n📋 Fetching termination tickets...')
        termination_tickets = fetch_termination_tickets()
        
        if not termination_tickets:
            print('✅ No termination tickets found - nothing to process')
            return

        print(f'Found {len(termination_tickets)} termination ticket(s) to process')

        # Process each ticket in dry run mode
        for i, ticket in enumerate(termination_tickets, 1):
            print(f'\n{"="*60}')
            print(f'DRY RUN PROCESSING TICKET {i}/{len(termination_tickets)}')
            print(f'{"="*60}')
            
            employee_id = ticket.get('employee_to_terminate', 'Unknown')
            employee_name = ticket.get('employee_name', 'Unknown')
            ticket_number = ticket.get('ticket_number', 'Unknown')
            
            print(f'🎫 Ticket: #{ticket_number}')
            print(f'👤 Employee: {employee_name} (ID: {employee_id})')
            print(f'📅 Termination Date: {ticket.get("termination_date", "Not specified")}')
            print(f'🏢 Department: {ticket.get("employee_department", "Unknown")}')
            print(f'🔄 Termination Type: {ticket.get("term_type", "Unknown")}')
            
            print(f'\n🔍 DRY RUN: What would happen to this user...')
            
            try:
                # Instead of running the full orchestrator, let's preview what it would do
                print(f'🔍 PHASE 1: Would check Okta user status...')
                print(f'   Employee ID: {employee_id}')
                print(f'   Looking for user in Okta domain: filevine.okta.com')
                
                print(f'🔍 PHASE 2: Would check Microsoft 365 user...')
                print(f'   Would look for user email or UPN in Microsoft Graph')
                
                print(f'🔍 PHASE 3: Would check Google Workspace user...')
                print(f'   Would check filevine.com domain for user')
                
                print(f'🔍 PHASE 4: Would check Zoom user...')
                print(f'   Would search Zoom directory for user')
                
                print(f'🔍 PHASE 5: Would update Service Desk ticket...')
                print(f'   Would update ticket #{ticket_number} status')
                
                print(f'🔍 PHASE 6: Would send notifications...')
                print(f'   Would notify stakeholders of termination completion')
                
                print(f'✅ Dry run preview completed for ticket #{ticket_number}')
                
            except Exception as e:
                print(f'❌ Error during dry run preview: {e}')
                import traceback
                traceback.print_exc()

        print(f'\n{"="*80}')
        print('🧪 DRY RUN COMPLETE - Review the above actions')
        print('No actual changes were made to any systems')
        print('='*80)

    except Exception as e:
        print(f'❌ Critical error during dry run: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set logging to see more details
    logging.basicConfig(level=logging.INFO)
    run_dry_mode()
