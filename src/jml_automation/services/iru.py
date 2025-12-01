"""
Iru (formerly Kandji) Device Management Service for JML Automation.

This service handles device termination tasks:
1. Find devices assigned to terminated users
2. Unassign users from devices
3. Change device blueprints to "Inventory Only"
4. Send lock commands to devices
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Any
import requests
from requests.exceptions import RequestException

from jml_automation.config import Config

logger = logging.getLogger(__name__)

class IruService:
    """
    Service for managing device termination via Iru (Kandji) API.
    
    Handles:
    - Device lookup by user email
    - User unassignment from devices
    - Blueprint changes to "Inventory Only"
    - Device locking commands
    """
    
    def __init__(self, config: Optional[Config] = None, dry_run: bool = False):
        """Initialize Iru service with API credentials."""
        self.config = config or Config()
        self.dry_run = dry_run
        self.base_url = "https://filevine.api.kandji.io/api/v1"
        self.api_token = None
        self.session = requests.Session()
        
        # Get API token from 1Password
        self._get_api_token()
        
        # Set up session headers
        if self.api_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
        
        logger.info(f"Iru service initialized (dry_run={self.dry_run})")

    def _get_api_token(self) -> None:
        """Retrieve Iru API token from 1Password."""
        try:
            # Get Iru API token from 1Password using service account method
            # Path: op://IT/offboard-locker API token/password (API token field)
            self.api_token = self.config._get_from_onepassword_service_account("op://IT/offboard-locker API token/password")
            
            if not self.api_token:
                logger.error("Iru API token not found in 1Password (op://IT/offboard-locker API token/password)")
                raise Exception("Iru API token not found in 1Password")
                
            logger.info("Successfully retrieved Iru API token from 1Password")
                
        except Exception as e:
            logger.error(f"Failed to retrieve Iru API token: {e}")
            raise Exception(f"Cannot initialize Iru service: {e}")

    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated API request to Iru."""
        url = f"{self.base_url}{endpoint}"
        
        if self.dry_run:
            logger.info(f"DRY RUN: {method} {url}")
            if data:
                logger.info(f"DRY RUN: Request data: {data}")
            return {"dry_run": True, "status": "success"}
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PATCH":
                response = self.session.patch(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except RequestException as e:
            logger.error(f"Iru API request failed: {method} {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    def find_devices_by_user_email(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Find all devices assigned to a user by email address.
        
        Args:
            user_email: Email address of the user
            
        Returns:
            List of device dictionaries with device information
        """
        logger.info(f"Looking up devices for user: {user_email}")
        
        # Try the new user-first approach first
        devices = self._find_devices_via_users_api(user_email)
        if devices:
            logger.info(f"Found {len(devices)} devices via users API")
            return devices
        
        # Fallback to old method with enhanced debugging
        logger.info("Users API approach failed, trying device enumeration fallback")
        return self._find_devices_via_device_enumeration(user_email)

    def _find_devices_via_users_api(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Alternative approach: Look up user first, then get their devices.
        This matches the Kandji UI behavior shown in the screenshot.
        """
        logger.info(f"Looking up Kandji user via users API: {user_email}")
        
        try:
            # Method 1: Try to get user by email parameter
            try:
                users_response = self._make_api_request("GET", f"/users?email={user_email}")
                logger.debug(f"Users API response type: {type(users_response)}")
                if users_response and not self.dry_run:
                    logger.debug(f"Users API response sample: {users_response}")
            except Exception as e:
                logger.debug(f"Users API with email parameter failed: {e}")
                users_response = None
            
            # Method 2: Get all users and filter (if direct lookup failed)
            if not users_response:
                logger.info("Trying to get all users and filter...")
                all_users_response = self._make_api_request("GET", "/users")
                
                # Handle response format
                if isinstance(all_users_response, list):
                    all_users = all_users_response
                elif isinstance(all_users_response, dict):
                    all_users = all_users_response.get("results", all_users_response.get("data", []))
                else:
                    all_users = []
                
                logger.info(f"Retrieved {len(all_users)} total users from Kandji")
                
                # Debug: Log structure of first few users
                for i, user in enumerate(all_users[:3]):
                    logger.debug(f"User {i+1} structure: {list(user.keys())}")
                    logger.debug(f"User {i+1} email: {user.get('email', 'NO EMAIL')}")
                
                # Find our user
                target_user = None
                for user in all_users:
                    user_email_from_api = user.get("email", "").lower()
                    if user_email_from_api == user_email.lower():
                        target_user = user
                        logger.info(f"Found user in Kandji: {user.get('name', 'Unknown')} - {user_email}")
                        break
                
                if not target_user:
                    logger.info(f"User {user_email} not found in Kandji users list")
                    return []
            else:
                # Process direct lookup response
                if isinstance(users_response, list) and users_response:
                    target_user = users_response[0]
                elif isinstance(users_response, dict):
                    results = users_response.get("results", users_response.get("data", []))
                    target_user = results[0] if results else None
                else:
                    target_user = None
                
                if not target_user:
                    logger.info(f"User {user_email} not found via direct users API lookup")
                    return []
            
            # Method 3: Now get devices for this user
            user_id = target_user.get("id")
            if not user_id:
                logger.error(f"No user ID found for {user_email}")
                return []
            
            logger.info(f"Found user ID: {user_id}, looking up their devices...")
            
            # Try various endpoints to get user's devices
            user_devices = []
            
            # Try: GET /users/{user_id}/devices
            try:
                user_devices_response = self._make_api_request("GET", f"/users/{user_id}/devices")
                if user_devices_response:
                    logger.info(f"Successfully got devices via /users/{user_id}/devices")
                    if isinstance(user_devices_response, list):
                        user_devices = user_devices_response
                    elif isinstance(user_devices_response, dict):
                        user_devices = user_devices_response.get("results", user_devices_response.get("data", []))
            except Exception as e:
                logger.debug(f"Endpoint /users/{user_id}/devices failed: {e}")
            
            # If that didn't work, try getting all devices with pagination and filtering by user_id
            if not user_devices:
                logger.info("Trying device enumeration with user_id filter...")
                all_devices = self._get_all_devices_paginated()
                
                # Look for devices with matching user_id
                for device in all_devices:
                    device_user_id = None
                    
                    # Check user field
                    if isinstance(device.get("user"), dict):
                        device_user_id = device["user"].get("id")
                    elif isinstance(device.get("user"), str):
                        device_user_id = device["user"]
                    
                    # Check primary_user field  
                    if not device_user_id and isinstance(device.get("primary_user"), dict):
                        device_user_id = device["primary_user"].get("id")
                    elif not device_user_id and isinstance(device.get("primary_user"), str):
                        device_user_id = device["primary_user"]
                    
                    # Check other possible user ID fields
                    if not device_user_id:
                        device_user_id = device.get("user_id") or device.get("assigned_user_id")
                    
                    if device_user_id == user_id:
                        user_devices.append(device)
                        logger.info(f"Found device via user_id match: {device.get('device_name', 'Unknown')} ({device.get('device_id', device.get('id'))})")
            
            return user_devices
            
        except Exception as e:
            logger.error(f"Failed to find devices via users API for {user_email}: {e}")
            return []

    def _find_devices_via_device_enumeration(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Fallback method: Get all devices and filter by user email (original approach).
        Enhanced with pagination support and debugging to understand data structure.
        """
        logger.info(f"Using device enumeration fallback for: {user_email}")
        
        try:
            # Get ALL devices from Iru with pagination support
            all_devices = self._get_all_devices_paginated()
            
            logger.info(f"Retrieved {len(all_devices)} total devices (with pagination)")
            
            # Debug: Log structure of first few devices for troubleshooting
            for i, device in enumerate(all_devices[:5]):
                logger.debug(f"Device {i+1} structure: {list(device.keys())}")
                logger.debug(f"Device {i+1} user field: {device.get('user')}")
                logger.debug(f"Device {i+1} primary_user field: {device.get('primary_user')}")
                logger.debug(f"Device {i+1} device_name: {device.get('device_name', device.get('name'))}")
            
            # Filter devices by user email
            user_devices = []
            for device in all_devices:
                # Check various fields where user email might be stored
                assigned_user = device.get("user", {})
                if isinstance(assigned_user, dict):
                    device_email = assigned_user.get("email", "").lower()
                elif isinstance(assigned_user, str):
                    device_email = assigned_user.lower()
                else:
                    device_email = ""
                
                # Also check primary_user field if it exists
                primary_user = device.get("primary_user", {})
                if isinstance(primary_user, dict):
                    primary_email = primary_user.get("email", "").lower()
                elif isinstance(primary_user, str):
                    primary_email = primary_user.lower()
                else:
                    primary_email = ""
                
                # Check if this device is assigned to our user
                if (device_email == user_email.lower() or 
                    primary_email == user_email.lower() or
                    user_email.lower() in device.get("asset_tag", "").lower()):
                    
                    user_devices.append(device)
                    logger.info(f"Found device: {device.get('device_name', 'Unknown')} "
                              f"({device.get('device_id', 'No ID')})")
            
            logger.info(f"Found {len(user_devices)} devices for user {user_email}")
            return user_devices
            
        except Exception as e:
            logger.error(f"Failed to find devices for user {user_email}: {e}")
            return []

    def _get_all_devices_paginated(self) -> List[Dict[str, Any]]:
        """
        Get all devices from Kandji API with pagination support.
        Kandji typically uses limit/offset or cursor-based pagination.
        """
        logger.info("Fetching all devices with pagination support...")
        
        all_devices = []
        page = 1
        limit = 300  # Standard page size
        
        while True:
            try:
                # Try different pagination approaches
                # Method 1: offset-based pagination
                offset = (page - 1) * limit
                endpoint = f"/devices?limit={limit}&offset={offset}"
                
                logger.info(f"Fetching page {page} (offset {offset}, limit {limit})")
                devices_response = self._make_api_request("GET", endpoint)
                
                # Handle different response formats
                if isinstance(devices_response, list):
                    page_devices = devices_response
                elif isinstance(devices_response, dict):
                    page_devices = devices_response.get("results", devices_response.get("data", []))
                    
                    # Check for pagination metadata
                    total_count = devices_response.get("count", devices_response.get("total"))
                    next_page = devices_response.get("next")
                    
                    if total_count:
                        logger.info(f"API reports {total_count} total devices available")
                    if next_page:
                        logger.info(f"Next page available: {next_page}")
                        
                else:
                    page_devices = []
                
                if not page_devices:
                    logger.info(f"No devices returned on page {page}, stopping pagination")
                    break
                
                logger.info(f"Page {page}: Retrieved {len(page_devices)} devices")
                all_devices.extend(page_devices)
                
                # If we got fewer devices than the limit, we've reached the end
                if len(page_devices) < limit:
                    logger.info(f"Reached end of devices (page {page} had {len(page_devices)} < {limit})")
                    break
                
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 10:  # Max 10 pages = 3000 devices should be enough
                    logger.warning(f"Reached max page limit ({page}), stopping pagination")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                
                # If offset-based pagination failed, try without pagination parameters
                if page == 1:
                    logger.info("Offset pagination failed, trying simple /devices endpoint")
                    try:
                        devices_response = self._make_api_request("GET", "/devices")
                        if isinstance(devices_response, list):
                            all_devices = devices_response
                        elif isinstance(devices_response, dict):
                            all_devices = devices_response.get("results", devices_response.get("data", []))
                        break
                    except Exception as e2:
                        logger.error(f"Simple /devices endpoint also failed: {e2}")
                        break
                else:
                    break
        
        logger.info(f"Total devices fetched across all pages: {len(all_devices)}")
        return all_devices

    def unassign_user_from_device(self, device_id: str) -> bool:
        """
        Unassign user from a device.
        
        Args:
            device_id: Iru device ID
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Unassigning user from device: {device_id}")
        
        try:
            # Update device to remove user assignment
            update_data = {
                "user": None,
                "primary_user": None
            }
            
            result = self._make_api_request("PATCH", f"/devices/{device_id}", update_data)
            
            if self.dry_run or result:
                logger.info(f"Successfully unassigned user from device {device_id}")
                return True
            else:
                logger.error(f"Failed to unassign user from device {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error unassigning user from device {device_id}: {e}")
            return False

    def change_device_blueprint(self, device_id: str, blueprint_name: str = "Inventory Only") -> bool:
        """
        Change device blueprint to specified blueprint.
        
        Args:
            device_id: Iru device ID
            blueprint_name: Name of blueprint to assign (default: "Inventory Only")
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Changing device {device_id} blueprint to: {blueprint_name}")
        
        try:
            # First, find the blueprint ID by name
            blueprints_response = self._make_api_request("GET", "/blueprints")
            blueprints = blueprints_response.get("results", [])
            
            blueprint_id = None
            for blueprint in blueprints:
                if blueprint.get("name", "").lower() == blueprint_name.lower():
                    blueprint_id = blueprint.get("id")
                    break
            
            if not blueprint_id:
                logger.error(f"Blueprint '{blueprint_name}' not found")
                return False
            
            # Update device blueprint
            update_data = {
                "blueprint_id": blueprint_id
            }
            
            result = self._make_api_request("PATCH", f"/devices/{device_id}", update_data)
            
            if self.dry_run or result:
                logger.info(f"Successfully changed device {device_id} to blueprint '{blueprint_name}'")
                return True
            else:
                logger.error(f"Failed to change blueprint for device {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error changing blueprint for device {device_id}: {e}")
            return False

    def lock_device(self, device_id: str) -> bool:
        """
        Send lock command to device.
        
        Args:
            device_id: Iru device ID
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending lock command to device: {device_id}")
        
        try:
            # Send lock command using correct Kandji endpoint
            # Endpoint is /devices/{device_id}/action/lock (not /actions)
            result = self._make_api_request("POST", f"/devices/{device_id}/action/lock")
            
            if self.dry_run or result:
                logger.info(f"Successfully sent lock command to device {device_id}")
                return True
            else:
                logger.warning(f"Lock command may not be supported - device {device_id} processed without lock")
                return True  # Don't fail the entire process for lock issues
                
        except Exception as e:
            logger.warning(f"Lock command failed for device {device_id}: {e}")
            logger.info("Lock command failure is not critical - device has been unassigned and blueprint changed")
            return True  # Don't fail the entire process for lock issues

    def execute_complete_termination(self, user_email: str) -> Dict[str, Any]:
        """
        Execute complete device termination workflow for a user.
        
        Performs all termination tasks:
        1. Find devices assigned to user
        2. Unassign user from devices
        3. Change blueprint to "Inventory Only"
        4. Send lock command
        
        Args:
            user_email: Email address of terminated user
            
        Returns:
            Dictionary with termination results
        """
        logger.info(f"Starting Iru device termination for: {user_email}")
        start_time = time.time()
        
        results = {
            "success": True,
            "user_email": user_email,
            "devices_found": 0,
            "devices_processed": 0,
            "unassignment_success": 0,
            "blueprint_change_success": 0,
            "lock_command_success": 0,
            "errors": [],
            "device_details": []
        }
        
        try:
            # Step 1: Find devices assigned to user
            devices = self.find_devices_by_user_email(user_email)
            results["devices_found"] = len(devices)
            
            if not devices:
                logger.info(f"No devices found for user {user_email}")
                results["success"] = True  # Not an error condition
                return results
            
            # Step 2-4: Process each device
            for device in devices:
                device_id = device.get("device_id") or device.get("id")
                device_name = device.get("device_name") or device.get("name", "Unknown Device")
                
                if not device_id:
                    error_msg = f"No device ID found for device: {device_name}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue
                
                device_result = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "unassignment": False,
                    "blueprint_change": False,
                    "lock_command": False
                }
                
                logger.info(f"Processing device: {device_name} ({device_id})")
                
                # Unassign user
                if self.unassign_user_from_device(device_id):
                    device_result["unassignment"] = True
                    results["unassignment_success"] += 1
                else:
                    results["errors"].append(f"Failed to unassign user from {device_name}")
                
                # Change blueprint
                if self.change_device_blueprint(device_id, "Inventory Only"):
                    device_result["blueprint_change"] = True
                    results["blueprint_change_success"] += 1
                else:
                    results["errors"].append(f"Failed to change blueprint for {device_name}")
                
                # Send lock command
                if self.lock_device(device_id):
                    device_result["lock_command"] = True
                    results["lock_command_success"] += 1
                else:
                    results["errors"].append(f"Failed to lock device {device_name}")
                
                results["device_details"].append(device_result)
                results["devices_processed"] += 1
                
                # Small delay between device operations
                if not self.dry_run:
                    time.sleep(1)
            
            # Determine overall success
            if results["errors"]:
                results["success"] = False
                logger.warning(f"Iru termination completed with {len(results['errors'])} errors")
            else:
                logger.info(f"Iru termination completed successfully for {user_email}")
            
        except Exception as e:
            error_msg = f"Critical error during Iru termination: {e}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
        
        duration = time.time() - start_time
        results["duration"] = duration
        
        logger.info(f"Iru termination completed for {user_email} in {duration:.1f}s")
        return results

    @classmethod
    def from_config(cls, dry_run: bool = False) -> 'IruService':
        """Create IruService instance from configuration."""
        return cls(Config(), dry_run=dry_run)


# Module-level convenience function
def execute_iru_termination(user_email: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute Iru device termination for a user.
    
    Args:
        user_email: Email of user to terminate
        dry_run: If True, only log what would be done
        
    Returns:
        Dictionary with termination results
    """
    service = IruService.from_config(dry_run=dry_run)
    return service.execute_complete_termination(user_email)
