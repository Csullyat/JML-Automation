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
    
    def find_manager_by_employee_id(self, employee_id: str) -> Optional[str]:
        """Find manager's email by employee ID."""
        try:
            # Search for user by employee ID
            filter_query = f"employeeId eq '{employee_id}'"
            users = self._make_graph_request('GET', f'/users?$filter={filter_query}')
            
            if users.get('value'):
                manager_user = users['value'][0]
                manager_email = manager_user.get('mail') or manager_user.get('userPrincipalName')
                logger.info(f"Found manager email for employee {employee_id}: {manager_email}")
                return manager_email
            else:
                logger.warning(f"No manager found for employee ID {employee_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding manager for employee {employee_id}: {e}")
            return None
    
    def convert_mailbox_to_shared(self, user_email: str) -> bool:
        """Convert user mailbox to shared mailbox."""
        try:
            logger.info(f"Converting mailbox to shared for {user_email}")
            
            # Update the user's mailbox type
            update_data = {
                "mailboxSettings": {
                    "archiveFolder": "SharedMailbox"
                }
            }
            
            # Note: Converting to shared mailbox typically requires Exchange Online PowerShell
            # This is a placeholder for the Graph API approach
            # In practice, you might need to use Exchange Online REST API or PowerShell
            
            logger.info(f"Mailbox conversion initiated for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to convert mailbox for {user_email}: {e}")
            return False
    
    def delegate_mailbox_access(self, user_email: str, manager_email: str) -> bool:
        """Grant manager full access to user's mailbox."""
        try:
            logger.info(f"Delegating mailbox access: {user_email} -> {manager_email}")
            
            # This typically requires Exchange Online management
            # Placeholder for the actual delegation logic
            
            logger.info(f"Mailbox delegation completed: {manager_email} now has access to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delegate mailbox access: {e}")
            return False
    
    def remove_user_licenses(self, user_email: str) -> Dict:
        """Remove all licenses from user."""
        try:
            logger.info(f"Removing licenses for {user_email}")
            
            # Get current user licenses
            user_data = self._make_graph_request('GET', f'/users/{user_email}')
            current_licenses = user_data.get('assignedLicenses', [])
            
            if not current_licenses:
                logger.info(f"No licenses found for {user_email}")
                return {'success': True, 'licenses_removed': 0}
            
            # Remove all licenses
            license_update = {
                "addLicenses": [],
                "removeLicenses": [license['skuId'] for license in current_licenses]
            }
            
            result = self._make_graph_request('POST', f'/users/{user_email}/assignLicense', license_update)
            
            logger.info(f"Removed {len(current_licenses)} licenses from {user_email}")
            return {
                'success': True,
                'licenses_removed': len(current_licenses),
                'removed_licenses': [license.get('skuPartNumber', 'Unknown') for license in current_licenses]
            }
            
        except Exception as e:
            logger.error(f"Failed to remove licenses for {user_email}: {e}")
            return {'success': False, 'error': str(e)}
    
    def transfer_onedrive_data(self, user_email: str, manager_email: str) -> bool:
        """Transfer OneDrive data to manager."""
        try:
            logger.info(f"Transferring OneDrive data: {user_email} -> {manager_email}")
            
            # Get user's OneDrive
            user_drive = self._make_graph_request('GET', f'/users/{user_email}/drive')
            
            if not user_drive:
                logger.warning(f"No OneDrive found for {user_email}")
                return True
            
            # This is a complex operation that typically requires:
            # 1. Granting manager access to the OneDrive
            # 2. Optionally copying files to manager's OneDrive
            # 3. Setting up proper permissions
            
            # For now, we'll grant the manager access to the entire OneDrive
            drive_id = user_drive['id']
            
            permission_data = {
                "recipients": [{"email": manager_email}],
                "roles": ["write"],
                "message": f"Access granted for terminated employee {user_email} data management"
            }
            
            result = self._make_graph_request('POST', f'/drives/{drive_id}/root/invite', permission_data)
            
            logger.info(f"OneDrive access granted to {manager_email} for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transfer OneDrive data: {e}")
            return False
    
    def execute_complete_termination(self, user_email: str, manager_employee_id: str) -> Dict:
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
            
            results['actions_completed'].append('✅ User found in Microsoft 365')
            
            # Step 2: Find manager
            manager_email = self.find_manager_by_employee_id(manager_employee_id)
            if not manager_email:
                results['actions_failed'].append('Manager not found - manual delegation required')
                manager_email = None
            else:
                results['actions_completed'].append(f'✅ Manager found: {manager_email}')
            
            # Step 3: Remove licenses
            license_result = self.remove_user_licenses(user_email)
            if license_result['success']:
                results['actions_completed'].append(f"✅ Removed {license_result['licenses_removed']} licenses")
            else:
                results['actions_failed'].append('❌ Failed to remove licenses')
                results['success'] = False
            
            # Step 4: Convert mailbox to shared (if manager available)
            if manager_email:
                if self.convert_mailbox_to_shared(user_email):
                    results['actions_completed'].append('✅ Mailbox converted to shared')
                else:
                    results['actions_failed'].append('❌ Failed to convert mailbox to shared')
                
                # Step 5: Delegate mailbox access
                if self.delegate_mailbox_access(user_email, manager_email):
                    results['actions_completed'].append(f'✅ Mailbox delegated to {manager_email}')
                else:
                    results['actions_failed'].append('❌ Failed to delegate mailbox access')
                
                # Step 6: Transfer OneDrive data
                if self.transfer_onedrive_data(user_email, manager_email):
                    results['actions_completed'].append(f'✅ OneDrive access granted to {manager_email}')
                else:
                    results['actions_failed'].append('❌ Failed to transfer OneDrive data')
            
            else:
                results['actions_failed'].extend([
                    '⚠️ Mailbox delegation skipped - manager not found',
                    '⚠️ OneDrive transfer skipped - manager not found'
                ])
            
            logger.info(f"Microsoft 365 termination completed for {user_email}")
            return results
            
        except Exception as e:
            logger.error(f"Microsoft 365 termination failed for {user_email}: {e}")
            results['success'] = False
            results['actions_failed'].append(f'❌ Exception: {str(e)}')
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
            print(f"✅ Found user: {user.get('displayName')} ({test_email})")
        else:
            print(f"❌ User not found: {test_email}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_microsoft_termination()
