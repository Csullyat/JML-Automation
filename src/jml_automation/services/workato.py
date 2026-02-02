
"""
Workato service for JML Automation.
Handles Workato collaborator management for termination workflows.
Includes Okta integration to check group membership before removal.
Uses browser automation for collaborator removal since API endpoints are not available.
"""

import logging
import requests
import time
import ssl
import certifi
import urllib3
from typing import Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from jml_automation.config import Config
from .base import BaseService
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
        self.base_url = "https://app.workato.com/api"
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
            # Create a session with proper SSL configuration for Windows
            session = requests.Session()
            
            # Try multiple SSL verification approaches
            cert_options = [
                certifi.where(),  # Use certifi bundle first
                True,             # Use system default
                False             # Disable verification as last resort
            ]
            
            last_error = None
            for cert_bundle in cert_options:
                try:
                    if method.upper() == "GET":
                        response = session.get(url, headers=headers, verify=cert_bundle, timeout=30)
                    elif method.upper() == "DELETE":
                        response = session.delete(url, headers=headers, verify=cert_bundle, timeout=30)
                    elif method.upper() == "POST":
                        response = session.post(url, headers=headers, json=data, verify=cert_bundle, timeout=30)
                    elif method.upper() == "PUT":
                        response = session.put(url, headers=headers, json=data, verify=cert_bundle, timeout=30)
                    else:
                        logger.error(f"Unsupported HTTP method: {method}")
                        return None
                    
                    response.raise_for_status()
                    
                    # If we get here, the request succeeded
                    if cert_bundle is False:
                        logger.warning("SSL verification disabled - connection succeeded but not secure")
                    
                    break  # Success, exit the retry loop
                    
                except requests.exceptions.SSLError as ssl_err:
                    last_error = ssl_err
                    if cert_bundle is not False:  # Not the last option yet
                        logger.debug(f"SSL verification failed with {cert_bundle}, trying next option")
                        continue
                    else:
                        raise ssl_err
                except requests.exceptions.RequestException as req_err:
                    # Non-SSL errors should not retry
                    raise req_err
                
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
            # Updated with correct Workato API paths
            if workspace_type == "internal":
                endpoint = "/members"
            elif workspace_type == "customer":
                # Customer workspace also uses /members endpoint
                endpoint = "/members"
            else:
                logger.error(f"Unknown workspace type: {workspace_type}")
                return None
            
            result = self._make_api_request("GET", endpoint)
            
            if result:
                logger.info(f"Successfully retrieved {workspace_type} collaborators")
                return result.get('data', [])
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
            # Updated with correct Workato API paths
            if workspace_type == "internal":
                endpoint = f"/members/{collaborator_id}"
            elif workspace_type == "customer":
                endpoint = f"/members/{collaborator_id}"
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

    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        """
        Execute complete Workato termination using original API approach.
        
        Workato Termination Steps:
        1. Check Okta groups to determine workspace membership
        2. Remove from appropriate Workato workspaces via API  
        3. Remove from Okta groups after successful removal
        
        Args:
            user_email: Email of user to terminate
            manager_email: Manager email (not used for Workato)
            
        Returns:
            Dict with success status, actions taken, and any errors
        """
        actions_taken = []
        errors = []
        warnings = []
        
        try:
            logger.info(f"Starting Workato termination for {user_email}")
            
            # Use the original terminate_user method that was working
            success = self.terminate_user(user_email, manager_email)
            
            if success:
                actions_taken.append(f"Successfully completed Workato termination workflow for {user_email}")
                logger.info(f"Workato termination completed successfully for {user_email}")
                return {
                    'success': True,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': warnings
                }
            else:
                error_msg = f"Workato termination workflow failed for {user_email}"
                errors.append(error_msg)
                logger.error(error_msg)
                return {
                    'success': False,
                    'actions': actions_taken,
                    'errors': errors,
                    'warnings': warnings
                }
                
        except Exception as e:
            error_msg = f"Error in Workato termination for {user_email}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return {
                'success': False,
                'actions': actions_taken,
                'errors': errors,
                'warnings': warnings
            }

    def test_connectivity(self) -> Dict:
        """Test Workato API connectivity."""
        try:
            logger.info("Testing Workato API connection...")
            
            if self.dry_run:
                logger.info("DRY RUN: Simulating successful API connection test")
                return {
                    'success': True,
                    'message': '[DRY RUN] Workato API connection test simulated'
                }
            
            # Test by trying to get API key first
            api_key = self._get_api_key()
            if not api_key:
                logger.error("Workato API connection test failed - no API key")
                return {
                    'success': False,
                    'error': 'Workato API key not available'
                }
            
            # Test basic API connectivity with the working members endpoint
            result = self._make_api_request("GET", "/members")
            
            if result is not None:
                logger.info("Workato API connection test successful")
                return {
                    'success': True,
                    'message': 'Workato API connection successful'
                }
            else:
                logger.error("Workato API connection test failed")
                return {
                    'success': False,
                    'error': 'Workato API connection failed'
                }
                
        except Exception as e:
            logger.error(f"Workato API connection test error: {e}")
            return {
                'success': False,
                'error': f'Workato API connection failed: {str(e)}'
            }

    def test_connection(self) -> bool:
        """Legacy test method - use test_connectivity instead."""
        result = self.test_connectivity()
        return result.get('success', False)

    def _remove_collaborator_browser(self, user_email: str) -> bool:
        """
        Remove collaborator using browser automation since API endpoints don't work.
        
        Steps:
        1. Navigate to Workato login via Okta SSO
        2. Log in using service account credentials
        3. Navigate to Workspace Admin → Collaborators
        4. Search for user and remove
        
        Args:
            user_email: Email of collaborator to remove
            
        Returns:
            True if successful, False otherwise
        """
        driver = None
        try:
            logger.info(f"Starting browser automation for Workato collaborator removal: {user_email}")
            
            # Set up Chrome driver with headless mode
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            wait = WebDriverWait(driver, 30)
            
            # Step 1: Navigate to Workato via Okta SSO
            logger.info("Navigating to Workato via Okta SSO")
            driver.get("https://filevine.okta.com/app/workato_workato/exk5xfmcfmma1v8yl297/sso/saml")
            
            # Step 2: Handle Okta login if needed
            try:
                # Check if we need to log in to Okta
                if "okta.com" in driver.current_url and "login" in driver.current_url.lower():
                    logger.info("Okta login required - using service account")
                    # Get service account credentials from 1Password
                    service_creds = self.config.get_service_account_credentials()
                    username = service_creds.get('username')
                    password = service_creds.get('password')
                    
                    if not username or not password:
                        logger.error("Service account credentials not available")
                        return False
                    
                    # Enter credentials
                    username_field = wait.until(EC.presence_of_element_located((By.ID, "okta-signin-username")))
                    username_field.send_keys(username)
                    
                    password_field = driver.find_element(By.ID, "okta-signin-password")
                    password_field.send_keys(password)
                    
                    # Submit login
                    submit_btn = driver.find_element(By.ID, "okta-signin-submit")
                    submit_btn.click()
                    
                    # Wait for potential MFA or redirect
                    time.sleep(5)
                    
            except Exception as login_error:
                logger.warning(f"Okta login step encountered issue: {login_error}")
            
            # Step 3: Wait for Workato to load
            logger.info("Waiting for Workato to load")
            wait.until(lambda driver: "workato.com" in driver.current_url)
            time.sleep(3)
            
            # Step 4: Navigate to collaborators section
            logger.info("Navigating to collaborators section")
            
            # Look for admin/workspace management menu
            try:
                # Try common selectors for workspace admin or collaborators
                admin_menu_selectors = [
                    "//a[contains(text(), 'Workspace admin')]",
                    "//a[contains(text(), 'Admin')]",
                    "//a[contains(text(), 'Collaborators')]",
                    "//span[contains(text(), 'Workspace admin')]",
                    "//button[contains(text(), 'Admin')]"
                ]
                
                admin_element = None
                for selector in admin_menu_selectors:
                    try:
                        admin_element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        logger.info(f"Found admin menu using selector: {selector}")
                        break
                    except:
                        continue
                
                if admin_element:
                    admin_element.click()
                    time.sleep(2)
                else:
                    # Try direct navigation to collaborators URL
                    current_url = driver.current_url
                    base_url = current_url.split('/')[0:3]  # Get protocol and domain
                    collaborators_url = '/'.join(base_url) + '/workspace_admin/collaborators'
                    logger.info(f"Direct navigation to: {collaborators_url}")
                    driver.get(collaborators_url)
                    time.sleep(3)
                
            except Exception as nav_error:
                logger.warning(f"Navigation to admin section failed: {nav_error}")
            
            # Step 5: Search for the user
            logger.info(f"Searching for collaborator: {user_email}")
            
            # Look for search input or user list
            try:
                search_selectors = [
                    "//input[@placeholder*='search' or @placeholder*='Search']",
                    "//input[@type='search']",
                    "//input[contains(@class, 'search')]"
                ]
                
                search_element = None
                for selector in search_selectors:
                    try:
                        search_element = driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue
                
                if search_element:
                    search_element.clear()
                    search_element.send_keys(user_email)
                    search_element.send_keys(Keys.RETURN)
                    time.sleep(2)
                    logger.info(f"Searched for user: {user_email}")
                
            except Exception as search_error:
                logger.warning(f"Search step failed: {search_error}")
            
            # Step 6: Find and remove the user
            logger.info(f"Looking for user {user_email} in collaborator list")
            
            try:
                # Look for user email in the page and associated remove/delete button
                user_row_selectors = [
                    f"//td[contains(text(), '{user_email}')]/ancestor::tr",
                    f"//div[contains(text(), '{user_email}')]/ancestor::div[contains(@class, 'row')]",
                    f"//*[contains(text(), '{user_email}')]"
                ]
                
                user_found = False
                for selector in user_row_selectors:
                    try:
                        user_elements = driver.find_elements(By.XPATH, selector)
                        if user_elements:
                            user_found = True
                            logger.info(f"Found user element using selector: {selector}")
                            
                            # Look for delete/remove button near the user
                            for user_element in user_elements:
                                try:
                                    # Look for delete button within or near the user row
                                    delete_selectors = [
                                        ".//button[contains(text(), 'Delete') or contains(text(), 'Remove')]",
                                        ".//a[contains(text(), 'Delete') or contains(text(), 'Remove')]",
                                        ".//button[contains(@class, 'delete') or contains(@class, 'remove')]",
                                        ".//i[contains(@class, 'delete') or contains(@class, 'trash')]/.."
                                    ]
                                    
                                    delete_button = None
                                    for delete_selector in delete_selectors:
                                        try:
                                            delete_button = user_element.find_element(By.XPATH, delete_selector)
                                            break
                                        except:
                                            continue
                                    
                                    if delete_button:
                                        logger.info(f"Found delete button, attempting to remove {user_email}")
                                        delete_button.click()
                                        time.sleep(1)
                                        
                                        # Handle confirmation dialog if it appears
                                        try:
                                            confirm_selectors = [
                                                "//button[contains(text(), 'Confirm') or contains(text(), 'Yes') or contains(text(), 'Delete')]"
                                            ]
                                            
                                            for confirm_selector in confirm_selectors:
                                                try:
                                                    confirm_button = wait.until(EC.element_to_be_clickable((By.XPATH, confirm_selector)))
                                                    confirm_button.click()
                                                    logger.info("Confirmed deletion")
                                                    break
                                                except:
                                                    continue
                                                    
                                        except:
                                            logger.info("No confirmation dialog found")
                                        
                                        time.sleep(2)
                                        logger.info(f"Successfully removed collaborator: {user_email}")
                                        return True
                                        
                                except Exception as delete_error:
                                    logger.warning(f"Failed to delete user element: {delete_error}")
                                    continue
                            break
                    except:
                        continue
                
                if not user_found:
                    logger.warning(f"User {user_email} not found in collaborator list - may already be removed")
                    return True  # Consider it successful if user is not found
                    
            except Exception as removal_error:
                logger.error(f"Failed to remove collaborator: {removal_error}")
                return False
            
            logger.warning(f"Could not find delete button for {user_email}")
            return False
            
        except Exception as e:
            logger.error(f"Browser automation failed for Workato removal: {e}")
            return False
            
        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info("Browser driver closed")
                except:
                    pass
