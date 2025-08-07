#!/usr/bin/env python3
"""
Complete Enterprise Termination Orchestrator
Combines ticket processing, Okta deactivation, session clearing, and Microsoft 365 termination
"""

import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import all termination components
from termination_extractor import fetch_tickets, parse_termination_ticket
from okta_termination import OktaTermination
from microsoft_termination import MicrosoftTermination
from google_termination import GoogleTerminationManager
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
            
            # Initialize Google Workspace termination (may fail if credentials not set up)
            try:
                self.google_termination = GoogleTerminationManager()
                self.google_enabled = True
                logger.info("Google Workspace termination enabled")
            except Exception as e:
                logger.warning(f"Google Workspace termination disabled: {e}")
                self.google_termination = None
                self.google_enabled = False
            
            # Note: Slack notifications disabled during testing phase
            self.slack_notifications = None
            
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
            'google_results': {},
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
            
            # Step 3: Google Workspace Termination (data transfer and user deletion)
            logger.info("Phase 3: Google Workspace data transfer and user deletion")
            if manager_email and self.google_enabled and self.google_termination:
                try:
                    google_results = self.google_termination.execute_complete_termination(user_email, manager_email)
                    termination_results['google_results'] = {'success': google_results}
                    
                    if google_results:
                        termination_results['summary'].append("Google Workspace termination completed successfully")
                        logger.info("Google Workspace termination phase completed successfully")
                        
                        # Step 3.5: Remove from Google Workspace Okta group (after data backup)
                        logger.info("Phase 3.5: Removing user from Google Workspace Okta group")
                        try:
                            # Get the user ID from the Okta results
                            okta_user_id = None
                            if 'user_id' in okta_results:
                                okta_user_id = okta_results['user_id']
                            else:
                                # Find user again if needed
                                user = self.okta_termination.find_user_by_email(user_email)
                                if user:
                                    okta_user_id = user['id']
                            
                            if okta_user_id:
                                google_group_removed = self.okta_termination.remove_user_from_google_workspace_group(okta_user_id)
                                
                                if google_group_removed:
                                    termination_results['summary'].append("Removed from Google Workspace Okta group")
                                    logger.info("Successfully removed user from Google Workspace Okta group")
                                else:
                                    termination_results['summary'].append("Failed to remove from Google Workspace Okta group")
                                    logger.warning("Failed to remove user from Google Workspace Okta group")
                            else:
                                logger.warning("Could not find Okta user ID for Google group removal")
                                termination_results['summary'].append("Could not remove from Google group - user ID not found")
                                
                        except Exception as e:
                            logger.error(f"Error removing user from Google Workspace Okta group: {e}")
                            termination_results['summary'].append("Error removing from Google Workspace Okta group")
                    else:
                        termination_results['summary'].append("Google Workspace termination had issues")
                        logger.warning("Google Workspace termination phase had issues")
                except Exception as e:
                    logger.error(f"Error in Google Workspace termination: {e}")
                    termination_results['summary'].append(f"Google Workspace termination error: {str(e)}")
                    termination_results['google_results'] = {'success': False, 'error': str(e)}
            elif not self.google_enabled:
                logger.info("Google Workspace termination disabled - credentials not configured")
                termination_results['summary'].append("Google Workspace termination skipped - not configured")
                termination_results['google_results'] = {'success': True, 'skipped': True, 'reason': 'Not configured'}
            elif not manager_email:
                logger.warning("No manager email provided - skipping Google Workspace data transfer")
                termination_results['summary'].append("Google Workspace termination skipped - no manager")
                termination_results['google_results'] = {'success': False, 'error': 'No manager provided'}
            else:
                logger.warning("Google Workspace termination unavailable")
                termination_results['summary'].append("Google Workspace termination unavailable")
                termination_results['google_results'] = {'success': False, 'error': 'Service unavailable'}
            
            # Step 4: Update ticket status if ticket ID provided
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
            google_result = termination_results.get('google_results', {})
            google_success = google_result.get('success', False) or google_result.get('skipped', False)
            
            # Success if Okta works and either manager wasn't provided or all manager-dependent services work
            termination_results['overall_success'] = (okta_success and 
                                                    (microsoft_success or not manager_email) and
                                                    (google_success or not manager_email or not self.google_enabled))
            
            # Step 5: Send Slack notification (disabled during testing)
            try:
                if self.slack_notifications:
                    self.send_termination_notification(termination_results)
                else:
                    logger.debug("Slack notifications disabled during testing phase")
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
        """Send Slack notification about termination results (disabled during testing)."""
        if not self.slack_notifications:
            logger.debug("Slack notifications disabled during testing phase")
            return
            
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
    
    def run_ticket_processing(self, max_workers: int = 2):
        """Main method to process all pending termination tickets with optional parallel processing."""
        logger.info("Starting enterprise termination ticket processing")
        
        try:
            # Get all actionable termination tickets
            tickets = self.process_termination_tickets()
            
            if not tickets:
                logger.info("No termination tickets to process")
                return
            
            total_processed = 0
            total_successful = 0
            
            # Process tickets - use parallel processing if multiple tickets
            if len(tickets) > 1 and max_workers > 1:
                logger.info(f"Processing {len(tickets)} tickets with {max_workers} workers")
                total_successful = self._process_tickets_parallel(tickets, max_workers)
                total_processed = len(tickets)
            else:
                # Sequential processing for single ticket or when parallel disabled
                logger.info(f"Processing {len(tickets)} tickets sequentially")
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

            # Send summary notification (disabled during testing)
            if self.slack_notifications:
                self.send_batch_summary(total_processed, total_successful)
            else:
                logger.debug("Batch summary notifications disabled during testing phase")
            
            logger.info(f"Ticket processing completed: {total_successful}/{total_processed} successful")
            
        except Exception as e:
            logger.error(f"Failed to run ticket processing: {e}")
            raise

    def _process_tickets_parallel(self, tickets: List[Dict], max_workers: int) -> int:
        """Process multiple tickets in parallel with controlled concurrency."""
        successful_count = 0
        
        def process_single_ticket(ticket):
            """Process a single ticket - wrapper for parallel execution."""
            try:
                user_email = ticket.get('employee_email')
                manager_email = ticket.get('manager_email')
                ticket_id = ticket.get('ticket_number')
                
                if not user_email:
                    logger.error(f"Could not extract user email from ticket {ticket_id}")
                    return False
                
                logger.info(f"[Parallel] Processing termination for {user_email} (ticket {ticket_id})")
                
                # Execute complete termination
                results = self.execute_user_termination(user_email, manager_email, ticket_id)
                
                if results['overall_success']:
                    logger.info(f"[Parallel] Termination successful for {user_email}")
                    return True
                else:
                    logger.warning(f"[Parallel] Termination had issues for {user_email}")
                    return False
                    
            except Exception as e:
                logger.error(f"[Parallel] Failed to process ticket {ticket.get('ticket_number', 'unknown')}: {e}")
                return False
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Termination") as executor:
            # Submit all tickets for processing
            future_to_ticket = {executor.submit(process_single_ticket, ticket): ticket for ticket in tickets}
            
            # Collect results as they complete
            for future in as_completed(future_to_ticket):
                ticket = future_to_ticket[future]
                try:
                    success = future.result()
                    if success:
                        successful_count += 1
                except Exception as e:
                    logger.error(f"Parallel processing exception for ticket {ticket.get('ticket_number')}: {e}")
        
        return successful_count
    
    def send_batch_summary(self, total_processed: int, total_successful: int):
        """Send summary notification for batch processing (disabled during testing)."""
        if not self.slack_notifications:
            logger.debug("Batch summary notifications disabled during testing phase")
            return
            
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
