# microsoft_termination.py - Microsoft 365 and Exchange termination automation

import logging
import requests
import json
from typing import Dict, Optional, List
from datetime import datetime
from config import get_microsoft_graph_credentials

logger = logging.getLogger(__name__)

class MicrosoftTermination:
    """Microsoft 365 and Exchange termination automation."""
    
    def __init__(self):
        """Initialize Microsoft Graph client."""
        self.credentials = get_microsoft_graph_credentials()
        self.access_token = None
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        
        if not self.credentials.get('client_id'):
            raise Exception("Microsoft Graph credentials not available")
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token for Microsoft Graph."""
        if self.access_token:
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
            
            logger.info("Successfully obtained Microsoft Graph access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph access token: {e}")
            raise
    
    def _make_graph_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
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
    
    def convert_mailbox_to_shared(self, user_email: str) -> bool:
        """Convert user mailbox to shared mailbox using certificate-based authentication."""
        try:
            logger.info(f"Attempting automated mailbox conversion for {user_email}")
            
            import subprocess
            from config import get_microsoft_graph_credentials
            
            # Get the app credentials
            creds = get_microsoft_graph_credentials()
            app_id = creds['client_id']
            tenant_id = creds['tenant_id']
            # Use domain name instead of tenant GUID for Exchange Online
            organization = "filevine.com"
            
            # Certificate thumbprint for Exchange Online authentication
            cert_thumbprint = "DF8B5FA21923E56ABA0FC540CBC2056977999CF9"
            
            # Try automated approach with certificate authentication
            ps_script = f"""
