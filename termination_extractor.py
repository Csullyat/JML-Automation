# termination_extractor.py - Extract termination tickets from SolarWinds

import requests
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Imports and API configuration
from config import get_samanage_token

logger = logging.getLogger(__name__)

BASE_URL = "https://api.samanage.com"
# Get the token once at module level
HEADERS = {
    "X-Samanage-Authorization": f"Bearer {get_samanage_token()}",
    "Accept": "application/vnd.samanage.v2.1+json"
}

# Termination subcategory ID from our analysis
TERMINATION_SUBCATEGORY_ID = 1574220  # "Termination" subcategory in Human Resources

# States that represent "active" termination requests - "New" and "Awaiting Input"
ACTIVE_STATES = {"New", "Awaiting Input"}

def fetch_page(page: int, per_page: int) -> List[Dict]:
    """Fetch a page of termination tickets."""
    params = {
        "per_page": per_page,
        "page": page,
        "subcategory_id": TERMINATION_SUBCATEGORY_ID,
        "sort": "created_at",
        "sort_order": "desc"
    }

    logger.debug(f"Fetching page {page}...")
    resp = requests.get(f"{BASE_URL}/incidents.json", headers=HEADERS, params=params)

    if resp.status_code != 200:
        print(f"Error on page {page}: {resp.status_code}: {resp.text}")
        return []

    return resp.json()

def fetch_tickets(per_page: int = 100, max_pages: int = 60, workers: int = 15) -> List[Dict]:
    """Fetch all termination tickets using concurrent requests."""
    all_tickets = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_page, page, per_page) for page in range(1, max_pages + 1)]
        for future in as_completed(futures):
            try:
                incidents = future.result()
                all_tickets.extend(incidents)
                if not incidents:  # Stop if we get empty pages
                    break
            except Exception as e:
                print(f"Thread error: {e}")

    print(f"Total termination tickets fetched: {len(all_tickets)}")
    return all_tickets

def parse_termination_ticket(ticket: Dict) -> Dict:
    """Parse a termination ticket and extract employee information."""
    try:
        # Validate ticket has minimum required fields
        if not isinstance(ticket, dict):
            raise ValueError(f"Invalid ticket format: expected dict, got {type(ticket)}")
        
        if not ticket.get("number"):
            raise ValueError("Ticket is missing required field: number")
            
        out = {
            "ticket_id": ticket.get("id"),
            "ticket_number": ticket.get("number"),
            "ticket_state": ticket.get("state", "Unknown"),
            "ticket_created": ticket.get("created_at", "Unknown"),
            "category": ticket.get("category", {}).get("name") if ticket.get("category") else None,
            "subcategory": ticket.get("subcategory", {}).get("name") if ticket.get("subcategory") else None
        }
        
        # Track required fields for termination
        required_fields = {"employee_to_terminate"}
        found_fields = set()
        
        # Parse custom fields for termination data
        for f in ticket.get("custom_fields_values", []):
            try:
                label = f.get("name", "").strip()
                val = f.get("value", "").strip()
                
                if not val:
                    continue

                if label == "Employee to Terminate":
                    out["employee_to_terminate"] = val
                    found_fields.add("employee_to_terminate")
                    # Get the actual email from the user object if available
                    user_obj = f.get("user", {})
                    if user_obj and user_obj.get("email"):
                        out["employee_email"] = user_obj["email"]
                        out["employee_name"] = user_obj.get("name", val)
                    else:
                        # Fallback to ID format if user object not available
                        out["employee_email"] = f"{val}@filevine.com"
                elif label == "Employee Department":
                    out["employee_department"] = val
                elif label == "Termination Date":
                    out["termination_date"] = val
                elif label == "Date to remove access":
                    out["date_to_remove_access"] = val
                elif label == "Term Type":
                    out["term_type"] = val
                elif label == "Transfer Data":
                    out["transfer_data"] = val
                    # Extract manager email from transfer data user object
                    user_obj = f.get("user", {})
                    if user_obj and user_obj.get("email"):
                        out["manager_email"] = user_obj["email"]
                        out["manager_name"] = user_obj.get("name", "")
                    elif "@filevine.com" in val:
                        # Fallback: Look for email pattern in transfer data value
                        import re
                        email_match = re.search(r'([a-zA-Z0-9._%+-]+@filevine\.com)', val)
                        if email_match:
                            out["manager_email"] = email_match.group(1)
                elif label == "Additional Information":
                    out["additional_info"] = val
                elif label == "Is this termination pre-hire date?":
                    out["is_pre_hire"] = val
                elif label == "CJIS Cleared? If yes, please inform Compliance (Kobe Andam or Sean Van Rooyen).":
                    out["cjis_cleared"] = val
                    
            except Exception as e:
                print(f"Error parsing field {label} for ticket {out['ticket_number']}: {e}")
                continue

        # Extract employee name from ticket title if available
        ticket_name = ticket.get("name", "")
        if "Employee Termination" in ticket_name:
            # Extract name after "Employee Termination - "
            name_part = ticket_name.replace("Employee Termination - ", "").strip()
            if name_part:
                out["employee_name"] = name_part

        # Validate required fields
        missing_fields = required_fields - found_fields
        if missing_fields:
            print(f"Ticket {out['ticket_number']} missing required fields: {', '.join(missing_fields)}")
            return {}  # Return empty dict for invalid tickets

        return out
        
    except Exception as e:
        print(f"Critical error parsing ticket {ticket.get('number', 'Unknown')}: {str(e)}")
        return {}

