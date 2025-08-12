# config.py
import subprocess
import os

OKTA_ORG_URL = "https://filevine.okta.com"
SAMANAGE_BASE_URL = "https://api.samanage.com"

def get_service_account_token_from_credential_manager():
    """Get the 1Password service account token from Windows Credential Manager."""
    try:
        # Use PowerShell script file with proper module path handling
        script_path = os.path.join(os.path.dirname(__file__), 'get_credential.ps1')
        result = subprocess.run([
            'powershell', '-ExecutionPolicy', 'Bypass', '-File', script_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            print(f"Failed to retrieve service account token: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Error retrieving service account token: {e}")
        return None

def get_secret_from_1password_service_account(resource_path: str) -> str:
    """Retrieve a secret using 1Password Service Account (via stored token)."""
    try:
        # Get the service account token from Windows Credential Manager
        service_token = get_service_account_token_from_credential_manager()
        if not service_token:
            raise Exception("Could not retrieve service account token from credential manager")
        
        # Use the service account token with 1Password CLI
        env = {"OP_SERVICE_ACCOUNT_TOKEN": service_token}
        result = subprocess.run(['op', 'read', resource_path], 
                              capture_output=True, 
                              text=True, 
                              check=True,
                              env={**os.environ, **env})
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error accessing 1Password with service account: {e}")
        raise

def get_okta_token() -> str:
    """Get the Okta API token from 1Password."""
    return get_secret_from_1password_service_account("op://IT/okta-api-token/password")

def get_samanage_token() -> str:
    """Get the Samanage API token from 1Password."""
    return get_secret_from_1password_service_account("op://IT/samanage-api-token/password")

def get_solarwinds_credentials() -> tuple[str, str]:
    """Get the Samanage API credentials (same system as SolarWinds Service Desk)."""
    token = get_secret_from_1password_service_account("op://IT/samanage-api-token/password")
    return token, ""

def get_google_service_account_credentials() -> str:
    """Get Google service account credentials from 1Password."""
    return get_secret_from_1password_service_account("op://IT/google-workspace-service-account/credential")

def get_microsoft_credentials() -> tuple[str, str, str]:
    """Get Microsoft Graph API credentials from 1Password."""
    tenant_id = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/tenant_id")
    client_id = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/username") 
    client_secret = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/password")
    return tenant_id, client_id, client_secret

def get_zoom_credentials() -> tuple[str, str, str]:
    """Get Zoom API credentials from 1Password."""
    api_key = get_secret_from_1password_service_account("op://IT/Zoom_API_Key/password")
    api_secret = get_secret_from_1password_service_account("op://IT/Zoom_API_Secret/password") 
    account_id = get_secret_from_1password_service_account("op://IT/Zoom_Account_ID/password")
    return api_key, api_secret, account_id

def get_exchange_credentials() -> dict:
    """Get Exchange Online credentials from 1Password."""
    return {
        'tenant_id': get_secret_from_1password_service_account("op://IT/microsoft-graph-api/tenant_id"),
        'app_id': get_secret_from_1password_service_account("op://IT/microsoft-graph-api/username"),
        'client_secret': get_secret_from_1password_service_account("op://IT/microsoft-graph-api/password")
    }

# Test function to validate all credentials
def test_credential_access():
    """Test access to all required credentials."""
    try:
        print("Testing 1Password service account access...")
        
        # Test basic service account token retrieval
        token = get_service_account_token_from_credential_manager()
        if not token:
            raise Exception("Failed to retrieve service account token")
        print(f"✓ Service account token retrieved (length: {len(token)})")
        
        # Test each credential that we know exists
        credentials_to_test = [
            ("Okta API token", lambda: get_okta_token()),
            ("Samanage API token", lambda: get_samanage_token()),
        ]
        
        # Test optional credentials (might not exist)
        optional_credentials = [
            ("Google service account", lambda: get_google_service_account_credentials()),
            ("Microsoft Graph credentials", lambda: get_microsoft_credentials()),
            ("Zoom API credentials", lambda: get_zoom_credentials()),
            ("Exchange Online credentials", lambda: get_exchange_credentials())
        ]
        
        for name, func in credentials_to_test:
            try:
                result = func()
                print(f"✓ {name} - accessible")
            except Exception as e:
                print(f"✗ {name} - failed: {e}")
                return False  # Core credentials must work
        
        for name, func in optional_credentials:
            try:
                result = func()
                print(f"✓ {name} - accessible")
            except Exception as e:
                print(f"⚠ {name} - not configured (optional): {e}")
        
        return True
        
    except Exception as e:
        print(f"Credential test failed: {e}")
        return False

if __name__ == "__main__":
    test_credential_access()
