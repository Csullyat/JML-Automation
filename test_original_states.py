#!/usr/bin/env python3
"""
Test script to check tickets in the original active states to see if they contain usernames.
"""

import logging
from datetime import datetime
from typing import List, Dict
from termination_extractor import fetch_tickets

# Set up basic logging for the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_original_states():
    """Test tickets in the original active states."""
    print("=" * 80)
    print("TESTING ORIGINAL ACTIVE STATES FOR USERNAME FORMAT")
    print("=" * 80)
    
    try:
        # Step 1: Fetch all tickets
        print("\nStep 1: Fetching all termination tickets...")
        all_tickets = fetch_tickets()
        print(f"Fetched {len(all_tickets)} total tickets")
        
        # Step 2: Check original active states
        original_active_states = {"New", "Assigned", "Auto-Assigned", "In Progress"}
        current_active_states = {"Awaiting Input"}
        
        original_tickets = [t for t in all_tickets if t.get('state') in original_active_states]
        current_tickets = [t for t in all_tickets if t.get('state') in current_active_states]
        
        print(f"\nOriginal Active States: {len(original_tickets)} tickets")
        print(f"Current Active States (Awaiting Input): {len(current_tickets)} tickets")
        
        # Step 3: Analyze ticket states
        states = {}
        for ticket in all_tickets:
            state = ticket.get('state', 'Unknown')
            states[state] = states.get(state, 0) + 1
        
        print(f"\nAll Ticket States:")
        for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {state}: {count}")
        
        # Step 4: Parse tickets from original states
        print(f"\nAnalyzing tickets from original active states...")
        
        def parse_ticket_simple(ticket):
            """Simple ticket parser like the original."""
            out = {
                "ticket_number": ticket.get("number"),
                "ticket_state": ticket.get("state"),
                "employee_to_terminate": None,
                "transfer_data": None
            }
            
            for f in ticket.get("custom_fields_values", []):
                label = f.get("name", "").strip()
                val = f.get("value", "").strip()
                
                if not val:
                    continue
                    
                if label == "Employee to Terminate":
                    out["employee_to_terminate"] = val
                elif label == "Transfer Data":
                    out["transfer_data"] = val
            
            return out
        
        # Parse original state tickets
        parsed_original = []
        for ticket in original_tickets:
            parsed = parse_ticket_simple(ticket)
            if parsed["employee_to_terminate"]:
                parsed_original.append(parsed)
        
        print(f"Found {len(parsed_original)} original state tickets with employee data")
        
        # Parse current state tickets
        parsed_current = []
        for ticket in current_tickets:
            parsed = parse_ticket_simple(ticket)
            if parsed["employee_to_terminate"]:
                parsed_current.append(parsed)
        
        print(f"Found {len(parsed_current)} current state tickets with employee data")
        
        # Step 5: Compare data formats
        print(f"\nDATA FORMAT COMPARISON:")
        print(f"=" * 60)
        
        print(f"\nORIGINAL ACTIVE STATES ({len(parsed_original)} tickets):")
        for i, ticket in enumerate(parsed_original[:5]):  # Show first 5
            employee = ticket["employee_to_terminate"]
            transfer = ticket["transfer_data"]
            print(f"  Ticket #{ticket['ticket_number']} ({ticket['ticket_state']})")
            print(f"    Employee: {employee}")
            print(f"    Transfer: {transfer}")
            
            # Check if it looks like username vs employee ID
            if employee:
                if employee.isdigit():
                    print(f"    -> Employee ID format (numeric)")
                elif any(c.isalpha() for c in employee):
                    print(f"    -> Username format (contains letters)")
                else:
                    print(f"    -> Unknown format")
            print()
        
        if len(parsed_original) > 5:
            print(f"  ... and {len(parsed_original) - 5} more")
        
        print(f"\nCURRENT ACTIVE STATES ({len(parsed_current)} tickets):")
        for i, ticket in enumerate(parsed_current[:5]):  # Show first 5
            employee = ticket["employee_to_terminate"]
            transfer = ticket["transfer_data"]
            print(f"  Ticket #{ticket['ticket_number']} ({ticket['ticket_state']})")
            print(f"    Employee: {employee}")
            print(f"    Transfer: {transfer}")
            
            # Check if it looks like username vs employee ID
            if employee:
                if employee.isdigit():
                    print(f"    -> Employee ID format (numeric)")
                elif any(c.isalpha() for c in employee):
                    print(f"    -> Username format (contains letters)")
                else:
                    print(f"    -> Unknown format")
            print()
        
        if len(parsed_current) > 5:
            print(f"  ... and {len(parsed_current) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

def main():
    """Main test function."""
    print("ORIGINAL STATES ANALYSIS TEST")
    print("This will check if tickets in the original active states contain usernames")
    print()
    
        # success = analyze_original_states()
    
        # if success:
        #     print("\nTest completed successfully!")
        # else:
        #     print("\nTest failed - check logs for details")

if __name__ == "__main__":
    main()