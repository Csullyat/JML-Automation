"""
Simple test to check if tickets have contractor hire type
"""
from src.jml_automation.services.solarwinds import SolarWindsService, fetch_ticket
from src.jml_automation.parsers.solarwinds_parser import parse_onboarding

def check_contractor_logic():
    print("🔍 Checking recent tickets for contractor hire type...")
    
    tickets = ["70811", "70812"]
    
    for ticket_id in tickets:
        try:
            print(f"\n📋 Checking ticket {ticket_id}...")
            
            # Fetch the raw ticket
            raw_ticket = fetch_ticket(ticket_id)
            print(f"   ✅ Fetched raw ticket data")
            
            # Parse the ticket
            parsed_ticket = parse_onboarding(raw_ticket)
            print(f"   ✅ Parsed ticket")
            
            # Check hire type
            hire_type = parsed_ticket.hire_type
            print(f"   📝 Hire Type: '{hire_type}'")
            
            if hire_type:
                if hire_type.strip().lower() == "contractor":
                    print(f"   🚨 CONTRACTOR DETECTED! Should be removed from SSO-Swagbucks")
                else:
                    print(f"   ℹ️  Not a contractor (hire_type: '{hire_type}')")
            else:
                print(f"   ❌ No hire type found")
                
            # Check user info
            if parsed_ticket.user:
                print(f"   👤 User: {parsed_ticket.user.email}")
            
        except Exception as e:
            print(f"   ❌ Error processing ticket {ticket_id}: {e}")

if __name__ == "__main__":
    check_contractor_logic()