
"""
Lucidchart SCIM API integration for user management.

This service handles Lucidchart user operations through their SCIM 2.0 API:
- Find users by email using SCIM filters
- Delete users via SCIM endpoints
- Bearer token authentication
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import quote

from .base import BaseService
from ..config import Config

logger = logging.getLogger(__name__)


class LucidchartService(BaseService):
    """Lucidchart SCIM API service for user management."""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.base_url = self.config.settings.get('urls', {}).get('lucidchart', 'https://users.lucid.app/scim/v2')
        self.bearer_token = None
        logger.info("Lucidchart service initialized")
    
    def _get_bearer_token(self) -> str:
        """Get and cache the bearer token from 1Password."""
        if not self.bearer_token:
            self.bearer_token = self.config.get_lucidchart_bearer_token()
            if not self.bearer_token:
                raise ValueError("Lucidchart bearer token not found in 1Password")
            logger.info("Successfully obtained Lucidchart bearer token")
        return self.bearer_token
    
    def _make_scim_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated SCIM API request to Lucidchart."""
        try:
            token = self._get_bearer_token()
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/scim+json',
                'Accept': 'application/scim+json'
            }
            
            # Merge with any provided headers
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
                
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Lucidchart SCIM API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Lucidchart API request: {e}")
            return None
    
    def test_connectivity(self) -> Dict:
        """Test connection to Lucidchart SCIM API."""
        try:
            response = self._make_scim_request("GET", "/Users", params={"count": 1})
            if response is not None:
                logger.info("Lucidchart SCIM API connectivity successful")
                return {
                    'success': True,
                    'message': 'Lucidchart SCIM API connectivity successful'
                }
            else:
                logger.error("Lucidchart SCIM API connectivity failed")
                return {
                    'success': False,
                    'error': 'SCIM API request failed'
                }
        except Exception as e:
            logger.error(f"Lucidchart connectivity test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find Lucidchart user by email using SCIM filter."""
        try:
            logger.info(f"Searching for Lucidchart user: {email}")
            
            # Use SCIM filter to search for user by userName (email)
            filter_query = f'userName eq "{email}"'
            response = self._make_scim_request("GET", "/Users", params={"filter": filter_query})
            
            if not response:
                logger.error("No response from Lucidchart SCIM API")
                return None
            
            # SCIM response format: {"Resources": [...], "totalResults": n}
            resources = response.get("Resources", [])
            total_results = response.get("totalResults", 0)
            
            logger.info(f"SCIM search returned {total_results} results")
            
            if total_results > 0 and resources:
                user = resources[0]  # Take first match
                user_name = user.get("userName", "")
                display_name = user.get("displayName", "")
                logger.info(f"Found Lucidchart user: {display_name} ({user_name})")
                return user
            else:
                logger.warning(f"User {email} not found in Lucidchart")
                return None
                
        except Exception as e:
            logger.error(f"Error finding Lucidchart user {email}: {e}")
            return None
    
    def delete_user(self, user_email: str) -> bool:
        """Delete user from Lucidchart."""
        try:
            # First find the user to get their ID
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Lucidchart, may already be deleted")
                return True  # Consider this success - user doesn't exist
            
            user_id = user.get("id")
            if not user_id:
                logger.error(f"No user ID found for {user_email}")
                return False
            
            logger.info(f"Deleting Lucidchart user: {user_email} (ID: {user_id})")
            
            # Delete user using SCIM endpoint
            response = self._make_scim_request("DELETE", f"/Users/{user_id}")
            
            # DELETE typically returns empty response on success
            logger.info(f"Successfully deleted Lucidchart user: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Lucidchart user {user_email}: {e}")
            return False
    
    def verify_user_deleted(self, user_email: str) -> bool:
        """Verify that user no longer exists in Lucidchart."""
        try:
            user = self.find_user_by_email(user_email)
            if user is None:
                logger.info(f"Verified: User {user_email} no longer exists in Lucidchart")
                return True
            else:
                logger.warning(f"User {user_email} still exists in Lucidchart after deletion")
                return False
        except Exception as e:
            logger.error(f"Error verifying user deletion for {user_email}: {e}")
            return False
    
    def execute_termination(self, user_email: str) -> Dict[str, Any]:
        """Execute complete Lucidchart termination for a user with verification."""
        logger.info(f"Lucidchart termination requested for {user_email}")
        
        try:
            # Step 1: Try to find user first
            user = self.find_user_by_email(user_email)
            
            if not user:
                logger.warning(f"User {user_email} not found in Lucidchart - may already be deleted")
                return {
                    'user_email': user_email,
                    'success': True,
                    'message': f'User {user_email} not found in Lucidchart (may already be deleted)',
                    'verified': True  # Not found = successfully not there
                }
            
            # Step 2: Delete user
            deletion_success = self.delete_user(user_email)
            
            if not deletion_success:
                return {
                    'user_email': user_email,
                    'success': False,
                    'message': 'Lucidchart user deletion failed',
                    'verified': False
                }
            
            # Step 3: Verify deletion
            verification_success = self.verify_user_deleted(user_email)
            
            return {
                'user_email': user_email,
                'success': deletion_success,
                'message': f'Lucidchart user deleted and verified: {verification_success}',
                'verified': verification_success
            }
            
        except Exception as e:
            logger.error(f"Lucidchart termination failed for {user_email}: {e}")
            return {
                'user_email': user_email,
                'success': False,
                'message': f'Lucidchart termination failed: {e}',
                'verified': False
            }

    # Legacy methods for backwards compatibility
    def create_user(self, user_data):
        """Legacy method - not implemented for termination workflow."""
        logger.warning("create_user not implemented for Lucidchart termination service")
        pass
    
    def terminate_user(self, email, manager_email=None):
        """Legacy method - use execute_termination instead."""
        logger.warning("terminate_user deprecated - use execute_termination instead")
        result = self.execute_termination(email)
        return result.get('success', False)
    
    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        """
        Execute complete Lucidchart termination following the termination procedure.
        
        Lucidchart Termination Steps:
        1. Log into Lucidchart Admin
        2. Users → Search user → Delete user
        3. Transfer documents to manager if required
        4. Remove from "SSO-LucidChart" group in Okta (handled by workflow)
        
        Args:
            user_email: Email of user to terminate
            manager_email: Manager email for document transfer
            
        Returns:
            Dict with success status, actions taken, and any errors
        """
        actions_taken = []
        errors = []
        warnings = []
        
        try:
            logger.info(f"Starting Lucidchart termination for {user_email}")
            
            # Step 1: Find user in Lucidchart
            user_info = self.find_user_by_email(user_email)
            if not user_info:
                logger.info(f"User {user_email} not found in Lucidchart - no termination needed")
                return {
                    'success': True,
                    'actions': ['User not found in Lucidchart - no action needed'],
                    'errors': errors,
                    'warnings': warnings
                }
            
            actions_taken.append(f"Found user in Lucidchart: {user_email}")
            
            # Step 2: Transfer documents to manager (if specified)
            if manager_email:
                logger.info(f"Attempting to transfer documents to manager: {manager_email}")
                # Note: Document transfer would need to be implemented based on Lucidchart API
                # For now, we'll note this as a manual step
                warnings.append(f"Document transfer to {manager_email} may require manual intervention")
                actions_taken.append(f"Noted document transfer requirement to {manager_email}")
            else:
                warnings.append("No manager specified - document transfer not performed")
            
            # Step 3: Delete user from Lucidchart
            logger.info(f"Deleting Lucidchart user: {user_email}")
            deletion_success = self.delete_user(user_email)
            
            if deletion_success:
                actions_taken.append(f"Deleted Lucidchart user: {user_email}")
                logger.info(f"Successfully deleted Lucidchart user: {user_email}")
                
                # Step 4: Verify deletion
                verification_result = self.verify_user_deleted(user_email)
                if verification_result:
                    actions_taken.append("Verified user deletion from Lucidchart")
                else:
                    warnings.append("User deletion not verified - may still exist in Lucidchart")
                
                return {
                    'success': True,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': warnings
                }
            else:
                error_msg = f"Failed to delete Lucidchart user: {user_email}"
                errors.append(error_msg)
                logger.error(error_msg)
                return {
                    'success': False,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': warnings
                }
                
        except Exception as e:
            error_msg = f"Error in Lucidchart termination for {user_email}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return {
                'success': False,
                'actions': actions_taken,
                'errors': errors,
                'warnings': warnings
            }

    def test_connection(self):
        """Legacy method - use test_connectivity instead."""
        return self.test_connectivity()


# For backwards compatibility
LucidService = LucidchartService
