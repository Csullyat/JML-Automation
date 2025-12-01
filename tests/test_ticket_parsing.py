#!/usr/bin/env python3

from jml_automation.parsers.solarwinds_parser import fetch_ticket, parse_ticket
from jml_automation.workflows.termination import TerminationWorkflow

def test_ticket_69988_parsing():
    """Test the complete parsing and email resolution for ticket 69988"""
    
    print("=== TICKET 69988 COMPLETE TEST ===")
    
    try:
        # Step 1: Fetch raw ticket
        print("1. Fetching ticket 69988...")
        raw_ticket = fetch_ticket("69988")
        print(f"   Raw ticket ID: {raw_ticket.get('id', 'N/A')}")
        print(f"   Raw ticket name: {raw_ticket.get('name', 'N/A')}")
        
        # Step 2: Parse ticket 
        print("\n2. Parsing ticket...")
        parsed_ticket = parse_ticket(raw_ticket)
        print(f"   Parsed user email: {parsed_ticket.user.email if parsed_ticket.user else 'N/A'}")
        print(f"   Parsed user name: {parsed_ticket.user.first_name} {parsed_ticket.user.last_name}")
        
        # Step 3: Test workflow email resolution
        print("\n3. Testing workflow email resolution...")
        workflow = TerminationWorkflow()
        
        # Test the enhanced resolution method
        resolved_email = workflow.resolve_user_email_from_ticket(raw_ticket)
        print(f"   Workflow resolved email: {resolved_email}")
        
        # Step 4: Test display name lookup specifically
        print("\n4. Testing display name lookup...")
        ticket_name = raw_ticket.get("name", "")
        if "Employee Termination" in ticket_name:
            display_name = ticket_name.replace("Employee Termination - ", "").strip()
            print(f"   Extracted display name: '{display_name}'")
            
            lookup_result = workflow.lookup_user_email_by_display_name(display_name)
            print(f"   Display name lookup result: {lookup_result}")
        
        # Final result
        print(f"\n=== FINAL RESULT ===")
        final_email = parsed_ticket.user.email if parsed_ticket.user else resolved_email
        print(f"Email that would be used: {final_email}")
        
        if final_email == "christophernielsen@filevine.com":
            print("✅ SUCCESS: Correct email found!")
        elif final_email == "chrisnielsen@filevine.com":
            print("❌ FAILURE: Wrong email found!")
        elif not final_email:
            print("⚠️  WARNING: No email found!")
        else:
            print(f"🤔 UNKNOWN: Unexpected email: {final_email}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_ticket_69988_parsing()