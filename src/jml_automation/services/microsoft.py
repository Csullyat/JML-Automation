# microsoft.py - Microsoft 365 and Exchange service automation

import logging
import requests
import json
import time
import tempfile
from typing import Dict, Optional, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MicrosoftService:
    """Microsoft 365 and Exchange service automation for onboarding and termination."""
    
    def __init__(self):
        """Initialize Microsoft Graph client."""
        # Import config to get certificate thumbprint and credentials
        from jml_automation.config import Config
        self.config = Config()
        
        self.credentials = self.config.get_microsoft_graph_credentials()
        self.access_token = None
        self.token_expires_at = 0  # Token expiration timestamp
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self._exchange_session_active = False  # Track if Exchange session is active
        
        if not self.credentials.get('client_id'):
            raise Exception("Microsoft Graph credentials not available")
    
    def _get_cert_thumbprint(self) -> str:
        """Get Exchange certificate thumbprint with consistent method."""
        # Try the primary method first
        thumbprint = self.config.get_exchange_certificate_thumbprint()
        if thumbprint:
            return thumbprint
        
        # Fallback to exchange credentials method
        exchange_creds = self.config.get_exchange_credentials()
        thumbprint = exchange_creds.get('cert_thumbprint', '')
        if thumbprint:
            return thumbprint
        
        raise Exception("Exchange certificate thumbprint not available from any source")
    
    def get_mailbox_status(self, user_email: str) -> Optional[str]:
        """Return the mailbox type (e.g., 'UserMailbox', 'SharedMailbox') for the given user."""
        import subprocess
        import os
        ps_script = f'''
try {{
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    Connect-ExchangeOnline -AppId '{self.credentials['client_id']}' -Organization 'filevine.com' -CertificateThumbprint '{self.config.get_exchange_certificate_thumbprint()}' -ShowBanner:$false
    $mailbox = Get-Mailbox -Identity '{user_email}' -ErrorAction Stop
    Write-Host $mailbox.RecipientTypeDetails
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
'''
        script_path = os.path.join(os.getcwd(), "temp_get_mailbox_status.ps1")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(ps_script)
        cmd = [
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        try:
            os.remove(script_path)
        except:
            pass
        if result.returncode == 0 and result.stdout:
            status = result.stdout.strip().splitlines()[-1]
            return status
        return None
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token for Microsoft Graph with caching."""
        # Check if we have a valid cached token
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        token_url = f"https://login.microsoftonline.com/{self.credentials['tenant_id']}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.credentials['client_id'],
            'client_secret': self.credentials['client_secret'],
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Cache token with 5-minute buffer before expiration
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = time.time() + expires_in - 300
            
            logger.info("Successfully obtained Microsoft Graph access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph access token: {e}")
            raise
    
    def _make_graph_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated request to Microsoft Graph API."""
        token = self._get_access_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.graph_endpoint}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle empty responses (like 204 No Content)
            if response.status_code == 204 or not response.content:
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Microsoft Graph API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find user in Microsoft 365 by email."""
        try:
            logger.info(f"Looking up Microsoft 365 user: {email}")
            
            # Use the user's email as their ID in Graph API
            user_data = self._make_graph_request('GET', f'/users/{email}')
            
            logger.info(f"Found Microsoft 365 user: {user_data.get('displayName')} ({email})")
            return user_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"User {email} not found in Microsoft 365")
                return None
            else:
                logger.error(f"Error finding user {email}: {e}")
                raise
        except Exception as e:
            logger.error(f"Exception finding user {email}: {e}")
            return None
    
    def find_manager_by_email(self, manager_email: str) -> Optional[Dict]:
        """Find manager by email address."""
        try:
            # Search for user by email
            user = self._make_graph_request('GET', f'/users/{manager_email}')
            
            if user:
                logger.info(f"Found manager: {user.get('displayName')} ({manager_email})")
                return user
            else:
                logger.warning(f"No manager found for email {manager_email}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding manager {manager_email}: {e}")
            return None
    
    def convert_mailbox_to_shared(self, user_email: str):
        """Convert user mailbox to shared mailbox using certificate-based authentication."""
        try:
            logger.info(f"Attempting automated mailbox conversion for {user_email}")
            
            import subprocess
            
            # Get the app credentials and certificate thumbprint
            app_id = self.credentials['client_id']
            tenant_id = self.credentials['tenant_id']
            # Use domain name instead of tenant GUID for Exchange Online
            organization = "filevine.com"
            
            # Get certificate thumbprint from 1Password/config
            cert_thumbprint = self.config.get_exchange_certificate_thumbprint()
            if not cert_thumbprint:
                logger.error("Exchange certificate thumbprint not available")
                return {
                    'success': False,
                    'error': 'Certificate thumbprint not available',
                    'requires_manual': True
                }
            
            # Try automated approach with certificate authentication
            ps_script = f"""
