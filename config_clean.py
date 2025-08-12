# config.py - Clean 1Password service account integration for termination automation
import subprocess
import os
import json
from google.oauth2 import service_account

# Base URLs and constants
OKTA_ORG_URL = "https://filevine.okta.com"
SAMANAGE_BASE_URL = "https://api.samanage.com"

def get_service_account_token_from_credential_manager():
    """Get the 1Password service account token from Windows Credential Manager."""
    try:
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
    """Retrieve a secret using 1Password Service Account."""
    try:
        service_token = get_service_account_token_from_credential_manager()
        if not service_token:
            raise Exception("Could not retrieve service account token from credential manager")
        
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

# Core credential functions
def get_okta_token() -> str:
    """Get the Okta API token from 1Password."""
    return get_secret_from_1password_service_account("op://IT/okta-api-token/password")

def get_okta_domain() -> str:
    """Get Okta domain."""
    return "filevine.okta.com"

def get_samanage_token() -> str:
    """Get the Samanage API token from 1Password."""
    return get_secret_from_1password_service_account("op://IT/samanage-api-token/password")

def get_solarwinds_credentials() -> tuple[str, str]:
    """Get the Samanage API credentials (same system as SolarWinds Service Desk)."""
    token = get_secret_from_1password_service_account("op://IT/samanage-api-token/password")
    return token, ""

def get_samanage_base_url() -> str:
    """Get SolarWinds Service Desk base URL.""" 
    return SAMANAGE_BASE_URL

def get_samanage_subdomain() -> str:
    """Get SolarWinds Service Desk subdomain."""
    return "it"

def get_microsoft_credentials() -> tuple[str, str, str]:
    """Get Microsoft Graph API credentials from 1Password."""
    tenant_id = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/tenant_id")
    client_id = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/username") 
    client_secret = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/password")
    return tenant_id, client_id, client_secret

def get_microsoft_graph_credentials() -> dict:
    """Get Microsoft Graph API credentials as dictionary."""
    tenant_id, client_id, client_secret = get_microsoft_credentials()
    return {
        'tenant_id': tenant_id,
        'client_id': client_id,
        'client_secret': client_secret
    }

def get_google_service_account_credentials():
    """Get Google service account credentials as proper credentials object."""
    try:
        # Get the JSON credential from 1Password
        json_creds = get_secret_from_1password_service_account("op://IT/google-workspace-service-account/credential")
        
        # Parse JSON and create service account credentials
        creds_info = json.loads(json_creds)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=[
                'https://www.googleapis.com/auth/admin.directory.user',
                'https://www.googleapis.com/auth/admin.directory.group',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        
        # Delegate to admin user for domain-wide delegation
        delegated_credentials = credentials.with_subject('admin@filevine.com')
        return delegated_credentials
        
    except Exception as e:
        print(f"Error creating Google service account credentials: {e}")
        raise

def get_google_credentials() -> dict:
    """Get Google credentials info for compatibility."""
    return {
        'domain': 'filevine.com',
        'admin_email': 'admin@filevine.com'
    }

def get_google_workspace_domain() -> str:
    """Get Google Workspace domain."""
    return "filevine.com"

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
