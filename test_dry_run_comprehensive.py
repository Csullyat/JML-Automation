#!/usr/bin/env python3
"""
DRY RUN TEST of the comprehensive termination workflow.
This will test all systems a        print("STEP 5: Testing Google Workspace connectivity (DRY RUN)")
        try:
            from jml_automation.services.google import GoogleTerminationManager
            google = GoogleTerminationManager()
            
            # Test by getting user info (read-only)
            user_info = google.find_user_by_email(user_email)
            if user_info:
                print(f"   SUCCESS: Google user found: {user_info.get('name', {}).get('fullName', user_email)}")
                results['systems_tested']['google'] = {'status': 'connected', 'user_found': True}
            else:
                print(f"   WARNING:  User {user_email} not found in Google Workspace")
                results['systems_tested']['google'] = {'status': 'connected', 'user_found': False}
                results['warnings'].append(f"User not found in Google Workspace") WITHOUT actually terminating anyone.
"""

import sys
import os
sys.path.append('src')

from jml_automation.workflows.termination import TerminationWorkflow
from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, extract_manager_email_from_ticket

def dry_run_comprehensive_workflow(ticket_id: str):
    """
    DRY RUN test of the comprehensive workflow.
    This will verify all systems can be reached and the workflow flows properly.
    NO ACTUAL TERMINATION WILL OCCUR.
    """
    print("=" * 70)
    print("=" * 70)
    
    results = {
        'ticket_id': ticket_id,
        'success': True,
        'systems_tested': {},
        'errors': [],
        'warnings': []
    }
    
    try:
        # STEP 1: Test SolarWinds ticket fetching
        print(f"STEP 1: Testing SolarWinds ticket fetch for {ticket_id}")
        solarwinds = SolarWindsService.from_config()
        ticket_data = solarwinds.fetch_ticket(ticket_id)
        
        if ticket_data:
            print(f"   SUCCESS: Ticket fetched: {ticket_data.get('subject', 'No subject')}")
            results['systems_tested']['solarwinds'] = {'status': 'connected', 'data': 'ticket_fetched'}
        else:
            print(f"   ERROR: Failed to fetch ticket {ticket_id}")
            results['errors'].append(f"Could not fetch ticket {ticket_id}")
            results['success'] = False
            return results
        
        # STEP 2: Test email extraction
        print("STEP 2: Testing email extraction from ticket")
        user_email = extract_user_email_from_ticket(ticket_data)
        manager_email = extract_manager_email_from_ticket(ticket_data)
        
        if user_email:
            print(f"   SUCCESS: Target user: {user_email}")
            results['user_email'] = user_email
        else:
            print("   ERROR: Could not extract user email")
            results['errors'].append("Email extraction failed")
            results['success'] = False
            return results
        
        if manager_email:
            print(f"   SUCCESS: Manager: {manager_email}")
            results['manager_email'] = manager_email
        else:
            print("   WARNING: No manager email found")
            results['warnings'].append("No manager email")
        
        # STEP 3: Test Okta connectivity
        print("STEP 3: Testing Okta connectivity (DRY RUN)")
        try:
            from jml_automation.services.okta import OktaService
            okta = OktaService.from_config()
            
            # Test connection by trying to find the user (read-only)
            user = okta.get_user_by_email(user_email)
            if user:
                print(f"   SUCCESS: User found in Okta: {user.get('profile', {}).get('displayName', user_email)}")
                print(f"   SUCCESS: Current status: {user.get('status', 'Unknown')}")
                results['systems_tested']['okta'] = {'status': 'connected', 'user_found': True}
            else:
                print(f"   WARNING: User {user_email} not found in Okta")
                results['systems_tested']['okta'] = {'status': 'connected', 'user_found': False}
                results['warnings'].append(f"User {user_email} not found in Okta")
                
        except Exception as e:
            print(f"   ERROR: Okta connection failed: {e}")
            results['systems_tested']['okta'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Okta connectivity: {e}")
        
        # STEP 4: Test Microsoft/Exchange connectivity
        print("STEP 4: Testing Microsoft/Exchange connectivity (DRY RUN)")
        try:
            from jml_automation.services.microsoft import MicrosoftTermination
            microsoft = MicrosoftTermination()
            
            # Test by checking mailbox status (read-only)
            mailbox_status = microsoft.get_mailbox_status(user_email)
            if mailbox_status and "ERROR" not in mailbox_status:
                print(f"   SUCCESS: Mailbox found: {mailbox_status.strip()}")
                results['systems_tested']['microsoft'] = {'status': 'connected', 'mailbox_type': mailbox_status.strip()}
            else:
                print(f"   WARNING: Mailbox status check: {mailbox_status}")
                results['systems_tested']['microsoft'] = {'status': 'connected', 'mailbox_status': 'uncertain'}
                results['warnings'].append(f"Microsoft mailbox status uncertain")
                
        except Exception as e:
            print(f"   ERROR: Microsoft connection failed: {e}")
            results['systems_tested']['microsoft'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Microsoft connectivity: {e}")
        
        # STEP 5: Test Google connectivity
        print("STEP 5: Testing Google Workspace connectivity (DRY RUN)")
        try:
            from jml_automation.services.google import GoogleTerminationManager
            google = GoogleTerminationManager()
            
            # Test by getting user info (read-only)
            user_info = google.find_user_by_email(user_email)
            if user_info:
                print(f"   SUCCESS: Google user found: {user_info.get('name', {}).get('fullName', user_email)}")
                results['systems_tested']['google'] = {'status': 'connected', 'user_found': True}
            else:
                print(f"   WARNING:  User {user_email} not found in Google Workspace")
                results['systems_tested']['google'] = {'status': 'connected', 'user_found': False}
                results['warnings'].append(f"User not found in Google Workspace")
                
        except Exception as e:
            print(f"   ERROR: Google connection failed: {e}")
            results['systems_tested']['google'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Google connectivity: {e}")
        
        # STEP 6: Test Zoom connectivity
        print(" STEP 6: Testing Zoom connectivity (DRY RUN)")
        try:
            from jml_automation.services.zoom import ZoomService
            zoom = ZoomService()
            
            # Test connectivity (would check if user exists)
            connectivity = zoom.test_connectivity()
            if connectivity.get('success'):
                print("   SUCCESS: Zoom API connection successful")
                results['systems_tested']['zoom'] = {'status': 'connected'}
            else:
                print(f"   ERROR: Zoom connectivity failed: {connectivity.get('error')}")
                results['systems_tested']['zoom'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"Zoom connectivity failed")
                
        except Exception as e:
            print(f"   ERROR: Zoom connection failed: {e}")
            results['systems_tested']['zoom'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Zoom connectivity: {e}")
        
        # STEP 7: Test Domo connectivity
        print(" STEP 7: Testing Domo connectivity (DRY RUN)")
        try:
            from jml_automation.services.domo import DomoService
            domo = DomoService()
            
            # Test connectivity
            connectivity = domo.test_connectivity()
            if connectivity.get('success'):
                print("   SUCCESS: Domo API connection successful")
                results['systems_tested']['domo'] = {'status': 'connected'}
            else:
                print(f"   ERROR: Domo connectivity failed: {connectivity.get('error')}")
                results['systems_tested']['domo'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"Domo connectivity failed")
                
        except Exception as e:
            print(f"   ERROR: Domo connection failed: {e}")
            results['systems_tested']['domo'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Domo connectivity: {e}")
        
        # STEP 8: Test Lucid connectivity
        print(" STEP 8: Testing Lucid connectivity (DRY RUN)")
        try:
            from jml_automation.services.lucid import LucidchartService
            lucid = LucidchartService()
            
            # Test connectivity
            connectivity = lucid.test_connectivity()
            if connectivity.get('success'):
                print("   SUCCESS: Lucid API connection successful")
                results['systems_tested']['lucid'] = {'status': 'connected'}
            else:
                print(f"   ERROR: Lucid connectivity failed: {connectivity.get('error')}")
                results['systems_tested']['lucid'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"Lucid connectivity failed")
                
        except Exception as e:
            print(f"   ERROR: Lucid connection failed: {e}")
            results['systems_tested']['lucid'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"Lucid connectivity: {e}")
        
        # STEP 9: Test SYNQ Prox connectivity
        print(" STEP 9: Testing SYNQ Prox connectivity (DRY RUN)")
        try:
            from jml_automation.services.synqprox import SynqProxService
            synq = SynqProxService()
            
            # Test connectivity (login test)
            connectivity = synq.test_connectivity()
            if connectivity.get('success'):
                print("   SUCCESS: SYNQ Prox connection successful")
                results['systems_tested']['synqprox'] = {'status': 'connected'}
            else:
                print(f"   ERROR: SYNQ Prox connectivity failed: {connectivity.get('error')}")
                results['systems_tested']['synqprox'] = {'status': 'failed', 'error': connectivity.get('error')}
                results['errors'].append(f"SYNQ Prox connectivity failed")
                
        except Exception as e:
            print(f"   ERROR: SYNQ Prox connection failed: {e}")
            results['systems_tested']['synqprox'] = {'status': 'failed', 'error': str(e)}
            results['errors'].append(f"SYNQ Prox connectivity: {e}")
        
        # SUMMARY
        print("\\n" + "=" * 70)
        print(" DRY RUN RESULTS SUMMARY")
        print("=" * 70)
        
        connected_systems = [sys for sys, data in results['systems_tested'].items() if data.get('status') == 'connected']
        failed_systems = [sys for sys, data in results['systems_tested'].items() if data.get('status') == 'failed']
        
        print(f"Ticket: Ticket: {ticket_id}")
        print(f"User: Target User: {results.get('user_email', 'Not found')}")
        print(f" Manager: {results.get('manager_email', 'Not found')}")
        print(f"SUCCESS: Connected Systems: {len(connected_systems)}/{len(results['systems_tested'])}")
        print(f"ERROR: Failed Systems: {len(failed_systems)}")
        
        print("\\n SYSTEM STATUS:")
        for system, data in results['systems_tested'].items():
            status_icon = "SUCCESS:" if data.get('status') == 'connected' else "ERROR:"
            print(f"   {status_icon} {system.upper()}: {data.get('status', 'unknown')}")
        
        if results['warnings']:
            print(f"\\nWARNING:  WARNINGS ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"   - {warning}")
        
        if results['errors']:
            print(f"\\nERROR: ERRORS ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"   - {error}")
        
        overall_success = len(failed_systems) == 0
        print(f"\\n DRY RUN RESULT: {'SUCCESS' if overall_success else 'PARTIAL SUCCESS'}")
        
        if overall_success:
            print("\\n ALL SYSTEMS CONNECTED SUCCESSFULLY!")
            print("   The comprehensive workflow is ready to execute")
        else:
            print("\\nWARNING:  SOME SYSTEMS FAILED TO CONNECT")
            print("   Review errors above before running actual workflow")
        
        results['overall_success'] = overall_success
        return results
        
    except Exception as e:
        print(f"\\nERROR: DRY RUN FAILED: {e}")
        results['errors'].append(f"Critical error: {e}")
        results['success'] = False
        return results

if __name__ == "__main__":
    # Test with ticket 64570 in DRY RUN mode
    ticket_id = "64570"
    print(f"\\n STARTING DRY RUN TEST WITH TICKET {ticket_id}")
    print("   NO ACTUAL TERMINATION WILL OCCUR")
    print("   TESTING SYSTEM CONNECTIVITY AND WORKFLOW ONLY")
    
    result = dry_run_comprehensive_workflow(ticket_id)
    
    print(f"\\n DRY RUN COMPLETED: {'SUCCESS' if result.get('overall_success') else 'PARTIAL'}")