#!/usr/bin/env python3
"""
Complete Enterprise Termination Orchestrator
Combines ticket processing, Okta deactivation, session clearing, and Microsoft 365 termination
"""

import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Import all termination components
from termination_extractor import fetch_tickets, parse_termination_ticket
from okta_termination import OktaTermination
from microsoft_termination import MicrosoftTermination
from slack_notifications import send_termination_notification
from logging_system import setup_logging

logger = logging.getLogger(__name__)

class EnterpriseTerminationOrchestrator:
    """Orchestrates complete enterprise user termination process."""
    
    def __init__(self):
        """Initialize all termination components."""
        try:
            self.okta_termination = OktaTermination()
            self.microsoft_termination = MicrosoftTermination()
            
            logger.info("Enterprise Termination Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize termination orchestrator: {e}")
            raise
    
    def process_termination_tickets(self) -> List[Dict]:
        """Fetch and filter termination tickets."""
        try:
            logger.info("Fetching termination tickets from service desk")
            
            # Get termination tickets using our working extractor
            raw_tickets = fetch_tickets(per_page=100, max_pages=60, workers=10)  # Get 6000 tickets
            
            if not raw_tickets:
                logger.info("No tickets found")
                return []
            
            logger.info(f"Fetched {len(raw_tickets)} raw tickets, parsing for terminations...")
            
            # Parse for termination tickets
            termination_tickets = []
            from termination_extractor import ACTIVE_STATES
            for ticket in raw_tickets:
                parsed = parse_termination_ticket(ticket)
                if parsed and parsed.get('employee_to_terminate') and parsed.get('ticket_state') in ACTIVE_STATES:
                    termination_tickets.append(parsed)
            
            active_states_str = "', '".join(ACTIVE_STATES)
            logger.info(f"Found {len(termination_tickets)} active state ('{active_states_str}') termination tickets to process")
            return termination_tickets
            
        except Exception as e:
            logger.error(f"Failed to process termination tickets: {e}")
            return []
    
    def execute_user_termination(self, user_email: str, manager_email: str, ticket_id: str = None) -> Dict:
        """Execute complete termination for a single user."""
        logger.info(f"Starting complete termination for {user_email}")
        
        termination_results = {
            'user_email': user_email,
            'manager_email': manager_email,
            'ticket_id': ticket_id,
            'start_time': datetime.now(),
            'okta_results': {},
            'microsoft_results': {},
            'overall_success': False,
            'summary': []
        }
        
        try:
            # Step 1: Okta Termination (deactivation, group removal, session clearing)
            logger.info("Phase 1: Okta user deactivation and cleanup")
            okta_results = self.okta_termination.execute_complete_termination(user_email)
            termination_results['okta_results'] = okta_results
            
            if okta_results['success']:
                termination_results['summary'].append("Okta termination completed successfully")
                logger.info("Okta termination phase completed successfully")
            else:
                termination_results['summary'].append("Okta termination had issues")
                logger.warning("Okta termination phase had issues")
            
            # Step 2: Microsoft 365 Termination (mailbox conversion, delegation, license removal)
            logger.info("Phase 2: Microsoft 365 mailbox and license management")
            if manager_email:
                microsoft_results = self.microsoft_termination.execute_complete_termination(user_email, manager_email)
                termination_results['microsoft_results'] = microsoft_results
                
                if microsoft_results['success']:
                    termination_results['summary'].append("Microsoft 365 termination completed successfully")
                    logger.info("Microsoft 365 termination phase completed successfully")
                    
                    # Step 2.5: Remove from Microsoft 365 Okta group (after license removal)
                    logger.info("Phase 2.5: Removing user from Microsoft 365 Okta group")
                    try:
                        # Get the user ID from the Okta results (we need it for group removal)
                        okta_user_id = None
                        if 'user_id' in okta_results:
                            okta_user_id = okta_results['user_id']
                        else:
                            # Find user again if needed
                            user = self.okta_termination.find_user_by_email(user_email)
                            if user:
                                okta_user_id = user['id']
                        
                        if okta_user_id:
                            m365_group_removed = self.okta_termination.remove_user_from_specific_group(
                                okta_user_id, 
                                "SSO-Microsoft 365 E3 - User"
                            )
                            
                            if m365_group_removed:
                                termination_results['summary'].append("Removed from Microsoft 365 E3 Okta group")
                                logger.info("Successfully removed user from Microsoft 365 E3 Okta group")
                            else:
                                termination_results['summary'].append("Failed to remove from Microsoft 365 E3 Okta group")
                                logger.warning("Failed to remove user from Microsoft 365 E3 Okta group")
                        else:
                            logger.warning("Could not find Okta user ID for group removal")
                            termination_results['summary'].append("Could not remove from M365 group - user ID not found")
                            
                    except Exception as e:
                        logger.error(f"Error removing user from Microsoft 365 Okta group: {e}")
                        termination_results['summary'].append("Error removing from Microsoft 365 E3 Okta group")
                else:
                    termination_results['summary'].append("Microsoft 365 termination had issues")
                    logger.warning("Microsoft 365 termination phase had issues")
            else:
                logger.warning("No manager email provided - skipping Microsoft 365 delegation")
                termination_results['summary'].append("Microsoft 365 termination skipped - no manager")
                termination_results['microsoft_results'] = {'success': False, 'error': 'No manager provided'}
            
            # Step 3: Update ticket status if ticket ID provided
            if ticket_id:
                try:
                    logger.info(f"Updating ticket {ticket_id} status")
                    # Note: You would implement update_ticket_status function in ticket_processor.py
                    # For now, we'll just log that we would update the ticket
                    logger.info(f"Ticket {ticket_id} marked for completion (update function not implemented)")
                    termination_results['summary'].append(f"Ticket {ticket_id} marked for completion")
                except Exception as e:
                    logger.error(f"Failed to update ticket {ticket_id}: {e}")
                    termination_results['summary'].append(f"Failed to update ticket {ticket_id}")
            
            # Determine overall success
            okta_success = okta_results.get('success', False)
            microsoft_success = termination_results['microsoft_results'].get('success', False)
            termination_results['overall_success'] = okta_success and (microsoft_success or not manager_email)
            
            # Step 4: Send Slack notification
            try:
                self.send_termination_notification(termination_results)
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
                termination_results['summary'].append("Failed to send Slack notification")
            
            termination_results['end_time'] = datetime.now()
            duration = termination_results['end_time'] - termination_results['start_time']
            termination_results['duration_seconds'] = duration.total_seconds()
            
            logger.info(f"Complete termination finished for {user_email} in {duration.total_seconds():.1f} seconds")
            return termination_results
            
        except Exception as e:
            logger.error(f"Fatal error during termination of {user_email}: {e}")
            termination_results['overall_success'] = False
            termination_results['summary'].append(f"Fatal error: {str(e)}")
            termination_results['end_time'] = datetime.now()
            return termination_results
    
    def send_termination_notification(self, termination_results: Dict):
        """Send Slack notification about termination results."""
        try:
            user_email = termination_results['user_email']
            success = termination_results['overall_success']
            
            if success:
                message = f"TERMINATION COMPLETED: {user_email}"
                color = "good"
            else:
                message = f"TERMINATION ISSUES: {user_email}"
                color = "warning"
            
            # Build detailed summary
            summary_text = "\n".join([f"• {item}" for item in termination_results['summary']])
            
            # Okta details
            okta_results = termination_results.get('okta_results', {})
            okta_actions = len(okta_results.get('actions_completed', []))
            okta_failures = len(okta_results.get('actions_failed', []))
            
            # Microsoft details
            ms_results = termination_results.get('microsoft_results', {})
            ms_actions = len(ms_results.get('actions_completed', []))
            ms_failures = len(ms_results.get('actions_failed', []))
            
            duration = termination_results.get('duration_seconds', 0)
            
            slack_message = {
                "text": message,
                "attachments": [{
                    "color": color,
                    "fields": [
                        {"title": "User", "value": user_email, "short": True},
                        {"title": "Manager", "value": termination_results.get('manager_email', 'None'), "short": True},
                        {"title": "Okta Actions", "value": f"{okta_actions} completed, {okta_failures} failed", "short": True},
                        {"title": "Microsoft Actions", "value": f"{ms_actions} completed, {ms_failures} failed", "short": True},
                        {"title": "Duration", "value": f"{duration:.1f} seconds", "short": True},
                        {"title": "Ticket", "value": termination_results.get('ticket_id', 'Manual'), "short": True},
                        {"title": "Summary", "value": summary_text, "short": False}
                    ],
                    "footer": "Enterprise Termination Automation",
                    "ts": int(termination_results['start_time'].timestamp())
                }]
            }
            
            self.slack_notifications.send_message(slack_message)
            logger.info("Termination notification sent to Slack")
            
        except Exception as e:
            logger.error(f"Failed to send termination notification: {e}")
    
    def run_ticket_processing(self):
        """Main method to process all pending termination tickets."""
        logger.info("Starting enterprise termination ticket processing")
        
        try:
            # Get all actionable termination tickets
            tickets = self.process_termination_tickets()
            
            if not tickets:
                logger.info("No termination tickets to process")
                return
            
            total_processed = 0
            total_successful = 0
            
            for ticket in tickets:
                try:
                    # User info is already extracted by parse_termination_ticket
                    user_email = ticket.get('employee_email')
                    manager_email = ticket.get('manager_email')
                    user_name = ticket.get('employee_name')
                    ticket_id = ticket.get('ticket_number')
                    
                    if not user_email:
                        logger.error(f"Could not extract user email from ticket {ticket_id}")
                        continue
                    
                    logger.info(f"Processing termination for {user_email} (ticket {ticket_id})")
                    
                    # Execute complete termination
                    results = self.execute_user_termination(user_email, manager_email, ticket_id)
                    
                    total_processed += 1
                    if results['overall_success']:
                        total_successful += 1
                        logger.info(f"Termination successful for {user_email}")
                    else:
                        logger.warning(f"Termination had issues for {user_email}")
                    
                except Exception as e:
                    logger.error(f"Failed to process ticket {ticket.get('id', 'unknown')}: {e}")
                    total_processed += 1
            
            # Send summary notification
            self.send_batch_summary(total_processed, total_successful)
            
            logger.info(f"Ticket processing completed: {total_successful}/{total_processed} successful")
            
        except Exception as e:
            logger.error(f"Failed to run ticket processing: {e}")
            raise
    
    def send_batch_summary(self, total_processed: int, total_successful: int):
        """Send summary notification for batch processing."""
        try:
            success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
            
            if success_rate == 100:
                color = "good"
                status = "ALL SUCCESSFUL"
            elif success_rate >= 80:
                color = "warning"
                status = "MOSTLY SUCCESSFUL"
            else:
                color = "danger"
                status = "ISSUES DETECTED"
            
            message = {
                "text": f"TERMINATION BATCH COMPLETE: {status}",
                "attachments": [{
                    "color": color,
                    "fields": [
                        {"title": "Total Processed", "value": str(total_processed), "short": True},
                        {"title": "Successful", "value": str(total_successful), "short": True},
                        {"title": "Success Rate", "value": f"{success_rate:.1f}%", "short": True},
                        {"title": "Timestamp", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                    ],
                    "footer": "Enterprise Termination Automation - Batch Summary"
                }]
            }
            
            self.slack_notifications.send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send batch summary: {e}")

def main():
    """Main entry point for enterprise termination automation."""
    # Setup logging
    setup_logging()
    
    logger.info("=" * 60)
    logger.info("ENTERPRISE TERMINATION AUTOMATION STARTING")
    logger.info("=" * 60)
    
    try:
        # Initialize orchestrator
        orchestrator = EnterpriseTerminationOrchestrator()
        
        # Check if user email provided as command line argument for single user termination
        if len(sys.argv) > 1:
            user_email = sys.argv[1]
            manager_email = sys.argv[2] if len(sys.argv) > 2 else None
            
            logger.info(f"Running single user termination for {user_email}")
            results = orchestrator.execute_user_termination(user_email, manager_email)
            
            if results['overall_success']:
                print(f"TERMINATION SUCCESSFUL for {user_email}")
                sys.exit(0)
            else:
                print(f"TERMINATION HAD ISSUES for {user_email}")
                sys.exit(1)
        else:
            # Run ticket-based processing
            orchestrator.run_ticket_processing()
            
    except KeyboardInterrupt:
        logger.info("Termination automation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in termination automation: {e}")
        sys.exit(1)
    
    logger.info("Enterprise termination automation completed")

if __name__ == "__main__":
    main()
