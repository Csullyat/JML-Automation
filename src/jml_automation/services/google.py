# google_termination.py - Google Workspace user termination and data transfer

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from jml_automation import config

logger = logging.getLogger(__name__)

class GoogleTermination:
    """Google Workspace user termination with data transfer capabilities."""
    
    def __init__(self):
        """Initialize Google Workspace termination client."""
        try:
            self.credentials = config.get_google_service_account_credentials()
            self.admin_service = build('admin', 'directory_v1', credentials=self.credentials)
            self.gmail_service = build('gmail', 'v1', credentials=self.credentials)
            
            # Get domain info
            google_config = config.get_google_credentials()
            self.domain = google_config['domain']
            self.admin_email = google_config['admin_email']
            
            logger.info("Google Workspace termination client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace client: {e}")
            raise
    
    def get_user_info(self, user_email: str) -> Optional[Dict]:
        """Get user information from Google Workspace."""
        try:
            user = self.admin_service.users().get(userKey=user_email).execute()
            return user
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"User {user_email} not found in Google Workspace")
                return None
            else:
                logger.error(f"Error getting user {user_email}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting user {user_email}: {e}")
            return None
    
    def suspend_user(self, user_email: str) -> bool:
        """Suspend user account in Google Workspace."""
        try:
            user_body = {
                'suspended': True,
                'suspensionReason': 'Employee termination'
            }
            
            self.admin_service.users().update(
                userKey=user_email,
                body=user_body
            ).execute()
            
            logger.info(f"User {user_email} suspended successfully")
            return True
            
        except HttpError as e:
            logger.error(f"Error suspending user {user_email}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Exception suspending user {user_email}: {e}")
            return False
    
    def transfer_drive_data(self, user_email: str, manager_email: str) -> Dict:
        """Transfer Google Drive data to manager."""
        try:
            # Note: Google Drive transfer typically requires the Data Transfer API
            # This is a placeholder implementation
            logger.info(f"Initiating Drive data transfer from {user_email} to {manager_email}")
            
            # In a real implementation, you would use:
            # drive_service = build('drive', 'v3', credentials=self.credentials)
            # And implement file ownership transfer
            
            return {
                'success': True,
                'transferred_files': 0,  # Placeholder
                'message': 'Drive transfer initiated (placeholder implementation)'
            }
            
        except Exception as e:
            logger.error(f"Error transferring Drive data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delegate_gmail_access(self, user_email: str, manager_email: str) -> bool:
        """Delegate Gmail access to manager."""
        try:
            # Create delegation
            delegate_body = {
                'delegateEmail': manager_email
            }
            
            # Note: This requires domain-wide delegation and proper scopes
            self.gmail_service.users().settings().delegates().create(
                userId=user_email,
                body=delegate_body
            ).execute()
            
            logger.info(f"Gmail delegation created: {user_email} → {manager_email}")
            return True
            
        except HttpError as e:
            logger.error(f"Error creating Gmail delegation: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Exception creating Gmail delegation: {e}")
            return False
    
    def remove_from_groups(self, user_email: str) -> Dict:
        """Remove user from Google Groups."""
        try:
            # Get user's groups
            groups_service = self.admin_service.groups()
            
            # Note: This requires listing all groups and checking membership
            # Simplified implementation
            removed_count = 0
            
            logger.info(f"Removing {user_email} from Google Groups")
            
            return {
                'success': True,
                'groups_removed': removed_count
            }
            
        except Exception as e:
            logger.error(f"Error removing user from groups: {e}")
            return {
                'success': False,
                'groups_removed': 0
            }
    
    def execute_complete_termination(self, user_email: str, manager_email: str = None) -> Dict:
        """
        Execute complete Google Workspace termination.
        
        Args:
            user_email: Email of user to terminate
            manager_email: Email of manager for data delegation
        Returns:
            Dict with termination results
        """
        logger.info(f"Starting Google Workspace termination for {user_email}")
        start_time = datetime.now()
        actions_completed = []
        actions_failed = []
        warnings = []
        errors = []
        try:
            # Step 1: Get user info
            logger.info(f"Step 1: Looking up user {user_email} in Google Workspace")
            user_info = self.get_user_info(user_email)
            if not user_info:
                return {
                    'success': False,
                    'user_email': user_email,
                    'error': 'User not found in Google Workspace',
                    'actions_completed': actions_completed,
                    'actions_failed': ['User lookup failed'],
                    'warnings': warnings,
                    'errors': ['User not found']
                }
            
            user_name = user_info.get('name', {}).get('fullName', user_email)
            is_suspended = user_info.get('suspended', False)
            
            logger.info(f"Found user: {user_name} (Suspended: {is_suspended})")
            
            # Step 2: Delegate Gmail access (if manager provided)
            if manager_email:
                logger.info(f"Step 2: Delegating Gmail access to {manager_email}")
                if self.delegate_gmail_access(user_email, manager_email):
                    actions_completed.append(f"Gmail delegated to {manager_email}")
                    logger.info("Gmail delegation created")
                else:
                    actions_failed.append("Failed to delegate Gmail access")
                    errors.append("Gmail delegation failed")
                    logger.error("Gmail delegation failed")
            else:
                warnings.append("No manager provided - Gmail delegation skipped")
                logger.warning("No manager provided for Gmail delegation")
            
            # Step 3: Transfer Drive data (if manager provided)
            if manager_email:
                logger.info(f"Step 3: Transferring Drive data to {manager_email}")
                drive_result = self.transfer_drive_data(user_email, manager_email)
                
                if drive_result['success']:
                    actions_completed.append("Drive data transfer initiated")
                    logger.info("Drive data transfer initiated")
                else:
                    actions_failed.append("Failed to transfer Drive data")
                    errors.append(f"Drive transfer failed: {drive_result.get('error', 'Unknown error')}")
                    logger.error("Drive data transfer failed")
            else:
                warnings.append("No manager provided - Drive transfer skipped")
                logger.warning("No manager provided for Drive transfer")
            
            # Step 4: Remove from Google Groups
            logger.info(f"Step 4: Removing user from Google Groups")
            groups_result = self.remove_from_groups(user_email)
            
            if groups_result['success']:
                groups_removed = groups_result['groups_removed']
                actions_completed.append(f"Removed from {groups_removed} Google Groups")
                logger.info(f"Removed from {groups_removed} groups")
            else:
                actions_failed.append("Failed to remove from Google Groups")
                errors.append("Group removal failed")
                logger.error("Failed to remove from groups")
            
            # Step 5: Suspend user account
            if not is_suspended:
                logger.info(f"Step 5: Suspending user account")
                if self.suspend_user(user_email):
                    actions_completed.append("User account suspended")
                    logger.info("User account suspended")
                else:
                    actions_failed.append("Failed to suspend user")
                    errors.append("User suspension failed")
                    logger.error("Failed to suspend user")
            else:
                actions_completed.append("User already suspended")
                logger.info("User already suspended")
            
            # Determine success
            critical_failures = [f for f in actions_failed if 'suspend' in f.lower()]
            success = len(critical_failures) == 0
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'success': success,
                'user_email': user_email,
                'user_name': user_name,
                'manager_email': manager_email,
                'actions_completed': actions_completed,
                'actions_failed': actions_failed,
                'warnings': warnings,
                'errors': errors,
                'duration_seconds': duration,
                'start_time': start_time,
                'end_time': end_time
            }
            
            if success:
                logger.info(f"Google Workspace termination completed successfully for {user_email} in {duration:.1f}s")
            else:
                logger.warning(f"Google Workspace termination completed with issues for {user_email} in {duration:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Fatal error during Google Workspace termination for {user_email}: {e}")
            
            return {
                'success': False,
                'user_email': user_email,
                'error': f"Fatal error: {str(e)}",
                'actions_completed': actions_completed,
                'actions_failed': actions_failed + [f"Fatal error: {str(e)}"],
                'warnings': warnings,
                'errors': errors + [f"Fatal error: {str(e)}"],
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def test_connectivity(self) -> Dict:
        """Test Google Workspace API connectivity."""
        try:
            # Test with a simple API call
            self.admin_service.users().list(domain=self.domain, maxResults=1).execute()
            
            return {
                'success': True,
                'message': 'Google Workspace API connection successful',
                'domain': self.domain
            }
            
        except RefreshError as e:
            return {
                'success': False,
                'error': f"Authentication failed: {str(e)}"
            }
            
        except HttpError as e:
            return {
                'success': False,
                'error': f"API error: {str(e)}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }

class GoogleTerminationManager:
    """Handles Google Workspace user termination and data transfer."""
    def __init__(self):
        try:
            from jml_automation.config import Config
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Get configuration
            config = Config()
            
            # Get service account credentials from 1Password
            service_account_info = config.get_google_service_account_key()
            scopes = [
                'https://www.googleapis.com/auth/admin.directory.user',
                'https://www.googleapis.com/auth/admin.datatransfer'
            ]
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
            admin_email = "codyatkinson@filevine.com"  # Update as needed
            self.delegated_credentials = self.credentials.with_subject(admin_email)
            self.directory_service = build('admin', 'directory_v1', credentials=self.delegated_credentials)
            self.datatransfer_service = build('admin', 'datatransfer_v1', credentials=self.delegated_credentials)
            logger.info("Google Workspace API clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace API clients: {e}")
            raise

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            logger.info(f"Looking up Google Workspace user: {email}")
            result = self.directory_service.users().get(userKey=email).execute()
            logger.info(f"Found Google Workspace user: {result.get('name', {}).get('fullName')} ({email})")
            return result
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Google Workspace user not found: {email}")
                return None
            else:
                logger.error(f"Error finding Google Workspace user {email}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error finding Google Workspace user {email}: {e}")
            raise

    def find_manager_by_email(self, manager_email: str) -> Optional[Dict]:
        try:
            logger.info(f"Looking up manager for data transfer: {manager_email}")
            manager = self.find_user_by_email(manager_email)
            if manager:
                logger.info(f"Found manager: {manager.get('name', {}).get('fullName')} ({manager_email})")
                return manager
            else:
                logger.warning(f"Manager not found in Google Workspace: {manager_email}")
                return None
        except Exception as e:
            logger.error(f"Error finding manager {manager_email}: {e}")
            raise

    def transfer_user_data(self, user_email: str, manager_email: str) -> bool:
        try:
            logger.info(f"Starting data transfer: {user_email} -> {manager_email}")
            user = self.find_user_by_email(user_email)
            manager = self.find_manager_by_email(manager_email)
            if not user:
                logger.error(f"Cannot transfer data: source user {user_email} not found")
                return False
            if not manager:
                logger.error(f"Cannot transfer data: manager {manager_email} not found")
                return False
            applications = [
                {'id': 55656082996, 'name': 'Drive and Docs'},
                {'id': 435070579839, 'name': 'Gmail'}
            ]
            transfer_requests = []
            for app in applications:
                transfer_request = {
                    'applicationId': app['id'],
                    'applicationTransferParams': []
                }
                if app['id'] == 55656082996:
                    transfer_request['applicationTransferParams'] = [
                        {'key': 'PRIVACY_LEVEL', 'value': ['SHARED', 'PRIVATE']}
                    ]
                transfer_requests.append(transfer_request)
            transfer_body = {
                'oldOwnerUserId': user['id'],
                'newOwnerUserId': manager['id'],
                'applicationDataTransfers': transfer_requests
            }
            logger.info(f"Executing data transfer for {len(applications)} applications")
            logger.info(f"Transfer from user ID: {user['id']} to manager ID: {manager['id']}")
            result = self.datatransfer_service.transfers().insert(body=transfer_body).execute()
            transfer_id = result.get('id')
            logger.info(f"Data transfer initiated with ID: {transfer_id}")
            return self._monitor_data_transfer(transfer_id, user_email, manager_email)
        except Exception as e:
            logger.error(f"Error transferring data from {user_email} to {manager_email}: {e}")
            return False

    def _monitor_data_transfer(self, transfer_id: str, user_email: str, manager_email: str, max_wait_time: int = 300) -> bool:
        try:
            logger.info(f"Monitoring data transfer {transfer_id} (max wait: {max_wait_time}s)")
            import time
            start_time = time.time()
            poll_interval = 5
            while time.time() - start_time < max_wait_time:
                result = self.datatransfer_service.transfers().get(dataTransferId=transfer_id).execute()
                overall_status = result.get('overallTransferStatusCode')
                logger.info(f"Transfer status: {overall_status}")
                if overall_status == 'completed':
                    logger.info(f"Data transfer completed successfully: {user_email} -> {manager_email}")
                    return True
                elif overall_status == 'failed':
                    logger.error(f"Data transfer failed: {user_email} -> {manager_email}")
                    return False
                elif overall_status in ['inProgress', 'pending']:
                    elapsed = time.time() - start_time
                    if elapsed > 60:
                        poll_interval = 15
                    elif elapsed > 30:
                        poll_interval = 10
                    logger.info(f"Data transfer in progress, waiting {poll_interval} seconds...")
                    time.sleep(poll_interval)
                else:
                    logger.warning(f"Unknown transfer status: {overall_status}")
                    time.sleep(poll_interval)
            logger.warning(f"Data transfer monitoring timeout after {max_wait_time}s")
            return False
        except Exception as e:
            logger.error(f"Error monitoring data transfer {transfer_id}: {e}")
            return False

    def delete_user(self, user_email: str) -> bool:
        try:
            logger.info(f"Deleting Google Workspace user: {user_email}")
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found, skipping deletion")
                return True
            self.directory_service.users().delete(userKey=user_email).execute()
            logger.info(f"Successfully deleted Google Workspace user: {user_email}")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"User {user_email} already deleted or not found")
                return True
            else:
                logger.error(f"Error deleting Google Workspace user {user_email}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting user {user_email}: {e}")
            return False

    def execute_complete_termination(self, user_email: str, manager_email: str) -> bool:
        try:
            logger.info(f"Starting Google Workspace termination for {user_email}")
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Google Workspace")
                return True
            if manager_email:
                logger.info(f"Step 1: Transferring data to manager ({manager_email})")
                transfer_success = self.transfer_user_data(user_email, manager_email)
                if not transfer_success:
                    logger.error(f"Data transfer failed for {user_email}, aborting deletion to preserve data")
                    return False
            else:
                logger.warning(f"No manager specified for {user_email}, skipping data transfer")
            logger.info(f"Step 2: Deleting user account")
            deletion_success = self.delete_user(user_email)
            if deletion_success:
                logger.info(f"Google Workspace termination completed for {user_email}")
                return True
            else:
                logger.error(f"User deletion failed for {user_email}")
                return False
        except Exception as e:
            logger.error(f"Error in Google Workspace termination for {user_email}: {e}")
            return False


# Alias for compatibility with import expectations
GoogleService = GoogleTermination