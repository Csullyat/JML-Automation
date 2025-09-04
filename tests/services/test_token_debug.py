from jml_automation.config import Config

config = Config()
token = config.get_secret("SAMANAGE_TOKEN") or config.get_secret("SOLARWINDS_TOKEN")

print(f"Raw token from 1Password: {token[:50]}..." if token else "No token")
print(f"Contains colons: {':' in token if token else False}")

if token and ":" in token:
    parts = token.split(":")
    print(f"Number of parts when split by colon: {len(parts)}")
    print(f"Part 0 (first): {parts[0][:20] if len(parts[0]) > 20 else parts[0]}...")
    print(f"Part 1 (middle): {parts[1][:20] if len(parts) > 1 and len(parts[1]) > 20 else parts[1] if len(parts) > 1 else 'N/A'}...")
    processed_token = parts[1] if len(parts) >= 2 else token
else:
    processed_token = token

print(f"\nFinal token being used: {processed_token[:50] if processed_token else 'None'}...")
print(f"Token length: {len(processed_token) if processed_token else 0}")
