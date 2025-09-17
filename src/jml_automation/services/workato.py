
"""
Workato service for JML Automation.
Handles Workato collaborator management for termination workflows.
Includes Okta integration to check group membership before removal.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from jml_automation.config import Config
from .base import BaseService
from .okta import OktaService
from .okta import OktaService

__all__ = ["WorkatoService"]

logger = logging.getLogger(__name__)

class WorkatoService(BaseService):
    """Workato API service for collaborator management with Okta integration."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize Workato service with API credentials and optional dry run mode."""
        self.service_name = "Workato"
        self.config = Config()
        self.dry_run = dry_run
        
        # Workato API base URL
        self.base_url = "https://www.workato.com/api"
        self.api_key = None
        
        # Initialize Okta service for group checks
        self.okta_service = None
        
        logger.info(f"Workato service initialized (dry_run={dry_run})")

    def _get_okta_service(self) -> Optional[OktaService]:
        """Get Okta service instance for group checks."""
        if self.okta_service is None:
            try:
                self.okta_service = OktaService.from_env()
                logger.info("Okta service initialized for Workato group checks")
            except Exception as e:
                logger.error(f"Failed to initialize Okta service: {e}")
                return None
        return self.okta_service

    def _get_api_key(self) -> Optional[str]:
        """Get API key from 1Password."""
        try:
            # Get Workato API key from 1Password (Vault IT, "Workato API Key", credential field)
            workato_creds = self.config.get_workato_credentials_dict()
            api_key = workato_creds.get('credential')
            
            if not api_key:
                logger.warning("Workato API key not found in 1Password")
                return None
            
            logger.info("Successfully retrieved Workato API key")
            return api_key
                
        except Exception as e:
            logger.error(f"Failed to get Workato API key: {e}")
            return None

    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated API request to Workato."""
        if self.dry_run:
            logger.info(f"DRY RUN: Would make {method} request to {self.base_url}{endpoint}")
            if data:
                logger.info(f"DRY RUN: Request data: {data}")
            return {"success": True, "status_code": 200, "dry_run": True}
        
        if not self.api_key:
            self.api_key = self._get_api_key()
            if not self.api_key:
                logger.error("No Workato API key available")
                return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response.raise_for_status()
            
            # Some DELETE operations may return empty response
            if response.status_code == 204 or not response.text:
                return {"success": True, "status_code": response.status_code}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Workato API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Workato API request: {e}")
            return None

    def get_collaborators(self, workspace_type: str = "internal") -> Optional[List[Dict]]:
        """
        Get list of collaborators from a workspace.
        
        Args:
            workspace_type: "internal" for our internal workspace, "customer" for embedded account/Filevine Operations
            
        Returns:
            List of collaborator dictionaries or None if error
        """
        try:
            if self.dry_run:
                logger.info(f"DRY RUN: Would get {workspace_type} collaborators")
                # Return mock data for dry run
                return [
                    {"id": "mock1", "email": "user1@example.com", "name": "Mock User 1"},
                    {"id": "mock2", "email": "user2@example.com", "name": "Mock User 2"}
                ]
            
            # Different endpoints for different workspace types
            # TODO: Update these endpoints with the correct Workato API paths
            if workspace_type == "internal":
                endpoint = "/collaborators"
            elif workspace_type == "customer":
                # Assuming embedded account has different endpoint
                endpoint = "/embedded_accounts/collaborators"
            else:
                logger.error(f"Unknown workspace type: {workspace_type}")
                return None
            
            result = self._make_api_request("GET", endpoint)
            
            if result:
                logger.info(f"Successfully retrieved {workspace_type} collaborators")
                return result.get('collaborators', [])
            else:
                logger.error(f"Failed to retrieve {workspace_type} collaborators")
                return None
                
        except Exception as e:
            logger.error(f"Error getting {workspace_type} collaborators: {e}")
            return None

    def remove_collaborator(self, email: str, workspace_type: str = "internal") -> bool:
        """
        Remove a collaborator from specified workspace.
        
        Args:
            email: Email address of collaborator to remove
            workspace_type: "internal" for our internal workspace, "customer" for embedded account/Filevine Operations
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                logger.info(f"DRY RUN: Would remove {email} from {workspace_type} workspace")
                return True
            
            # First, find the collaborator ID by email
            collaborators = self.get_collaborators(workspace_type)
            if not collaborators:
                logger.error(f"Could not retrieve {workspace_type} collaborators")
                return False
            
            collaborator_id = None
            for collab in collaborators:
                if collab.get('email', '').lower() == email.lower():
                    collaborator_id = collab.get('id')
                    break
            
            if not collaborator_id:
                logger.warning(f"Collaborator {email} not found in {workspace_type} workspace")
                return False
            
            # Different endpoints for different workspace types
            # TODO: Update these endpoints with the correct Workato API paths
            if workspace_type == "internal":
                endpoint = f"/collaborators/{collaborator_id}"
            elif workspace_type == "customer":
                endpoint = f"/embedded_accounts/collaborators/{collaborator_id}"
            else:
                logger.error(f"Unknown workspace type: {workspace_type}")
                return False
            
            result = self._make_api_request("DELETE", endpoint)
            
            if result:
                logger.info(f"Successfully removed collaborator {email} from {workspace_type} workspace")
                return True
            else:
                logger.error(f"Failed to remove collaborator {email} from {workspace_type} workspace")
                return False
                
        except Exception as e:
            logger.error(f"Error removing collaborator {email} from {workspace_type} workspace: {e}")
            return False

    def check_okta_groups(self, email: str) -> Dict[str, bool]:
        """
        Check if user is in Workato-related Okta groups.
        
        Args:
            email: Email address of user to check
            
        Returns:
            Dict with group names as keys and membership status as values
        """
        okta = self._get_okta_service()
        if not okta:
            logger.error("Could not initialize Okta service for group checks")
            return {"SSO-Workato": False, "SSO-Workato_Operations": False}
        
        try:
            user_id = okta.find_user_by_email(email)
            if not user_id:
                logger.warning(f"User {email} not found in Okta")
                return {"SSO-Workato": False, "SSO-Workato_Operations": False}
            
            logger.info(f"Checking Okta groups for user {email} (ID: {user_id})")
            
            # Check both Workato groups
            is_in_internal = okta.is_user_in_group(user_id, "SSO-Workato")
            is_in_customer = okta.is_user_in_group(user_id, "SSO-Workato_Operations")
            
            result = {
                "SSO-Workato": is_in_internal,
                "SSO-Workato_Operations": is_in_customer
            }
            
            logger.info(f"Okta group membership for {email}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking Okta groups for {email}: {e}")
            return {"SSO-Workato": False, "SSO-Workato_Operations": False}

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
                logger.warning(f"User {email} not found in Okta")
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

    def create_user(self, user_data: Dict) -> bool:
        """Create/provision user - not implemented for Workato."""
        logger.warning("create_user not implemented for Workato service")
        return False

    def terminate_user(self, email: str, manager_email: Optional[str] = None) -> bool:
        """
        Terminate user with Okta group checks and workflow.
        
        Workflow:
        1. Check if user is in SSO-Workato or SSO-Workato_Operations groups
        2. If in groups, remove from corresponding Workato workspaces
        3. Remove from Okta groups after successful Workato removal
        
        Args:
            email: Email address of user to terminate
            manager_email: Manager email (not used for Workato)
            
        Returns:
            True if workflow completed successfully, False otherwise
        """
        try:
            logger.info(f"Starting Workato termination workflow for {email}")
            
            # Step 1: Check Okta groups
            group_membership = self.check_okta_groups(email)
            
            is_in_internal = group_membership.get("SSO-Workato", False)
            is_in_customer = group_membership.get("SSO-Workato_Operations", False)
            
            if not is_in_internal and not is_in_customer:
                logger.info(f"User {email} is not in any Workato Okta groups - no action needed")
                return True
            
            # Step 2: Remove from Workato workspaces based on group membership
            internal_success = True
            customer_success = True
            
            if is_in_internal:
                logger.info(f"User {email} is in SSO-Workato group, removing from internal workspace")
                internal_success = self.remove_collaborator(email, "internal")
            else:
                logger.info(f"User {email} is not in SSO-Workato group, skipping internal workspace")
            
            if is_in_customer:
                logger.info(f"User {email} is in SSO-Workato_Operations group, removing from customer workspace")
                customer_success = self.remove_collaborator(email, "customer")
            else:
                logger.info(f"User {email} is not in SSO-Workato_Operations group, skipping customer workspace")
            
            workato_success = internal_success and customer_success
            
            # Step 3: Remove from Okta groups if Workato removal was successful
            if workato_success:
                groups_to_remove = []
                if is_in_internal:
                    groups_to_remove.append("SSO-Workato")
                if is_in_customer:
                    groups_to_remove.append("SSO-Workato_Operations")
                
                if groups_to_remove:
                    okta_success = self.remove_from_okta_groups(email, groups_to_remove)
                    
                    if okta_success:
                        logger.info(f"Successfully completed Workato termination workflow for {email}")
                        return True
                    else:
                        logger.warning(f"Workato removal successful but Okta group removal failed for {email}")
                        return False
                else:
                    logger.info(f"No Okta groups to remove for {email}")
                    return True
            else:
                logger.error(f"Workato removal failed for {email}, skipping Okta group removal")
                return False
            
        except Exception as e:
            logger.error(f"Error in Workato termination workflow for {email}: {e}")
            return False

    def test_connection(self) -> bool:
        """Test Workato API connectivity."""
        try:
            logger.info("Testing Workato API connection...")
            
            if self.dry_run:
                logger.info("DRY RUN: Simulating successful API connection test")
                return True
            
            # Test by trying to get API key first
            api_key = self._get_api_key()
            if not api_key:
                logger.error("Workato API connection test failed - no API key")
                return False
            
            # Test basic API connectivity (you may need to adjust the endpoint)
            # For now, just test if we can authenticate
            result = self._make_api_request("GET", "/connections")  # Common endpoint
            
            if result is not None:
                logger.info("Workato API connection test successful")
                return True
            else:
                logger.error("Workato API connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Workato API connection test error: {e}")
            return False
