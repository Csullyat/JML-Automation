# config.py - Configuration and credential management for termination automation

import os
import subprocess
import json
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Constants - same as working project
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

def get_secret_from_1password(secret_path: str) -> str:
    """Retrieve a secret from 1Password using the CLI."""
    try:
        result = subprocess.run(['op', 'read', secret_path], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error accessing 1Password: {e}")
        raise

def get_okta_token() -> str:
    """Get the Okta API token from 1Password."""
    try:
        # Try service account first, fallback to regular CLI
        return get_secret_from_1password_service_account("op://IT/okta-api-token/password")
    except:
        print("Service account failed, falling back to regular 1Password CLI")
        return get_secret_from_1password("op://IT/okta-api-token/password")

def get_okta_domain() -> str:
    """Get Okta domain."""
    return "filevine.okta.com"  # Same as working project

def get_samanage_token() -> str:
    """Get the Samanage API token from 1Password."""
    try:
        # Try service account first, fallback to regular CLI
        return get_secret_from_1password_service_account("op://IT/samanage-api-token/password")
    except:
        print("Service account failed, falling back to regular 1Password CLI")
        return get_secret_from_1password("op://IT/samanage-api-token/password")

def get_solarwinds_credentials() -> Tuple[str, str]:
    """Get the Samanage API credentials (same system as SolarWinds Service Desk)."""
    try:
        # Try service account first, fallback to regular CLI
        token = get_secret_from_1password_service_account("op://IT/samanage-api-token/password")
        return token, ""
    except:
        print("Service account failed, falling back to regular 1Password CLI")
        token = get_secret_from_1password("op://IT/samanage-api-token/password")
        return token, ""

def get_samanage_base_url() -> str:
    """Get SolarWinds Service Desk base URL."""
    return SAMANAGE_BASE_URL

def get_slack_webhook_url() -> str:
    """Get Slack webhook URL from 1Password."""
    try:
        # Try service account first, fallback to regular CLI
        return get_secret_from_1password_service_account("op://IT/slack-termination-webhook/password")
    except:
        print("Service account failed, falling back to regular 1Password CLI")
        try:
            return get_secret_from_1password("op://IT/slack-termination-webhook/password")
        except:
            logger.warning("Could not retrieve Slack webhook from 1Password - notifications disabled")
            return ""

def get_slack_channel() -> str:
    """Get Slack channel for notifications."""
    try:
        # Try service account first, fallback to regular CLI
        return get_secret_from_1password_service_account("op://IT/slack-termination-channel/password")
    except:
        print("Service account failed, falling back to regular 1Password CLI")
        try:
            return get_secret_from_1password("op://IT/slack-termination-channel/password")
        except:
            return "#it-automation"  # Default channel

def get_samanage_subdomain() -> str:
    """Get SolarWinds Service Desk subdomain."""
    return "it"  # From URL: it.filevine.com

def get_microsoft_graph_credentials() -> Dict[str, str]:
    """Get Microsoft Graph API credentials from 1Password."""
    try:
        # Try service account first, fallback to regular CLI
        client_id = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/username")
        client_secret = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/password")
        tenant_id = get_secret_from_1password_service_account("op://IT/microsoft-graph-api/tenant_id")
        
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'tenant_id': tenant_id
        }
    except:
        print("Service account failed, falling back to regular 1Password CLI")
        try:
            client_id = get_secret_from_1password("op://IT/microsoft-graph-api/username")
            client_secret = get_secret_from_1password("op://IT/microsoft-graph-api/password")
            tenant_id = get_secret_from_1password("op://IT/microsoft-graph-api/tenant_id")
            
            return {
                'client_id': client_id,
                'client_secret': client_secret,
                'tenant_id': tenant_id
            }
        except Exception as e:
            logger.error(f"Could not retrieve Microsoft Graph credentials: {e}")
            return {}

def validate_configuration() -> Dict[str, bool]:
    """
    Validate all required configuration items are available.
    
    Returns:
        Dictionary with validation results for each component
    """
    results = {}
    
    try:
        results['okta_token'] = bool(get_okta_token())
    except:
        results['okta_token'] = False
    
    try:
        results['okta_domain'] = bool(get_okta_domain())
    except:
        results['okta_domain'] = False
    
    try:
        results['samanage_token'] = bool(get_samanage_token())
    except:
        results['samanage_token'] = False
    
    try:
        results['samanage_subdomain'] = bool(get_samanage_subdomain())
    except:
        results['samanage_subdomain'] = False
    
    # Slack is optional
    results['slack_webhook'] = bool(get_slack_webhook_url())
    
    # Microsoft Graph validation
    try:
        graph_creds = get_microsoft_graph_credentials()
        results['microsoft_graph'] = bool(graph_creds.get('client_id') and 
                                         graph_creds.get('client_secret') and 
                                         graph_creds.get('tenant_id'))
    except:
        results['microsoft_graph'] = False
    
    return results
