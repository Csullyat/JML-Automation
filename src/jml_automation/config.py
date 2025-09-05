# src/jml_automation/config.py

import os
import subprocess
import json
import logging
from typing import Any, Dict, Optional, Tuple
from .logger import logger
from .utils.yaml_loader import load_yaml

# Try to import Google OAuth2 if available
try:
    from google.oauth2 import service_account
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False
    logger.warning("google.oauth2 not installed - Google service account features unavailable")


class Config:
    """Configuration manager for JML Automation."""
    
    def __init__(self):
        """Initialize configuration from YAML files and environment."""
        self.settings = load_yaml('settings.yaml')
        self.departments = load_yaml('departments.yaml')
        self.termination = load_yaml('termination_order.yaml')
        self._secrets_cache: Dict[str, str] = {}
        
        # Load base URLs from settings or use defaults
        self.OKTA_ORG_URL = self.okta_url or "https://filevine.okta.com"
        self.SAMANAGE_BASE_URL = self.solarwinds_url or "https://api.samanage.com"

    # ========== Property Methods ==========
    
    @property
    def okta_url(self) -> Optional[str]:
        """Get Okta URL from settings."""
        return self.settings.get('okta_url') or self.settings.get('urls', {}).get('okta')

    @property
    def solarwinds_url(self) -> Optional[str]:
        """Get SolarWinds URL from settings."""
        return self.settings.get('urls', {}).get('solarwinds') or self.settings.get('solarwinds', {}).get('base_url')

    @property
    def google_domain(self) -> str:
        """Get Google Workspace domain from settings."""
        return self.settings.get('google', {}).get('domain', 'filevine.com')

    @property
    def google_admin_email(self) -> str:
        """Get Google Workspace admin email from settings."""
        return self.settings.get('google', {}).get('admin_email', f'admin@{self.google_domain}')

    # ========== Department Management ==========
    
    def get_groups_for_department(self, department: str) -> list:
        """Get Okta group IDs for a given department."""
        if not department:
            return [self.departments.get('default_group')]
        
        # Check special assignments first
        special = self.departments.get('special_assignments', {})
        if department in special:
            return [special[department]]
        
        # Check direct mappings
        mappings = self.departments.get('department_mappings', {})
        if department in mappings:
            return [mappings[department]['group_id']]
        
        # Check aliases
        for dept_name, dept_info in mappings.items():
            if department in dept_info.get('aliases', []):
                return [dept_info['group_id']]
        
        # Try partial matches for flexible matching
        dept_lower = department.lower()
        for dept_name, dept_info in mappings.items():
            if dept_lower in dept_name.lower() or dept_name.lower() in dept_lower:
                return [dept_info['group_id']]
        
        # Fallback to default group
        return [self.departments.get('default_group')]

    # ========== 1Password Integration ==========
    
    def get_service_account_token_from_credential_manager(self) -> Optional[str]:
        """Get the 1Password service account token from Windows Credential Manager."""
        try:
            # Look for get_credential.ps1 in the scripts directory
            script_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'scripts', 'get_credential.ps1'
            )
            
            if not os.path.exists(script_path):
                logger.warning(f"get_credential.ps1 not found at {script_path}")
                return None
            
            result = subprocess.run([
                'powershell', '-ExecutionPolicy', 'Bypass', '-File', script_path
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                logger.error(f"Failed to retrieve service account token: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("PowerShell script timed out")
            return None
        except Exception as e:
            logger.error(f"Error retrieving service account token: {e}")
            return None

    def _get_from_onepassword_service_account(self, resource_path: str) -> Optional[str]:
        """Retrieve a secret using 1Password Service Account (via stored token)."""
        try:
            service_token = self.get_service_account_token_from_credential_manager()
            if not service_token:
                logger.debug("No service account token available, falling back to regular CLI")
                return None
            
            env = {"OP_SERVICE_ACCOUNT_TOKEN": service_token}
            result = subprocess.run(
                ['op', 'read', resource_path], 
                capture_output=True, 
                text=True, 
                check=True,
                env={**os.environ, **env},
                timeout=10
            )
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Service account access failed: {e.stderr}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("1Password CLI timed out")
            return None
        except FileNotFoundError:
            logger.error("1Password CLI (op) not found")
            return None
        except Exception as e:
            logger.error(f"Error accessing 1Password with service account: {e}")
            return None

    def _get_from_onepassword(self, op_path: str) -> Optional[str]:
        """
        Retrieve a secret from 1Password.
        Tries service account first, then falls back to regular CLI.
        """
        # Try service account first (for automated/scheduled tasks)
        result = self._get_from_onepassword_service_account(op_path)
        if result:
            logger.debug("Retrieved secret using service account")
            return result
        
        # Fall back to regular 1Password CLI (for interactive use)
        try:
            result = subprocess.run(
                ['op', 'read', op_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"1Password error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("1Password CLI timed out")
            return None
        except FileNotFoundError:
            logger.error("1Password CLI (op) not found. Please install it first.")
            return None
        except Exception as e:
            logger.error(f"Error accessing 1Password: {e}")
            return None

    def get_secret(self, key: str, use_cache: bool = True) -> Optional[str]:
        """
        Get a secret value by key.
        Checks cache, environment variables, then 1Password.
        """
        # Check cache first
        if use_cache and key in self._secrets_cache:
            return self._secrets_cache[key]
        
        # Check environment variables
        value = os.getenv(key)
        if value:
            if use_cache:
                self._secrets_cache[key] = value
            return value
        
        # Map common keys to 1Password op:// paths from settings
        op_paths = {
            "SLACK_TOKEN": "slack_token",
            "OKTA_TOKEN": "okta_token",
            "SAMANAGE_TOKEN": "samanage_token",
            "SOLARWINDS_TOKEN": "solarwinds_token",
        }
        
        if key in op_paths:
            path_key = op_paths[key]
            op_path = self.settings.get('onepassword', {}).get('paths', {}).get(path_key)
            if op_path:
                value = self._get_from_onepassword(op_path)
                if value and use_cache:
                    self._secrets_cache[key] = value
                return value
        
        return None

    # ========== Service-Specific Credential Methods ==========
    
    def get_okta_token(self) -> Optional[str]:
        """Get the Okta API token from 1Password."""
        return self.get_secret("OKTA_TOKEN")

    def get_okta_domain(self) -> str:
        """Get Okta domain from settings or default."""
        return self.settings.get('okta', {}).get('domain', 'filevine.okta.com')

    def get_samanage_token(self) -> Optional[str]:
        """Get the Samanage API token from 1Password."""
        return self.get_secret("SAMANAGE_TOKEN")

    def get_samanage_base_url(self) -> str:
        """Get SolarWinds Service Desk base URL."""
        return self.SAMANAGE_BASE_URL

    def get_samanage_subdomain(self) -> str:
        """Get SolarWinds Service Desk subdomain from settings."""
        return self.settings.get('solarwinds', {}).get('subdomain', 'it')

    def get_solarwinds_credentials(self) -> Tuple[Optional[str], str]:
        """Get the SolarWinds API credentials (same system as Samanage)."""
        token = self.get_secret("SOLARWINDS_TOKEN")
        return token, ""

    def get_solarwinds_config(self) -> Dict[str, Any]:
        """Get SolarWinds configuration from settings."""
        return self.settings.get('solarwinds', {})

    def get_microsoft_credentials(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get Microsoft Graph API credentials from 1Password."""
        paths = self.settings.get('onepassword', {}).get('paths', {})
        tenant_id = self._get_from_onepassword(paths.get('microsoft_tenant_id', "op://IT/microsoft-graph-api/tenant_id"))
        client_id = self._get_from_onepassword(paths.get('microsoft_client_id', "op://IT/microsoft-graph-api/username"))
        client_secret = self._get_from_onepassword(paths.get('microsoft_client_secret', "op://IT/microsoft-graph-api/password"))
        return tenant_id, client_id, client_secret

    def get_microsoft_graph_credentials(self) -> Dict[str, Optional[str]]:
        """Get Microsoft Graph API credentials as dictionary."""
        tenant_id, client_id, client_secret = self.get_microsoft_credentials()
        return {
            'tenant_id': tenant_id,
            'client_id': client_id,
            'client_secret': client_secret
        }

    def get_exchange_credentials(self) -> Dict[str, Optional[str]]:
        """Get Exchange Online credentials from 1Password."""
        paths = self.settings.get('onepassword', {}).get('paths', {})
        return {
            'tenant_id': self._get_from_onepassword(paths.get('exchange_tenant_id', "op://IT/microsoft-graph-api/tenant_id")),
            'app_id': self._get_from_onepassword(paths.get('exchange_app_id', "op://IT/microsoft-graph-api/username")),
            'cert_thumbprint': self._get_from_onepassword(paths.get('exchange_cert_thumbprint', "op://IT/microsoft-graph-api/certificate_thumbprint"))
        }

    def get_exchange_certificate_from_1password(self) -> Optional[str]:
        """
        Download Exchange certificate from 1Password and ensure it's installed.
        Returns the certificate thumbprint if successful.
        """
        try:
            # Path to the certificate in 1Password
            cert_path = "op://IT/ExchangeOnline_Cert/ExchangeOnline-Cert.cer"
            
            logger.info("Ensuring Exchange certificate is available locally...")
            
            # Create local docs/certs directory if it doesn't exist
            cert_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs', 'certs')
            os.makedirs(cert_dir, exist_ok=True)
            
            # Download certificate to local storage (for backup/reference)
            cert_out_path = os.path.join(cert_dir, 'exchange_online.cer')
            
            # Only download if we don't already have it
            if not os.path.exists(cert_out_path):
                try:
                    result = subprocess.run([
                        'op', 'read', cert_path, '--out-file', cert_out_path
                    ], capture_output=True, text=True, timeout=30, env=os.environ.copy())
                    
                    if result.returncode == 0:
                        logger.info(f"Certificate downloaded to: {cert_out_path}")
                    else:
                        logger.warning(f"Could not download certificate: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Could not download certificate: {e}")
            
            # Get the thumbprint from 1Password (already stored)
            exchange_creds = self.get_exchange_credentials()
            thumbprint = exchange_creds.get('cert_thumbprint')
            
            if thumbprint:
                logger.info(f"Using certificate thumbprint from 1Password: {thumbprint}")
                self._secrets_cache['EXCHANGE_CERT_THUMBPRINT'] = thumbprint
                return thumbprint
            else:
                logger.error("Certificate thumbprint not found in 1Password")
                return None
                
        except Exception as e:
            logger.error(f"Error ensuring Exchange certificate availability: {e}")
            return None

    def get_exchange_certificate_thumbprint(self) -> Optional[str]:
        """
        Get Exchange certificate thumbprint, installing certificate if needed.
        """
        # Check if we have a cached thumbprint
        if 'EXCHANGE_CERT_THUMBPRINT' in self._secrets_cache:
            return self._secrets_cache['EXCHANGE_CERT_THUMBPRINT']
        
        # Try to get thumbprint from 1Password first
        exchange_creds = self.get_exchange_credentials()
        if exchange_creds.get('cert_thumbprint'):
            thumbprint = exchange_creds['cert_thumbprint']
            if thumbprint:  # Only cache if not None
                self._secrets_cache['EXCHANGE_CERT_THUMBPRINT'] = thumbprint
            return thumbprint
        
        # If no thumbprint in 1Password, try to install certificate and get thumbprint
        return self.get_exchange_certificate_from_1password()

    def get_google_service_account_key(self) -> Dict:
        """Get Google Workspace service account key from 1Password."""
        try:
            paths = self.settings.get('onepassword', {}).get('paths', {})
            service_account_json = self._get_from_onepassword(paths.get('google_service_account', "op://IT/google-workspace-service-account/credential"))
            if service_account_json:
                return json.loads(service_account_json)
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Google service account key: {e}")
            return {}
        except Exception as e:
            logger.error(f"Could not retrieve Google service account key: {e}")
            return {}

    def get_google_service_account_credentials(self):
        """Get Google service account credentials as proper credentials object."""
        if not HAS_GOOGLE_AUTH:
            logger.error("google-auth library not installed. Run: pip install google-auth")
            return None
            
        try:
            # Get the JSON credential from 1Password
            paths = self.settings.get('onepassword', {}).get('paths', {})
            json_creds = self._get_from_onepassword(paths.get('google_service_account', "op://IT/google-workspace-service-account/credential"))
            if not json_creds:
                logger.error("Could not retrieve Google service account credentials")
                return None
            
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
            delegated_credentials = credentials.with_subject(self.google_admin_email)
            return delegated_credentials
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Google service account credentials: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating Google service account credentials: {e}")
            return None

    def get_google_credentials(self) -> Dict[str, str]:
        """Get Google credentials info for compatibility."""
        return {
            'domain': self.google_domain,
            'admin_email': self.google_admin_email
        }

    def get_google_workspace_domain(self) -> str:
        """Get Google Workspace domain."""
        return self.google_domain

    def get_zoom_credentials(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get Zoom API credentials from 1Password."""
        paths = self.settings.get('onepassword', {}).get('paths', {})
        api_key = self._get_from_onepassword(paths.get('zoom_api_key', "op://IT/Zoom_API_Key/password"))
        api_secret = self._get_from_onepassword(paths.get('zoom_api_secret', "op://IT/Zoom_API_Secret/password"))
        account_id = self._get_from_onepassword(paths.get('zoom_account_id', "op://IT/Zoom_Account_ID/password"))
        return api_key, api_secret, account_id

    def get_zoom_credentials_dict(self) -> Dict[str, Optional[str]]:
        """Get Zoom API credentials as dictionary."""
        api_key, api_secret, account_id = self.get_zoom_credentials()
        return {
            'client_id': api_key,
            'client_secret': api_secret,
            'account_id': account_id
        }

    def get_domo_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Domo API credentials from 1Password."""
        paths = self.settings.get('onepassword', {}).get('paths', {})
        client_id = self._get_from_onepassword(paths.get('domo_client_id', "op://IT/domo-api/username"))
        client_secret = self._get_from_onepassword(paths.get('domo_client_secret', "op://IT/domo-api/password"))
        return client_id, client_secret

    def get_domo_credentials_dict(self) -> Dict[str, Optional[str]]:
        """Get Domo API credentials as dictionary."""
        client_id, client_secret = self.get_domo_credentials()
        return {
            'client_id': client_id,
            'client_secret': client_secret
        }

    # ========== Configuration Validation ==========
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of all configuration status."""
        results = {}
        
        # Test 1Password service account
        try:
            token = self.get_service_account_token_from_credential_manager()
            results['onepassword_service_account'] = bool(token)
        except:
            results['onepassword_service_account'] = False
        
        # Test core credentials
        component_status = {}
        
        try:
            component_status['okta_token'] = bool(self.get_okta_token())
        except:
            component_status['okta_token'] = False
        
        try:
            component_status['samanage_token'] = bool(self.get_samanage_token())
        except:
            component_status['samanage_token'] = False
        
        try:
            ms_creds = self.get_microsoft_graph_credentials()
            component_status['microsoft_graph'] = all(ms_creds.values())
        except:
            component_status['microsoft_graph'] = False
        
        try:
            component_status['google_service_account'] = bool(self.get_google_service_account_key())
        except:
            component_status['google_service_account'] = False
        
        try:
            zoom_creds = self.get_zoom_credentials_dict()
            component_status['zoom'] = all(zoom_creds.values())
        except:
            component_status['zoom'] = False
        
        results['component_validation'] = component_status
        
        # Determine overall readiness
        critical_components = ['okta_token', 'samanage_token']
        results['critical_components_ready'] = all(
            component_status.get(comp, False) for comp in critical_components
        ) and results['onepassword_service_account']
        
        results['all_components_ready'] = all(component_status.values()) and results['onepassword_service_account']
        
        return results

    def validate_configuration(self, verbose: bool = False) -> bool:
        """
        Validate that all required configuration is present.
        
        Args:
            verbose: If True, print detailed status
            
        Returns:
            True if all critical components are configured
        """
        summary = self.get_configuration_summary()
        
        if verbose:
            logger.info("Configuration Status:")
            logger.info(f"  1Password Service Account: {'✓' if summary['onepassword_service_account'] else '✗'}")
            logger.info("  Components:")
            for component, status in summary['component_validation'].items():
                logger.info(f"    {component}: {'✓' if status else '✗'}")
            logger.info(f"  Critical Components Ready: {'✓' if summary['critical_components_ready'] else '✗'}")
            logger.info(f"  All Components Ready: {'✓' if summary['all_components_ready'] else '✗'}")
        
        return summary['critical_components_ready']