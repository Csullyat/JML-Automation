"""
Okta service for user management.

This module handles all Okta operations including user creation,
group assignment, user termination, and employee ID lookups.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Iterable, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)


class OktaError(RuntimeError):
    pass


class OktaService:
    """
    Minimal Okta client used by termination/onboarding workflows.

    Requires:
      - OKTA_ORG_URL (e.g., https://your-org.okta.com)
      - OKTA_TOKEN   (SSWS token)
    """

    # Class-level caches for performance
    _group_name_id_cache: Dict[str, str] = {}
    _employee_id_cache: Dict[str, str] = {}  # employee_id -> email
    _user_cache: Dict[str, Dict[str, Any]] = {}  # email -> user object

    def __init__(self, base_url: str, token: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"SSWS {self.token}", "Accept": "application/json"},
            timeout=timeout,
        )

    @classmethod
    def from_env(cls) -> "OktaService":
        from jml_automation.config import Config
        config = Config()
        base = os.getenv("OKTA_ORG_URL") or config.okta_url or "https://filevine.okta.com"
        token = config.get_secret("OKTA_TOKEN")
        if not token:
            raise OktaError("Missing OKTA_TOKEN (not found in environment or 1Password)")
        return cls(base_url=base, token=token)

    @classmethod
    def from_config(cls) -> "OktaService":
        """Alias for from_env for compatibility."""
        return cls.from_env()

    # ---- HTTP helpers --------------------------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _get(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.get(path, **kwargs)
        if resp.status_code >= 400:
            raise OktaError(f"GET {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _post(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.post(path, **kwargs)
        if resp.status_code >= 400:
            raise OktaError(f"POST {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _put(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.put(path, **kwargs)
        if resp.status_code >= 400:
            raise OktaError(f"PUT {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _delete(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.delete(path, **kwargs)
        if resp.status_code >= 400:
            raise OktaError(f"DELETE {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    # ---- User Management ------------------------------------------------------

    def find_user_by_email(self, email: str) -> Optional[str]:
        """Return Okta user id for email, or None if not found."""
        # Check cache first
        email_lower = email.lower()
        if email_lower in self._user_cache:
            return self._user_cache[email_lower].get("id")
        
        # https://developer.okta.com/docs/reference/api/users/#list-users
        resp = self._get("/api/v1/users", params={"search": f'profile.email eq "{email_lower}"'})
        users = resp.json()
        if users:
            user = users[0]
            self._user_cache[email_lower] = user
            return user.get("id")
        return None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details by ID."""
        try:
            resp = self._get(f"/api/v1/users/{user_id}")
            user = resp.json()
            # Cache by email for future lookups
            email = user.get("profile", {}).get("email", "").lower()
            if email:
                self._user_cache[email] = user
            return user
        except OktaError as e:
            if "404" in str(e):
                return None
            raise

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get full user object by email."""
        # Check cache first
        email_lower = email.lower()
        if email_lower in self._user_cache:
            return self._user_cache[email_lower]
        
        user_id = self.find_user_by_email(email)
        if user_id:
            return self.get_user(user_id)
        return None

    def create_user(self, profile: dict, activate: bool = True) -> str:
        """Create a new Okta user. Returns user_id."""
        # https://developer.okta.com/docs/reference/api/users/#create-user-with-password
        params = {"activate": str(activate).lower()}
        resp = self._post("/api/v1/users", params=params, json={"profile": profile})
        user = resp.json()
        
        # Cache the new user
        email = profile.get("email", "").lower()
        if email:
            self._user_cache[email] = user
        
        return user["id"]

    def update_profile(self, user_id: str, profile: dict) -> None:
        """Update an Okta user's profile."""
        # https://developer.okta.com/docs/reference/api/users/#update-user
        self._post(f"/api/v1/users/{user_id}", json={"profile": profile})
        
        # Invalidate cache for this user
        # We could update the cache instead, but safer to invalidate
        for email, user in list(self._user_cache.items()):
            if user.get("id") == user_id:
                del self._user_cache[email]
                break

    def clear_sessions(self, user_id: str) -> None:
        """End all sessions for a user."""
        # https://developer.okta.com/docs/reference/api/sessions/#end-all-sessions-for-a-user
        self._delete(f"/api/v1/users/{user_id}/sessions")

    def deactivate_user(self, user_id: str) -> None:
        """Deactivate a user."""
        # https://developer.okta.com/docs/reference/api/users/#deactivate-user
        self._post(f"/api/v1/users/{user_id}/lifecycle/deactivate")

    # ---- Group Management -----------------------------------------------------

    def find_group_id(self, name: str) -> Optional[str]:
        """Find Okta group ID by name, with in-memory cache."""
        if name in self._group_name_id_cache:
            return self._group_name_id_cache[name]
        
        # https://developer.okta.com/docs/reference/api/groups/#list-groups
        resp = self._get("/api/v1/groups", params={"q": name})
        groups = resp.json()
        for group in groups:
            if group.get("profile", {}).get("name", "").lower() == name.lower():
                gid = group["id"]
                self._group_name_id_cache[name] = gid
                return gid
        return None

    def add_to_groups(self, user_id: str, group_ids: Iterable[str]) -> None:
        """Add user to one or more Okta groups."""
        # https://developer.okta.com/docs/reference/api/groups/#add-user-to-group
        for gid in group_ids:
            try:
                self._put(f"/api/v1/groups/{gid}/users/{user_id}")
                log.debug(f"Successfully added user to group {gid}")
            except OktaError as e:
                if "501" in str(e) or "E0000060" in str(e):
                    # This is likely a dynamic/rule-based group
                    log.info(f"Group {gid} is rule-based, user will be added automatically via rules")
                else:
                    raise

    def remove_from_groups(self, user_id: str, group_ids: Iterable[str]) -> None:
        """Remove user from one or more groups."""
        # https://developer.okta.com/docs/reference/api/groups/#remove-user-from-group
        for gid in group_ids:
            try:
                self._delete(f"/api/v1/groups/{gid}/users/{user_id}")
                log.debug(f"Removed user from group {gid}")
            except OktaError as e:
                if "404" in str(e):
                    log.debug(f"User not in group {gid}, skipping")
                else:
                    raise

    def remove_from_all_groups(self, user_id: str, skip_system_groups: bool = True) -> Dict[str, Any]:
        """
        Remove user from all groups.
        
        Args:
            user_id: Okta user ID
            skip_system_groups: If True, skip 'Everyone' and 'OKTA' groups
            
        Returns:
            Dict with success status and count of groups removed
        """
        try:
            user_groups = self.get_user_groups(user_id)
            group_ids = []
            skipped_groups = []
            
            for group in user_groups:
                group_name = group.get('profile', {}).get('name', '')
                group_id = group.get('id')
                
                # Skip system groups if requested
                if skip_system_groups and ('Everyone' in group_name or 'OKTA' in group_name.upper()):
                    skipped_groups.append(group_name)
                    continue
                    
                group_ids.append(group_id)
            
            # Remove from all non-system groups
            if group_ids:
                self.remove_from_groups(user_id, group_ids)
            
            return {
                'success': True,
                'groups_removed': len(group_ids),
                'groups_skipped': len(skipped_groups)
            }
            
        except Exception as e:
            log.error(f"Error removing user {user_id} from all groups: {e}")
            return {
                'success': False,
                'groups_removed': 0,
                'error': str(e)
            }

    def get_user_groups(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all groups for a user."""
        resp = self._get(f"/api/v1/users/{user_id}/groups")
        return resp.json()

    def is_user_in_group(self, user_id: str, group_name: str) -> bool:
        """Check if a user is in a specific group by group name."""
        try:
            user_groups = self.get_user_groups(user_id)
            for group in user_groups:
                if group.get('profile', {}).get('name') == group_name:
                    return True
            return False
        except Exception as e:
            log.error(f"Error checking if user {user_id} is in group {group_name}: {e}")
            return False

    def get_user_groups_by_names(self, user_id: str, group_names: list[str]) -> list[str]:
        """Get which groups from a list the user is actually in."""
        try:
            user_groups = self.get_user_groups(user_id)
            user_group_names = [group.get('profile', {}).get('name') for group in user_groups]
            return [name for name in group_names if name in user_group_names]
        except Exception as e:
            log.error(f"Error getting user groups for {user_id}: {e}")
            return []

    # ---- Employee ID Lookup (Enhanced from ticket_processor.py) --------------

    def lookup_email_by_employee_id(self, employee_id: str) -> Optional[str]:
        """
        Lookup user email by employee ID.
        Searches for users with employeeNumber matching the given ID.
        Results are cached for performance.
        """
        if not employee_id:
            return None
        
        # Check cache first
        if employee_id in self._employee_id_cache:
            return self._employee_id_cache[employee_id]
        
        try:
            # Search by employeeNumber field
            # https://developer.okta.com/docs/reference/api/users/#list-users-with-search
            search_query = f'profile.employeeNumber eq "{employee_id}"'
            resp = self._get("/api/v1/users", params={"search": search_query})
            users = resp.json()
            
            if users:
                email = users[0].get("profile", {}).get("email", "").lower()
                if email:
                    self._employee_id_cache[employee_id] = email
                    # Also cache the full user object
                    self._user_cache[email] = users[0]
                    log.info(f"Found email {email} for employee ID {employee_id}")
                    return email
            
            log.warning(f"No user found with employee ID {employee_id}")
            return None
            
        except Exception as e:
            log.error(f"Error looking up employee ID {employee_id}: {e}")
            return None

    def search_users(self, query: str, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Search for users using Okta's search syntax.
        Returns list of user objects.
        """
        resp = self._get("/api/v1/users", params={"search": query, "limit": str(limit)})
        return resp.json()

    # ---- Utility Methods ------------------------------------------------------

    def test_user_lookup(self, user_email: str) -> Dict[str, Any]:
        """
        Test if user exists and get basic info.
        Useful for validation before operations.
        
        Args:
            user_email: Email address to test
            
        Returns:
            Dict with lookup results
        """
        try:
            user = self.get_user_by_email(user_email)
            
            if user:
                return {
                    'success': True,
                    'user_exists': True,
                    'user_id': user['id'],
                    'user_status': user['status'],
                    'user_name': user.get('profile', {}).get('displayName', user_email),
                    'groups_count': len(self.get_user_groups(user['id']))
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

    def validate_connection(self) -> bool:
        """
        Validate Okta connection and credentials.
        Enhanced version that tests actual API access.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to fetch a single user to validate API access
            resp = self._get("/api/v1/users", params={"limit": "1"})
            if resp.status_code == 200:
                log.info("Okta connection validated successfully")
                return True
            else:
                log.error(f"Okta connection validation failed: {resp.status_code}")
                return False
        except Exception as e:
            log.error(f"Okta connection validation error: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test the Okta connection.
        Alias for validate_connection for backward compatibility.
        """
        return self.validate_connection()

    def clear_caches(self) -> None:
        """Clear all internal caches. Useful for long-running processes."""
        self._group_name_id_cache.clear()
        self._employee_id_cache.clear()
        self._user_cache.clear()
        log.info("Cleared all Okta service caches")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cached data."""
        return {
            "cached_groups": len(self._group_name_id_cache),
            "cached_employee_ids": len(self._employee_id_cache),
            "cached_users": len(self._user_cache)
        }