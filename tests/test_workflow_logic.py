#!/usr/bin/env python3

from jml_automation.parsers.solarwinds_parser import fetch_ticket, parse_ticket
from jml_automation.workflows.termination import TerminationWorkflow

def test_workflow_logic():
    """Test the workflow email resolution logic for ticket 69988"""
    
    print("=== WORKFLOW LOGIC TEST ===")
    
    try:
        # Simulate what happens in the workflow
        raw_ticket = fetch_ticket("69988")
        parsed_ticket = parse_ticket(raw_ticket)
        workflow = TerminationWorkflow()
        
        print(f"1. Parsed ticket email: '{parsed_ticket.user.email if parsed_ticket.user else 'None'}'")
        
        # This is the workflow logic
        user_email = parsed_ticket.user.email if parsed_ticket.user else None
        print(f"2. Initial user_email: '{user_email}'")
        
        if not user_email:
            print("3. No email in parsed ticket, resolving via workflow...")
            user_email = workflow.resolve_user_email_from_ticket(raw_ticket)
            print(f"4. Resolved user_email: '{user_email}'")
            
            # Handle employee ID lookups (with display name fallback) 
            if user_email and user_email.startswith("LOOKUP_EMPLOYEE_ID:"):
                print("5. Found employee ID lookup marker, processing...")
                employee_id = user_email.split(":", 1)[1]
                print(f"6. Employee ID: {employee_id}")
                user_email = workflow.okta.lookup_email_by_employee_id(employee_id)
                print(f"7. Employee ID lookup result: '{user_email}'")
                if not user_email:
                    print("8. Employee ID lookup failed, trying display name fallback...")
                    user_email = workflow.resolve_user_email_from_ticket(raw_ticket)
                    print(f"9. Display name fallback result: '{user_email}'")
        
        print(f"\n=== FINAL WORKFLOW RESULT ===")
        print(f"Email that would be used: '{user_email}'")
        
        if user_email == "christophernielsen@filevine.com":
            print("✅ SUCCESS: Correct email would be used!")
        elif user_email == "chrisnielsen@filevine.com":
            print("❌ FAILURE: Wrong email would be used!")
        elif not user_email:
            print("❌ FAILURE: No email would be found!")
        else:
            print(f"🤔 UNKNOWN: Unexpected email: {user_email}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_workflow_logic()