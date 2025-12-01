#!/usr/bin/env python3
"""
Test script to check contractor hire type in recent tickets
"""
from src.jml_automation.services.solarwinds import SolarWindsService
from src.jml_automation.config import Config

def check_ticket_hire_type(ticket_id):
    try:
        config = Config()
        sw = SolarWindsService(
            base_url=config.get_solarwinds_url(),
            token=config.get_solarwinds_token()
        )
        
        print(f"\n Checking ticket {ticket_id}...")
        ticket_data = sw.get_incident(ticket_id)
        
        # Check custom_fields for hire type
        cf = ticket_data.get('custom_fields', {})
        hire_type = cf.get('New Hire Type')
        
        print(f"Ticket {ticket_id}:")
        print(f"New Hire Type: '{hire_type}'")
        
        if hire_type:
            print(f"   Raw value: '{repr(hire_type)}'")
            if hire_type.strip().lower() == "contractor":
                print("This is a CONTRACTOR - should be removed from SSO-Swagbucks")
            else:
                print(f"Not a contractor (value: '{hire_type}')")
        else:
            print("No 'New Hire Type' field found")
            print("Available custom fields with 'type', 'hire', or 'contractor':")
            for key, value in cf.items():
                if any(word in key.lower() for word in ['type', 'hire', 'contractor']):
                    print(f"     {key}: {value}")
                    
        # Also check the subject to see what type of request this is
        subject = ticket_data.get('subject', '')
        print(f"   Subject: {subject}")
        
        return hire_type
        
    except Exception as e:
        print(f" Error checking ticket {ticket_id}: {e}")
        return None

if __name__ == "__main__":
    # Check the tickets from your recent onboarding
    tickets_to_check = ["70811", "70812"]
    
    for ticket_id in tickets_to_check:
        hire_type = check_ticket_hire_type(ticket_id)