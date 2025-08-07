# google_termination.py - Google Workspace termination automation

import logging
import time
from typing import Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import configuration for secure credential management
from config import get_google_service_account_key

logger = logging.getLogger(__name__)

class GoogleTerminationManager:
    """Handles Google Workspace user termination and data transfer."""
    
    def __init__(self):
        """Initialize Google Workspace API client with service account credentials."""
        try:
            # Get service account credentials from 1Password
            service_account_info = get_google_service_account_key()
            
            # Define required scopes for user management and data transfer
            scopes = [
                'https://www.googleapis.com/auth/admin.directory.user',
                'https://www.googleapis.com/auth/admin.datatransfer'
            ]
            
            # Create credentials from service account
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
            
            # Delegate credentials to admin user for domain-wide delegation
            admin_email = "codyatkinson@filevine.com"
            self.delegated_credentials = self.credentials.with_subject(admin_email)
            
            # Initialize Directory API service with delegated credentials
            self.directory_service = build('admin', 'directory_v1', credentials=self.delegated_credentials)
            
            # Initialize Data Transfer API service with delegated credentials
            self.datatransfer_service = build('admin', 'datatransfer_v1', credentials=self.delegated_credentials)
            
            logger.info("Google Workspace API clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace API clients: {e}")
            raise

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find a Google Workspace user by email address."""
        try:
            logger.info(f"Looking up Google Workspace user: {email}")
            
            # Query Directory API for user
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
        """Find manager user for data transfer."""
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
        """Transfer user data to manager before deletion."""
        try:
            logger.info(f"Starting data transfer: {user_email} -> {manager_email}")
            
            # Verify both users exist
            user = self.find_user_by_email(user_email)
            manager = self.find_manager_by_email(manager_email)
            
            if not user:
                logger.error(f"Cannot transfer data: source user {user_email} not found")
                return False
                
            if not manager:
                logger.error(f"Cannot transfer data: manager {manager_email} not found")
                return False
            
            # Define data transfer applications (Google Drive, Gmail, etc.)
            applications = [
                {
                    'id': 55656082996,  # Google Drive
                    'name': 'Drive and Docs'
                },
                {
                    'id': 435070579839,  # Gmail
                    'name': 'Gmail'
                }
            ]
            
            transfer_requests = []
            
            # Create transfer requests for each application
            for app in applications:
                transfer_request = {
                    'applicationId': app['id'],
                    'applicationTransferParams': []
                }
                
                # Add specific parameters for Drive transfer
                if app['id'] == 55656082996:  # Google Drive
                    transfer_request['applicationTransferParams'] = [
                        {
                            'key': 'PRIVACY_LEVEL',
                            'value': ['SHARED', 'PRIVATE']  # Transfer both shared and private files
                        }
                    ]
                
                transfer_requests.append(transfer_request)
            
            # Execute data transfer
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
            
            # Monitor transfer progress
            return self._monitor_data_transfer(transfer_id, user_email, manager_email)
            
        except Exception as e:
            logger.error(f"Error transferring data from {user_email} to {manager_email}: {e}")
            return False

    def _monitor_data_transfer(self, transfer_id: str, user_email: str, manager_email: str, 
                              max_wait_time: int = 300) -> bool:
        """Monitor data transfer progress with optimized polling."""
        try:
            logger.info(f"Monitoring data transfer {transfer_id} (max wait: {max_wait_time}s)")
            
            start_time = time.time()
            poll_interval = 5  # Start with 5-second polls for faster response
            
            while time.time() - start_time < max_wait_time:
                # Check transfer status
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
                    # Adaptive polling - increase interval for longer transfers
                    elapsed = time.time() - start_time
                    if elapsed > 60:  # After 1 minute, poll every 15 seconds
                        poll_interval = 15
                    elif elapsed > 30:  # After 30 seconds, poll every 10 seconds
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
        """Delete Google Workspace user account."""
        try:
            logger.info(f"Deleting Google Workspace user: {user_email}")
            
            # Verify user exists before deletion
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found, skipping deletion")
                return True  # Consider this success since user doesn't exist
            
            # Delete the user
            self.directory_service.users().delete(userKey=user_email).execute()
            
            logger.info(f"Successfully deleted Google Workspace user: {user_email}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"User {user_email} already deleted or not found")
                return True  # Consider this success
            else:
                logger.error(f"Error deleting Google Workspace user {user_email}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting user {user_email}: {e}")
            return False

    def execute_complete_termination(self, user_email: str, manager_email: str) -> bool:
        """Execute complete Google Workspace termination workflow."""
        try:
            logger.info(f"Starting Google Workspace termination for {user_email}")
            
            # Step 1: Verify user exists
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Google Workspace")
                return True  # Consider this success since user doesn't exist
            
            # Step 2: Transfer data to manager (required for data protection)
            if manager_email:
                logger.info(f"Step 1: Transferring data to manager ({manager_email})")
                transfer_success = self.transfer_user_data(user_email, manager_email)
                
                if not transfer_success:
                    logger.error(f"Data transfer failed for {user_email}, aborting deletion to preserve data")
                    return False
            else:
                logger.warning(f"No manager specified for {user_email}, skipping data transfer")
            
            # Step 3: Delete user account
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

def test_google_termination():
    """Test function for Google Workspace termination."""
    try:
        # Initialize the manager
        google_manager = GoogleTerminationManager()
        
        # Test user lookup
        test_email = "test@filevine.com"
        user = google_manager.find_user_by_email(test_email)
        
        if user:
            print(f"Found user: {user.get('name', {}).get('fullName')}")
        else:
            print(f"User not found: {test_email}")
            
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    test_google_termination()
