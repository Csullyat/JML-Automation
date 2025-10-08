"""
Domo service for JML Automation.
Handles Domo user management for termination workflows using Domo's User Management API.
"""

import logging
import requests
from typing import Dict, Any, Optional
from jml_automation.config import Config

__all__ = ["DomoService"]

logger = logging.getLogger(__name__)

class DomoService:
    """Domo API service for user management."""
    
    def __init__(self):
        """Initialize Domo service with API credentials."""
        self.service_name = "Domo"
        self.config = Config()
        
        # TODO: Add Domo credentials to config
        # For now, we'll implement the structure but note missing credentials
        self.base_url = "https://api.domo.com/v1"
        self.access_token = None
        
        logger.info("Domo service initialized")

    def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token for Domo API."""
        try:
            # Get credentials from 1Password
            domo_creds = self.config.get_domo_credentials_dict()
            client_id = domo_creds.get('client_id')
            client_secret = domo_creds.get('client_secret')
            
            if not client_id or not client_secret:
                logger.warning("Domo API credentials not found in 1Password")
                return None
            
            # Domo OAuth token endpoint
            token_url = "https://api.domo.com/oauth/token"
            
            # Prepare OAuth request
            data = {
                "grant_type": "client_credentials",
                "scope": "user"  # Scope for user management
            }
            
            # Make OAuth request
            response = requests.post(
                token_url,
                auth=(client_id, client_secret),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            if access_token:
                logger.info("Successfully obtained Domo access token")
                return access_token
            else:
                logger.error("No access token in Domo OAuth response")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get Domo access token: {e}")
            return None

    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated API request to Domo."""
        if not self.access_token:
            self.access_token = self._get_access_token()
            if not self.access_token:
                logger.error("No Domo access token available")
                return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Domo API request failed: {e}")
            return None

    def find_user_by_email_direct(self, email: str) -> Optional[Dict]:
        """Try to find user by using email as direct identifier."""
        try:
            # Try using email as direct identifier
            user_response = self._make_api_request("GET", f"/users/{email}")
            
            if user_response:
                logger.info(f"Found Domo user directly: {user_response.get('displayName')} ({email})")
                return user_response
                
            return None
            
        except Exception as e:
            logger.debug(f"Direct email lookup failed for {email}: {e}")
            return None

    def find_user_by_email_search(self, email: str) -> Optional[Dict]:
        """Find Domo user by email address using search endpoint."""
        try:
            # Try using a search endpoint first (if available)
            search_response = self._make_api_request("GET", f"/users/search?email={email}")
            
            if search_response and isinstance(search_response, dict):
                user = search_response.get('user')
                if user:
                    logger.info(f"Found Domo user via search: {user.get('displayName')} ({email})")
                    return user
            
            return None
            
        except Exception as e:
            logger.debug(f"Search endpoint failed for {email}: {e}")
            return None

    def _find_user_by_listing(self, email: str) -> Optional[Dict]:
        """Find user by listing all users with pagination support."""
        try:
            offset = 0
            limit = 100  # Adjust based on Domo's limits
            total_checked = 0
            
            while True:
                # Add pagination parameters
                endpoint = f"/users?limit={limit}&offset={offset}"
                users_response = self._make_api_request("GET", endpoint)
                
                if not users_response:
                    break
                    
                # Handle different response formats
                if isinstance(users_response, list):
                    users_list = users_response
                else:
                    users_list = users_response.get("users", [])
                    
                total_checked += len(users_list)
                logger.debug(f"Checking batch of {len(users_list)} users (total checked: {total_checked})")
                
                # Search for user in current batch
                for user in users_list:
                    user_email = user.get("email", "")
                    if user_email.lower() == email.lower():
                        logger.info(f"Found Domo user: {user.get('displayName')} ({email})")
                        return user
                
                # Check if we've reached the end
                if len(users_list) < limit:
                    break
                    
                offset += limit
                
            logger.warning(f"User {email} not found among {total_checked} Domo users")
            return None
            
        except Exception as e:
            logger.error(f"Error finding Domo user {email}: {e}")
            return None

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """Find Domo user by email address with enhanced debugging."""
        try:
            logger.info(f"Searching for Domo user: {email}")
            
            # Try direct lookup first
            user = self.find_user_by_email_direct(email)
            if user:
                return user
                
            # Try search endpoint
            user = self.find_user_by_email_search(email)
            if user:
                return user
            
            # Get users list with debugging
            users_response = self._make_api_request("GET", "/users")
            
            if not users_response:
                logger.error("No response from Domo users API")
                return None
            
            # Log response structure for debugging
            logger.debug(f"Domo users response type: {type(users_response)}")
            if isinstance(users_response, dict):
                logger.debug(f"Domo users response keys: {list(users_response.keys())}")
            
            # Handle different response formats
            if isinstance(users_response, list):
                users_list = users_response
            else:
                users_list = users_response.get("users", [])
            
            logger.info(f"Retrieved {len(users_list)} users from Domo API")
            
            # Log some sample emails for debugging (without exposing full emails)
            if users_list and len(users_list) > 0:
                sample_emails = []
                for user in users_list[:5]:  # First 5 users
                    email_addr = user.get("email", "")
                    if email_addr:
                        masked_email = email_addr[:3] + "***@" + email_addr.split("@")[1] if "@" in email_addr else email_addr[:3] + "***"
                        sample_emails.append(masked_email)
                logger.debug(f"Sample emails in response: {sample_emails}")
                
                # Check if our target domain exists
                target_domain = email.split("@")[1] if "@" in email else ""
                domain_matches = [user.get("email", "") for user in users_list if target_domain in user.get("email", "")]
                logger.info(f"Found {len(domain_matches)} users with domain {target_domain}")
            
            # Search for user by email
            for user in users_list:
                user_email = user.get("email", "")
                if user_email.lower() == email.lower():
                    logger.info(f"Found Domo user: {user.get('displayName')} ({email})")
                    return user
            
            # If not found, try pagination approach
            logger.warning(f"User {email} not found in first {len(users_list)} users, trying pagination...")
            return self._find_user_by_listing(email)
            
        except Exception as e:
            logger.error(f"Error finding Domo user {email}: {e}")
            return None

    def delete_user(self, user_email: str) -> bool:
        """Delete user from Domo."""
        try:
            # First, find the user
            user = self.find_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in Domo, may already be deleted")
                return True
                
            user_id = user.get("id")
            if not user_id:
                logger.error(f"No user ID found for {user_email}")
                return False
                
            # Delete the user
            logger.info(f"Deleting Domo user: {user_email} (ID: {user_id})")
            delete_response = self._make_api_request("DELETE", f"/users/{user_id}")
            
            if delete_response is not None:
                logger.info(f"Successfully deleted Domo user: {user_email}")
                return True
            else:
                logger.error(f"Failed to delete Domo user: {user_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting Domo user {user_email}: {e}")
            return False

    def verify_user_deleted(self, user_email: str) -> bool:
        """Verify that user has been deleted from Domo."""
        try:
            user = self.find_user_by_email(user_email)
            if user:
                logger.error(f"User {user_email} still exists in Domo after deletion attempt")
                return False
            else:
                logger.info(f"Verified: User {user_email} no longer exists in Domo")
                return True
        except Exception as e:
            logger.error(f"Error verifying Domo user deletion for {user_email}: {e}")
            return False

    def execute_termination(self, user_email: str) -> Dict[str, Any]:
        """Execute complete Domo termination for a user with verification."""
        logger.info(f"Domo termination requested for {user_email}")
        
        try:
            # Step 1: Try to find user first - CRITICAL CHECK
            user = self.find_user_by_email(user_email)
            
            if not user:
                logger.error(f"CRITICAL: User {user_email} not found in Domo - this may indicate an API issue or user doesn't exist")
                logger.error("This requires manual verification before proceeding with Okta group removal")
                return {
                    'user_email': user_email,
                    'success': False,
                    'message': f'User {user_email} not found in Domo - manual verification required',
                    'verified': False,
                    'requires_manual_check': True  # Flag for manual intervention
                }
            
            logger.info(f"Found user in Domo: {user.get('displayName')} (ID: {user.get('id')})")
            
            # Step 2: Delete user
            deletion_success = self.delete_user(user_email)
            
            if not deletion_success:
                return {
                    'user_email': user_email,
                    'success': False,
                    'message': 'Domo user deletion failed',
                    'verified': False
                }
            
            # Step 3: Verify deletion
            verification_success = self.verify_user_deleted(user_email)
            
            return {
                'user_email': user_email,
                'success': deletion_success,
                'message': f'Domo user deleted and verified: {verification_success}',
                'verified': verification_success
            }
            
        except Exception as e:
            logger.error(f"Domo termination failed for {user_email}: {e}")
            return {
                'user_email': user_email,
                'success': False,
                'message': f'Domo termination failed: {e}',
                'verified': False
            }

    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        """
        Execute complete Domo termination following the termination procedure.
        
        Domo Termination Steps:
        1. Log into Domo Admin via Okta
        2. Select user → Delete person
        3. Remove from "SSO-Domo" group in Okta (handled by workflow)
        
        Args:
            user_email: Email of user to terminate
            manager_email: Manager email (not used for Domo)
            
        Returns:
            Dict with success status, actions taken, and any errors
        """
        actions_taken = []
        errors = []
        warnings = []
        
        try:
            logger.info(f"Starting Domo termination for {user_email}")
            
            # Step 1: Find user in Domo
            user_info = self.find_user_by_email(user_email)
            if not user_info:
                logger.info(f"User {user_email} not found in Domo - no termination needed")
                return {
                    'success': True,
                    'actions': ['User not found in Domo - no action needed'],
                    'errors': errors,
                    'warnings': warnings
                }
            
            actions_taken.append(f"Found user in Domo: {user_email}")
            
            # Step 2: Delete user from Domo
            logger.info(f"Deleting Domo user: {user_email}")
            deletion_success = self.delete_user(user_email)
            
            if deletion_success:
                actions_taken.append(f"Deleted Domo user: {user_email}")
                logger.info(f"Successfully deleted Domo user: {user_email}")
                
                # Step 3: Verify deletion
                verification_result = self.verify_user_deleted(user_email)
                if verification_result:
                    actions_taken.append("Verified user deletion from Domo")
                else:
                    warnings.append("User deletion not verified - may still exist in Domo")
                
                return {
                    'success': True,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': warnings
                }
            else:
                error_msg = f"Failed to delete Domo user: {user_email}"
                errors.append(error_msg)
                logger.error(error_msg)
                return {
                    'success': False,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': warnings
                }
                
        except Exception as e:
            error_msg = f"Error in Domo termination for {user_email}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return {
                'success': False,
                'actions': actions_taken,
                'errors': errors,
                'warnings': warnings
            }

    def test_connectivity(self) -> Dict[str, Any]:
        """Test Domo API connectivity."""
        try:
            if not self._get_access_token():
                return {
                    'success': False,
                    'message': 'Domo API credentials not configured'
                }
                
            # Try to list users as a connectivity test
            response = self._make_api_request("GET", "/users")
            
            if response:
                return {
                    'success': True,
                    'message': 'Domo API connectivity successful'
                }
            else:
                return {
                    'success': False,
                    'message': 'Domo API connectivity failed'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Domo connectivity test failed: {e}'
            }