try {{
    Write-Host "Importing Exchange Online Management module..."
    Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
    
    Write-Host "Connecting to Exchange Online with certificate authentication..."
    # Using certificate-based authentication for unattended automation
    Connect-ExchangeOnline -AppId '{app_id}' -Organization '{organization}' -CertificateThumbprint '{cert_thumbprint}' -ShowBanner:$false
    
    Write-Host "Getting current mailbox information..."
    $currentMailbox = Get-Mailbox -Identity '{user_email}' -ErrorAction Stop
    Write-Host "Current mailbox type: $($currentMailbox.RecipientTypeDetails)"
    
    Write-Host "Converting mailbox to shared type..."
    Set-Mailbox -Identity '{user_email}' -Type Shared -Confirm:$false -ErrorAction Stop
    Write-Host "Conversion command completed."
    
    Write-Host "Waiting for changes to propagate..."
    Start-Sleep -Seconds 10
    
    Write-Host "Verifying conversion..."
    $mailbox = Get-Mailbox -Identity '{user_email}' -ErrorAction Stop
    Write-Host "New mailbox type: $($mailbox.RecipientTypeDetails)"
    
    if ($mailbox.RecipientTypeDetails -eq "SharedMailbox") {{
        Write-Host "SUCCESS: Mailbox successfully converted to SharedMailbox"
        Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
        exit 0
    }} else {{
        Write-Host "ERROR: Mailbox type is $($mailbox.RecipientTypeDetails), expected SharedMailbox"
        Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
        exit 1
    }}
}} catch {{
    Write-Host "ERROR: $($_.Exception.Message)"
    Write-Host "Full error: $_"
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 2
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)  # 1 minute timeout for automation
            
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
            
            # Check for success based on exit code AND output content
            if result.returncode == 0 and "SUCCESS: Mailbox successfully converted to SharedMailbox" in result.stdout:
                logger.info(f"SUCCESS: Mailbox successfully converted to shared for {user_email}")
                return True
            else:
                logger.warning(f"Automated conversion failed (exit code {result.returncode})")
                if "Connect-ExchangeOnline" in result.stderr and "not recognized" in result.stderr:
                    logger.error("Exchange Online PowerShell module commands not available in subprocess")
                
                # Fall back to manual instructions
                logger.warning("=" * 60)
                logger.warning("MANUAL ACTION REQUIRED: Mailbox conversion to shared type")
                logger.warning("=" * 60)
                logger.warning("The automated PowerShell approach failed due to module loading constraints.")
                logger.warning("Please run ONE of the following commands manually:")
                logger.warning("")
                logger.warning("Option 1 - Run the prepared script:")
                logger.warning(f"   powershell.exe -ExecutionPolicy Bypass -File 'manual_convert.ps1'")
                logger.warning("")
                logger.warning("Option 2 - Run individual PowerShell commands:")
                logger.warning("   Import-Module ExchangeOnlineManagement")
                logger.warning("   Connect-ExchangeOnline")
                logger.warning(f"   Set-Mailbox -Identity '{user_email}' -Type Shared")
                logger.warning("   Disconnect-ExchangeOnline")
                logger.warning("")
                logger.warning("After conversion, the automation will continue with delegation and license removal.")
                logger.warning("=" * 60)
                
                # Return False to indicate manual action needed
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
            from config import get_microsoft_graph_credentials
            
            # Get the app credentials
            creds = get_microsoft_graph_credentials()
            app_id = creds['client_id']
            tenant_id = creds['tenant_id']
            # Use domain name instead of tenant GUID for Exchange Online
            organization = "filevine.com"
            
            # Certificate thumbprint for Exchange Online authentication
            cert_thumbprint = "DF8B5FA21923E56ABA0FC540CBC2056977999CF9"
            
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
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
        """Execute complete Microsoft 365 termination."""
        logger.info(f"Starting Microsoft 365 termination for {user_email}")
        
        results = {
            'user_email': user_email,
            'termination_time': datetime.now(),
            'actions_completed': [],
            'actions_failed': [],
            'success': True
        }
        
        try:
            # Step 1: Verify user exists
            user = self.find_user_by_email(user_email)
            if not user:
                results['success'] = False
                results['actions_failed'].append('User not found in Microsoft 365')
                return results
            
            results['actions_completed'].append('User found in Microsoft 365')
            
            # Step 2: Find manager by email
            manager_found = self.find_manager_by_email(manager_email)
            if not manager_found:
                results['actions_failed'].append('Manager not found - manual delegation required')
                manager_email = None
            else:
                results['actions_completed'].append(f'Manager found: {manager_email}')
            
            # Step 3: Convert mailbox to shared FIRST (before removing license!)
            if manager_email:
                if self.convert_mailbox_to_shared(user_email):
                    results['actions_completed'].append('Mailbox converted to shared')
                else:
                    results['actions_failed'].append('Failed to convert mailbox to shared')
                
                # Step 4: Delegate mailbox access (while user still has Exchange license)
                if self.delegate_mailbox_access(user_email, manager_email):
                    results['actions_completed'].append(f'Mailbox delegated to {manager_email}')
                else:
                    results['actions_failed'].append('Failed to delegate mailbox access')
            
            # Step 5: Remove licenses LAST (after all Exchange operations)
            license_result = self.remove_user_licenses(user_email)
            if license_result['success']:
                if license_result['licenses_removed'] > 0:
                    license_names = ', '.join(license_result['removed_licenses'])
                    results['actions_completed'].append(f"Removed {license_result['licenses_removed']} licenses: {license_names}")
                else:
                    results['actions_completed'].append("No licenses to remove (user already unlicensed)")
            else:
                results['actions_failed'].append('Failed to remove licenses')
                results['success'] = False
            
            # Handle case where manager was not found
            if not manager_email:
                results['actions_failed'].extend([
                    'Mailbox delegation skipped - manager not found'
                ])
            
            logger.info(f"Microsoft 365 termination completed for {user_email}")
            return results
            
        except Exception as e:
            logger.error(f"Microsoft 365 termination failed for {user_email}: {e}")
            results['success'] = False
            results['actions_failed'].append(f'Exception: {str(e)}')
            return results

# Test function
def test_microsoft_termination():
    """Test Microsoft 365 termination functionality."""
    try:
        ms_term = MicrosoftTermination()
        
        # Test user lookup
        test_email = "test@filevine.com"  # Replace with actual test email
        user = ms_term.find_user_by_email(test_email)
        
        if user:
            print(f"Found user: {user.get('displayName')} ({test_email})")
        else:
            print(f"User not found: {test_email}")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_microsoft_termination()
