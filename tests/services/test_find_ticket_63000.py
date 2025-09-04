import httpx
from jml_automation.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed

def search_page(page_num, headers):
    """Search a single page for ticket 63000"""
    try:
        response = httpx.get(
            "https://api.samanage.com/incidents.json",
            headers=headers,
            params={"per_page": 100, "page": page_num},
            timeout=30
        )
        
        if response.status_code == 200:
            tickets = response.json()
            for ticket in tickets:
                if str(ticket.get('number')) == '63000':
                    return ticket
            return None
        else:
            print(f"Error on page {page_num}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception on page {page_num}: {e}")
        return None

def find_ticket_63000():
    config = Config()
    token = config.get_secret("SAMANAGE_TOKEN") or config.get_secret("SOLARWINDS_TOKEN")
    
    headers = {
        "X-Samanage-Authorization": f"Bearer {token}",
        "Accept": "application/vnd.samanage.v2.1+json",
        "Content-Type": "application/json",
    }
    
    print("Searching for ticket #63000...")
    
    # Search pages in parallel (like your working code)
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit pages 1-100 (10,000 tickets)
        futures = {executor.submit(search_page, page, headers): page 
                   for page in range(1, 101)}
        
        for future in as_completed(futures):
            page = futures[future]
            try:
                result = future.result()
                if result:
                    print(f"\n✓ FOUND on page {page}!")
                    print(f"  Internal ID: {result.get('id')}")
                    print(f"  Number: {result.get('number')}")
                    print(f"  Name: {result.get('name')}")
                    print(f"  State: {result.get('state')}")
                    print(f"  Created: {result.get('created_at')}")
                    print(f"\nTo fetch this ticket directly, use ID: {result.get('id')}")
                    return result
                else:
                    print(f".", end="", flush=True)
            except Exception as e:
                print(f"Error processing page {page}: {e}")
    
    print("\nTicket #63000 not found in first 10,000 tickets")
    return None

if __name__ == "__main__":
    ticket = find_ticket_63000()
    if ticket:
        # Now you can use the internal ID
        print(f"\nYou can now fetch with: fetch_ticket('{ticket.get('id')}')")
