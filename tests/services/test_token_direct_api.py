import httpx
import base64
from jml_automation.config import Config

config = Config()
raw_token = config.get_secret("SAMANAGE_TOKEN")
parts = raw_token.split(":")

# Let's decode the first part to see what it is
first_part_decoded = base64.b64decode(parts[0]).decode('utf-8')
print(f"First part decoded: {first_part_decoded}")

# The JWT token (middle part)
jwt_token = parts[1]

# Test the API with just the JWT token
headers = {
    "X-Samanage-Authorization": f"Bearer {jwt_token}",
    "Accept": "application/vnd.samanage.v2.1+json",
    "Content-Type": "application/json",
}

try:
    response = httpx.get("https://api.samanage.com/incidents.json?per_page=1", headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS! Token is valid")
    else:
        print(f"Failed: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
