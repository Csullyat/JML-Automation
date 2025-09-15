#!/usr/bin/env python3
"""
Test the comprehensive termination workflow from ticket number.
This tests the complete end-to-end process.
"""

import sys
import os
sys.path.append('src')

from jml_automation.workflows.termination import TerminationWorkflow

def test_comprehensive_termination_workflow():
    """Test the complete workflow with ticket 64570."""
    print(" TESTING COMPREHENSIVE TERMINATION WORKFLOW")
    print("=" * 60)
    print("This will execute the complete termination process:")
    print("• Okta (find, clear sessions, deactivate, remove groups)")
    print("• Exchange (convert to shared, delegate)")
    print("• M365 (revoke licenses, remove groups)")
    print("• Google (transfer data, delete user)")
    print("• Zoom (transfer data, delete user)")
    print("• Domo (delete user)")
    print("• Lucid (transfer data, delete user, remove groups)")
    print("• SYNQ Prox (delete user)")
    print("=" * 60)
    
    # Use ticket 64570 for testing
    ticket_id = "64570"
    
    try:
        # Initialize the termination workflow
        print(" Initializing termination workflow...")
        workflow = TerminationWorkflow()
        
        # Execute the comprehensive termination
        print(f" Executing comprehensive termination for ticket {ticket_id}...")
        print("   This may take several minutes...")
        
        result = workflow.execute_comprehensive_termination_from_ticket(ticket_id)
        
        # Display results
        print("\\n" + "=" * 60)
        print(" COMPREHENSIVE TERMINATION RESULTS")
        print("=" * 60)
        
        print(f"Ticket: Ticket ID: {result.get('ticket_id')}")
        print(f"User: User Email: {result.get('user_email')}")
        print(f"Manager: Manager Email: {result.get('manager_email', 'None')}")
        print(f"  Duration: {result.get('duration', 0):.1f} seconds")
        print(f"SUCCESS: Overall Success: {result.get('overall_success')}")
        
        print("\\n SYSTEM BREAKDOWN:")
        system_results = result.get('system_results', {})
        for system, sys_result in system_results.items():
            status = "SUCCESS:" if sys_result.get('success') else "ERROR:"
            message = sys_result.get('message', 'No message')
            print(f"   {status} {system.upper()}: {message}")
        
        print(f"\\n SUMMARY ({len(result.get('summary', []))}):")
        for summary_item in result.get('summary', []):
            print(f"   {summary_item}")
        
        if result.get('warnings'):
            print(f"\\nWARNING:  WARNINGS ({len(result.get('warnings'))}):")
            for warning in result.get('warnings'):
                print(f"   - {warning}")
        
        if result.get('errors'):
            print(f"\\nERROR: ERRORS ({len(result.get('errors'))}):")
            for error in result.get('errors'):
                print(f"   - {error}")
        
        success = result.get('overall_success', False)
        print(f"\\n FINAL RESULT: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            print("\\n COMPREHENSIVE TERMINATION COMPLETED!")
            print("   All critical systems processed successfully")
        else:
            print("\\nFAILED: COMPREHENSIVE TERMINATION FAILED")
            print("   Check errors above for details")
        
        return success
        
    except Exception as e:
        print(f"\\nERROR: Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_comprehensive_termination_workflow()
    print(f"\\n Test Result: {'PASSED' if success else 'FAILED'}")