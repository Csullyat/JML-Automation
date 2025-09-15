# src/jml_automation/workflows/single_ticket.py

import logging
from datetime import datetime
from typing import Dict, Optional

from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, extract_manager_email_from_ticket
from jml_automation.services.okta import OktaService
from jml_automation.services.microsoft import MicrosoftTermination
from jml_automation.services.google import GoogleTerminationManager
from jml_automation.services.zoom import ZoomTerminationManager
from jml_automation.services.domo import DomoService
from jml_automation.services.lucid import LucidService
from jml_automation.services.synqprox import SynqProxService

logger = logging.getLogger(__name__)

class SingleTicketWorkflow:
    """Workflow for processing individual termination tickets with dry run and production modes."""
    
    def __init__(self):
        """Initialize the single ticket workflow."""
        self.logger = logger
        
    def execute_single_ticket_dry_run(self, ticket_id: str) -> Dict:
        """
        Execute dry run mode for a single ticket - tests connectivity without making changes.
        
        Args:
            ticket_id: The ticket ID to process
            
        Returns:
            Dict with connectivity test results
        """
        self.logger.info(f"STARTING DRY RUN for ticket {ticket_id}")
        start_time = datetime.now()
        
        results = {
            'ticket_id': ticket_id,
            'mode': 'dry_run',
            'overall_success': False,
            'user_email': None,
            'manager_email': None,
            'systems_tested': {},
            'errors': [],
            'warnings': [],
            'start_time': start_time
        }
        
        try:
            # STEP 1: Fetch ticket
            self.logger.info(f"STEP 1: Fetching ticket {ticket_id}")
            solarwinds = SolarWindsService.from_config()
            ticket_data = solarwinds.fetch_ticket(ticket_id)
            
            if not ticket_data:
                results['errors'].append(f"Could not fetch ticket {ticket_id}")
                return self._finalize_results(results)
            
            results['systems_tested']['solarwinds'] = {'status': 'connected', 'data': 'ticket_fetched'}
            self.logger.info(f"SUCCESS: Ticket fetched: {ticket_data.get('subject', 'No subject')}")
            
            # STEP 2: Extract emails
            self.logger.info("STEP 2: Extracting user and manager information")
            user_email = extract_user_email_from_ticket(ticket_data)
            manager_email = extract_manager_email_from_ticket(ticket_data)
            
            if not user_email:
                results['errors'].append("Could not extract user email from ticket")
                return self._finalize_results(results)
            
            results['user_email'] = user_email
            results['manager_email'] = manager_email
            self.logger.info(f"SUCCESS: Target user: {user_email}")
            if manager_email:
                self.logger.info(f"SUCCESS: Manager: {manager_email}")
            else:
                results['warnings'].append("No manager email found")
            
            # STEP 3-9: Test all system connectivity
            self._test_okta_connectivity(user_email, results)
            self._test_microsoft_connectivity(user_email, results)
            self._test_google_connectivity(user_email, results)
            self._test_zoom_connectivity(results)
            self._test_domo_connectivity(results)
            self._test_lucid_connectivity(results)
            self._test_synqprox_connectivity(results)
            
            # Determine overall success
            connected_systems = [name for name, data in results['systems_tested'].items() 
                               if data.get('status') == 'connected']
            failed_systems = [name for name, data in results['systems_tested'].items() 
                            if data.get('status') == 'failed']
            
            results['overall_success'] = len(failed_systems) == 0
            
            self.logger.info(f"DRY RUN COMPLETED: {len(connected_systems)}/{len(results['systems_tested'])} systems connected")
            
            return self._finalize_results(results)
            
        except Exception as e:
            self.logger.error(f"Fatal error in dry run: {e}")
            results['errors'].append(f"Fatal error: {str(e)}")
            return self._finalize_results(results)
    
    def execute_single_ticket_production(self, ticket_id: str) -> Dict:
        """
        Execute production mode for a single ticket - performs actual termination.
        
        Args:
            ticket_id: The ticket ID to process
            
        Returns:
            Dict with termination results
        """
        self.logger.info(f"STARTING PRODUCTION TERMINATION for ticket {ticket_id}")
        start_time = datetime.now()
        
        results = {
            'ticket_id': ticket_id,
            'mode': 'production',
            'overall_success': False,
            'user_email': None,
            'manager_email': None,
            'system_results': {},
            'summary': [],
            'errors': [],
            'warnings': [],
            'start_time': start_time
        }
        
        try:
            # STEP 1: Fetch ticket
            self.logger.info(f"STEP 1: Fetching termination ticket {ticket_id}")
            solarwinds = SolarWindsService.from_config()
            ticket_data = solarwinds.fetch_ticket(ticket_id)
            
            if not ticket_data:
                results['errors'].append(f"Could not fetch ticket {ticket_id}")
                return self._finalize_results(results)
            
            ticket_subject = ticket_data.get('subject', 'Unknown')
            self.logger.info(f"SUCCESS: Ticket fetched: {ticket_subject}")
            
            # STEP 2: Extract emails
            self.logger.info("STEP 2: Extracting user and manager information")
            user_email = extract_user_email_from_ticket(ticket_data)
            manager_email = extract_manager_email_from_ticket(ticket_data)
            
            if not user_email:
                results['errors'].append("Could not extract user email from ticket")
                return self._finalize_results(results)
            
            results['user_email'] = user_email
            results['manager_email'] = manager_email
            self.logger.info(f"SUCCESS: Target user: {user_email}")
            if manager_email:
                self.logger.info(f"SUCCESS: Manager: {manager_email}")
            else:
                self.logger.warning("WARNING: No manager email found")
            
            # STEP 3: Execute comprehensive termination
            self.logger.info(f"STEP 3: COMPREHENSIVE TERMINATION EXECUTION")
            
            # Import and use the existing comprehensive termination method
            from jml_automation.workflows.termination import TerminationWorkflow
            termination_workflow = TerminationWorkflow()
            
            termination_result = termination_workflow.execute_comprehensive_termination_from_ticket(ticket_id)
            
            # Map the termination result to our format
            results['system_results'] = termination_result.get('system_results', {})
            results['summary'] = termination_result.get('summary', [])
            results['errors'].extend(termination_result.get('errors', []))
            results['warnings'].extend(termination_result.get('warnings', []))
            results['overall_success'] = termination_result.get('overall_success', False)
            
            if results['overall_success']:
                self.logger.info(f"SUCCESS: Comprehensive termination completed for {user_email}")
            else:
                self.logger.warning(f"WARNING: Termination completed with issues for {user_email}")
            
            return self._finalize_results(results)
            
        except Exception as e:
            self.logger.error(f"Fatal error in production termination: {e}")
            results['errors'].append(f"Fatal error: {str(e)}")
            return self._finalize_results(results)
    
    def _test_okta_connectivity(self, user_email: str, results: Dict) -> None:
        """Test Okta connectivity."""
        self.logger.info("STEP 3: Testing Okta connectivity")
        try:
            okta = OktaService.from_config()
            user = okta.get_user_by_email(user_email)
            if user:
                results['systems_tested']['okta'] = {'status': 'connected', 'user_found': True}
                self.logger.info(f"SUCCESS: User found in Okta: {user.get('profile', {}).get('displayName', user_email)}")
            else:
                results['systems_tested']['okta'] = {'status': 'connected', 'user_found': False}
                results['warnings'].append(f"User {user_email} not found in Okta")
        except Exception as e:
            results['systems_tested']['okta'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Okta connectivity: {e}")
    
    def _test_microsoft_connectivity(self, user_email: str, results: Dict) -> None:
        """Test Microsoft/Exchange connectivity."""
        self.logger.info("STEP 4: Testing Microsoft/Exchange connectivity")
        try:
            microsoft = MicrosoftTermination()
            mailbox_status = microsoft.get_mailbox_status(user_email)
            if mailbox_status and "ERROR" not in mailbox_status:
                results['systems_tested']['microsoft'] = {'status': 'connected', 'mailbox_type': mailbox_status.strip()}
                self.logger.info(f"SUCCESS: Mailbox found: {mailbox_status.strip()}")
            else:
                results['systems_tested']['microsoft'] = {'status': 'connected', 'mailbox_status': 'uncertain'}
                results['warnings'].append("Microsoft mailbox status uncertain")
        except Exception as e:
            results['systems_tested']['microsoft'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Microsoft connectivity: {e}")
    
    def _test_google_connectivity(self, user_email: str, results: Dict) -> None:
        """Test Google Workspace connectivity."""
        self.logger.info("STEP 5: Testing Google Workspace connectivity")
        try:
            google = GoogleTerminationManager()
            user_info = google.find_user_by_email(user_email)
            if user_info:
                results['systems_tested']['google'] = {'status': 'connected', 'user_found': True}
                self.logger.info(f"SUCCESS: Google user found: {user_info.get('name', {}).get('fullName', user_email)}")
            else:
                results['systems_tested']['google'] = {'status': 'connected', 'user_found': False}
                results['warnings'].append("User not found in Google Workspace")
        except Exception as e:
            results['systems_tested']['google'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Google connectivity: {e}")
    
    def _test_zoom_connectivity(self, results: Dict) -> None:
        """Test Zoom connectivity."""
        self.logger.info("STEP 6: Testing Zoom connectivity")
        try:
            zoom = ZoomTerminationManager()
            connectivity = zoom.test_connectivity()
            if connectivity.get('success'):
                results['systems_tested']['zoom'] = {'status': 'connected'}
                self.logger.info("SUCCESS: Zoom API connection successful")
            else:
                results['systems_tested']['zoom'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"Zoom connectivity: {connectivity.get('error')}")
        except Exception as e:
            results['systems_tested']['zoom'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Zoom connectivity: {e}")
    
    def _test_domo_connectivity(self, results: Dict) -> None:
        """Test Domo connectivity."""
        self.logger.info("STEP 7: Testing Domo connectivity")
        try:
            domo = DomoService()
            connectivity = domo.test_connectivity()
            if connectivity.get('success'):
                results['systems_tested']['domo'] = {'status': 'connected'}
                self.logger.info("SUCCESS: Domo API connection successful")
            else:
                results['systems_tested']['domo'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"Domo connectivity: {connectivity.get('error')}")
        except Exception as e:
            results['systems_tested']['domo'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Domo connectivity: {e}")
    
    def _test_lucid_connectivity(self, results: Dict) -> None:
        """Test Lucidchart connectivity."""
        self.logger.info("STEP 8: Testing Lucid connectivity")
        try:
            lucid = LucidService()
            connectivity = lucid.test_connectivity()
            if connectivity.get('success'):
                results['systems_tested']['lucid'] = {'status': 'connected'}
                self.logger.info("SUCCESS: Lucid API connection successful")
            else:
                results['systems_tested']['lucid'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"Lucid connectivity: {connectivity.get('error')}")
        except Exception as e:
            results['systems_tested']['lucid'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Lucid connectivity: {e}")
    
    def _test_synqprox_connectivity(self, results: Dict) -> None:
        """Test SYNQ Prox connectivity."""
        self.logger.info("STEP 9: Testing SYNQ Prox connectivity")
        try:
            synqprox = SynqProxService()
            connectivity = synqprox.test_connectivity()
            if connectivity.get('success'):
                results['systems_tested']['synqprox'] = {'status': 'connected'}
                self.logger.info("SUCCESS: SYNQ Prox connection successful")
            else:
                results['systems_tested']['synqprox'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"SYNQ Prox connectivity: {connectivity.get('error')}")
        except Exception as e:
            results['systems_tested']['synqprox'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"SYNQ Prox connectivity: {e}")
    
    def _finalize_results(self, results: Dict) -> Dict:
        """Finalize results with timing and summary information."""
        end_time = datetime.now()
        results['end_time'] = end_time
        results['duration_seconds'] = (end_time - results['start_time']).total_seconds()
        
        return results
    
    def print_dry_run_summary(self, results: Dict) -> None:
        """Print a summary of dry run results."""
        print("=" * 70)
        print(" DRY RUN RESULTS SUMMARY")
        print("=" * 70)
        print(f"Ticket: {results['ticket_id']}")
        print(f"User: {results.get('user_email', 'Not found')}")
        print(f"Manager: {results.get('manager_email', 'Not found')}")
        
        connected_systems = [name for name, data in results['systems_tested'].items() 
                           if data.get('status') == 'connected']
        failed_systems = [name for name, data in results['systems_tested'].items() 
                        if data.get('status') == 'failed']
        
        print(f"SUCCESS: Connected Systems: {len(connected_systems)}/{len(results['systems_tested'])}")
        print(f"ERROR: Failed Systems: {len(failed_systems)}")
        
        print("\nSYSTEM STATUS:")
        for system, data in results['systems_tested'].items():
            status = "SUCCESS:" if data.get('status') == 'connected' else "ERROR:"
            print(f"   {status} {system.upper()}: {data.get('status')}")
        
        if results.get('warnings'):
            print(f"\nWARNING: WARNINGS ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"   - {warning}")
        
        if results.get('errors'):
            print(f"\nERROR: ERRORS ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"   - {error}")
        
        print(f"\nDRY RUN RESULT: {'SUCCESS' if results['overall_success'] else 'PARTIAL'}")
        
        if results['overall_success']:
            print("\nALL SYSTEMS CONNECTED SUCCESSFULLY!")
            print("   The comprehensive workflow is ready to execute")
        
        print(f"\nDRY RUN COMPLETED: {'SUCCESS' if results.get('overall_success') else 'PARTIAL'}")
    
    def print_production_summary(self, results: Dict) -> None:
        """Print a summary of production results."""
        print("=" * 70)
        print(" PRODUCTION TERMINATION RESULTS")
        print("=" * 70)
        print(f"Ticket: {results['ticket_id']}")
        print(f"User: {results.get('user_email', 'Not found')}")
        print(f"Manager: {results.get('manager_email', 'Not found')}")
        print(f"Duration: {results.get('duration_seconds', 0):.1f} seconds")
        print(f"Overall Success: {results.get('overall_success')}")
        
        if results.get('system_results'):
            print("\nSYSTEM BREAKDOWN:")
            for system, sys_result in results['system_results'].items():
                status = "SUCCESS:" if sys_result.get('success') else "ERROR:"
                print(f"   {status} {system.upper()}: {sys_result.get('success', False)}")
        
        if results.get('summary'):
            print(f"\nSUMMARY ({len(results['summary'])}):")
            for item in results['summary']:
                print(f"   - {item}")
        
        if results.get('warnings'):
            print(f"\nWARNING: WARNINGS ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"   - {warning}")
        
        if results.get('errors'):
            print(f"\nERROR: ERRORS ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"   - {error}")
        
        print(f"\nFINAL RESULT: {'SUCCESS' if results['overall_success'] else 'FAILED'}")


# Convenience functions for direct usage
def single_ticket_dry_run(ticket_id: str) -> Dict:
    """Execute dry run for a single ticket."""
    workflow = SingleTicketWorkflow()
    return workflow.execute_single_ticket_dry_run(ticket_id)

def single_ticket_production(ticket_id: str) -> Dict:
    """Execute production termination for a single ticket."""
    workflow = SingleTicketWorkflow()
    return workflow.execute_single_ticket_production(ticket_id)