from jml_automation.config import Config
import httpx

config = Config()
raw_token = config.get_secret("SAMANAGE_TOKEN") or config.get_secret("SOLARWINDS_TOKEN")

# Try using the FULL token, not just the middle part
headers = {
    "X-Samanage-Authorization": f"Bearer {raw_token}",
    "Accept": "application/vnd.samanage.v2.1+json",
    "Content-Type": "application/json",
}

response = httpx.get("https://api.samanage.com/incidents.json?per_page=1", headers=headers, timeout=10)
print(f"Status with full token: {response.status_code}")
if response.status_code == 200:
    print("SUCCESS! Full token works")
else:
    print(f"Failed: {response.text[:200]}")
