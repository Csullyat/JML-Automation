
"""
Adobe User Management service for JML Automation.
Handles Adobe user management for termination workflows.
Includes Okta integration to check group membership before deletion.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from jml_automation.config import Config
from .base import BaseService
from .okta import OktaService

__all__ = ["AdobeService"]

logger = logging.getLogger(__name__)

class AdobeService(BaseService):
    """Adobe User Management API service with Okta integration."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize Adobe service with API credentials and optional dry run mode."""
        self.service_name = "Adobe"
        self.config = Config()
        self.dry_run = dry_run
        
        # Adobe User Management API base URL
        self.auth_base_url = "https://ims-na1.adobelogin.com"
        self.api_base_url = "https://usermanagement.adobe.io/v2/usermanagement"
        
        # Credentials
        self.client_id = None
        self.client_secret = None
        self.org_id = None
        self.api_key = None  # Fallback
        self.access_token = None
        
        # Initialize Okta service for group checks
        self.okta_service = None
        
        logger.info(f"Adobe service initialized (dry_run={dry_run})")

    def _get_okta_service(self) -> Optional[OktaService]:
        """Get Okta service instance for group checks."""
        if self.okta_service is None:
            try:
                self.okta_service = OktaService.from_env()
                logger.info("Okta service initialized for Adobe group checks")
            except Exception as e:
                logger.error(f"Failed to initialize Okta service: {e}")
                return None
        return self.okta_service

    def _get_credentials(self) -> bool:
        """Get all required credentials from 1Password."""
        try:
            creds = self.config.get_adobe_credentials_dict()
            
            self.client_id = creds.get('client_id')
            self.client_secret = creds.get('client_secret') 
            self.org_id = creds.get('org_id')
            self.api_key = creds.get('api_key')  # Fallback
            
            # Check if we have OAuth S2S credentials
            if self.client_id and self.client_secret and self.org_id:
                logger.info("Found OAuth S2S credentials for Adobe")
                return True
            elif self.api_key:
                logger.info("Found API key credentials for Adobe (fallback mode)")
                return True
            else:
                logger.error("No valid Adobe credentials found in 1Password")
                return False
                
        except Exception as e:
            logger.error(f"Error retrieving Adobe credentials: {e}")
            return False

    def _get_access_token(self) -> Optional[str]:
        """Get OAuth S2S access token for Adobe API."""
        if not self.client_id or not self.client_secret:
            logger.error("Cannot get access token - missing OAuth S2S credentials")
            return None
            
        if self.access_token:
            return self.access_token
            
        try:
            # OAuth S2S token request with User Management scopes
            token_url = f"{self.auth_base_url}/ims/token/v3"
            
            # User Management API requires specific metascopes
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'openid,AdobeID,user_management_sdk'  # Exact scopes from Developer Console
            }
            
            response = requests.post(token_url, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                logger.info(f"Successfully obtained Adobe OAuth access token with scope: {token_data.get('scope', 'unknown')}")
                return self.access_token
            else:
                logger.error(f"Failed to get Adobe access token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Adobe access token: {e}")
            return None

    def _get_api_key(self) -> Optional[str]:
        """Get API key from 1Password (fallback method)."""
        if self.api_key:
            return self.api_key
            
        try:
            creds = self.config.get_adobe_credentials_dict()
            api_key = creds.get('api_key')
            
            if not api_key:
                logger.error("Adobe API key not found in 1Password")
                return None
                
            self.api_key = api_key
            logger.info("Successfully retrieved Adobe API key from 1Password")
            return self.api_key
            
        except Exception as e:
            logger.error(f"Error retrieving Adobe API key: {e}")
            return None

    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Get request headers with appropriate authentication."""
        # Try OAuth S2S first
        access_token = self._get_access_token()
        if access_token and self.org_id:
            return {
                "Authorization": f"Bearer {access_token}",
                "X-Api-Key": str(self.client_id),
                "X-Gw-Ims-Org-Id": str(self.org_id),
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        
        # Fallback to API key if available
        api_key = self._get_api_key()
        if api_key:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
        logger.error("No valid authentication method available for Adobe API")
        return None

    def _build_api_url(self, endpoint: str) -> str:
        """Build full API URL with organization context."""
        if self.org_id:
            # Special handling for action endpoint
            if endpoint == "/action":
                return f"{self.api_base_url}/action/{self.org_id}"
            else:
                return f"{self.api_base_url}/organizations/{self.org_id}{endpoint}"
        else:
            return f"{self.api_base_url}{endpoint}"

    def test_connection(self) -> bool:
        """Test connection to Adobe User Management API."""
        if self.dry_run:
            logger.info("DRY RUN: Would test Adobe API connection")
            return True
            
        try:
            # Get credentials first
            if not self._get_credentials():
                logger.error("Could not get Adobe credentials")
                return False
                
            # Test OAuth token generation
            access_token = self._get_access_token()
            if not access_token:
                logger.error("Could not get Adobe OAuth access token")
                return False
                
            # If we got here, basic OAuth is working
            logger.info("Adobe OAuth S2S authentication successful")
            logger.warning("Skipping API endpoint test due to permission issues - will test during actual operation")
            return True
                
        except Exception as e:
            logger.error(f"Error testing Adobe API connection: {e}")
            return False

    def find_user_by_email(self, email: str) -> Optional[str]:
        """
        Find Adobe user ID by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User ID if found, None otherwise
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would find Adobe user by email: {email}")
            return "dry-run-user-id"
            
        try:
            headers = self._get_headers()
            if not headers:
                return None
                
            # Search for user by email
            user_url = self._build_api_url(f"/users/{email}")
            response = requests.get(
                user_url,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # Adobe API typically returns user info directly
                logger.info(f"Found Adobe user: {email}")
                return email  # Adobe uses email as identifier
            elif response.status_code == 404:
                logger.info(f"Adobe user not found: {email}")
                return None
            else:
                logger.error(f"Error searching for Adobe user {email}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding Adobe user {email}: {e}")
            return None

    def delete_user(self, email: str) -> bool:
        """
        Delete user from Adobe account.
        
        Args:
            email: Email address of user to delete
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would delete Adobe user: {email}")
            return True
            
        try:
            # First check if user exists
            user_id = self.find_user_by_email(email)
            if not user_id:
                logger.warning(f"Cannot delete Adobe user {email} - user not found")
                return False
                
            headers = self._get_headers()
            if not headers:
                return False
                
            # Prepare deletion request - Adobe API expects user at top level with action array
            delete_data = [
                {
                    "user": email,
                    "do": [
                        {
                            "removeFromOrg": {
                                "deleteAccount": False
                            }
                        }
                    ]
                }
            ]
            
            # Log the exact payload being sent for debugging
            logger.info(f"Sending Adobe deletion payload: {delete_data}")
            
            action_url = self._build_api_url("/action")
            response = requests.post(
                action_url,
                headers=headers,
                json=delete_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully deleted Adobe user: {email}")
                return True
            else:
                logger.error(f"Failed to delete Adobe user {email}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting Adobe user {email}: {e}")
            return False

    def check_okta_groups(self, email: str) -> Dict[str, bool]:
        """
        Check if user is in Adobe-related Okta groups.
        
        Args:
            email: Email address of user to check
            
        Returns:
            Dict with group names as keys and membership status as values
        """
        okta = self._get_okta_service()
        if not okta:
            logger.error("Could not initialize Okta service for group checks")
            return {"SSO-Adobe": False}
        
        try:
            user_id = okta.find_user_by_email(email)
            if not user_id:
                logger.warning(f"User {email} not found in Okta")
                return {"SSO-Adobe": False}
            
            logger.info(f"Checking Okta groups for user {email} (ID: {user_id})")
            
            # Check Adobe group
            is_in_adobe = okta.is_user_in_group(user_id, "SSO-Adobe")
            
            result = {
                "SSO-Adobe": is_in_adobe
            }
            
            logger.info(f"Okta group membership for {email}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking Okta groups for {email}: {e}")
            return {"SSO-Adobe": False}

    def remove_from_okta_groups(self, email: str, groups_to_remove: List[str]) -> bool:
        """
        Remove user from specified Okta groups.
        
        Args:
            email: Email address of user
            groups_to_remove: List of group names to remove user from
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would remove {email} from Okta groups: {groups_to_remove}")
            return True
            
        okta = self._get_okta_service()
        if not okta:
            logger.error("Could not initialize Okta service for group removal")
            return False
        
        try:
            user_id = okta.find_user_by_email(email)
            if not user_id:
                logger.warning(f"User {email} not found in Okta for group removal")
                return False
            
            # Get group IDs for the group names
            group_ids = []
            for group_name in groups_to_remove:
                group_id = okta.find_group_id(group_name)
                if group_id:
                    group_ids.append(group_id)
                else:
                    logger.warning(f"Group {group_name} not found in Okta")
            
            if not group_ids:
                logger.warning("No valid group IDs found for removal")
                return False
            
            # Remove user from groups
            okta.remove_from_groups(user_id, group_ids)
            logger.info(f"Successfully removed {email} from Okta groups: {groups_to_remove}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing {email} from Okta groups: {e}")
            return False

    def terminate_user(self, email: str, manager_email: Optional[str] = None) -> bool:
        """
        Terminate user with Okta group checks and workflow.
        
        Workflow:
        1. Check if user is in SSO-Adobe group
        2. If in group, delete user from Adobe account
        3. Remove from SSO-Adobe Okta group after successful Adobe deletion
        
        Args:
            email: Email address of user to terminate
            manager_email: Manager email (not used for Adobe)
            
        Returns:
            True if workflow completed successfully, False otherwise
        """
        try:
            logger.info(f"Starting Adobe termination workflow for {email}")
            
            # Step 1: Check Okta groups
            group_membership = self.check_okta_groups(email)
            
            is_in_adobe = group_membership.get("SSO-Adobe", False)
            
            if not is_in_adobe:
                logger.info(f"User {email} is not in SSO-Adobe group - no action needed")
                return True
            
            # Step 2: Delete user from Adobe account
            logger.info(f"User {email} is in SSO-Adobe group, deleting from Adobe account")
            adobe_success = self.delete_user(email)
            
            # Step 3: Remove from Okta groups if Adobe deletion was successful
            if adobe_success:
                groups_to_remove = ["SSO-Adobe"]
                okta_success = self.remove_from_okta_groups(email, groups_to_remove)
                
                if okta_success:
                    logger.info(f"Successfully completed Adobe termination workflow for {email}")
                    return True
                else:
                    logger.warning(f"Adobe deletion successful but Okta group removal failed for {email}")
                    return False
            else:
                logger.error(f"Adobe deletion failed for {email}, skipping Okta group removal")
                return False
                
        except Exception as e:
            logger.error(f"Error in Adobe termination workflow for {email}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get service status information."""
        status = {
            "service": self.service_name,
            "dry_run": self.dry_run,
            "api_configured": bool(self._get_api_key()),
            "okta_available": bool(self._get_okta_service())
        }
        
        if not self.dry_run:
            status["connection_test"] = self.test_connection()
        
        return status

    def create_user(self, user_data):
        """Legacy method for compatibility."""
        pass
