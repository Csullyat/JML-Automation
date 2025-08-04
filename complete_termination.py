# complete_termination.py - Complete termination with Okta + Microsoft 365

import logging
from datetime import datetime
from typing import Dict, Optional
from termination_extractor import fetch_tickets, parse_termination_ticket
from okta_termination import OktaTermination
from microsoft_termination import MicrosoftTermination
from slack_notifications import send_termination_notification

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteTermination:
    """Complete termination automation - Okta + Microsoft 365."""
    
    def __init__(self):
        """Initialize termination systems."""
        self.okta = OktaTermination()
        self.microsoft = MicrosoftTermination()
    
    def execute_termination(self, user_email: str, manager_employee_id: str, test_mode: bool = True) -> Dict:
        """Execute complete termination for a user."""
        
        logger.info(f"Starting complete termination for {user_email}")
        
        if test_mode:
            logger.warning("🧪 TEST MODE - Limited actions will be performed")
        
        results = {
            'user_email': user_email,
            'termination_time': datetime.now(),
            'test_mode': test_mode,
            'okta_results': {},
            'microsoft_results': {},
            'overall_success': False
        }
        
        try:
            # Phase 1: CRITICAL SECURITY - Okta termination
            logger.info("Phase 1: Okta Security Actions")
            okta_results = self._execute_okta_termination(user_email, test_mode)
            results['okta_results'] = okta_results
            
            # Phase 2: Microsoft 365 termination
            logger.info("Phase 2: Microsoft 365 Actions")
            if not test_mode:
                microsoft_results = self.microsoft.execute_complete_termination(user_email, manager_employee_id)
                results['microsoft_results'] = microsoft_results
            else:
                logger.info("TEST MODE: Skipping Microsoft 365 changes")
                results['microsoft_results'] = {
                    'success': True,
                    'test_mode': True,
                    'actions_completed': [
                        '🧪 TEST: Would remove Microsoft 365 licenses',
                        '🧪 TEST: Would convert mailbox to shared',
                        f'🧪 TEST: Would delegate mailbox to manager (Employee ID: {manager_employee_id})',
                        '🧪 TEST: Would transfer OneDrive data to manager'
                    ]
                }
            
            # Determine overall success
            results['overall_success'] = (
                okta_results.get('success', False) and 
                results['microsoft_results'].get('success', False)
            )
            
            # Send notifications
            self._send_completion_notification(results)
            
            logger.info(f"Complete termination {'succeeded' if results['overall_success'] else 'completed with errors'} for {user_email}")
            return results
            
        except Exception as e:
            logger.error(f"Complete termination failed for {user_email}: {e}")
            results['error'] = str(e)
            return results
    
    def _execute_okta_termination(self, user_email: str, test_mode: bool) -> Dict:
        """Execute Okta termination."""
        try:
            if test_mode:
                # In test mode, just verify user exists
                user = self.okta.find_user_by_email(user_email)
                if user:
                    return {
                        'success': True,
                        'test_mode': True,
                        'user_found': True,
                        'user_status': user.get('status', 'Unknown'),
                        'actions_completed': [
                            '🧪 TEST: Would clear all active sessions',
                            '🧪 TEST: Would deactivate user account',
                            '🧪 TEST: Would remove from all groups'
                        ]
                    }
                else:
                    return {
                        'success': False,
                        'test_mode': True,
                        'user_found': False,
                        'error': 'User not found in Okta'
                    }
            else:
                # Production mode - actually perform actions
                user = self.okta.find_user_by_email(user_email)
                if not user:
                    return {'success': False, 'error': 'User not found in Okta'}
                
                user_id = user['id']
                
                # Clear sessions
                sessions_cleared = self.okta.clear_user_sessions(user_id)
                
                # Deactivate user
                user_deactivated = self.okta.deactivate_user(user_id)
                
                # Remove from groups
                group_removal = self.okta.remove_user_from_all_groups(user_id)
                
                return {
                    'success': sessions_cleared and user_deactivated,
                    'sessions_cleared': sessions_cleared,
                    'user_deactivated': user_deactivated,
                    'groups_removed': group_removal.get('groups_removed', 0),
                    'actions_completed': [
                        '✅ All active sessions cleared' if sessions_cleared else '❌ Failed to clear sessions',
                        '✅ User account deactivated' if user_deactivated else '❌ Failed to deactivate user',
                        f"✅ Removed from {group_removal.get('groups_removed', 0)} groups"
                    ]
                }
                
        except Exception as e:
            logger.error(f"Okta termination failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_completion_notification(self, results: Dict):
        """Send notification about termination completion."""
        try:
            user_email = results['user_email']
            test_mode = results.get('test_mode', False)
            overall_success = results['overall_success']
            
            status_icon = "✅" if overall_success else "⚠️"
            mode_text = " (TEST MODE)" if test_mode else ""
            
            message = f"""
{status_icon} TERMINATION COMPLETED{mode_text}: {user_email}

**Okta Actions:**
{chr(10).join(f"• {action}" for action in results['okta_results'].get('actions_completed', ['No actions recorded']))}

**Microsoft 365 Actions:**
{chr(10).join(f"• {action}" for action in results['microsoft_results'].get('actions_completed', ['No actions recorded']))}

**Completion Time:** {results['termination_time'].strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            if results['microsoft_results'].get('actions_failed'):
                message += f"\n\n**⚠️ Manual Actions Required:**\n"
                message += chr(10).join(f"• {action}" for action in results['microsoft_results']['actions_failed'])
            
            send_termination_notification(message)
            
        except Exception as e:
            logger.error(f"Failed to send completion notification: {e}")

def process_termination_tickets(test_mode: bool = True):
    """Process all active termination tickets."""
    logger.info("Processing termination tickets...")
    
    termination_system = CompleteTermination()
    
    # For now, let's manually specify termination details
    # In the future, this would come from parsing tickets
    
    test_terminations = [
        {
            'user_email': 'valeriebaird@filevine.com',  # We know this one exists
            'manager_employee_id': '7467777'  # From the ticket data
        }
    ]
    
    for termination in test_terminations:
        logger.info(f"Processing termination: {termination['user_email']}")
        
        result = termination_system.execute_termination(
            user_email=termination['user_email'],
            manager_employee_id=termination['manager_employee_id'],
            test_mode=test_mode
        )
        
        if result['overall_success']:
            logger.info(f"✅ Termination successful for {termination['user_email']}")
        else:
            logger.error(f"❌ Termination failed for {termination['user_email']}")

def main():
    """Main execution function."""
    print("=" * 60)
    print("COMPLETE TERMINATION AUTOMATION")
    print("Okta + Microsoft 365 Integration")
    print("=" * 60)
    
    # Run in test mode by default
    process_termination_tickets(test_mode=True)

if __name__ == "__main__":
    main()
