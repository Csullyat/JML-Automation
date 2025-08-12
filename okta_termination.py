# okta_termination.py - Okta user termination and deactivation functionality

import logging
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import get_okta_domain, get_okta_token

logger = logging.getLogger(__name__)

class OktaTermination:
    """Enhanced Okta termination class with session clearing and security focus."""
    
    def __init__(self):
        """Initialize Okta termination client."""
        self.okta_token = get_okta_token()
        self.okta_domain = get_okta_domain()
        self.headers = {
            'Authorization': f'SSWS {self.okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def find_user_by_employee_id(self, employee_id: str) -> Optional[Dict]:
        """Find user by employee ID custom field."""
        try:
            # Search by employeeNumber field
            filter_query = f'profile.employeeNumber eq "{employee_id}"'
            
            response = requests.get(
                f"https://{self.okta_domain}/api/v1/users",
                headers=self.headers,
                params={'filter': filter_query},
                timeout=30
            )
            
            if response.status_code == 200:
                users = response.json()
                if users:
                    return users[0]  # Return first match
                return None
            else:
                logger.error(f"Error searching for employee {employee_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception finding employee {employee_id}: {e}")
            return None
    
    def clear_user_sessions(self, user_id: str) -> bool:
        """Clear all active sessions for immediate security."""
        try:
            response = requests.delete(
                f"https://{self.okta_domain}/api/v1/users/{user_id}/sessions",
                headers=self.headers,
                timeout=30
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error clearing sessions for {user_id}: {e}")
            return False
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account."""
        try:
            response = requests.post(
                f"https://{self.okta_domain}/api/v1/users/{user_id}/lifecycle/deactivate",
                headers=self.headers,
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False
    
    def remove_user_from_all_groups(self, user_id: str) -> Dict:
        """Remove user from all groups (except system groups)."""
        try:
            # Get user's groups
            response = requests.get(
                f"https://{self.okta_domain}/api/v1/users/{user_id}/groups",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return {'success': False, 'groups_removed': 0}
            
            groups = response.json()
            removed_count = 0
            
            for group in groups:
                group_name = group.get('profile', {}).get('name', '')
                
                # Skip system groups
                if 'Everyone' in group_name or 'OKTA' in group_name.upper():
                    continue
                
                # Remove from group
                remove_response = requests.delete(
                    f"https://{self.okta_domain}/api/v1/groups/{group['id']}/users/{user_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if remove_response.status_code == 204:
                    removed_count += 1
            
            return {'success': True, 'groups_removed': removed_count}
            
        except Exception as e:
            logger.error(f"Error removing user {user_id} from groups: {e}")
            return {'success': False, 'groups_removed': 0}
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address."""
        try:
            response = requests.get(
                f"https://{self.okta_domain}/api/v1/users/{email}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"User {email} not found in Okta")
                return None
            else:
                logger.error(f"Error getting user {email}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting user {email}: {e}")
            return None
    
    def execute_complete_termination(self, user_email: str) -> Dict:
        """
        Execute complete Okta termination for a user.
        
        Args:
            user_email: Email address of user to terminate
            
        Returns:
            Dict with termination results
        """
        logger.info(f"🔒 Starting Okta termination for {user_email}")
        
        start_time = datetime.now()
        actions_completed = []
        actions_failed = []
        warnings = []
        
        try:
            # Step 1: Find the user
            logger.info(f"Step 1: Looking up user {user_email}")
            user = self.get_user_by_email(user_email)
            
            if not user:
                return {
                    'success': False,
                    'user_email': user_email,
                    'error': 'User not found in Okta',
                    'actions_completed': actions_completed,
                    'actions_failed': ['User lookup failed'],
                    'warnings': warnings
                }
            
            user_id = user['id']
            user_name = user.get('profile', {}).get('displayName', user_email)
            user_status = user['status']
            
            logger.info(f"Found user: {user_name} (ID: {user_id}, Status: {user_status})")
            
            # Step 2: Clear all active sessions (CRITICAL for security)
            logger.info(f"Step 2: Clearing all active sessions for {user_email}")
            if self.clear_user_sessions(user_id):
                actions_completed.append("All active sessions cleared")
                logger.info("✅ All sessions cleared successfully")
            else:
                actions_failed.append("Failed to clear sessions")
                logger.error("❌ Failed to clear sessions - SECURITY RISK!")
            
            # Step 3: Remove from all groups
            logger.info(f"Step 3: Removing user from all groups")
            group_result = self.remove_user_from_all_groups(user_id)
            
            if group_result['success']:
                groups_removed = group_result['groups_removed']
                if groups_removed > 0:
                    actions_completed.append(f"Removed from {groups_removed} groups")
                    logger.info(f"✅ Removed from {groups_removed} groups")
                else:
                    actions_completed.append("No groups to remove")
                    logger.info("ℹ️ User was not in any removable groups")
            else:
                actions_failed.append("Failed to remove from groups")
                logger.error("❌ Failed to remove from groups")
            
            # Step 4: Deactivate user (if not already deactivated)
            if user_status not in ['DEPROVISIONED', 'SUSPENDED']:
                logger.info(f"Step 4: Deactivating user account")
                if self.deactivate_user(user_id):
                    actions_completed.append("User account deactivated")
                    logger.info("✅ User account deactivated")
                else:
                    actions_failed.append("Failed to deactivate user")
                    logger.error("❌ Failed to deactivate user")
            else:
                actions_completed.append(f"User already inactive (Status: {user_status})")
                logger.info(f"ℹ️ User already inactive (Status: {user_status})")
            
            # Determine overall success
            critical_failures = [f for f in actions_failed if 'sessions' in f or 'deactivate' in f]
            success = len(critical_failures) == 0
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'success': success,
                'user_email': user_email,
                'user_name': user_name,
                'user_id': user_id,
                'original_status': user_status,
                'actions_completed': actions_completed,
                'actions_failed': actions_failed,
                'warnings': warnings,
                'duration_seconds': duration,
                'start_time': start_time,
                'end_time': end_time
            }
            
            if success:
                logger.info(f"✅ Okta termination completed successfully for {user_email} in {duration:.1f}s")
            else:
                logger.warning(f"⚠️ Okta termination completed with issues for {user_email} in {duration:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Fatal error during Okta termination for {user_email}: {e}")
            
            return {
                'success': False,
                'user_email': user_email,
                'error': f"Fatal error: {str(e)}",
                'actions_completed': actions_completed,
                'actions_failed': actions_failed + [f"Fatal error: {str(e)}"],
                'warnings': warnings,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def test_user_lookup(self, user_email: str) -> Dict:
        """Test if user exists and connection is working."""
        try:
            user = self.get_user_by_email(user_email)
            
            if user:
                return {
                    'success': True,
                    'user_exists': True,
                    'user_id': user['id'],
                    'user_status': user['status'],
                    'user_name': user.get('profile', {}).get('displayName', user_email)
                }
            else:
                return {
                    'success': True,
                    'user_exists': False,
                    'message': 'User not found in Okta'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'user_exists': False
            }

def validate_okta_connection(okta_token: str) -> bool:
    """
    Validate connection to Okta by testing the API.
    
    Args:
        okta_token: Okta API token
        
    Returns:
        bool: True if connection is valid, False otherwise
    """
    try:
        okta_domain = get_okta_domain()
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Test with a simple API call
        response = requests.get(
            f"https://{okta_domain}/api/v1/users?limit=1",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("Okta connection validated successfully")
            return True
        else:
            logger.error(f"Okta connection failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error validating Okta connection: {str(e)}")
        return False

def find_okta_user(email: str, okta_token: str) -> Optional[Dict[str, Any]]:
    """
    Find a user in Okta by email address.
    
    Args:
        email: User's email address
        okta_token: Okta API token
        
    Returns:
        Dict containing user information if found, None otherwise
    """
    try:
        okta_domain = get_okta_domain()
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Search for user by email
        response = requests.get(
            f"https://{okta_domain}/api/v1/users/{email}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Found Okta user: {user_data.get('profile', {}).get('email', 'Unknown')}")
            return user_data
        elif response.status_code == 404:
            logger.warning(f"User not found in Okta: {email}")
            return None
        else:
            logger.error(f"Error finding user {email}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception finding user {email}: {str(e)}")
        return None

def deactivate_okta_user(user_id: str, okta_token: str) -> bool:
    """
    Deactivate a user in Okta.
    
    Args:
        user_id: Okta user ID
        okta_token: Okta API token
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        okta_domain = get_okta_domain()
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Deactivate user
        response = requests.post(
            f"https://{okta_domain}/api/v1/users/{user_id}/lifecycle/deactivate",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully deactivated user ID: {user_id}")
            return True
        else:
            logger.error(f"Failed to deactivate user {user_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception deactivating user {user_id}: {str(e)}")
        return False

def get_user_groups(user_id: str, okta_token: str) -> List[Dict[str, Any]]:
    """
    Get all groups that a user is a member of.
    
    Args:
        user_id: Okta user ID
        okta_token: Okta API token
        
    Returns:
        List of group dictionaries
    """
    try:
        okta_domain = get_okta_domain()
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Get user's groups
        response = requests.get(
            f"https://{okta_domain}/api/v1/users/{user_id}/groups",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            groups = response.json()
            logger.info(f"Found {len(groups)} groups for user {user_id}")
            return groups
        else:
            logger.error(f"Failed to get groups for user {user_id}: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Exception getting groups for user {user_id}: {str(e)}")
        return []

def clear_user_sessions(user_id: str, okta_token: str) -> bool:
    """
    Clear all active sessions for a user (critical security step for terminations).
    
    Args:
        user_id: Okta user ID
        okta_token: Okta API token
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        okta_domain = get_okta_domain()
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Clear all sessions for the user
        response = requests.delete(
            f"https://{okta_domain}/api/v1/users/{user_id}/sessions",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 204:
            logger.info(f"Successfully cleared all sessions for user {user_id}")
            return True
        else:
            logger.error(f"Failed to clear sessions for user {user_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception clearing sessions for user {user_id}: {str(e)}")
        return False

def remove_user_from_group(user_id: str, group_id: str, okta_token: str) -> bool:
    """
    Remove a user from a specific group.
    
    Args:
        user_id: Okta user ID
        group_id: Okta group ID
        okta_token: Okta API token
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        okta_domain = get_okta_domain()
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Remove user from group
        response = requests.delete(
            f"https://{okta_domain}/api/v1/groups/{group_id}/users/{user_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 204:
            logger.info(f"Successfully removed user {user_id} from group {group_id}")
            return True
        else:
            logger.error(f"Failed to remove user {user_id} from group {group_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception removing user {user_id} from group {group_id}: {str(e)}")
        return False

def terminate_okta_user(email: str, name: str, ticket_id: str, ticket_number: str, okta_token: str) -> Dict[str, Any]:
    """
    Complete termination process for a user in Okta.
    
    Args:
        email: User's email address
        name: User's display name
        ticket_id: Service desk ticket ID
        ticket_number: Service desk ticket number
        okta_token: Okta API token
        
    Returns:
        Dict containing termination results and actions taken
    """
    termination_start = datetime.now()
    actions_taken = []
    errors = []
    
    logger.info(f"Starting termination process for {name} ({email}) - Ticket #{ticket_number}")
    
    try:
        # Step 1: Find the user
        logger.info(f"Step 1: Finding user {email} in Okta...")
        user_data = find_okta_user(email, okta_token)
        
        if not user_data:
            error_msg = f"User {email} not found in Okta"
            logger.error(error_msg)
            return {
                'success': False,
                'email': email,
                'name': name,
                'ticket_number': ticket_number,
                'error': error_msg,
                'actions_taken': actions_taken,
                'duration': datetime.now() - termination_start
            }
        
        user_id = user_data['id']
        user_status = user_data['status']
        actions_taken.append(f"✅ Found user in Okta (ID: {user_id}, Status: {user_status})")
        
        # Step 2: Get user's groups before termination
        logger.info(f"Step 2: Getting group memberships for {email}...")
        user_groups = get_user_groups(user_id, okta_token)
        group_names = [group.get('profile', {}).get('name', 'Unknown') for group in user_groups]
        
        if user_groups:
            actions_taken.append(f"📋 Found {len(user_groups)} group memberships: {', '.join(group_names[:5])}")
            if len(group_names) > 5:
                actions_taken.append(f"    ... and {len(group_names) - 5} more groups")
        else:
            actions_taken.append("📋 No group memberships found")
        
        # Step 3: CRITICAL - Clear all active sessions immediately
        logger.info(f"Step 3: CLEARING ALL SESSIONS for {email} (SECURITY CRITICAL)...")
        if clear_user_sessions(user_id, okta_token):
            actions_taken.append("🔐 ALL ACTIVE SESSIONS CLEARED (Security Critical)")
        else:
            error_msg = "FAILED TO CLEAR SESSIONS - SECURITY RISK!"
            errors.append(error_msg)
            logger.error(error_msg)

        # Step 4: Remove from all groups (except system groups)
        logger.info(f"Step 4: Removing group memberships for {email}...")
        groups_removed = 0
        for group in user_groups:
            group_id = group['id']
            group_name = group.get('profile', {}).get('name', 'Unknown')
            
            # Skip system groups (typically start with "Everyone" or contain "OKTA")
            if 'Everyone' in group_name or 'OKTA' in group_name.upper():
                logger.info(f"Skipping system group: {group_name}")
                continue
            
            logger.info(f"Removing user from group: {group_name}")
            if remove_user_from_group(user_id, group_id, okta_token):
                groups_removed += 1
            else:
                errors.append(f"Failed to remove from group: {group_name}")
        
        if groups_removed > 0:
            actions_taken.append(f"🗑️  Removed from {groups_removed} groups")
        
        # Step 5: Deactivate the user (if not already deactivated)
        if user_status != 'DEPROVISIONED' and user_status != 'SUSPENDED':
            logger.info(f"Step 5: Deactivating user {email}...")
            if deactivate_okta_user(user_id, okta_token):
                actions_taken.append("🔒 User account deactivated")
            else:
                error_msg = "Failed to deactivate user account"
                errors.append(error_msg)
                logger.error(error_msg)
        else:
            actions_taken.append(f"ℹ️  User already inactive (Status: {user_status})")
        
        # Determine success
        success = len(errors) == 0
        termination_duration = datetime.now() - termination_start
        
        if success:
            logger.info(f"✅ Successfully terminated {name} ({email}) in {termination_duration}")
        else:
            logger.error(f"❌ Termination completed with errors for {name} ({email}): {', '.join(errors)}")
        
        return {
            'success': success,
            'email': email,
            'name': name,
            'ticket_number': ticket_number,
            'ticket_id': ticket_id,
            'user_id': user_id,
            'original_status': user_status,
            'groups_removed': groups_removed,
            'actions_taken': actions_taken,
            'errors': errors,
            'duration': termination_duration
        }
        
    except Exception as e:
        error_msg = f"Exception during termination: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'email': email,
            'name': name,
            'ticket_number': ticket_number,
            'error': error_msg,
            'actions_taken': actions_taken,
            'duration': datetime.now() - termination_start
        }