try {{
    Write-Host "Importing Exchange Online Management module..."
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    
    Write-Host "Connecting to Exchange Online with certificate authentication..."
    # Using certificate-based authentication for unattended automation
    Connect-ExchangeOnline -AppId '{app_id}' -Organization '{organization}' -CertificateThumbprint '{cert_thumbprint}' -ShowBanner:$false
    
    Write-Host "Converting mailbox to shared type..."
    Set-Mailbox -Identity '{user_email}' -Type Shared -Confirm:$false -ErrorAction Stop
    Write-Host "SUCCESS: Mailbox conversion command completed successfully."
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    Write-Host "Full error: $_"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
"""
            
            logger.info("Attempting automated PowerShell mailbox conversion")
            
            # Write PowerShell script to a temporary file
            import os
            script_path = os.path.join(os.getcwd(), "temp_exchange_convert.ps1")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(ps_script)
            
            # Execute PowerShell script file
            cmd = [
                "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", 
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", script_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)  # 90 second timeout
            
            # Clean up temp file
            try:
                os.remove(script_path)
            except:
                pass
            
            # Log all output
            if result.stdout:
                logger.info(f"PowerShell output: {result.stdout}")
            if result.stderr:
                logger.warning(f"PowerShell errors: {result.stderr}")

            # Check for 'already shared' warning FIRST, before any other success logic
            if result.stdout:
                logger.info(f"DEBUG: PowerShell stdout for mailbox conversion: {result.stdout}")
            if result.stdout and "already of the type" in result.stdout:
                logger.info(f"Mailbox {user_email} is already a shared mailbox. Skipping conversion.")
                return "already_shared"
            elif result.returncode == 0 and "SUCCESS: Mailbox conversion command completed successfully" in result.stdout:
                logger.info(f"SUCCESS: Mailbox successfully converted to shared for {user_email}")
                return True
            else:
                # Command failed - just log and continue with delegation
                logger.warning(f"Mailbox conversion command failed (exit code {result.returncode})")
                if "Connect-ExchangeOnline" in result.stderr and "not recognized" in result.stderr:
                    logger.error("Exchange Online PowerShell module commands not available in subprocess")
                
                # Don't block the workflow - continue with delegation regardless
                logger.info("Continuing with mailbox delegation despite conversion uncertainty")
                return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"PowerShell mailbox conversion timed out for {user_email}")
            return False
        except Exception as e:
            logger.error(f"Failed to execute PowerShell conversion for {user_email}: {e}")
            return False
    
    def delegate_mailbox_access(self, user_email: str, manager_email: str) -> bool:
        """Grant manager full access to user's mailbox using Exchange Online PowerShell."""
        try:
            logger.info(f"Delegating mailbox access: {user_email} -> {manager_email}")
            
            import subprocess
            
            # Get the app credentials and certificate thumbprint
            app_id = self.credentials['client_id']
            tenant_id = self.credentials['tenant_id']
            # Use domain name instead of tenant GUID for Exchange Online
            organization = "filevine.com"
            
            # Get certificate thumbprint from 1Password/config
            cert_thumbprint = self.config.get_exchange_certificate_thumbprint()
            if not cert_thumbprint:
                logger.error("Exchange certificate thumbprint not available")
                return False
            
            ps_script = f"""
try {{
    Write-Host "Importing Exchange Online Management module..."
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    
    Write-Host "Connecting to Exchange Online with certificate authentication..."
    Connect-ExchangeOnline -AppId '{app_id}' -Organization '{organization}' -CertificateThumbprint '{cert_thumbprint}' -ShowBanner:$false
    
    Write-Host "Granting FullAccess permission to {manager_email}..."
    Add-MailboxPermission -Identity '{user_email}' -User '{manager_email}' -AccessRights FullAccess -InheritanceType All -Confirm:$false -ErrorAction Stop
    
    Write-Host "Granting SendAs permission to {manager_email}..."
    Add-RecipientPermission -Identity '{user_email}' -Trustee '{manager_email}' -AccessRights SendAs -Confirm:$false -ErrorAction Stop
    
    Write-Host "SUCCESS: Mailbox permissions granted successfully"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
"""
            
            # Write PowerShell script to a temporary file
            import os
            script_path = os.path.join(os.getcwd(), "temp_exchange_delegate.ps1")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(ps_script)
            
            # Execute PowerShell script file
            cmd = [
                "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", 
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", script_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            
            # Clean up temp file
            try:
                os.remove(script_path)
            except:
                pass
            
            # Log output
            if result.stdout:
                logger.info(f"PowerShell output: {result.stdout}")
            if result.stderr:
                logger.warning(f"PowerShell errors: {result.stderr}")
            
            if result.returncode == 0 and "SUCCESS: Mailbox permissions granted successfully" in result.stdout:
                logger.info(f"Mailbox delegation completed: {manager_email} now has access to {user_email}")
                return True
            else:
                logger.error(f"Failed to delegate mailbox access (exit code {result.returncode})")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delegate mailbox access: {e}")
            return False
    
    def remove_user_licenses(self, user_email: str) -> Dict:
        """Remove all licenses from user."""
        try:
            logger.info(f"Checking licenses for {user_email}")
            
            # Get current user licenses using licenseDetails endpoint
            license_data = self._make_graph_request('GET', f'/users/{user_email}/licenseDetails')
            current_licenses = license_data.get('value', [])
            
            if not current_licenses:
                logger.info(f"No licenses found for {user_email}")
                return {'success': True, 'licenses_removed': 0, 'message': 'No licenses to remove'}
            
            # Extract SKU IDs for removal
            sku_ids = [license['skuId'] for license in current_licenses]
            license_names = [license.get('skuPartNumber', 'Unknown') for license in current_licenses]
            
            logger.info(f"Found {len(current_licenses)} licenses: {', '.join(license_names)}")
            
            # Remove all licenses
            license_update = {
                "addLicenses": [],
                "removeLicenses": sku_ids
            }
            
            result = self._make_graph_request('POST', f'/users/{user_email}/assignLicense', license_update)
            
            logger.info(f"Successfully removed {len(current_licenses)} licenses from {user_email}")
            return {
                'success': True,
                'licenses_removed': len(current_licenses),
                'removed_licenses': license_names
            }
            
        except Exception as e:
            logger.error(f"Failed to remove licenses for {user_email}: {e}")
            return {'success': False, 'error': str(e)}
    
    # OneDrive functionality removed - out of scope for this automation
    
    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        """
        Execute Microsoft 365 termination process.
        
        Process:
        1. Verify user exists in Microsoft 365
        2. Verify manager exists in Microsoft 365  
        3. Convert mailbox to shared and delegate access (if both user and manager found)
        4. Remove all licenses (frees licenses for other users)
        5. Keep user account in unlicensed state (Okta manages access control)
        
        Returns detailed results of all operations performed.
        """
        logger.info(f"Starting Microsoft 365 termination for {user_email}")
        
        results = {
            'user_email': user_email,
            'termination_time': datetime.now(),
            'actions_completed': [],
            'actions_failed': [],
            'success': True
        }
        
        try:
            # Step 1: Check if user exists in Microsoft 365 FIRST
            logger.info(f"Checking if user exists in Microsoft 365: {user_email}")
            user = self.find_user_by_email(user_email)
            
            if not user:
                logger.warning(f"User NOT FOUND in Microsoft 365: {user_email}")
                results['success'] = False
                results['actions_failed'].append('User not found in Microsoft 365 - skipping M365 termination')
                return results
            
            logger.info(f"User FOUND in Microsoft 365: {user.get('displayName')} ({user_email})")
            results['user_name'] = user.get('displayName')  # Store for Slack notification
            results['actions_completed'].append(f"User found in Microsoft 365: {user.get('displayName')}")
            
            # Step 2: Check if manager exists in Microsoft 365
            logger.info(f"Checking if manager exists in Microsoft 365: {manager_email}")
            manager_found = self.find_manager_by_email(manager_email)
            
            # Step 3: Only proceed with mailbox operations if BOTH user AND manager are found
            if not manager_found:
                logger.warning(f"Manager NOT FOUND in Microsoft 365: {manager_email}")
                logger.warning(f"Skipping mailbox conversion and delegation - both user and manager must exist")
                results['actions_failed'].append('Manager not found - skipping mailbox operations (requires both user and manager)')
            else:
                logger.info(f"Manager FOUND in Microsoft 365: {manager_found.get('displayName')} ({manager_email})")
                results['actions_completed'].append(f"Manager found: {manager_found.get('displayName')} ({manager_email})")
                
                # Both user and manager found - proceed with mailbox operations
                logger.info(f"Both user and manager found - proceeding with mailbox operations")
                
                # Convert mailbox to shared FIRST (CRITICAL - must succeed before removing licenses)
                logger.info(f"Converting mailbox to shared for: {user_email}")
                if self.convert_mailbox_to_shared(user_email):
                    logger.info(f"Mailbox successfully converted to shared: {user_email}")
                    results['actions_completed'].append('Mailbox converted to shared')
                else:
                    logger.error(f"Failed to convert mailbox to shared: {user_email}")
                    results['actions_failed'].append('Failed to convert mailbox to shared')
                
                # Delegate mailbox access to manager
                logger.info(f"Delegating mailbox access: {user_email} -> {manager_email}")
                if self.delegate_mailbox_access(user_email, manager_email):
                    logger.info(f"Mailbox successfully delegated to manager: {manager_email}")
                    results['actions_completed'].append(f'Mailbox delegated to {manager_email}')
                else:
                    logger.error(f"Failed to delegate mailbox access to: {manager_email}")
                    results['actions_failed'].append('Failed to delegate mailbox access')
            
            # Step 4: Remove licenses (after all Exchange operations) - frees licenses for other users
            license_result = self.remove_user_licenses(user_email)
            if license_result['success']:
                if license_result['licenses_removed'] > 0:
                    license_names = ', '.join(license_result['removed_licenses'])
                    results['actions_completed'].append(f"Removed {license_result['licenses_removed']} licenses: {license_names}")
                    logger.info(f"Licenses removed - now available for other users: {license_names}")
                else:
                    results['actions_completed'].append("No licenses to remove (user already unlicensed)")
            else:
                results['actions_failed'].append('Failed to remove licenses')
                results['success'] = False
            
            # NOTE: User account is kept in Microsoft 365 (unlicensed state)
            # Okta will handle group removals and access control
            logger.info(f"Microsoft 365 user account retained (unlicensed): {user_email}")
            results['actions_completed'].append('User account retained in Microsoft 365 (unlicensed - Okta manages access)')
            
            logger.info(f"Microsoft 365 termination completed for {user_email}")
            return results
            
        except Exception as e:
            logger.error(f"Microsoft 365 termination failed for {user_email}: {e}")
            results['success'] = False
            results['actions_failed'].append(f'Exception: {str(e)}')
            return results

    def delete_user_account(self, user_email: str) -> bool:
        """Delete Microsoft 365 user account completely."""
        try:
            logger.info(f"DELETING Microsoft 365 user account: {user_email}")
            
            # Get user ID for deletion
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found, skipping deletion")
                return True  # Consider success since user doesn't exist
                
            user_id = user.get('id')
            user_name = user.get('displayName', 'Unknown')
            logger.info(f"Found user to delete: {user_name} (ID: {user_id})")
            
            # Make API call to delete user
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Content-Type': 'application/json'
            }
            
            # Delete user via Microsoft Graph API
            delete_url = f'https://graph.microsoft.com/v1.0/users/{user_id}'
            response = requests.delete(delete_url, headers=headers)
            
            if response.status_code == 204:
                logger.info(f"SUCCESS: User completely DELETED from Microsoft 365: {user_email}")
                return True
            else:
                logger.error(f"FAILED to delete user {user_email}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"ERROR deleting Microsoft 365 user {user_email}: {e}")
            return False

    def test_connectivity(self) -> Dict:
        """Test Microsoft Graph API connectivity."""
        try:
            # Test with a simple API call to get current user
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Content-Type': 'application/json'
            }
            
            # Test API call - get organization info
            response = requests.get(
                f'{self.graph_endpoint}/organization',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                org_data = response.json()
                org_name = org_data.get('value', [{}])[0].get('displayName', 'Unknown')
                logger.info("Microsoft Graph API connectivity test successful")
                return {
                    'success': True,
                    'message': f'Connected to Microsoft Graph for organization: {org_name}'
                }
            else:
                logger.error(f"Microsoft Graph API connectivity test failed: {response.status_code}")
                return {
                    'success': False,
                    'error': f'Microsoft Graph API test failed with status {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Microsoft Graph API connectivity test error: {e}")
            return {
                'success': False,
                'error': f'Microsoft Graph API connection failed: {str(e)}'
            }



    def _check_user_exists_in_exchange(self, user_email: str, max_retries: int = 5) -> bool:
        """Check if user exists in Exchange Online with retry logic."""
        import subprocess
        import os
        import time
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"Checking if user {user_email} exists in Exchange Online (attempt {attempt}/{max_retries})")
            
            ps_script = f'''
try {{
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    Connect-ExchangeOnline -AppId '{self.credentials['client_id']}' -Organization 'filevine.com' -CertificateThumbprint '{self.config.get_exchange_certificate_thumbprint()}' -ShowBanner:$false
    $user = Get-User -Identity '{user_email}' -ErrorAction Stop
    Write-Host "USER_EXISTS"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    if ($_.Exception.Message -like "*Couldn't find object*") {{
        Write-Host "USER_NOT_FOUND"
    }} else {{
        Write-Host "ERROR: $($_.Exception.Message)"
    }}
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
'''
            script_path = os.path.join(os.getcwd(), f"temp_check_user_{int(time.time())}.ps1")
            
            try:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(ps_script)
                
                cmd = [
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", script_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                
                # Check for user exists first (success case)
                if result.returncode == 0 and "USER_EXISTS" in result.stdout:
                    logger.info(f"User {user_email} exists in Exchange Online")
                    return True
                
                # Check for user not found (retryable case)
                elif "USER_NOT_FOUND" in result.stdout:
                    if attempt < max_retries:
                        wait_time = min(60, 15 * attempt)  # 15s, 30s, 45s, 60s, 60s
                        logger.info(f"User {user_email} not found in Exchange, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"User {user_email} still not found in Exchange after {max_retries} attempts")
                        return False
                
                # Other errors
                else:
                    logger.error(f"Error checking user existence: {result.stdout}")
                    return False
                    
            except Exception as e:
                logger.error(f"Exception checking user existence: {e}")
                return False
            finally:
                try:
                    os.remove(script_path)
                except:
                    pass
        
        return False

    def add_user_to_group(self, user_email: str, group_name: str) -> bool:
        """Add user to Microsoft 365 group by email and group name using PowerShell."""
        logger.info(f"Adding user {user_email} to Microsoft 365 group: {group_name}")
        
        # First check if user exists in Exchange Online
        if not self._check_user_exists_in_exchange(user_email):
            logger.error(f"User {user_email} does not exist in Exchange Online, skipping group assignment to {group_name}")
            return False
        
        # Use PowerShell directly since it works with our certificate authentication
        return self._add_user_to_group_powershell(user_email, group_name)

    def _add_user_to_group_powershell(self, user_email: str, group_name: str) -> bool:
        """Add user to mail-enabled security group using PowerShell with certificate authentication."""
        try:
            import subprocess
            logger.info(f"Adding user {user_email} to group {group_name} via PowerShell with certificate auth")
            
            # Get Exchange credentials including certificate thumbprint
            exchange_creds = self.config.get_exchange_credentials()
            tenant_id = exchange_creds.get('tenant_id', '')
            client_id = exchange_creds.get('app_id', '')  # Exchange uses 'app_id' key
            cert_thumbprint = exchange_creds.get('cert_thumbprint', '')
            
            if not all([tenant_id, client_id, cert_thumbprint]):
                logger.error(f"Missing required credentials for certificate authentication:")
                logger.error(f"  tenant_id: {'✓' if tenant_id else '✗'}")
                logger.error(f"  client_id: {'✓' if client_id else '✗'}")
                logger.error(f"  cert_thumbprint: {'✓' if cert_thumbprint else '✗'}")
                return False
            
            # Use PowerShell script file to avoid module loading issues
            script_path = r"C:\Users\Cody\Desktop\JML_Automation\scripts\add_user_to_distribution_group.ps1"
            
            # Execute PowerShell script using PowerShell 7 (which has all the required modules)
            # PowerShell 7 is installed in Program Files and handles Exchange modules better
            powershell_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
            
            # Fall back to Windows PowerShell if PowerShell 7 is not available
            import os
            if not os.path.exists(powershell_path):
                powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
                logger.warning("PowerShell 7 not found, falling back to Windows PowerShell 5.1")
            
            result = subprocess.run([
                powershell_path,
                "-ExecutionPolicy", "Bypass",
                "-File", script_path,
                "-UserEmail", user_email,
                "-GroupName", group_name,
                "-CertThumbprint", cert_thumbprint or "",
                "-AppId", client_id or ""
            ], capture_output=True, text=True, timeout=180)
            
            # Check for success
            success_indicators = ["SUCCESS:", "already a member", "already exists"]
            if result.returncode == 0 or any(indicator in result.stdout for indicator in success_indicators):
                logger.info(f"Successfully added user {user_email} to group {group_name} via PowerShell")
                return True
            
            # Check for certificate authentication errors
            if "Key not valid for use in specified state" in result.stdout or "Key not valid for use in specified state" in result.stderr:
                logger.error(f"CERTIFICATE ERROR: Certificate authentication failed for group '{group_name}'")
                logger.warning(f"MANUAL ACTION REQUIRED: Please add {user_email} to group '{group_name}' manually in Exchange Admin Center")
                logger.warning(f"REASON: Certificate authentication is currently experiencing issues")
                logger.info(f"The app registration should already be configured as manager of '{group_name}' from previous setup")
                return False
            
            # Check for permissions errors
            if "sufficient permissions" in result.stdout or "manager of the group" in result.stdout:
                logger.error(f"PERMISSIONS ERROR: App registration needs manager rights for group '{group_name}'")
                logger.error(f"MANUAL ACTION REQUIRED: Run this PowerShell command as an Exchange admin:")
                logger.error(f"  Set-DistributionGroup -Identity '{group_name}' -ManagedBy @{{Add='{client_id}'}}")
                logger.error(f"  Or add the app registration as a manager in Exchange Admin Center")
                return False
            else:
                logger.error(f"PowerShell command failed (exit code {result.returncode})")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding user {user_email} to group {group_name} via PowerShell: {e}")
            return False

    def remove_user_from_group(self, user_email: str, group_name: str) -> bool:
        """Remove user from Microsoft 365 group by email and group name using PowerShell."""
        logger.info(f"Removing user {user_email} from Microsoft 365 group: {group_name}")
        
        # First check if user exists in Exchange Online
        if not self._check_user_exists_in_exchange(user_email):
            logger.error(f"User {user_email} does not exist in Exchange Online, skipping group removal from {group_name}")
            return False
        
        # Use PowerShell directly since it works with our certificate authentication
        return self._remove_user_from_group_powershell(user_email, group_name)

    def _remove_user_from_group_powershell(self, user_email: str, group_name: str) -> bool:
        """Remove user from mail-enabled security group using PowerShell with certificate authentication."""
        try:
            import subprocess
            logger.info(f"Removing user {user_email} from group {group_name} via PowerShell with certificate auth")
            
            # Get Exchange credentials including certificate thumbprint
            exchange_creds = self.config.get_exchange_credentials()
            tenant_id = exchange_creds.get('tenant_id', '')
            client_id = exchange_creds.get('app_id', '')  # Exchange uses 'app_id' key
            cert_thumbprint = exchange_creds.get('cert_thumbprint', '')
            
            if not all([tenant_id, client_id, cert_thumbprint]):
                logger.error(f"Missing required credentials for certificate authentication:")
                logger.error(f"  tenant_id: {'✓' if tenant_id else '✗'}")
                logger.error(f"  client_id: {'✓' if client_id else '✗'}")
                logger.error(f"  cert_thumbprint: {'✓' if cert_thumbprint else '✗'}")
                return False
            
            # Use PowerShell script file for removal
            script_path = r"C:\Users\Cody\Desktop\JML_Automation\scripts\remove_user_from_distribution_group.ps1"
            
            # Execute PowerShell script using PowerShell 7 (which has all the required modules)
            powershell_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
            
            # Fall back to Windows PowerShell if PowerShell 7 is not available
            import os
            if not os.path.exists(powershell_path):
                powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
                logger.warning("PowerShell 7 not found, falling back to Windows PowerShell 5.1")
            
            cmd = [
                powershell_path, 
                "-ExecutionPolicy", "Bypass",
                "-File", script_path,
                "-UserEmail", user_email,
                "-GroupName", group_name,
                "-CertThumbprint", cert_thumbprint,
                "-AppId", client_id
            ]
            
            logger.info(f"Executing PowerShell command to remove user from group: {' '.join(cmd[:6])}...")  # Don't log sensitive params
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            logger.info(f"PowerShell removal output: {result.stdout}")
            if result.stderr:
                logger.warning(f"PowerShell removal stderr: {result.stderr}")
            
            if result.returncode == 0:
                logger.info(f"Successfully removed user {user_email} from group {group_name}")
                return True
            elif "not a member" in result.stdout.lower() or "not found in group" in result.stdout.lower():
                logger.info(f"User {user_email} was not a member of group {group_name} (no action needed)")
                return True
            elif "manager of the group" in result.stdout.lower():
                logger.error(f"PowerShell removal failed: App registration needs manager permissions for group {group_name}")
                logger.error(f"Manual action required: Add app registration as manager of group {group_name}")
                return False
            else:
                logger.error(f"PowerShell removal command failed (exit code {result.returncode})")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing user {user_email} from group {group_name} via PowerShell: {e}")
            return False

    def add_user_to_groups_by_department(self, user_email: str, department: str) -> Dict[str, Any]:
        """Add user to Microsoft 365 groups based on their department - optimized batch operation."""
        results = {
            'success': False,
            'groups_added': [],
            'groups_failed': [],
            'errors': []
        }
        
        try:
            logger.info(f"Processing Microsoft 365 group assignment for {user_email} in department: {department}")
            
            # Everyone gets Opensense and Apple ID
            groups_to_add = ["Opensense", "Apple ID"]
            
            # Add Sales Apps for AE/SDR users only
            if department in ["AE - Account Executives", "SDR - Sales Development Reps"]:
                groups_to_add.append("Sales Apps")
            
            logger.info(f"Groups to assign: {groups_to_add}")
            
            # CHECK USER EXISTS ONCE UPFRONT
            logger.info(f"Checking if user {user_email} exists in Exchange Online before group assignments")
            if not self._check_user_exists_in_exchange(user_email):
                error_msg = f"User {user_email} does not exist in Exchange Online, skipping all group assignments"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
            
            logger.info(f"User {user_email} exists - proceeding with BATCH group assignment (single PowerShell session)")
            
            # BATCH ADD: Add to all groups in a single PowerShell session
            batch_result = self._add_user_to_groups_batch(user_email, groups_to_add)
            
            if batch_result['success']:
                results['groups_added'] = batch_result['groups_added']
                results['groups_failed'] = batch_result['groups_failed']
                results['success'] = len(results['groups_added']) > 0
                
                if results['success']:
                    logger.info(f"Successfully added {user_email} to {len(results['groups_added'])} groups: {results['groups_added']}")
            else:
                results['errors'].append(batch_result.get('error', 'Batch add failed'))
                logger.error(f"Batch group assignment failed: {batch_result.get('error')}")
            
        except Exception as e:
            error_msg = f"Error in Microsoft 365 group assignment for {user_email}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results

    def _add_user_to_groups_batch(self, user_email: str, group_names: List[str]) -> Dict[str, Any]:
        """Add user to multiple groups in a single PowerShell session - MUCH faster!"""
        try:
            import subprocess
            import os
            
            # Get credentials
            app_id = self.credentials['client_id']
            cert_thumbprint = self._get_cert_thumbprint()
            
            # Build PowerShell commands for all groups
            group_commands = []
            for group_name in group_names:
                group_commands.append(f"""
        Write-Host "Adding to {group_name}..."
        try {{
            Add-DistributionGroupMember -Identity '{group_name}' -Member '{user_email}' -ErrorAction Stop
            Write-Host "SUCCESS: Added to {group_name}"
        }} catch {{
            if ($_.Exception.Message -like "*already a member*") {{
                Write-Host "SKIP: Already in {group_name}"
            }} else {{
                Write-Host "FAILED: {group_name} - $($_.Exception.Message)"
            }}
        }}""")
            
            ps_script = f"""
try {{
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    Connect-ExchangeOnline -AppId '{app_id}' -Organization 'filevine.com' -CertificateThumbprint '{cert_thumbprint}' -ShowBanner:$false
    
    {''.join(group_commands)}
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    Write-Host "CRITICAL_ERROR: $($_.Exception.Message)"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
"""
            
            script_path = os.path.join(os.getcwd(), f"temp_batch_add_{int(time.time())}.ps1")
            
            try:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(ps_script)
                
                cmd = [
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", script_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                
            finally:
                try:
                    os.remove(script_path)
                except:
                    pass
            
            # Parse results
            groups_added = []
            groups_failed = []
            
            for group_name in group_names:
                if f"SUCCESS: Added to {group_name}" in result.stdout or f"SKIP: Already in {group_name}" in result.stdout:
                    groups_added.append(group_name)
                else:
                    groups_failed.append(group_name)
            
            logger.info(f"Batch add results: {len(groups_added)} succeeded, {len(groups_failed)} failed")
            
            return {
                'success': True,
                'groups_added': groups_added,
                'groups_failed': groups_failed,
                'output': result.stdout
            }
            
        except Exception as e:
            logger.error(f"Batch group add failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'groups_added': [],
                'groups_failed': group_names
            }

    def create_shared_mailbox(self, display_name: str, email_address: str, alias: str = None) -> Dict[str, Any]:
        """
        Create a shared mailbox in Exchange Online.
        
        Args:
            display_name: Display name for the shared mailbox
            email_address: Email address for the shared mailbox (e.g., john.hamster@filevine.com)
            alias: Alias for the mailbox (defaults to username part of email)
            
        Returns:
            Dict with success status and details
        """
        try:
            if not alias:
                alias = email_address.split('@')[0]
            
            # Get credentials and certificate info
            app_id = self.credentials['client_id']
            organization = 'filevine.com'
            cert_thumbprint = self._get_cert_thumbprint()
            
            logger.info(f"Creating shared mailbox: {email_address} ({display_name})")
            
            # PowerShell script to create shared mailbox
            ps_script = f'''
try {{
    Write-Host "Importing Exchange Online Management module..."
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    
    Write-Host "Connecting to Exchange Online..."
    Connect-ExchangeOnline -AppId '{app_id}' -Organization '{organization}' -CertificateThumbprint '{cert_thumbprint}' -ShowBanner:$false
    
    Write-Host "Creating shared mailbox: {email_address}"
    $mailbox = New-Mailbox -Shared -Name "{display_name}" -DisplayName "{display_name}" -PrimarySmtpAddress "{email_address}" -Alias "{alias}"
    
    if ($mailbox) {{
        Write-Host "SUCCESS: Shared mailbox created successfully"
        Write-Host "Identity: $($mailbox.Identity)"
        Write-Host "PrimarySmtpAddress: $($mailbox.PrimarySmtpAddress)"
        Write-Host "RecipientTypeDetails: $($mailbox.RecipientTypeDetails)"
    }} else {{
        Write-Host "ERROR: Failed to create shared mailbox"
    }}
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
'''
            
            # Execute PowerShell script with secure temp file handling
            import subprocess
            import os
            
            script_fd, script_path = tempfile.mkstemp(suffix=".ps1", prefix="jml_create_mailbox_")
            
            try:
                # Write script to temp file
                with os.fdopen(script_fd, 'w', encoding='utf-8') as f:
                    f.write(ps_script)
                
                cmd = [
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", script_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
            finally:
                # Clean up temp file with proper error handling
                try:
                    os.remove(script_path)
                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.warning(f"Could not remove temp file {script_path}: {e}")
            
            if result.returncode == 0:
                logger.info(f"Successfully created shared mailbox: {email_address}")
                return {
                    "success": True,
                    "email": email_address,
                    "display_name": display_name,
                    "alias": alias,
                    "output": result.stdout
                }
            else:
                error_msg = f"Failed to create shared mailbox {email_address}: {result.stderr}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "output": result.stderr}
                
        except Exception as e:
            error_msg = f"Error creating shared mailbox {email_address}: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def setup_email_forwarding(self, mailbox_email: str, forward_to_email: str) -> Dict[str, Any]:
        """
        Set up email forwarding for a mailbox to forward all emails to an external address.
        
        Args:
            mailbox_email: The mailbox to set up forwarding for (e.g., johnhamster@filevine.com)
            forward_to_email: External email address to forward to (e.g., john@hamsterwheel.com)
            
        Returns:
            Dict with success status and details
        """
        try:
            # Get credentials and certificate info
            app_id = self.credentials['client_id']
            organization = 'filevine.com'
            cert_thumbprint = self._get_cert_thumbprint()
            
            logger.info(f"Setting up email forwarding: {mailbox_email} -> {forward_to_email}")
            
            # PowerShell script to set up email forwarding
            ps_script = f'''
try {{
    Write-Host "Importing Exchange Online Management module..."
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    
    Write-Host "Connecting to Exchange Online..."
    Connect-ExchangeOnline -AppId '{app_id}' -Organization '{organization}' -CertificateThumbprint '{cert_thumbprint}' -ShowBanner:$false
    
    Write-Host "Setting up email forwarding for: {mailbox_email}"
    Set-Mailbox -Identity "{mailbox_email}" -ForwardingSmtpAddress "{forward_to_email}" -DeliverToMailboxAndForward $false
    
    # Verify forwarding was set up (Exchange prefixes external addresses with "smtp:")
    $mailbox = Get-Mailbox -Identity "{mailbox_email}"
    $expectedSmtpAddress = "smtp:{forward_to_email}"
    if ($mailbox.ForwardingSmtpAddress -eq $expectedSmtpAddress -or $mailbox.ForwardingSmtpAddress -eq "{forward_to_email}") {{
        Write-Host "SUCCESS: Email forwarding configured successfully"
        Write-Host "Mailbox: {mailbox_email}"
        Write-Host "Forwarding to: {forward_to_email}"
        Write-Host "Deliver to mailbox and forward: $($mailbox.DeliverToMailboxAndForward)"
    }} else {{
        Write-Host "ERROR: Email forwarding configuration failed"
        Write-Host "Expected: {forward_to_email} (or smtp:{forward_to_email})"
        Write-Host "Actual ForwardingSmtpAddress: $($mailbox.ForwardingSmtpAddress)"
        Write-Host "Actual ForwardingAddress: $($mailbox.ForwardingAddress)"
    }}
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 0
}} catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}}
'''
            
            # Execute PowerShell script with secure temp file handling
            import subprocess
            import os
            
            script_fd, script_path = tempfile.mkstemp(suffix=".ps1", prefix="jml_setup_forwarding_")
            
            try:
                # Write script to temp file
                with os.fdopen(script_fd, 'w', encoding='utf-8') as f:
                    f.write(ps_script)
                
                cmd = [
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", script_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
            finally:
                # Clean up temp file with proper error handling
                try:
                    os.remove(script_path)
                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.warning(f"Could not remove temp file {script_path}: {e}")
            
            if result.returncode == 0:
                logger.info(f"Successfully set up email forwarding: {mailbox_email} -> {forward_to_email}")
                return {
                    "success": True,
                    "mailbox": mailbox_email,
                    "forward_to": forward_to_email,
                    "output": result.stdout
                }
            else:
                error_msg = f"Failed to set up email forwarding {mailbox_email} -> {forward_to_email}: {result.stderr}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "output": result.stderr}
                
        except Exception as e:
            error_msg = f"Error setting up email forwarding {mailbox_email} -> {forward_to_email}: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def create_partner_mailbox_with_forwarding(self, partner_name: str, filevine_email: str, partner_email: str) -> Dict[str, Any]:
        """
        Create a shared mailbox for a partner and set up email forwarding.
        This is a convenience method that combines shared mailbox creation and forwarding setup.
        
        Args:
            partner_name: Partner's full name for display name
            filevine_email: Filevine email address (e.g., johnhamster@filevine.com)
            partner_email: Partner's external email for forwarding (e.g., john@hamsterwheel.com)
            
        Returns:
            Dict with success status and details of both operations
        """
        try:
            # Extract alias from filevine email
            alias = filevine_email.split('@')[0]
            
            logger.info(f"Creating partner mailbox with forwarding: {partner_name} ({filevine_email} -> {partner_email})")
            
            # Step 1: Create shared mailbox
            mailbox_result = self.create_shared_mailbox(partner_name, filevine_email, alias)
            
            if not mailbox_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to create shared mailbox: {mailbox_result.get('error')}",
                    "mailbox_result": mailbox_result
                }
            
            # Step 2: Set up email forwarding
            forwarding_result = self.setup_email_forwarding(filevine_email, partner_email)
            
            if not forwarding_result["success"]:
                return {
                    "success": False,
                    "error": f"Shared mailbox created but forwarding failed: {forwarding_result.get('error')}",
                    "mailbox_result": mailbox_result,
                    "forwarding_result": forwarding_result
                }
            
            logger.info(f"Successfully created partner mailbox with forwarding: {filevine_email}")
            return {
                "success": True,
                "partner_name": partner_name,
                "filevine_email": filevine_email,
                "partner_email": partner_email,
                "mailbox_result": mailbox_result,
                "forwarding_result": forwarding_result
            }
            
        except Exception as e:
            error_msg = f"Error creating partner mailbox with forwarding: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

# Test function
def test_microsoft_service():
    """Test Microsoft 365 service functionality."""
    try:
        ms = MicrosoftService()
        
        # Test user lookup
        test_email = "test@filevine.com"  # Replace with actual test email
        user = ms.find_user_by_email(test_email)
        
        if user:
            print(f"Found user: {user.get('displayName')} ({test_email})")
        else:
            print(f"User not found: {test_email}")
            
    except Exception as e:
        print(f"Test failed: {e}")

# Aliases for compatibility with import expectations
MicrosoftTermination = MicrosoftService  # For existing termination workflows

if __name__ == "__main__":
    test_microsoft_service()
