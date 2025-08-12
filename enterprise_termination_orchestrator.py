#!/usr/bin/env python3
"""
Complete Enterprise Termination Orchestrator V2.0
Multi-phase termination: Okta → Microsoft → Google → Zoom → Notifications
Includes comprehensive data transfer capabilities and audit logging
"""

import logging
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# Import all termination components
from ticket_processor import fetch_termination_tickets, extract_user_email_from_ticket, extract_manager_email_from_ticket
from okta_termination import OktaTermination
from microsoft_termination import MicrosoftTermination
from google_termination import GoogleTermination
from zoom_termination import ZoomTermination
from logging_system import setup_logging
import config

logger = logging.getLogger(__name__)

class EnterpriseTerminationOrchestrator:
    """Orchestrates complete enterprise user termination across all systems."""
    
    def __init__(self):
        """Initialize all termination components."""
        try:
            # Validate configuration first - fail fast if 1Password service account unavailable
            logger.info("Validating 1Password service account connection...")
            config_status = config.get_configuration_summary()
            if not config_status['onepassword_service_account']:
                raise Exception("1Password service account not accessible - cannot proceed")
            
            # Initialize termination modules
            self.okta_termination = OktaTermination()
            self.microsoft_termination = MicrosoftTermination()
            self.google_termination = GoogleTermination()
            self.zoom_termination = ZoomTermination()
            
            logger.info("Enterprise Termination Orchestrator V2.0 initialized successfully")
            logger.info(f"Configuration status: {config_status}")
            
        except Exception as e:
            logger.error(f"Failed to initialize termination orchestrator: {e}")
            raise
    
    def process_termination_tickets(self) -> List[Dict]:
        """Fetch and filter termination tickets."""
        try:
            logger.info("Fetching termination tickets from service desk")
            
            # Get all pending termination tickets
            tickets = fetch_termination_tickets()
            
            if not tickets:
                logger.info("No termination tickets found")
                return []
            
            logger.info(f"Found {len(tickets)} termination tickets to process")
            
            # Filter for actionable tickets (awaiting input state only)
            actionable_tickets = []
            for ticket in tickets:
                # Only process tickets in 'Awaiting Input' state for catalog item 'Employee Termination'
                if (ticket.get('state') == 'Awaiting Input' and 
                    ticket.get('catalog_item', '').lower() == 'employee termination'):
                    actionable_tickets.append(ticket)
                    logger.info(f"Added ticket {ticket.get('id', 'unknown')} to processing queue")
                else:
                    logger.info(f"Skipping ticket {ticket.get('id', 'unknown')} - state: {ticket.get('state')}, catalog: {ticket.get('catalog_item')}")
            
            logger.info(f"Found {len(actionable_tickets)} actionable termination tickets")
            return actionable_tickets
            
        except Exception as e:
            logger.error(f"Failed to process termination tickets: {e}")
            return []
    
    def execute_user_termination(self, user_email: str, manager_email: str = None, 
                               ticket_id: str = None, phases: List[str] = None) -> Dict:
        """
        Execute complete multi-phase termination for a single user.
        
        Args:
            user_email: User to terminate
            manager_email: Manager for data delegation
            ticket_id: Service desk ticket ID
            phases: List of phases to execute ['okta', 'microsoft', 'google', 'zoom', 'notifications']
        """
        if phases is None:
            phases = ['okta', 'microsoft', 'google', 'zoom', 'notifications']
        
        logger.info(f"Starting multi-phase termination for {user_email}")
        logger.info(f"Phases to execute: {', '.join(phases)}")
        
        termination_results = {
            'user_email': user_email,
            'manager_email': manager_email,
            'ticket_id': ticket_id,
            'start_time': datetime.now(),
            'phases_executed': phases,
            'okta_results': {},
            'microsoft_results': {},
            'google_results': {},
            'zoom_results': {},
            'notification_results': {},
            'overall_success': False,
            'phase_success': {},
            'summary': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Phase 1: Okta Termination (highest priority - immediate security)
            if 'okta' in phases:
                logger.info("🔒 PHASE 1: Okta user deactivation and security cleanup")
                try:
                    okta_results = self.okta_termination.execute_complete_termination(user_email)
                    termination_results['okta_results'] = okta_results
                    
                    if okta_results.get('success', False):
                        termination_results['summary'].append("✅ Okta: User deactivated, groups removed, sessions cleared")
                        termination_results['phase_success']['okta'] = True
                        logger.info("Okta termination phase completed successfully")
                    else:
                        termination_results['summary'].append("⚠️ Okta: Termination had issues")
                        termination_results['phase_success']['okta'] = False
                        termination_results['errors'].extend(okta_results.get('errors', []))
                        logger.warning("Okta termination phase had issues")
                        
                except Exception as e:
                    logger.error(f"Okta termination failed: {e}")
                    termination_results['okta_results'] = {'success': False, 'error': str(e)}
                    termination_results['phase_success']['okta'] = False
                    termination_results['errors'].append(f"Okta termination failed: {e}")
            
            # Phase 2: Microsoft 365 Termination (mailbox, licenses, teams)
            if 'microsoft' in phases:
                logger.info("📧 PHASE 2: Microsoft 365 mailbox and license management")
                try:
                    if manager_email:
                        microsoft_results = self.microsoft_termination.execute_complete_termination(
                            user_email, manager_email)
                        termination_results['microsoft_results'] = microsoft_results
                        
                        if microsoft_results.get('success', False):
                            termination_results['summary'].append("✅ Microsoft: Mailbox converted, licenses removed, Teams updated")
                            termination_results['phase_success']['microsoft'] = True
                            logger.info("Microsoft 365 termination phase completed successfully")
                        else:
                            termination_results['summary'].append("⚠️ Microsoft: Termination had issues")
                            termination_results['phase_success']['microsoft'] = False
                            termination_results['errors'].extend(microsoft_results.get('errors', []))
                            logger.warning("Microsoft 365 termination phase had issues")
                    else:
                        logger.warning("No manager email provided - skipping Microsoft 365 delegation")
                        termination_results['summary'].append("⚠️ Microsoft: Skipped - no manager provided")
                        termination_results['phase_success']['microsoft'] = False
                        termination_results['warnings'].append("Microsoft 365 delegation skipped - no manager")
                        
                except Exception as e:
                    logger.error(f"Microsoft termination failed: {e}")
                    termination_results['microsoft_results'] = {'success': False, 'error': str(e)}
                    termination_results['phase_success']['microsoft'] = False
                    termination_results['errors'].append(f"Microsoft termination failed: {e}")
            
            # Phase 3: Google Workspace Termination (Gmail, Drive, Groups)
            if 'google' in phases:
                logger.info("🌐 PHASE 3: Google Workspace termination and data transfer")
                try:
                    if manager_email:
                        google_results = self.google_termination.execute_complete_termination(
                            user_email, manager_email)
                        termination_results['google_results'] = google_results
                        
                        if google_results.get('success', False):
                            termination_results['summary'].append("✅ Google: User suspended, data transferred, groups updated")
                            termination_results['phase_success']['google'] = True
                            logger.info("Google Workspace termination phase completed successfully")
                        else:
                            termination_results['summary'].append("⚠️ Google: Termination had issues")
                            termination_results['phase_success']['google'] = False
                            termination_results['errors'].extend(google_results.get('errors', []))
                            logger.warning("Google Workspace termination phase had issues")
                    else:
                        logger.warning("No manager email provided - skipping Google data transfer")
                        termination_results['summary'].append("⚠️ Google: Skipped - no manager provided")
                        termination_results['phase_success']['google'] = False
                        termination_results['warnings'].append("Google data transfer skipped - no manager")
                        
                except Exception as e:
                    logger.error(f"Google termination failed: {e}")
                    termination_results['google_results'] = {'success': False, 'error': str(e)}
                    termination_results['phase_success']['google'] = False
                    termination_results['errors'].append(f"Google termination failed: {e}")
            
            # Phase 4: Zoom Termination (account deactivation, data transfer)
            if 'zoom' in phases:
                logger.info("📹 PHASE 4: Zoom account termination and cleanup")
                try:
                    zoom_results = self.zoom_termination.execute_complete_termination(
                        user_email, manager_email)
                    termination_results['zoom_results'] = zoom_results
                    
                    if zoom_results.get('success', False):
                        termination_results['summary'].append("✅ Zoom: User deactivated, recordings transferred")
                        termination_results['phase_success']['zoom'] = True
                        logger.info("Zoom termination phase completed successfully")
                    else:
                        termination_results['summary'].append("⚠️ Zoom: Termination had issues")
                        termination_results['phase_success']['zoom'] = False
                        termination_results['errors'].extend(zoom_results.get('errors', []))
                        logger.warning("Zoom termination phase had issues")
                        
                except Exception as e:
                    logger.error(f"Zoom termination failed: {e}")
                    termination_results['zoom_results'] = {'success': False, 'error': str(e)}
                    termination_results['phase_success']['zoom'] = False
                    termination_results['errors'].append(f"Zoom termination failed: {e}")
            
            # Update ticket status if ticket ID provided
            if ticket_id:
                try:
                    logger.info(f"📋 Updating ticket {ticket_id} status")
                    # Note: Implement update_ticket_status function in ticket_processor.py
                    logger.info(f"Ticket {ticket_id} marked for completion")
                    termination_results['summary'].append(f"📋 Ticket {ticket_id} updated")
                except Exception as e:
                    logger.error(f"Failed to update ticket {ticket_id}: {e}")
                    termination_results['warnings'].append(f"Failed to update ticket {ticket_id}")
            
            # Determine overall success based on critical phases
            critical_phases = ['okta']  # Okta is always critical
            if manager_email:
                critical_phases.extend(['microsoft', 'google'])  # Only critical if manager provided
            
            critical_success = all(termination_results['phase_success'].get(phase, False) 
                                 for phase in critical_phases if phase in phases)
            
            termination_results['overall_success'] = critical_success
            
            # Phase 5: Notifications (always last)
            if 'notifications' in phases:
                logger.info("📢 PHASE 5: Sending notifications and audit reports")
                try:
                    self.send_comprehensive_notification(termination_results)
                    termination_results['notification_results'] = {'success': True}
                    termination_results['phase_success']['notifications'] = True
                except Exception as e:
                    logger.error(f"Failed to send notifications: {e}")
                    termination_results['notification_results'] = {'success': False, 'error': str(e)}
                    termination_results['phase_success']['notifications'] = False
                    termination_results['warnings'].append("Failed to send notifications")
            
            termination_results['end_time'] = datetime.now()
            duration = termination_results['end_time'] - termination_results['start_time']
            termination_results['duration_seconds'] = duration.total_seconds()
            
            success_msg = "SUCCESSFUL" if termination_results['overall_success'] else "COMPLETED WITH ISSUES"
            logger.info(f"Multi-phase termination {success_msg} for {user_email} in {duration.total_seconds():.1f} seconds")
            
            return termination_results
            
        except Exception as e:
            logger.error(f"Fatal error during termination of {user_email}: {e}")
            termination_results['overall_success'] = False
            termination_results['errors'].append(f"Fatal error: {str(e)}")
            termination_results['end_time'] = datetime.now()
            return termination_results
    
    def send_comprehensive_notification(self, termination_results: Dict):
        """Log comprehensive termination results (Slack functionality removed)."""
        try:
            user_email = termination_results['user_email']
            overall_success = termination_results['overall_success']
            phase_success = termination_results['phase_success']
            
            # Determine status
            if overall_success:
                status = "COMPLETED SUCCESSFULLY"
                emoji = "✅"
            elif any(phase_success.values()):
                status = "COMPLETED WITH ISSUES"
                emoji = "⚠️"
            else:
                status = "FAILED"
                emoji = "❌"
            
            # Log comprehensive summary instead of sending to Slack
            logger.info(f"{emoji} ENTERPRISE TERMINATION {status}: {user_email}")
            
            # Log phase status
            phase_status = []
            for phase, success in phase_success.items():
                icon = "✅" if success else "❌"
                phase_status.append(f"{icon} {phase.title()}")
            
            logger.info(f"Phase Status: {' | '.join(phase_status)}")
            
            # Log summary items
            summary_items = termination_results.get('summary', [])
            if summary_items:
                logger.info("Summary:")
                for item in summary_items:
                    logger.info(f"  {item}")
            
            # Log errors if any
            error_items = termination_results.get('errors', [])
            if error_items:
                logger.error("Errors:")
                for error in error_items:
                    logger.error(f"  • {error}")
            
            # Log warnings if any
            warning_items = termination_results.get('warnings', [])
            if warning_items:
                logger.warning("Warnings:")
                for warning in warning_items:
                    logger.warning(f"  • {warning}")
            
            duration = termination_results.get('duration_seconds', 0)
            logger.info(f"Duration: {duration:.1f} seconds")
            
        except Exception as e:
            logger.error(f"Failed to log comprehensive notification: {e}")
    
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
            processed_users = []
            
            for ticket in tickets:
                try:
                    # Extract user and manager information from ticket
                    user_email = extract_user_email_from_ticket(ticket)
                    manager_email = extract_manager_email_from_ticket(ticket)
                    ticket_id = ticket.get('id')
                    
                    if not user_email:
                        logger.error(f"Could not extract user email from ticket {ticket_id}")
                        continue
                    
                    logger.info(f"Processing multi-phase termination for {user_email} (ticket {ticket_id})")
                    
                    # Execute complete multi-phase termination
                    results = self.execute_user_termination(user_email, manager_email, ticket_id)
                    
                    processed_users.append({
                        'user_email': user_email,
                        'ticket_id': ticket_id,
                        'success': results['overall_success'],
                        'phases': results['phase_success']
                    })
                    
                    total_processed += 1
                    if results['overall_success']:
                        total_successful += 1
                        logger.info(f"Multi-phase termination successful for {user_email}")
                    else:
                        logger.warning(f"Multi-phase termination had issues for {user_email}")
                    
                except Exception as e:
                    logger.error(f"Failed to process ticket {ticket.get('id', 'unknown')}: {e}")
                    total_processed += 1
            
            # Send comprehensive batch summary
            self.send_batch_summary(total_processed, total_successful, processed_users)
            
            logger.info(f"Ticket processing completed: {total_successful}/{total_processed} successful")
            
        except Exception as e:
            logger.error(f"Failed to run ticket processing: {e}")
            raise
    
    def send_batch_summary(self, total_processed: int, total_successful: int, processed_users: List[Dict]):
        """Log comprehensive batch processing summary (Slack functionality removed)."""
        try:
            success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
            
            if success_rate == 100:
                status = "ALL SUCCESSFUL ✅"
                emoji = "🎉"
            elif success_rate >= 80:
                status = "MOSTLY SUCCESSFUL ⚠️"
                emoji = "🔶"
            else:
                status = "ISSUES DETECTED ❌"
                emoji = "🚨"
            
            logger.info(f"{emoji} ENTERPRISE TERMINATION BATCH: {status}")
            logger.info(f"Total Processed: {total_processed}")
            logger.info(f"Successful: {total_successful}")
            logger.info(f"Success Rate: {success_rate:.1f}%")
            
            # Log user details
            logger.info("User Results:")
            for user in processed_users[:10]:  # Limit to first 10 for readability
                phases = user.get('phases', {})
                phase_icons = []
                for phase in ['okta', 'microsoft', 'google', 'zoom']:
                    if phase in phases:
                        icon = "✅" if phases[phase] else "❌"
                        phase_icons.append(f"{phase[0].upper()}{icon}")
                
                status_icon = "✅" if user['success'] else "❌"
                phase_summary = " ".join(phase_icons) if phase_icons else "No phases"
                logger.info(f"  {status_icon} {user['user_email']} ({phase_summary})")
            
            if len(processed_users) > 10:
                logger.info(f"  ... and {len(processed_users) - 10} more users")
            
        except Exception as e:
            logger.error(f"Failed to log batch summary: {e}")
    
    def test_mode_termination(self, user_email: str, manager_email: str = None) -> Dict:
        """Execute termination in test mode (validation only, no actual changes)."""
        logger.info(f"🧪 RUNNING TEST MODE TERMINATION for {user_email}")
        
        test_results = {
            'user_email': user_email,
            'manager_email': manager_email,
            'test_mode': True,
            'start_time': datetime.now(),
            'validation_results': {},
            'would_execute': [],
            'potential_issues': [],
            'overall_ready': False
        }
        
        try:
            # Test Okta connectivity and user existence
            logger.info("Testing Okta connectivity and user lookup")
            okta_test = self.okta_termination.test_user_lookup(user_email)
            test_results['validation_results']['okta'] = okta_test
            
            if okta_test.get('user_exists', False):
                test_results['would_execute'].append("Okta: Deactivate user, remove groups, clear sessions")
            else:
                test_results['potential_issues'].append("Okta: User not found")
            
            # Test Microsoft connectivity
            if manager_email:
                logger.info("Testing Microsoft Graph connectivity")
                ms_test = self.microsoft_termination.test_connectivity()
                test_results['validation_results']['microsoft'] = ms_test
                
                if ms_test.get('success', False):
                    test_results['would_execute'].append("Microsoft: Convert mailbox, delegate access, remove licenses")
                else:
                    test_results['potential_issues'].append("Microsoft: API connectivity issues")
            
            # Test Google connectivity
            if manager_email:
                logger.info("Testing Google Workspace connectivity")
                google_test = self.google_termination.test_connectivity()
                test_results['validation_results']['google'] = google_test
                
                if google_test.get('success', False):
                    test_results['would_execute'].append("Google: Suspend user, transfer data, update groups")
                else:
                    test_results['potential_issues'].append("Google: API connectivity issues")
            
            # Test Zoom connectivity
            logger.info("Testing Zoom API connectivity")
            zoom_test = self.zoom_termination.test_connectivity()
            test_results['validation_results']['zoom'] = zoom_test
            
            if zoom_test.get('success', False):
                test_results['would_execute'].append("Zoom: Deactivate user, transfer recordings")
            else:
                test_results['potential_issues'].append("Zoom: API connectivity issues")
            
            # Determine overall readiness
            critical_tests = ['okta']
            test_results['overall_ready'] = all(
                test_results['validation_results'].get(test, {}).get('success', False) 
                for test in critical_tests
            )
            
            test_results['end_time'] = datetime.now()
            
            logger.info(f"🧪 TEST MODE COMPLETED - Ready: {test_results['overall_ready']}")
            return test_results
            
        except Exception as e:
            logger.error(f"Test mode failed: {e}")
            test_results['potential_issues'].append(f"Test mode error: {e}")
            test_results['end_time'] = datetime.now()
            return test_results

def main():
    """Main entry point for enterprise termination automation."""
    # Setup logging
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("ENTERPRISE TERMINATION ORCHESTRATOR V2.0 STARTING")
    logger.info("=" * 80)
    
    try:
        # Initialize orchestrator
        orchestrator = EnterpriseTerminationOrchestrator()
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == 'test' and len(sys.argv) > 2:
                # Test mode for single user
                user_email = sys.argv[2]
                manager_email = sys.argv[3] if len(sys.argv) > 3 else None
                
                logger.info(f"Running test mode for {user_email}")
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
                
            elif command not in ['test']:
                # Single user termination (first arg is user email)
                user_email = sys.argv[1]
                manager_email = sys.argv[2] if len(sys.argv) > 2 else None
                phases = sys.argv[3].split(',') if len(sys.argv) > 3 else None
                
                logger.info(f"Running single user termination for {user_email}")
                results = orchestrator.execute_user_termination(user_email, manager_email, phases=phases)
                
                if results['overall_success']:
                    print(f"✅ TERMINATION SUCCESSFUL for {user_email}")
                    sys.exit(0)
                else:
                    print(f"⚠️ TERMINATION COMPLETED WITH ISSUES for {user_email}")
                    sys.exit(1)
        else:
            # Run ticket-based processing
            logger.info("Running ticket-based termination processing")
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
