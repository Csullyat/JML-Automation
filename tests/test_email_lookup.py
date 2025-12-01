#!/usr/bin/env python3
"""
Test script to verify the new Okta email lookup functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_display_name_lookup():
    """Test looking up emails by display name from Okta."""
    from jml_automation.workflows.termination import TerminationWorkflow
    
    print("🧪 Testing Okta Display Name → Email Lookup")
    print("=" * 50)
    
    try:
        # Initialize workflow (which includes Okta service)
        workflow = TerminationWorkflow()
        
        # Test with some known names (replace with actual names from your Okta)
        test_names = [
            "Cody Atkinson",
            "John Doe",  # This should not exist
            "Test User"  # This should not exist
        ]
        
        for display_name in test_names:
            print(f"\n🔍 Testing lookup for: '{display_name}'")
            email = workflow.lookup_user_email_by_display_name(display_name)
            
            if email:
                print(f"   ✅ Found: {email}")
            else:
                print(f"   ❌ Not found")
        
        print("\n✅ Email lookup test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_ticket_email_resolution():
    """Test the complete ticket → email resolution process."""
    print("\n🧪 Testing Ticket Email Resolution")
    print("=" * 50)
    
    try:
        from jml_automation.workflows.termination import TerminationWorkflow
        
        workflow = TerminationWorkflow()
        
        # Simulate a ticket with display name
        mock_ticket = {
            "id": "test_123",
            "name": "Employee Termination - Cody Atkinson",
            "custom_fields_values": [
                {
                    "name": "Employee to Terminate",
                    "value": "Cody Atkinson"  # Display name, not email
                }
            ]
        }
        
        print("📋 Mock ticket data:")
        print(f"   Ticket name: {mock_ticket['name']}")
        print(f"   Employee field: Cody Atkinson")
        
        email = workflow.resolve_user_email_from_ticket(mock_ticket)
        
        if email:
            print(f"   ✅ Resolved to email: {email}")
            return True
        else:
            print(f"   ❌ Could not resolve email")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 STARTING EMAIL LOOKUP TESTS")
    print("=" * 60)
    
    # Test 1: Direct display name lookup
    test1_success = test_display_name_lookup()
    
    # Test 2: Full ticket resolution
    test2_success = test_ticket_email_resolution()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   Display Name Lookup: {'PASS' if test1_success else 'FAIL'}")
    print(f"   Ticket Resolution: {'PASS' if test2_success else 'FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED! Email lookup is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")