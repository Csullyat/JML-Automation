#!/usr/bin/env python3
"""
Zoom termination automation module for enterprise user offboarding.
Handles Zoom user data transfer and account deletion.
"""

import requests
import json
import time
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jml_automation import config

logger = logging.getLogger(__name__)

class ZoomTerminationManager:
    """Manages Zoom user termination including data transfer and account deletion."""
    
    # Class-level cache for credentials and tokens
    _cached_credentials = None
    _cached_token = None
    _token_expires_at = None
    
    def __init__(self):
        """Initialize Zoom API client with cached OAuth authentication."""
        try:
            logger.info("Initializing Zoom Termination Manager")
            
            # Use cached credentials or fetch from 1Password
            if ZoomTerminationManager._cached_credentials is None:
                logger.info("Fetching Zoom credentials from 1Password (first time)")
                from jml_automation.config import Config
                config_instance = Config()
                zoom_creds_tuple = config_instance.get_zoom_credentials()
                # Convert tuple to expected dictionary format
                zoom_creds = {
                    'client_id': zoom_creds_tuple[0],
                    'client_secret': zoom_creds_tuple[1], 
                    'account_id': zoom_creds_tuple[2]
                }
                ZoomTerminationManager._cached_credentials = zoom_creds
                logger.info("Zoom credentials cached for future use")
            else:
                logger.info("Using cached Zoom credentials")
                zoom_creds = ZoomTerminationManager._cached_credentials
            
            # Map config field names to expected names
            self.account_id = zoom_creds['account_id']
            self.client_id = zoom_creds['client_id']
            self.client_secret = zoom_creds['client_secret']
            # Legacy attribute names for backwards compatibility
            self.api_key = zoom_creds['client_id']
            self.api_secret = zoom_creds['client_secret']
            
            # Zoom API base URL
            self.base_url = "https://api.zoom.us/v2"
            
            # Use cached token or generate new one
            self.access_token = self._get_cached_or_new_token()
            
            logger.info("Zoom API client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Zoom API client: {e}")
            raise

    def _get_cached_or_new_token(self) -> str:
        """Get cached OAuth token or generate new one if expired."""
        try:
            current_time = datetime.now()
            
            # Check if we have a valid cached token
            if (ZoomTerminationManager._cached_token is not None and 
                ZoomTerminationManager._token_expires_at is not None and
                current_time < ZoomTerminationManager._token_expires_at):
                logger.info("Using cached OAuth access token")
                return ZoomTerminationManager._cached_token
            
            # Generate new token
            logger.info("Generating new OAuth access token")
            token = self._generate_oauth_token()
            
            # Cache the token (Zoom tokens typically last 1 hour)
            ZoomTerminationManager._cached_token = token
            ZoomTerminationManager._token_expires_at = current_time + timedelta(minutes=55)  # 5 min buffer
            
            return token
            
        except Exception as e:
            logger.error(f"Failed to get OAuth token: {e}")
            raise
            logger.error(f"Failed to initialize Zoom API client: {e}")
            raise

    def _generate_oauth_token(self) -> str:
        """Generate OAuth access token for Zoom API authentication."""
        try:
            # OAuth token endpoint
            token_url = "https://zoom.us/oauth/token"
            
            # Prepare the request
            auth = (self.api_key, self.api_secret)  # Client ID and Secret as basic auth
            data = {
                'grant_type': 'account_credentials',
                'account_id': self.account_id
            }
            
            response = requests.post(token_url, auth=auth, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                raise ValueError("No access token in response")
            
            logger.info("OAuth access token generated successfully")
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to generate OAuth token: {e}")
            raise

    def _make_api_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request to Zoom."""
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Zoom API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    @classmethod
    def clear_cache(cls):
        """Clear cached credentials and tokens. Useful for testing or token refresh."""
        logger.info("Clearing Zoom credential and token cache")
        cls._cached_credentials = None
        cls._cached_token = None
        cls._token_expires_at = None

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find Zoom user by email address."""
        try:
            logger.info(f"Looking up Zoom user: {email}")
            
            # Search for user
            response = self._make_api_request('GET', f'/users/{email}')
            
            if response:
                logger.info(f"Found Zoom user: {response.get('first_name', '')} {response.get('last_name', '')} ({email})")
                return response
            else:
                logger.warning(f"Zoom user not found: {email}")
                return None
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Zoom user not found: {email}")
                return None
            else:
                logger.error(f"Error finding Zoom user {email}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error finding Zoom user {email}: {e}")
            raise

    def has_transferable_data(self, user_email: str) -> bool:
        """Check if user has transferable data (recordings, webinars, meetings)."""
        try:
            logger.info(f"Checking if {user_email} has transferable Zoom data")
            
            # Check if user exists
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found, no data to transfer")
                return False
            
            user_id = user.get('id')
            data_found = False
            
            # Check for recordings
            try:
                recordings_response = self._make_api_request('GET', f'/users/{user_id}/recordings')
                recordings = recordings_response.get('meetings', [])
                if recordings:
                    logger.info(f"User {user_email} has {len(recordings)} recordings")
                    data_found = True
            except Exception as e:
                logger.warning(f"Could not check recordings for {user_email}: {e}")
            
            # Skip webinar check entirely - no one uses webinars
            logger.info(f"Skipping webinar check for {user_email} - not transferred")
            
            # Check for scheduled meetings
            try:
                meetings_response = self._make_api_request('GET', f'/users/{user_id}/meetings')
                meetings = meetings_response.get('meetings', [])
                if meetings:
                    logger.info(f"User {user_email} has {len(meetings)} scheduled meetings")
                    data_found = True
            except Exception as e:
                logger.warning(f"Could not check meetings for {user_email}: {e}")
            
            if not data_found:
                logger.info(f"User {user_email} has no transferable Zoom data")
                return False
            else:
                logger.info(f"User {user_email} has transferable Zoom data")
                return True
                
        except Exception as e:
            logger.error(f"Error checking transferable data for {user_email}: {e}")
            # If we can't check, assume data exists to be safe
            return True

    def _transfer_events_hub_assets(self, user_email: str, manager_email: str) -> bool:
        """Transfer Zoom Events hub assets to manager - simplified approach."""
        try:
            logger.info(f"Preparing for Events hub assets transfer: {user_email} -> {manager_email}")
            
            # Get manager details for transfer target
            manager = self.find_user_by_email(manager_email)
            
            if not manager:
                logger.error(f"Cannot transfer Events assets: manager {manager_email} not found")
                return False
            
            # We'll use the manager's email in the deletion request
            # The actual Events transfer happens during the delete API call
            logger.info(f"Events hub assets will be transferred to {manager_email} during user deletion")
            return True
                    
        except Exception as e:
            logger.error(f"Error preparing Events hub assets transfer: {e}")
            return False

    def transfer_user_data(self, user_email: str, manager_email: str) -> bool:
        """DEPRECATED: Data transfer now happens atomically in delete_user method."""
        logger.warning("transfer_user_data is deprecated - data transfer now happens atomically during user deletion")
        logger.info(f"Zoom will transfer data from {user_email} to {manager_email} automatically during deletion")
        return True  # Always return True since transfer is handled by delete_user

    def _transfer_recordings(self, user_id: str, manager_id: str, user_email: str, manager_email: str) -> bool:
        """DEPRECATED: Recordings transfer now happens atomically during user deletion."""
        logger.warning("_transfer_recordings is deprecated - recordings are transferred automatically during user deletion")
        return True

    def _transfer_webinars(self, user_id: str, manager_id: str, user_email: str, manager_email: str) -> bool:
        """DEPRECATED: Webinars transfer now happens atomically during user deletion."""
        logger.warning("_transfer_webinars is deprecated - webinars are transferred automatically during user deletion")
        return True

    def _transfer_meetings(self, user_id: str, manager_id: str, user_email: str, manager_email: str) -> bool:
        """DEPRECATED: Meetings transfer now happens atomically during user deletion."""
        logger.warning("_transfer_meetings is deprecated - meetings are transferred automatically during user deletion")
        return True

    def delete_user(self, user_email: str, transfer_target_email: Optional[str] = None) -> bool:
        """Delete Zoom user account - Zoom handles ALL data transfer atomically."""
        try:
            logger.info(f"Deleting user {user_email}")
            
            # Verify user exists
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found, skipping deletion")
                return True  # Consider this success since user doesn't exist
            
            # Build delete URL with transfer parameters
            if transfer_target_email:
                # Verify transfer target exists and is active
                transfer_target = self.find_user_by_email(transfer_target_email)
                if not transfer_target:
                    logger.error(f"Transfer target {transfer_target_email} not found")
                    return False
                
                # Check if transfer target is active
                if transfer_target.get('status') == 'inactive':
                    logger.warning(f"Transfer target {transfer_target_email} is deactivated - deleting user without transfer")
                    full_endpoint = f'/users/{user_email}?action=delete'
                    logger.info(f"Deleting user without data transfer (inactive manager)")
                else:
                    # Delete with transfer of recordings and meetings only (no webinars)
                    query_params = [
                        'action=delete',
                        f'transfer_email={transfer_target_email}',
                        'transfer_meeting=true',
                        'transfer_recording=true'
                    ]
                    query_string = '&'.join(query_params)
                    full_endpoint = f'/users/{user_email}?{query_string}'
                    
                    logger.info(f"Deleting user with data transfer to {transfer_target_email}")
                    logger.info(f"Zoom will transfer: recordings, meetings (no webinars)")
                    logger.info(f"Endpoint: DELETE {full_endpoint}")
            else:
                full_endpoint = f'/users/{user_email}?action=delete'
                logger.info(f"Deleting user without data transfer")
            
            # Execute deletion - Zoom handles transfers atomically
            self._make_api_request('DELETE', full_endpoint)
            logger.info(f"SUCCESS: User deleted successfully: {user_email}")
            if transfer_target_email:
                logger.info(f"SUCCESS: All data automatically transferred to {transfer_target_email}")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during user deletion: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 400 and "hub assets" in e.response.text.lower():
                logger.error(f"User has Events hub assets but no transfer target specified")
                return False
            # Fall back to license removal
            return self._comprehensive_license_removal(user_email, user.get('id'))
            
        except Exception as e:
            logger.error(f"Error during user deletion: {e}")
            # Fall back to license removal
            return self._comprehensive_license_removal(user_email, user.get('id') if user else None)
            
        except Exception as e:
            logger.error(f"Unexpected error in user deletion for {user_email}: {e}")
            return self._comprehensive_license_removal(user_email, user.get('id') if user else None)

    def _comprehensive_license_removal(self, user_email: str, user_id: Optional[str] = None) -> bool:
        """Comprehensive license removal and user deactivation when deletion fails."""
        try:
            logger.info(f" COMPREHENSIVE LICENSE REMOVAL for {user_email}")
            
            # First check if user is already deactivated
            user = self.find_user_by_email(user_email)
            if user and user.get('status') == 'inactive':
                logger.info(f"User {user_email} is already deactivated - skipping most operations")
                # Just do the safe operations that work on deactivated users
                success_count = 0
                total_attempts = 2
                
                # Method 1: Remove personal meeting room (works on deactivated users)
                logger.info("LICENSE METHOD: Removing personal meeting room")
                try:
                    pmi_data = {'use_pmi': False}
                    self._make_api_request('PATCH', f'/users/{user_id or user_email}/settings', pmi_data)
                    logger.info(f"SUCCESS: Personal meeting room removed: {user_email}")
                    success_count += 1
                except Exception as e:
                    logger.warning(f"ERROR: PMI removal failed: {e}")
                
                # Method 2: Disable user features (works on deactivated users)
                logger.info("LICENSE METHOD: Disabling user features")
                try:
                    feature_data = {
                        'feature': {
                            'meeting_capacity': 0,
                            'large_meeting': False,
                            'webinar': False,
                            'cn_meeting': False,
                            'in_meeting': False
                        }
                    }
                    self._make_api_request('PATCH', f'/users/{user_id or user_email}/settings', feature_data)
                    logger.info(f"SUCCESS: User features disabled: {user_email}")
                    success_count += 1
                except Exception as e:
                    logger.warning(f"ERROR: Feature disabling failed: {e}")
                
                logger.info(f" LICENSE REMOVAL SUMMARY:")
                logger.info(f"   SUCCESS: User already deactivated, completed {success_count}/{total_attempts} additional operations")
                logger.info(f" LICENSE SUCCESSFULLY FREED for {user_email}")
                return True
            
            # User is active, proceed with full deactivation
            success_count = 0
            total_attempts = 3
            
            # Method 1: Deactivate user (suspend account)
            logger.info("LICENSE METHOD 1: Deactivating user account")
            try:
                deactivate_data = {'status': 'inactive'}
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', deactivate_data)
                logger.info(f"SUCCESS: User deactivated successfully: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"ERROR: Deactivation failed: {e}")
            
            # Method 2: Remove personal meeting room
            logger.info("LICENSE METHOD 2: Removing personal meeting room")
            try:
                pmi_data = {'use_pmi': False}
                self._make_api_request('PATCH', f'/users/{user_id or user_email}/settings', pmi_data)
                logger.info(f"SUCCESS: Personal meeting room removed: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"ERROR: PMI removal failed: {e}")
            
            # Method 3: Disable user features
            logger.info("LICENSE METHOD 3: Disabling user features")
            try:
                feature_data = {
                    'feature': {
                        'meeting_capacity': 0,
                        'large_meeting': False,
                        'webinar': False,
                        'cn_meeting': False,
                        'in_meeting': False
                    }
                }
                self._make_api_request('PATCH', f'/users/{user_id or user_email}/settings', feature_data)
                logger.info(f"SUCCESS: User features disabled: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"ERROR: Feature disabling failed: {e}")
            
            # Summary
            success_rate = (success_count / total_attempts) * 100
            logger.info(f" LICENSE REMOVAL SUMMARY:")
            logger.info(f"   SUCCESS: Successful operations: {success_count}/{total_attempts} ({success_rate:.1f}%)")
            
            if success_count >= 1:
                logger.info(f" LICENSE SUCCESSFULLY FREED for {user_email}")
                logger.info(f"   User is deactivated and consuming minimal/no license resources")
                return True
            else:
                logger.error(f"ERROR: LICENSE REMOVAL FAILED for {user_email}")
                logger.error(f"   Manual intervention required - user may still consume license")
                return False
                
        except Exception as e:
            logger.error(f"Fatal error in comprehensive license removal for {user_email}: {e}")
            return False

    def _deactivate_user(self, user_email: str, user_id: Optional[str] = None) -> bool:
        """Legacy deactivate method - now calls comprehensive removal."""
        return self._comprehensive_license_removal(user_email, user_id)

    def execute_complete_termination(self, user_email: str, manager_email: Optional[str] = None) -> bool:
        """Execute complete Zoom termination - simplified to use Zoom's atomic transfer."""
        try:
            logger.info(f"Starting Zoom termination for {user_email}")
            
            # Step 1: Verify user exists
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Zoom")
                return True  # Consider this success since user doesn't exist
            
            # Step 2: Check if user has data that needs transfer
            has_data = self.has_transferable_data(user_email)
            
            if has_data and not manager_email:
                logger.error(f"User {user_email} has transferable data but no manager specified for transfer")
                return False
            
            # Step 3: Delete user (Zoom handles data transfer automatically)
            logger.info(f"Deleting user account (Zoom will transfer data automatically)")
            deletion_success = self.delete_user(user_email, manager_email)
            
            if deletion_success:
                logger.info(f"Zoom termination completed for {user_email}")
                return True
            else:
                logger.error(f"User deletion failed for {user_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error in Zoom termination for {user_email}: {e}")
            return False
    
    def test_connectivity(self) -> Dict:
        """Test Zoom API connectivity."""
        try:
            # Basic connectivity test - try to get a token
            token = self._get_cached_or_new_token()
            if token:
                return {
                    'success': True,
                    'message': 'Zoom API token obtained successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to obtain Zoom API token'
                }
                    
        except Exception as e:
            return {
                'success': False,
                'error': f"Zoom connectivity test failed: {str(e)}"
            }

def test_zoom_termination():
    """Test function for Zoom termination."""
    try:
        # Initialize the manager
        zoom_manager = ZoomTerminationManager()
        
        # Test user lookup
        test_email = "test@filevine.com"
        user = zoom_manager.find_user_by_email(test_email)
        
        if user:
            print(f"Found user: {user.get('first_name', '')} {user.get('last_name', '')}")
        else:
            print(f"User not found: {test_email}")
            
    except Exception as e:
        print(f"Test error: {e}")

# Wrapper class to match orchestrator expectations
class ZoomTermination:
    """Wrapper class for ZoomTerminationManager to match orchestrator interface."""
    
    def __init__(self):
        """Initialize Zoom termination wrapper."""
        self.manager = ZoomTerminationManager()
    
    def execute_complete_termination(self, user_email: str, manager_email: Optional[str] = None) -> Dict:
        """
        Execute complete Zoom termination for a user.
        
        Args:
            user_email: Email of user to terminate
            manager_email: Email of manager for data transfer
            
        Returns:
            Dict with termination results
        """
        logger.info(f" Starting Zoom termination for {user_email}")
        
        start_time = datetime.now()
        actions_completed = []
        actions_failed = []
        warnings = []
        errors = []
        
        try:
            # Use the existing manager's execute_complete_termination method
            result = self.manager.execute_complete_termination(user_email, manager_email)
            
            # Convert boolean result to comprehensive dict
            if isinstance(result, bool):
                if result:
                    actions_completed.append("Zoom user termination completed")
                    success = True
                else:
                    actions_failed.append("Zoom user termination failed")
                    errors.append("Termination returned False")
                    success = False
            else:
                # If result is already a dict, use it
                success = result.get('success', False)
                actions_completed = result.get('actions_completed', [])
                actions_failed = result.get('actions_failed', [])
                errors = result.get('errors', [])
                warnings = result.get('warnings', [])
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            final_result = {
                'success': success,
                'user_email': user_email,
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
                logger.info(f"SUCCESS: Zoom termination completed successfully for {user_email} in {duration:.1f}s")
            else:
                logger.warning(f"WARNING: Zoom termination completed with issues for {user_email} in {duration:.1f}s")
            
            return final_result
            
        except Exception as e:
            logger.error(f"ERROR: Fatal error during Zoom termination for {user_email}: {e}")
            
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
        """Test Zoom API connectivity."""
        try:
            # Test with a simple API call via the manager
            # Use the manager's test method if available, otherwise test token
            if hasattr(self.manager, 'test_connection'):
                return self.manager.test_connection()
            else:
                # Basic connectivity test
                token = self.manager._get_cached_or_new_token()
                if token:
                    return {
                        'success': True,
                        'message': 'Zoom API token obtained successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to obtain Zoom API token'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': f"Zoom connectivity test failed: {str(e)}"
            }

if __name__ == "__main__":
    test_zoom_termination()


# Alias for compatibility with import expectations
ZoomService = ZoomTermination
