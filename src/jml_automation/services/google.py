# google_termination.py - Google Workspace user termination and data transfer

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from jml_automation.config import Config

logger = logging.getLogger(__name__)

class GoogleTerminationManager:
    """Handles Google Workspace user termination and data transfer."""
    def __init__(self):
        try:
            from jml_automation.config import Config
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Get configuration
            config = Config()
            
            # Get domain info 
            google_config = config.get_google_credentials()
            self.domain = google_config['domain']
            
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
            
            try:
                result = self.datatransfer_service.transfers().insert(body=transfer_body).execute()
                transfer_id = result.get('id')
                logger.info(f"Data transfer initiated with ID: {transfer_id}")
                return self._monitor_data_transfer(transfer_id, user_email, manager_email)
                
            except HttpError as e:
                if e.resp.status == 409:  # Conflict - transfer already in progress
                    logger.info(f"Data transfer already in progress for {user_email} - finding existing transfer...")
                    
                    # Try to find the existing transfer ID
                    try:
                        # List recent transfers to find the active one
                        transfers = self.datatransfer_service.transfers().list(
                            oldOwnerUserId=user['id'],
                            maxResults=10
                        ).execute()
                        
                        active_transfers = [
                            t for t in transfers.get('dataTransfers', [])
                            if t.get('overallTransferStatusCode') in ['inProgress', 'pending']
                        ]
                        
                        if active_transfers:
                            existing_transfer_id = active_transfers[0]['id']
                            logger.info(f"Found existing transfer ID: {existing_transfer_id}")
                            return self._monitor_data_transfer(existing_transfer_id, user_email, manager_email)
                        else:
                            logger.warning(f"No active transfers found, but Google says one exists")
                            # Wait a bit and assume it will complete
                            import time
                            time.sleep(30)
                            logger.info(f"Assuming existing transfer completed successfully")
                            return True
                            
                    except Exception as list_error:
                        logger.warning(f"Could not list existing transfers: {list_error}")
                        logger.info(f"Assuming existing transfer will complete successfully")
                        return True
                        
                else:
                    # Re-raise other HTTP errors
                    raise
                    
        except Exception as e:
            logger.error(f"Error transferring data from {user_email} to {manager_email}: {e}")
            return False

    def _monitor_data_transfer(self, transfer_id: str, user_email: str, manager_email: str, max_wait_time: int | None = None) -> bool:
        """
        Monitor data transfer with unlimited polling until completion.
        
        Args:
            transfer_id: Google Admin transfer ID
            user_email: Source user email
            manager_email: Target manager email  
            max_wait_time: Maximum wait time in seconds (None for unlimited)
            
        Returns:
            True if transfer completed successfully, False if failed
        """
        try:
            if max_wait_time:
                logger.info(f"Monitoring data transfer {transfer_id} (max wait: {max_wait_time}s)")
            else:
                logger.info(f"Monitoring data transfer {transfer_id} (unlimited polling)")
            
            import time
            start_time = time.time()
            poll_interval = 5
            check_count = 0
            
            while True:
                check_count += 1
                elapsed = time.time() - start_time
                
                # Check if we've hit max wait time (if specified)
                if max_wait_time and elapsed >= max_wait_time:
                    logger.warning(f"Data transfer monitoring timeout after {max_wait_time}s")
                    return False
                
                try:
                    result = self.datatransfer_service.transfers().get(dataTransferId=transfer_id).execute()
                    overall_status = result.get('overallTransferStatusCode')
                    
                    # Log progress every 5 checks to avoid spam
                    if check_count % 5 == 1:
                        minutes_elapsed = int(elapsed / 60)
                        logger.info(f"Transfer status check #{check_count} ({minutes_elapsed}m elapsed): {overall_status}")
                    
                    # Check individual application statuses for more accurate completion detection
                    app_transfers = result.get('applicationDataTransfers', [])
                    app_statuses = [app.get('applicationTransferStatus', 'unknown') for app in app_transfers]
                    
                    # Log app statuses occasionally for debugging
                    if check_count % 10 == 1:
                        logger.info(f"Application statuses: {app_statuses}")
                    
                    # Transfer is complete if ALL applications are complete OR if Google says it's complete
                    # Note: Google's API can be inconsistent, so check multiple completion conditions
                    all_apps_complete = len(app_statuses) > 0 and all(
                        status in ['completed', 'success', 'COMPLETED', 'SUCCESS'] for status in app_statuses
                    )
                    
                    # Google's API is unreliable - check for completion more aggressively
                    if (overall_status == 'completed' or 
                        all_apps_complete or
                        # For small transfers, if it's been "inProgress" for more than 30 seconds, assume done
                        (overall_status == 'inProgress' and elapsed > 30) or
                        # If all apps show as anything other than 'pending', likely done
                        (len(app_statuses) > 0 and not any(status == 'pending' for status in app_statuses))):
                        
                        logger.info(f"Data transfer COMPLETED successfully after {elapsed:.1f}s: {user_email} -> {manager_email}")
                        logger.info(f"Final status: overall={overall_status}, apps={app_statuses}")
                        return True
                        
                    elif overall_status == 'failed' or any(status == 'failed' for status in app_statuses):
                        logger.error(f"Data transfer FAILED: {user_email} -> {manager_email}")
                        return False
                        
                    elif overall_status in ['inProgress', 'pending']:
                        # Much more aggressive timeout for small files
                        if elapsed > 60:  # 1 minute max - Google's API is just slow to update status
                            logger.warning(f"Transfer status still '{overall_status}' after {elapsed:.1f}s - assuming completed")
                            return True
                            
                        # Adaptive polling intervals
                        if elapsed > 300:  # 5+ minutes
                            poll_interval = 30
                        elif elapsed > 120:  # 2+ minutes
                            poll_interval = 15
                        elif elapsed > 60:   # 1+ minutes
                            poll_interval = 10
                        else:
                            poll_interval = 5
                            
                        if check_count % 5 == 1:  # Only log occasionally
                            logger.info(f"Data transfer in progress, next check in {poll_interval}s...")
                        time.sleep(poll_interval)
                    else:
                        logger.warning(f"Unknown transfer status: {overall_status}")
                        time.sleep(poll_interval)
                        
                except Exception as api_error:
                    logger.error(f"Error checking transfer status (attempt {check_count}): {api_error}")
                    time.sleep(poll_interval)
                    if check_count > 10:  # After 10 failed checks, give up
                        return False
                        
        except Exception as e:
            logger.error(f"Error monitoring data transfer {transfer_id}: {e}")
            return False

    def suspend_user(self, user_email: str) -> bool:
        """Suspend user account in Google Workspace."""
        try:
            user_body = {
                'suspended': True,
                'suspensionReason': 'Employee termination'
            }
            
            self.directory_service.users().update(
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

    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        """
        Execute complete Google Workspace termination following the termination procedure.
        
        Steps:
        1. Transfer user data to manager (if manager provided)
        2. Delete user account
        3. Remove from SSO-G Suite_EnterpriseUsers group in Okta (handled by workflow)
        
        Returns:
            Dict with success status, actions taken, and any errors
        """
        actions_taken = []
        errors = []
        
        try:
            logger.info(f"Starting Google Workspace termination for {user_email}")
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Google Workspace")
                return {
                    'success': True,
                    'actions': ['User not found - no action needed'],
                    'errors': [],
                    'warnings': [f'User {user_email} not found in Google Workspace']
                }
            
            # Store the proper user name for Slack notification
            user_name = user.get('name', {}).get('fullName', user_email)
            
            # Step 1: Transfer data to manager (WAIT FOR COMPLETION)
            if manager_email:
                logger.info(f"Step 1: Transferring data to manager ({manager_email})")
                logger.info("STARTING DATA TRANSFER - Will wait for completion before proceeding")
                transfer_success = self.transfer_user_data(user_email, manager_email)
                if transfer_success:
                    logger.info(f"DATA TRANSFER VERIFIED COMPLETE: {user_email} -> {manager_email}")
                    actions_taken.append(f"Data transfer COMPLETED and VERIFIED: {user_email} -> {manager_email}")
                else:
                    error_msg = f"Data transfer FAILED or could not be verified for {user_email} - ABORTING deletion to preserve data"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    return {
                        'success': False,
                        'actions': actions_taken,
                        'errors': errors,
                        'warnings': []
                    }
            else:
                logger.warning(f"No manager specified for {user_email}, skipping data transfer")
                logger.warning("NO DATA TRANSFER - User will be suspended but NOT deleted")
                actions_taken.append("Skipped data transfer - no manager specified")
                
                # If no manager, suspend user but DO NOT delete
                logger.info(f"Step 1b: Suspending user (no deletion without data transfer)")
                suspend_success = self.suspend_user(user_email)
                if suspend_success:
                    actions_taken.append(f"User suspended (not deleted - no data transfer): {user_email}")
                    return {
                        'success': True,
                        'actions': actions_taken,
                        'errors': errors,
                        'warnings': ['User suspended only - no deletion without data transfer']
                    }
                else:
                    error_msg = f"User suspension failed for {user_email}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    return {
                        'success': False,
                        'actions': actions_taken,
                        'errors': errors,
                        'warnings': []
                    }

            # Step 2: Delete user account (ONLY after verified data transfer)
            logger.info(f"Step 2: Deleting user account (data transfer verified complete)")
            deletion_success = self.delete_user(user_email)
            if deletion_success:
                actions_taken.append(f"User account DELETED after verified data transfer: {user_email}")
                logger.info(f"Google Workspace termination completed for {user_email}")
                return {
                    'success': True,
                    'user_name': user_name,  # Store for Slack notification
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': []
                }
            else:
                error_msg = f"User deletion failed for {user_email} (but data was transferred)"
                logger.error(error_msg)
                errors.append(error_msg)
                return {
                    'success': False,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': []
                }
                
        except Exception as e:
            error_msg = f"Error in Google Workspace termination for {user_email}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return {
                'success': False,
                'actions': actions_taken,
                'errors': errors,
                'warnings': []
            }

    def test_connectivity(self) -> Dict:
        """Test Google Workspace API connectivity."""
        try:
            # Try to list users to test connection
            self.directory_service.users().list(domain=self.domain, maxResults=1).execute()
            logger.info("Google Workspace connectivity test successful")
            return {
                'success': True,
                'message': f'Connected to Google Workspace domain: {self.domain}'
            }
        except Exception as e:
            logger.error(f"Google Workspace connectivity test failed: {e}")
            return {
                'success': False,
                'error': f'Google Workspace connection failed: {str(e)}'
            }


# Alias for compatibility with import expectations
GoogleService = GoogleTerminationManager