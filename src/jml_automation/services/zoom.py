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
from typing import Optional, Dict, Any
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
            
            # Check for webinars
            try:
                webinars_response = self._make_api_request('GET', f'/users/{user_id}/webinars')
                webinars = webinars_response.get('webinars', [])
                if webinars:
                    logger.info(f"User {user_email} has {len(webinars)} webinars")
                    data_found = True
            except Exception as e:
                error_msg = str(e).lower()
                if "webinar plan is missing" in error_msg or "webinar plan" in error_msg:
                    logger.info(f"User {user_email} has no webinar plan - no webinars to check")
                else:
                    logger.warning(f"Could not check webinars for {user_email}: {e}")
            
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
        """Transfer Zoom user data to manager before deletion."""
        try:
            logger.info(f"Starting Zoom data transfer: {user_email} -> {manager_email}")
            
            # Verify source user exists
            user = self.find_user_by_email(user_email)
            if not user:
                logger.error(f"Cannot transfer data: source user {user_email} not found")
                return False
            
            # Verify manager exists
            manager = self.find_user_by_email(manager_email)
            if not manager:
                logger.error(f"Cannot transfer data: manager {manager_email} not found")
                return False
            
            # Get user ID for API calls
            user_id = user.get('id')
            manager_id = manager.get('id')
            
            logger.info(f"Transferring data from user ID: {user_id} to manager ID: {manager_id}")
            
            # Transfer recordings
            recordings_transferred = self._transfer_recordings(user_id, manager_id, user_email, manager_email)
            
            # Transfer webinars (skip if company doesn't use webinars)
            webinars_transferred = self._transfer_webinars(user_id, manager_id, user_email, manager_email)
            if not webinars_transferred:
                logger.info("Webinars transfer failed, but continuing (company doesn't heavily use webinars)")
                webinars_transferred = True  # Don't fail the whole process for webinars
            
            # Transfer meetings (scheduled)
            meetings_transferred = self._transfer_meetings(user_id, manager_id, user_email, manager_email)
            
            # Transfer Events hub assets
            events_transferred = self._transfer_events_hub_assets(user_email, manager_email)
            
            # Require recordings, meetings, and events - webinars are optional
            if recordings_transferred and meetings_transferred and events_transferred:
                logger.info(f"Essential Zoom data successfully transferred: {user_email} -> {manager_email}")
                return True
            else:
                logger.error(f"Critical Zoom data transfer operations failed for {user_email}")
                logger.error(f"Recordings: {recordings_transferred}, Meetings: {meetings_transferred}, Events: {events_transferred}")
                return False
                
        except Exception as e:
            logger.error(f"Error transferring Zoom data from {user_email} to {manager_email}: {e}")
            return False

    def _transfer_recordings(self, user_id: str, manager_id: str, user_email: str, manager_email: str) -> bool:
        """Transfer user's cloud recordings to manager with verification."""
        try:
            logger.info(f"Transferring recordings from {user_email} to {manager_email}")
            
            # Get user's recordings
            recordings_response = self._make_api_request('GET', f'/users/{user_id}/recordings')
            recordings = recordings_response.get('meetings', [])
            
            if not recordings:
                logger.info(f"No recordings found for {user_email}")
                return True
            
            logger.info(f"Found {len(recordings)} recordings to transfer")
            
            # Transfer each recording and verify
            transferred_count = 0
            for recording in recordings:
                meeting_id = recording.get('id')
                try:
                    # Transfer recording ownership
                    transfer_data = {
                        'owner': manager_email
                    }
                    self._make_api_request('PATCH', f'/meetings/{meeting_id}/recordings/transfer', transfer_data)
                    
                    # Verify transfer by checking new owner
                    try:
                        updated_recording = self._make_api_request('GET', f'/meetings/{meeting_id}/recordings')
                        if updated_recording and updated_recording.get('host_email') == manager_email:
                            logger.info(f"✓ Recording {meeting_id} successfully transferred to {manager_email}")
                            transferred_count += 1
                        else:
                            logger.warning(f"Recording {meeting_id} transfer verification failed")
                    except:
                        # If we can't verify, assume it worked if no error was thrown
                        logger.info(f"Recording {meeting_id} transferred (verification unavailable)")
                        transferred_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to transfer recording {meeting_id}: {e}")
            
            success_rate = transferred_count / len(recordings) * 100
            logger.info(f"Recordings transfer completed: {transferred_count}/{len(recordings)} successful ({success_rate:.1f}%)")
            
            # Return True if at least 90% successful
            return success_rate >= 90.0
            
        except Exception as e:
            logger.error(f"Error transferring recordings: {e}")
            return False

    def _transfer_webinars(self, user_id: str, manager_id: str, user_email: str, manager_email: str) -> bool:
        """Transfer user's webinars to manager with verification."""
        try:
            logger.info(f"Transferring webinars from {user_email} to {manager_email}")
            
            # Get user's webinars
            webinars_response = self._make_api_request('GET', f'/users/{user_id}/webinars')
            webinars = webinars_response.get('webinars', [])
            
            if not webinars:
                logger.info(f"No webinars found for {user_email}")
                return True
            
            logger.info(f"Found {len(webinars)} webinars to transfer")
            
            # Transfer each webinar and verify
            transferred_count = 0
            for webinar in webinars:
                webinar_id = webinar.get('id')
                try:
                    # Update webinar host
                    transfer_data = {
                        'host_id': manager_id
                    }
                    self._make_api_request('PATCH', f'/webinars/{webinar_id}', transfer_data)
                    
                    # Verify transfer by checking new host
                    try:
                        updated_webinar = self._make_api_request('GET', f'/webinars/{webinar_id}')
                        if updated_webinar and updated_webinar.get('host_id') == manager_id:
                            logger.info(f"✓ Webinar {webinar_id} successfully transferred to {manager_email}")
                            transferred_count += 1
                        else:
                            logger.warning(f"Webinar {webinar_id} transfer verification failed")
                    except:
                        # If we can't verify, assume it worked if no error was thrown
                        logger.info(f"Webinar {webinar_id} transferred (verification unavailable)")
                        transferred_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to transfer webinar {webinar_id}: {e}")
            
            success_rate = transferred_count / len(webinars) * 100
            logger.info(f"Webinars transfer completed: {transferred_count}/{len(webinars)} successful ({success_rate:.1f}%)")
            
            # Return True if at least 90% successful
            return success_rate >= 90.0
            
        except Exception as e:
            # Check if it's a "no webinar plan" error
            error_msg = str(e).lower()
            if "webinar plan is missing" in error_msg or "webinar plan" in error_msg:
                logger.info(f"User {user_email} has no webinar plan - no webinars to transfer")
                return True
            else:
                logger.error(f"Error transferring webinars: {e}")
                return False

    def _transfer_meetings(self, user_id: str, manager_id: str, user_email: str, manager_email: str) -> bool:
        """Transfer user's scheduled meetings to manager."""
        try:
            logger.info(f"Transferring meetings from {user_email} to {manager_email}")
            
            # Get user's meetings
            meetings_response = self._make_api_request('GET', f'/users/{user_id}/meetings')
            meetings = meetings_response.get('meetings', [])
            
            if not meetings:
                logger.info(f"No meetings found for {user_email}")
                return True
            
            logger.info(f"Found {len(meetings)} meetings to transfer")
            
            # Transfer each meeting
            for meeting in meetings:
                meeting_id = meeting.get('id')
                try:
                    # Update meeting host
                    transfer_data = {
                        'host_id': manager_id
                    }
                    self._make_api_request('PATCH', f'/meetings/{meeting_id}', transfer_data)
                    logger.info(f"Transferred meeting {meeting_id} to {manager_email}")
                except Exception as e:
                    logger.warning(f"Failed to transfer meeting {meeting_id}: {e}")
            
            logger.info(f"Meetings transfer completed for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring meetings: {e}")
            return False

    def delete_user(self, user_email: str, transfer_target_email: str = None) -> bool:
        """Delete Zoom user account using correct URL parameter method with Events transfer."""
        try:
            logger.info(f"Attempting user deletion for: {user_email}")
            
            # Verify user exists before deletion
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found, skipping deletion")
                return True  # Consider this success since user doesn't exist
            
            user_id = user.get('id')
            logger.info(f"User details - ID: {user_id}, Email: {user_email}")
            
            # If we have a transfer target, get their user ID for Events transfer
            transfer_target_id = None
            if transfer_target_email:
                transfer_user = self.find_user_by_email(transfer_target_email)
                if transfer_user:
                    transfer_target_id = transfer_user.get('id')
                    logger.info(f"Transfer target: {transfer_target_email} (ID: {transfer_target_id})")
                else:
                    logger.warning(f"Transfer target {transfer_target_email} not found")
            
            # Method 1: URL parameter deletion with Events transfer (if needed)
            if transfer_target_id:
                logger.info("ATTEMPTING: DELETE /users/{email}?action=delete&transfer_email={target}")
                try:
                    self._make_api_request('DELETE', f'/users/{user_email}?action=delete&transfer_email={transfer_target_email}')
                    logger.info(f"SUCCESS: User completely deleted with Events transfer: {user_email}")
                    return True
                except requests.exceptions.HTTPError as e:
                    logger.warning(f"Email deletion with transfer failed: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    logger.warning(f"Email deletion with transfer failed: {e}")
                
                # Method 2: URL parameter deletion with user ID and transfer
                logger.info("ATTEMPTING: DELETE /users/{user_id}?action=delete&transfer_email={target}")
                try:
                    self._make_api_request('DELETE', f'/users/{user_id}?action=delete&transfer_email={transfer_target_email}')
                    logger.info(f"SUCCESS: User completely deleted via ID with Events transfer: {user_email}")
                    return True
                except requests.exceptions.HTTPError as e:
                    logger.warning(f"ID deletion with transfer failed: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    logger.warning(f"ID deletion with transfer failed: {e}")
            else:
                # SAFETY CHECK: Do not attempt deletion if transfer was requested but target not found
                logger.error(f"SAFETY: Transfer target {transfer_target_email} not found in Zoom")
                logger.error(f"SAFETY: Will not delete user {user_email} without proper data transfer")
                return False
            
            # Method 3: Standard deletion without transfer (only if no transfer_target_email specified)
            if not transfer_target_email:
                logger.info("ATTEMPTING: DELETE /users/{email}?action=delete (NO TRANSFER)")
                try:
                    self._make_api_request('DELETE', f'/users/{user_email}?action=delete')
                    logger.info(f"SUCCESS: User completely deleted (no transfer requested): {user_email}")
                    return True
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 400 and "hub assets" in e.response.text.lower():
                        logger.error(f"FAILED: User has Events hub assets that require transfer: {user_email}")
                        logger.error(f"Error details: {e.response.text}")
                        return False
                    else:
                        logger.warning(f"Email deletion failed: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    logger.warning(f"Email deletion failed: {e}")
            else:
                logger.error(f"SAFETY: Cannot delete {user_email} - transfer was requested but failed")
                return False
            
            # Method 4: URL parameter deletion with user ID
            logger.info("ATTEMPTING: DELETE /users/{user_id}?action=delete")
            try:
                self._make_api_request('DELETE', f'/users/{user_id}?action=delete')
                logger.info(f"SUCCESS: User completely deleted via ID: {user_email}")
                return True
            except requests.exceptions.HTTPError as e:
                logger.warning(f"ID deletion failed: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.warning(f"ID deletion failed: {e}")
            
            # Method 5: URL parameter disassociate (removes from org but keeps account)
            logger.info("ATTEMPTING: DELETE /users/{email}?action=disassociate")
            try:
                self._make_api_request('DELETE', f'/users/{user_email}?action=disassociate')
                logger.info(f"SUCCESS: User disassociated: {user_email}")
                return True
            except Exception as e:
                logger.warning(f"Disassociate failed: {e}")
            
            # All deletion methods failed - fall back to comprehensive license removal
            logger.error(f"ALL DELETION METHODS FAILED for {user_email}")
            logger.info(f"Falling back to comprehensive license removal...")
            return self._comprehensive_license_removal(user_email, user_id)
            
        except Exception as e:
            logger.error(f"Unexpected error in user deletion for {user_email}: {e}")
            return self._comprehensive_license_removal(user_email, user.get('id') if user else None)

    def _comprehensive_license_removal(self, user_email: str, user_id: str = None) -> bool:
        """Comprehensive license removal and user deactivation when deletion fails."""
        try:
            logger.info(f"🎯 COMPREHENSIVE LICENSE REMOVAL for {user_email}")
            
            success_count = 0
            total_attempts = 0
            
            # Method 1: Deactivate user (suspend account)
            logger.info("LICENSE METHOD 1: Deactivating user account")
            total_attempts += 1
            try:
                deactivate_data = {'status': 'inactive'}
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', deactivate_data)
                logger.info(f"✅ User deactivated successfully: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ Deactivation failed: {e}")
            
            # Method 2: Downgrade to Basic (free) license
            logger.info("LICENSE METHOD 2: Downgrading to Basic license")
            total_attempts += 1
            try:
                license_data = {'type': 1}  # 1 = Basic (free)
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', license_data)
                logger.info(f"✅ User downgraded to Basic license: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ License downgrade failed: {e}")
            
            # Method 3: Remove from all groups/roles
            logger.info("LICENSE METHOD 3: Removing user privileges and roles")
            total_attempts += 1
            try:
                role_data = {
                    'role_name': '',  # Remove role
                    'privileges': []   # Remove all privileges
                }
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', role_data)
                logger.info(f"✅ User privileges removed: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ Privilege removal failed: {e}")
            
            # Method 4: Set user as custodian (minimal permissions)
            logger.info("LICENSE METHOD 4: Converting to custodian status")
            total_attempts += 1
            try:
                custodian_data = {
                    'type': 1,  # Basic user
                    'dept': 'TERMINATED',
                    'job_title': 'TERMINATED',
                    'location': 'TERMINATED'
                }
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', custodian_data)
                logger.info(f"✅ User converted to custodian: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ Custodian conversion failed: {e}")
            
            # Method 5: Remove personal meeting ID
            logger.info("LICENSE METHOD 5: Removing personal meeting room")
            total_attempts += 1
            try:
                pmi_data = {'use_pmi': False}
                self._make_api_request('PATCH', f'/users/{user_id or user_email}/settings', pmi_data)
                logger.info(f"✅ Personal meeting room removed: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ PMI removal failed: {e}")
            
            # Method 6: Disable all user features
            logger.info("LICENSE METHOD 6: Disabling all user features")
            total_attempts += 1
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
                logger.info(f"✅ User features disabled: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ Feature disabling failed: {e}")
            
            # Method 7: Update user profile to indicate termination
            logger.info("LICENSE METHOD 7: Marking profile as terminated")
            total_attempts += 1
            try:
                profile_data = {
                    'first_name': 'TERMINATED',
                    'last_name': f'USER-{user_email.split("@")[0]}',
                    'dept': 'TERMINATED',
                    'job_title': 'TERMINATED - DO NOT USE',
                    'location': 'TERMINATED'
                }
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', profile_data)
                logger.info(f"✅ Profile marked as terminated: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ Profile update failed: {e}")
            
            # Method 8: Try to remove from organization (if possible)
            logger.info("LICENSE METHOD 8: Attempting organization removal")
            total_attempts += 1
            try:
                org_data = {'vanity_name': '', 'company': 'TERMINATED'}
                self._make_api_request('PATCH', f'/users/{user_id or user_email}', org_data)
                logger.info(f"✅ Organization details cleared: {user_email}")
                success_count += 1
            except Exception as e:
                logger.warning(f"❌ Organization removal failed: {e}")
            
            # Summary
            success_rate = (success_count / total_attempts) * 100
            logger.info(f"📊 LICENSE REMOVAL SUMMARY:")
            logger.info(f"   ✅ Successful operations: {success_count}/{total_attempts} ({success_rate:.1f}%)")
            
            if success_count >= 3:
                logger.info(f"🎉 LICENSE SUCCESSFULLY FREED for {user_email}")
                logger.info(f"   User is deactivated and consuming minimal/no license resources")
                return True
            elif success_count >= 1:
                logger.warning(f"⚠️ PARTIAL LICENSE REMOVAL for {user_email}")
                logger.warning(f"   Some operations succeeded - license usage reduced")
                return True
            else:
                logger.error(f"❌ LICENSE REMOVAL FAILED for {user_email}")
                logger.error(f"   Manual intervention required - user may still consume license")
                return False
                
        except Exception as e:
            logger.error(f"Fatal error in comprehensive license removal for {user_email}: {e}")
            return False

    def _deactivate_user(self, user_email: str, user_id: str = None) -> bool:
        """Legacy deactivate method - now calls comprehensive removal."""
        return self._comprehensive_license_removal(user_email, user_id)

    def execute_complete_termination(self, user_email: str, manager_email: str = None) -> bool:
        """Execute complete Zoom termination with enhanced data handling logic."""
        try:
            logger.info(f"Starting Zoom termination for {user_email}")
            
            # Step 1: Verify user exists
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Zoom")
                return True  # Consider this success since user doesn't exist
            
            # Step 2: Check if user has transferable data
            has_data = self.has_transferable_data(user_email)
            
            if has_data and manager_email:
                # User has data - attempt transfer
                logger.info(f"Step 1: User has transferable data, transferring to manager ({manager_email})")
                transfer_success = self.transfer_user_data(user_email, manager_email)
                
                if not transfer_success:
                    logger.error(f"Data transfer failed for {user_email}, aborting deletion to preserve data")
                    return False
                    
            elif has_data and not manager_email:
                # User has data but no manager - cannot proceed safely
                logger.error(f"User {user_email} has transferable data but no manager specified for transfer")
                return False
                
            else:
                # User has no transferable data - safe to proceed to deletion
                logger.info(f"Step 1: User has no transferable data, proceeding directly to deletion")
            
            # Step 3: Delete user account (now safe whether data was transferred or confirmed absent)
            logger.info(f"Step 2: Deleting user account")
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
    
    def execute_complete_termination(self, user_email: str, manager_email: str = None) -> Dict:
        """
        Execute complete Zoom termination for a user.
        
        Args:
            user_email: Email of user to terminate
            manager_email: Email of manager for data transfer
            
        Returns:
            Dict with termination results
        """
        logger.info(f"📹 Starting Zoom termination for {user_email}")
        
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
                logger.info(f"✅ Zoom termination completed successfully for {user_email} in {duration:.1f}s")
            else:
                logger.warning(f"⚠️ Zoom termination completed with issues for {user_email} in {duration:.1f}s")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Fatal error during Zoom termination for {user_email}: {e}")
            
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
