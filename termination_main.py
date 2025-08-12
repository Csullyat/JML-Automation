#!/usr/bin/env python3
"""
Main orchestration script for employee termination automation V2.0.
Handles multi-phase ticket processing and user deactivation across all enterprise platforms.
Supports: Okta → Microsoft → Google → Zoom → Notifications
"""

import logging
import sys
from datetime import datetime
from enterprise_termination_orchestrator import EnterpriseTerminationOrchestrator
from logging_system import setup_logging

logger = logging.getLogger(__name__)

def main(test_mode: bool = True):
    """
    Main entry point for enterprise termination automation V2.0.
    
    Args:
        test_mode: If True, only process first termination ticket for testing
    """
    # Setup logging
    setup_logging()
    
    logger.info("=" * 80)
    if test_mode:
        logger.info("ENTERPRISE TERMINATION AUTOMATION V2.0 STARTING (TEST MODE)")
    else:
        logger.info("ENTERPRISE TERMINATION AUTOMATION V2.0 STARTING (PRODUCTION MODE)")
    logger.info("=" * 80)
    
    try:
        # Initialize V2.0 orchestrator
        logger.info("Initializing enterprise termination orchestrator V2.0...")
        orchestrator = EnterpriseTerminationOrchestrator()
        
        # Check for command line arguments for single user termination
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == 'test' and len(sys.argv) > 2:
                # Test mode for single user: python termination_main.py test user@domain.com manager@domain.com
                user_email = sys.argv[2]
                manager_email = sys.argv[3] if len(sys.argv) > 3 else None
                
                logger.info(f"Running test mode validation for {user_email}")
                print(f"🧪 Running test mode validation for {user_email}")
                
                results = orchestrator.test_mode_termination(user_email, manager_email)
                
                print(f"\\n🧪 TEST MODE RESULTS for {user_email}")
                print(f"Overall Ready: {'✅ YES' if results['overall_ready'] else '❌ NO'}")
                print(f"\\nWould Execute:")
                for action in results['would_execute']:
                    print(f"  ✅ {action}")
                print(f"\\nPotential Issues:")
                for issue in results['potential_issues']:
                    print(f"  ⚠️ {issue}")
                
                sys.exit(0 if results['overall_ready'] else 1)
                
            else:
                # Single user termination: python termination_main.py user@domain.com manager@domain.com [phases]
                user_email = sys.argv[1]
                manager_email = sys.argv[2] if len(sys.argv) > 2 else None
                phases = sys.argv[3].split(',') if len(sys.argv) > 3 else None
                
                logger.info(f"Running single user multi-phase termination for {user_email}")
                print(f"🚀 Running multi-phase termination for {user_email}")
                if phases:
                    print(f"Phases: {', '.join(phases)}")
                
                results = orchestrator.execute_user_termination(user_email, manager_email, phases=phases)
                
                if results['overall_success']:
                    print(f"✅ MULTI-PHASE TERMINATION SUCCESSFUL for {user_email}")
                    logger.info(f"Single user termination completed successfully for {user_email}")
                    sys.exit(0)
                else:
                    print(f"⚠️ MULTI-PHASE TERMINATION COMPLETED WITH ISSUES for {user_email}")
                    logger.warning(f"Single user termination had issues for {user_email}")
                    sys.exit(1)
        else:
            # Run ticket-based processing
            if test_mode:
                logger.info("Test mode: Will process first termination ticket only")
                print("🧪 TEST MODE: Processing first termination ticket only")
                
                # Fetch tickets and process only the first one
                tickets = orchestrator.process_termination_tickets()
                
                if not tickets:
                    logger.info("No termination tickets found")
                    print("No termination tickets found.")
                    return
                
                # Process only the first ticket in test mode
                ticket = tickets[0]
                from ticket_processor import extract_user_email_from_ticket, extract_manager_email_from_ticket
                
                user_email = extract_user_email_from_ticket(ticket)
                manager_email = extract_manager_email_from_ticket(ticket)
                ticket_id = ticket.get('ticket_id')
                
                if not user_email:
                    logger.error(f"Could not extract user email from test ticket {ticket_id}")
                    print(f"❌ Could not extract user email from ticket {ticket_id}")
                    return
                
                logger.info(f"TEST MODE: Processing multi-phase termination for {user_email} (ticket {ticket_id})")
                print(f"🧪 TEST MODE: Processing multi-phase termination for {user_email}")
                
                results = orchestrator.execute_user_termination(user_email, manager_email, ticket_id)
                
                if results['overall_success']:
                    print(f"✅ TEST MULTI-PHASE TERMINATION SUCCESSFUL for {user_email}")
                    logger.info(f"Test termination completed successfully")
                else:
                    print(f"⚠️ TEST MULTI-PHASE TERMINATION HAD ISSUES for {user_email}")
                    logger.warning(f"Test termination had issues")
                    
                print("\\n🧪 Test mode completed. Review logs and results.")
                print("💡 To run in production mode, edit this file and set test_mode=False")
                print("💡 To test a specific user: python termination_main.py test user@domain.com manager@domain.com")
                
            else:
                # Production mode - process all tickets with multi-phase termination
                logger.info("Production mode: Processing all termination tickets with multi-phase workflow")
                print("🚀 PRODUCTION MODE: Processing all termination tickets")
                print("Phases: Okta → Microsoft → Google → Zoom → Notifications")
                orchestrator.run_ticket_processing()
            
    except KeyboardInterrupt:
        logger.info("Termination automation interrupted by user")
        print("\\n⚠️ Termination automation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in termination automation: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
    
    logger.info("Enterprise termination automation V2.0 completed successfully")
    print("✅ Enterprise termination automation completed")

if __name__ == "__main__":
    # Set to True for testing, False for production
    # Change this line to main(test_mode=False) when ready for production
    main(test_mode=True)
