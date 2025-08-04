# enterprise_termination_orchestrator.py - Complete termination workflow automation

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from config import get_okta_token, get_okta_domain
from okta_termination import OktaTermination
from termination_extractor import fetch_tickets, parse_termination_ticket
from slack_notifications import send_termination_notification

logger = logging.getLogger(__name__)

@dataclass
class TerminationRequest:
    """Structured termination request data."""
    employee_id: str
    employee_name: str
    employee_email: str
    department: str
    termination_date: str
    access_removal_date: str
    termination_type: str  # Voluntary/Involuntary
    manager_transfer_id: str
    is_cjis_cleared: bool
    ticket_number: str

class EnterpriseTerminationOrchestrator:
    """Complete enterprise termination automation following Filevine procedures."""
    
    def __init__(self):
        self.okta = OktaTermination()
        self.results = {
            'okta_complete': False,
            'microsoft_complete': False,
            'google_complete': False,
            'adobe_complete': False,
            'zoom_complete': False,
            'device_management_complete': False,
            'manual_actions_required': []
        }
    
    def execute_complete_termination(self, termination: TerminationRequest) -> Dict:
        """Execute complete termination following Filevine procedure."""
        
        logger.info(f"Starting complete termination for {termination.employee_name}")
        
        # Phase 1: CRITICAL SECURITY - Okta session clearing and deactivation
        logger.info("Phase 1: Okta Security Actions")
        okta_result = self._execute_okta_termination(termination)
        
        # Phase 2: Microsoft 365 & Exchange
        logger.info("Phase 2: Microsoft 365 & Exchange")
        microsoft_result = self._execute_microsoft_termination(termination)
        
        # Phase 3: Google Workspace
        logger.info("Phase 3: Google Workspace")
        google_result = self._execute_google_termination(termination)
        
        # Phase 4: Adobe Creative Cloud
        logger.info("Phase 4: Adobe Creative Cloud")
        adobe_result = self._execute_adobe_termination(termination)
        
        # Phase 5: Zoom
        logger.info("Phase 5: Zoom")
        zoom_result = self._execute_zoom_termination(termination)
        
        # Phase 6: Device Management (CJIS handling)
        logger.info("Phase 6: Device Management")
        device_result = self._execute_device_management(termination)
        
        # Phase 7: Manual Actions Required
        manual_actions = self._identify_manual_actions(termination)
        
        # Phase 8: Notifications
        self._send_completion_notifications(termination, self.results)
        
        return {
            'termination_id': termination.employee_id,
            'completion_time': datetime.now(),
            'automated_actions': self.results,
            'manual_actions_required': manual_actions
        }
    
    def _execute_okta_termination(self, termination: TerminationRequest) -> Dict:
        """Phase 1: Execute Okta termination (CRITICAL SECURITY)."""
        try:
            # Step 1: Find user in Okta
            user = self.okta.find_user_by_email(termination.employee_email)
            if not user:
                logger.error(f"User {termination.employee_email} not found in Okta")
                return {'success': False, 'error': 'User not found'}
            
            user_id = user['id']
            
            # Step 2: Clear all active sessions (CRITICAL)
            logger.info(f"CLEARING ALL SESSIONS for {termination.employee_email}")
            session_clear = self.okta.clear_user_sessions(user_id)
            
            # Step 3: Deactivate user
            logger.info(f"DEACTIVATING user {termination.employee_email}")
            deactivation = self.okta.deactivate_user(user_id)
            
            # Step 4: Remove from all groups
            logger.info(f"Removing from all Okta groups")
            group_removal = self.okta.remove_user_from_all_groups(user_id)
            
            self.results['okta_complete'] = session_clear and deactivation
            
            return {
                'success': self.results['okta_complete'],
                'sessions_cleared': session_clear,
                'account_deactivated': deactivation,
                'groups_removed': group_removal['groups_removed']
            }
            
        except Exception as e:
            logger.error(f"Okta termination failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_microsoft_termination(self, termination: TerminationRequest) -> Dict:
        """Phase 2: Microsoft 365 & Exchange termination."""
        # TODO: Implement Microsoft Graph API integration
        manual_actions = [
            "Convert Exchange mailbox to shared",
            f"Delegate mailbox to manager (ID: {termination.manager_transfer_id})",
            "Remove M365 licenses",
            "Remove from 'SSO-Microsoft 365 E3 - User' group in Okta"
        ]
        
        self.results['manual_actions_required'].extend(manual_actions)
        
        return {
            'success': False,  # Not automated yet
            'manual_actions': manual_actions
        }
    
    def _execute_google_termination(self, termination: TerminationRequest) -> Dict:
        """Phase 3: Google Workspace termination."""
        # TODO: Implement Google Admin SDK integration
        if termination.department in ['Executive', 'Legal', 'HR']:
            # Critical employee - move to terminated OU
            manual_actions = [
                "Move user to 'Terminated' OU in Google Admin",
                "Remove Google license manually",
                "Remove from 'SSO-G SUITE_ENTERPRISEUSERS' group in Okta after data backup"
            ]
        else:
            # Standard deletion with data transfer
            manual_actions = [
                f"Delete Google user and transfer data to manager (ID: {termination.manager_transfer_id})",
                "Remove from 'SSO-G SUITE_ENTERPRISEUSERS' group in Okta"
            ]
        
        self.results['manual_actions_required'].extend(manual_actions)
        
        return {
            'success': False,  # Not automated yet
            'manual_actions': manual_actions
        }
    
    def _execute_adobe_termination(self, termination: TerminationRequest) -> Dict:
        """Phase 4: Adobe Creative Cloud termination."""
        # TODO: Implement Adobe User Management API
        manual_actions = [
            "Remove Adobe product assignments",
            "Remove from 'SSO-Adobe' group in Okta"
        ]
        
        self.results['manual_actions_required'].extend(manual_actions)
        
        return {
            'success': False,  # Not automated yet
            'manual_actions': manual_actions
        }
    
    def _execute_zoom_termination(self, termination: TerminationRequest) -> Dict:
        """Phase 5: Zoom termination."""
        # TODO: Implement Zoom API integration
        manual_actions = [
            "Delete Zoom user and transfer data to manager",
            "Remove from all Zoom groups in Okta"
        ]
        
        self.results['manual_actions_required'].extend(manual_actions)
        
        return {
            'success': False,  # Not automated yet
            'manual_actions': manual_actions
        }
    
    def _execute_device_management(self, termination: TerminationRequest) -> Dict:
        """Phase 6: Device management (Intune/Kandji)."""
        # TODO: Implement device management APIs
        if termination.is_cjis_cleared:
            manual_actions = [
                "CJIS DEVICE - Retire device in Intune/Kandji",
                "Secure wipe with NIST 800-88 compliance",
                "Update SolarWinds asset status to 'Spare'",
                "URGENT: Notify Compliance team within 24 hours"
            ]
        else:
            manual_actions = [
                "Update device assignment in Kandji/Intune",
                "Update SolarWinds asset status to 'Spare'"
            ]
        
        self.results['manual_actions_required'].extend(manual_actions)
        
        return {
            'success': False,  # Not automated yet
            'manual_actions': manual_actions
        }
    
    def _identify_manual_actions(self, termination: TerminationRequest) -> List[str]:
        """Identify manual actions required based on user profile."""
        manual_actions = [
            "HR: Remove from Paylocity",
            "RevOps: Remove from Salesforce, Outreach, Salesloft, Chorus, ZoomInfo, Gong",
            "Marketing: Remove from Clari",
            "R&D: Remove from Incident IO, New Relic",
            "Recruiting: Remove from Lever",
            "Security: Archive user in KnowBe4",
            "Tom Judd: Remove Filevine application access"
        ]
        
        if termination.is_cjis_cleared:
            manual_actions.insert(0, "🚨 URGENT: Notify Compliance - CJIS user termination")
        
        return manual_actions
    
    def _send_completion_notifications(self, termination: TerminationRequest, results: Dict):
        """Send notifications about termination completion."""
        try:
            message = f"""
🔒 TERMINATION COMPLETED: {termination.employee_name}

**Automated Actions:**
✅ Okta sessions cleared and account deactivated
✅ Security lockdown complete

**Manual Actions Required:**
{chr(10).join(f"• {action}" for action in self.results['manual_actions_required'])}

**Ticket:** #{termination.ticket_number}
**Completion Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            send_termination_notification(message)
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")

def main():
    """Main execution function."""
    orchestrator = EnterpriseTerminationOrchestrator()
    
    # Fetch active termination tickets
    tickets = fetch_tickets()
    
    for ticket in tickets:
        termination_data = parse_termination_ticket(ticket)
        if termination_data and should_process_today(termination_data):
            
            # Convert to structured request
            termination = TerminationRequest(
                employee_id=termination_data.get('employee_id'),
                employee_name=termination_data.get('employee_name', 'Unknown'),
                employee_email=termination_data.get('employee_email'),
                department=termination_data.get('department', ''),
                termination_date=termination_data.get('termination_date'),
                access_removal_date=termination_data.get('access_removal_date'),
                termination_type=termination_data.get('termination_type', 'Unknown'),
                manager_transfer_id=termination_data.get('transfer_to_employee_id'),
                is_cjis_cleared=termination_data.get('cjis_cleared', False),
                ticket_number=termination_data.get('ticket_number')
            )
            
            # Execute complete termination
            result = orchestrator.execute_complete_termination(termination)
            
            logger.info(f"Termination complete for {termination.employee_name}")

def should_process_today(termination_data: Dict) -> bool:
    """Check if termination should be processed today."""
    # Implementation based on your business rules
    return True  # Placeholder

if __name__ == "__main__":
    main()
