# termination_main.py - Main orchestration script for employee termination automation

import logging
import os
from datetime import datetime
from config import get_okta_token, get_samanage_token
from ticket_processor import fetch_termination_tickets, filter_termination_requests
from okta_termination import terminate_okta_user, validate_okta_connection
from slack_notifications import send_termination_notification, send_termination_summary
from logging_system import setup_logging, log_termination_action

def main(test_mode: bool = True):
    """
    Main termination automation workflow.
    
    Args:
        test_mode: If True, only processes the first ticket for safety validation
    """
    logger = setup_logging()
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info(f"TERMINATION AUTOMATION STARTED - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # Validate connections
        logger.info("Validating system connections...")
        okta_token = get_okta_token()
        if not validate_okta_connection(okta_token):
            logger.error("Failed to connect to Okta. Aborting automation.")
            print("❌ Okta connection failed. Check credentials and try again.")
            return
        
        logger.info("✅ Okta connection validated")
        print("✅ System connections validated")
        
        # Fetch termination tickets
        logger.info("Fetching termination tickets from Service Desk...")
        print("🔍 Fetching termination requests...")
        
        tickets = fetch_termination_tickets()
        termination_requests = filter_termination_requests(tickets)
        
        logger.info(f"Found {len(termination_requests)} termination requests to process")
        print(f"📋 Found {len(termination_requests)} termination requests")
        
        if not termination_requests:
            logger.info("No termination requests found. Exiting.")
            print("✅ No pending terminations found.")
            return
        
        # Process requests
        iterable = termination_requests[:1] if test_mode else termination_requests
        mode_msg = "TEST MODE - Processing first request only" if test_mode else f"PRODUCTION MODE - Processing all {len(termination_requests)} requests"
        logger.info(mode_msg)
        print(f"⚙️  {mode_msg}")
        
        successful_terminations = 0
        failed_terminations = 0
        termination_results = []
        
        for i, request in enumerate(iterable, 1):
            user_email = request.get('email', 'Unknown')
            user_name = request.get('name', 'Unknown')
            ticket_number = request.get('ticket_number', 'Unknown')
            ticket_id = request.get('ticket_id')
            
            logger.info(f"Processing termination {i}/{len(iterable)}: {user_name} ({user_email}) - Ticket #{ticket_number}")
            print(f"\n🔄 Processing: {user_name} ({user_email})")
            
            try:
                # Perform Okta termination
                termination_result = terminate_okta_user(
                    email=user_email,
                    name=user_name,
                    ticket_id=ticket_id,
                    ticket_number=ticket_number,
                    okta_token=okta_token
                )
                
                if termination_result['success']:
                    successful_terminations += 1
                    logger.info(f"✅ Successfully terminated {user_email}")
                    print(f"✅ Terminated: {user_email}")
                    
                    # Send Slack notification
                    send_termination_notification(
                        user_name=user_name,
                        user_email=user_email,
                        ticket_number=ticket_number,
                        actions_taken=termination_result.get('actions_taken', [])
                    )
                    
                else:
                    failed_terminations += 1
                    logger.error(f"❌ Failed to terminate {user_email}: {termination_result.get('error', 'Unknown error')}")
                    print(f"❌ Failed: {user_email}")
                
                termination_results.append(termination_result)
                
            except Exception as e:
                failed_terminations += 1
                logger.error(f"❌ Error processing {user_email}: {str(e)}", exc_info=True)
                print(f"❌ Error processing {user_email}: {str(e)}")
                
                termination_results.append({
                    'success': False,
                    'email': user_email,
                    'error': str(e)
                })
        
        # Log summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info(f"TERMINATION AUTOMATION SUMMARY - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Successful terminations: {successful_terminations}")
        logger.info(f"Failed terminations: {failed_terminations}")
        logger.info(f"Total requests processed: {len(iterable)}")
        logger.info("=" * 60)
        
        # Console summary
        print(f"\n📊 Termination Automation Complete!")
        print(f"✅ {successful_terminations} users terminated successfully")
        if failed_terminations > 0:
            print(f"❌ {failed_terminations} terminations failed")
        print(f"⏱️  Completed in {duration}")
        print("📝 Check logs for detailed information")
        
        # Send summary to Slack (if not test mode)
        if not test_mode and (successful_terminations > 0 or failed_terminations > 0):
            send_termination_summary(
                successful_count=successful_terminations,
                failed_count=failed_terminations,
                total_processed=len(iterable),
                duration=duration,
                results=termination_results
            )
        
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in termination automation: {str(e)}", exc_info=True)
        print(f"💥 Critical error: {str(e)}")
        raise

if __name__ == "__main__":
    # For safety, default to test mode
    # Change to main(test_mode=False) when ready for production
    main(test_mode=True)
