import httpx
from jml_automation.config import Config

config = Config()
token = config.get_secret("SAMANAGE_TOKEN") or config.get_secret("SOLARWINDS_TOKEN")

headers = {
    "X-Samanage-Authorization": f"Bearer {token}",
    "Accept": "application/vnd.samanage.v2.1+json",
    "Content-Type": "application/json",
}

# Search for tickets with number 63000
response = httpx.get(
    "https://api.samanage.com/incidents.json",
    headers=headers,
    params={"number": "63000"},
    timeout=10
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data)} tickets")
    if data:
        ticket = data[0]
        print(f"Ticket ID: {ticket.get('id')}")
        print(f"Ticket Number: {ticket.get('number')}")
        print(f"Ticket Name: {ticket.get('name')}")
        print(f"State: {ticket.get('state')}")
else:
    print(f"Error: {response.text[:200]}")