def filter_termination_users(tickets: List[Dict]) -> List[Dict]:
    """Filter and parse termination tickets for active terminations."""
    def should_parse(t: Dict) -> bool:
        return t.get("state") in ACTIVE_STATES

    filtered = [t for t in tickets if should_parse(t)]
    print(f"Filtered to {len(filtered)} active termination tickets")

    users = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(parse_termination_ticket, t): t for t in filtered}
        for future in as_completed(futures):
            try:
                u = future.result()
                if u and "employee_to_terminate" in u:
                    users.append(u)
            except Exception as e:
                print(f"Parse error: {e}")

    print(f"Final parsed termination users: {len(users)} of {len(tickets)} tickets")
    return users

def print_terminations(users: List[Dict]):
    """Print termination information in a readable format."""
    if not users:
        print("No active termination tickets found.")
        return
        
    print(f"\nACTIVE TERMINATION REQUESTS ({len(users)}):")
    print("=" * 80)
    
    for i, u in enumerate(users, 1):
        print(f"\nTERMINATION #{i}")
        print(f"Ticket: #{u.get('ticket_number')} | State: {u.get('ticket_state')} | Created: {u.get('ticket_created')}")
        print(f"Employee Name: {u.get('employee_name', 'Unknown')}")
        print(f"Employee ID: {u.get('employee_to_terminate', 'Unknown')}")
        print(f"Department: {u.get('employee_department', 'Unknown')}")
        print(f"Termination Date: {u.get('termination_date', 'Unknown')}")
        print(f"Remove Access Date: {u.get('date_to_remove_access', 'Unknown')}")
        print(f"Term Type: {u.get('term_type', 'Unknown')}")
        
        if u.get('additional_info'):
            print(f"Additional Info: {u.get('additional_info')}")
        if u.get('transfer_data'):
            print(f"Transfer Data: {u.get('transfer_data')}")
        if u.get('cjis_cleared'):
            print(f"CJIS Cleared: {u.get('cjis_cleared')}")
            
        print("-" * 60)

def get_termination_summary(users: List[Dict]) -> Dict:
    """Get summary statistics about terminations."""
    if not users:
        return {}
        
    summary = {
        "total_terminations": len(users),
        "departments": {},
        "term_types": {},
        "states": {}
    }
    
    for user in users:
        dept = user.get('employee_department', 'Unknown')
        term_type = user.get('term_type', 'Unknown')
        state = user.get('ticket_state', 'Unknown')
        
        summary["departments"][dept] = summary["departments"].get(dept, 0) + 1
        summary["term_types"][term_type] = summary["term_types"].get(term_type, 0) + 1
        summary["states"][state] = summary["states"].get(state, 0) + 1
    
    return summary

if __name__ == "__main__":
    try:
        print("Fetching termination tickets from SolarWinds...")
        tickets = fetch_tickets()
        
        if not tickets:
            print("No termination tickets found.")
        else:
            users = filter_termination_users(tickets)
            print_terminations(users)
            
            # Print summary
            summary = get_termination_summary(users)
            if summary:
                print(f"\nTERMINATION SUMMARY:")
                print(f"Total Active Terminations: {summary['total_terminations']}")
                print(f"By Department: {dict(summary['departments'])}")
                print(f"By Term Type: {dict(summary['term_types'])}")
                print(f"By State: {dict(summary['states'])}")
                
    except Exception as e:
        print(f"Script error: {e}")
