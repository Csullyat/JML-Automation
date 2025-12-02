"""
Okta service for user management.

This module handles all Okta operations including user creation,
group assignment, user termination, and employee ID lookups.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Iterable, Dict, Any, List
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

    def is_partner_user(self, user_id: str) -> bool:
        """Check if a user is a partner user (member of any Partner - * group)."""
        try:
            user_groups = self.get_user_groups(user_id)
            for group in user_groups:
                group_name = group.get('profile', {}).get('name', '')
                if group_name.startswith('Partner - '):
                    return True
            return False
        except Exception as e:
            log.error(f"Error checking if user {user_id} is a partner: {e}")
            return False

    def is_partner_user_by_email(self, email: str) -> bool:
        """Check if a user is a partner user by email address."""
        user_id = self.find_user_by_email(email)
        if user_id:
            return self.is_partner_user(user_id)
        return False

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

    # ---- Partner Organization Management ---------------------------------------

    def create_partner_organization(self, partner_name: str, needs_knowbe4: bool = False) -> Dict[str, Any]:
        """
        Create a complete partner organization setup in Okta.
        This includes:
        1. Partner group (Partner - Partnername)
        2. Zscaler group (SSO-Zscaler_ZPA_Partner_Partnername)
        3. Assignment rule for automatic group membership
        4. Assignment of Zscaler group to Zscaler ZPA application
        
        Args:
            partner_name: Name of the partner organization
            needs_knowbe4: Whether to include KnowBe4 access
            
        Returns:
            Dict with creation results and group IDs
        """
        results = {
            'success': True,
            'partner_name': partner_name,
            'groups_created': [],
            'rule_created': None,
            'app_assignment_created': False,
            'errors': []
        }
        
        try:
            # Clean partner name for group naming (remove spaces, special chars)
            clean_partner_name = partner_name.replace(' ', '').replace('-', '').replace('_', '')
            
            # 1. Create main partner group
            partner_group_name = f"Partner - {partner_name}"
            partner_group_id = self._create_group(partner_group_name, f"SSO for {partner_name}")
            if partner_group_id:
                results['groups_created'].append({
                    'name': partner_group_name,
                    'id': partner_group_id,
                    'type': 'partner'
                })
            
            # 2. Create Zscaler group
            zscaler_group_name = f"SSO-Zscaler_ZPA_Partner_{clean_partner_name}"
            zscaler_group_id = self._create_group(zscaler_group_name, f"Partnership group for {partner_name} to grant Zscaler ZPA Access")
            if zscaler_group_id:
                results['groups_created'].append({
                    'name': zscaler_group_name,
                    'id': zscaler_group_id,
                    'type': 'zscaler'
                })
            
            # 3. Assign Zscaler group to Zscaler ZPA application
            if zscaler_group_id:
                zpa_app_assignment = self._assign_group_to_zscaler_zpa(zscaler_group_id, zscaler_group_name)
                results['app_assignment_created'] = zpa_app_assignment
            
            # 4. Create group assignment rule
            if partner_group_id and zscaler_group_id:
                rule_groups = [
                    zscaler_group_name,
                    "SSO-SolarWinds_User",
                    "SSO-Zscaler_ZIA_Users",
                    "Partner Access"
                ]
                
                if needs_knowbe4:
                    rule_groups.append("SSO-KnowBe4")
                
                rule_id = self._create_partner_assignment_rule(
                    partner_name, 
                    partner_group_name, 
                    rule_groups
                )
                if rule_id:
                    results['rule_created'] = {
                        'id': rule_id,
                        'name': f"Partner {partner_name} Assignments",
                        'groups': rule_groups
                    }
            
            log.info(f"Successfully created partner organization for {partner_name}")
            return results
            
        except Exception as e:
            log.error(f"Error creating partner organization {partner_name}: {e}")
            results['success'] = False
            results['errors'].append(str(e))
            return results

    def _create_group(self, name: str, description: str) -> Optional[str]:
        """
        Create a new Okta group.
        
        Args:
            name: Group name
            description: Group description
            
        Returns:
            Group ID if successful, None otherwise
        """
        try:
            # Check if group already exists
            existing_id = self.find_group_id(name)
            if existing_id:
                log.info(f"Group '{name}' already exists with ID {existing_id}")
                return existing_id
            
            # Create new group
            group_data = {
                "profile": {
                    "name": name,
                    "description": description
                }
            }
            
            resp = self._post("/api/v1/groups", json=group_data)
            group = resp.json()
            group_id = group["id"]
            
            # Cache the new group
            self._group_name_id_cache[name] = group_id
            
            log.info(f"Created group '{name}' with ID {group_id}")
            return group_id
            
        except Exception as e:
            log.error(f"Error creating group '{name}': {e}")
            return None

    def _assign_group_to_zscaler_zpa(self, group_id: str, group_name: str) -> bool:
        """
        Assign a group to the Zscaler ZPA application.
        
        Args:
            group_id: Okta group ID
            group_name: Group name for logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find Zscaler ZPA application
            zpa_app_id = self._find_application_id("Zscaler ZPA")
            if not zpa_app_id:
                log.error("Zscaler ZPA application not found")
                return False
            
            # Try different assignment methods
            assignment_data = {
                "id": group_id,
                "priority": 0
            }
            
            try:
                # Try PUT first (most common for app assignments)
                resp = self._put(f"/api/v1/apps/{zpa_app_id}/groups/{group_id}", json=assignment_data)
            except Exception as put_error:
                log.warning(f"PUT method failed, trying POST: {put_error}")
                # Fallback to POST if PUT fails
                resp = self._post(f"/api/v1/apps/{zpa_app_id}/groups", json=assignment_data)
            
            log.info(f"Assigned group '{group_name}' to Zscaler ZPA application")
            return True
            
        except Exception as e:
            log.error(f"Error assigning group '{group_name}' to Zscaler ZPA: {e}")
            # Don't fail the entire partner creation if ZPA assignment fails
            log.warning(f"ZPA assignment failed, but continuing with partner setup")
            return False

    def _find_application_id(self, app_name: str) -> Optional[str]:
        """
        Find Okta application ID by name.
        
        Args:
            app_name: Application name to search for
            
        Returns:
            Application ID if found, None otherwise
        """
        try:
            resp = self._get("/api/v1/apps", params={"q": app_name})
            apps = resp.json()
            
            for app in apps:
                if app_name.lower() in app.get("label", "").lower():
                    return app["id"]
            
            return None
            
        except Exception as e:
            log.error(f"Error finding application '{app_name}': {e}")
            return None

    def _create_partner_assignment_rule(self, partner_name: str, partner_group_name: str, target_groups: List[str]) -> Optional[str]:
        """
        Create a group assignment rule for partner organization.
        
        Args:
            partner_name: Partner organization name
            partner_group_name: Name of the partner group
            target_groups: List of groups to assign when rule triggers
            
        Returns:
            Rule ID if successful, None otherwise
        """
        try:
            # Get partner group ID
            partner_group_id = self.find_group_id(partner_group_name)
            if not partner_group_id:
                log.error(f"Partner group '{partner_group_name}' not found")
                return None
            
            # Get target group IDs
            target_group_ids = []
            for group_name in target_groups:
                group_id = self.find_group_id(group_name)
                if group_id:
                    target_group_ids.append(group_id)
                else:
                    log.warning(f"Target group '{group_name}' not found, skipping")
            
            if not target_group_ids:
                log.error("No valid target groups found for rule creation")
                return None
            
            # Create rule data - using the working simple format
            rule_data = {
                "type": "group_rule",
                "name": f"Partner {partner_name} Assignments",
                "status": "INACTIVE",  # Create inactive, will be activated separately
                "conditions": {
                    "expression": {
                        "value": f"isMemberOfGroup(\"{partner_group_id}\")",
                        "type": "urn:okta:expression:1.0"
                    }
                },
                "actions": {
                    "assignUserToGroups": {
                        "groupIds": target_group_ids
                    }
                }
            }
            
            resp = self._post("/api/v1/groups/rules", json=rule_data)
            rule = resp.json()
            rule_id = rule["id"]
            
            # Activate the rule
            self._post(f"/api/v1/groups/rules/{rule_id}/lifecycle/activate")
            
            log.info(f"Created and activated partner assignment rule for {partner_name}")
            return rule_id
            
        except Exception as e:
            log.error(f"Error creating partner assignment rule for {partner_name}: {e}")
            return None

    def create_partner_user(self, partner_email: str, partner_name: str, filevine_email: str, partner_company: str) -> Optional[str]:
        """
        Create a new partner user in Okta.
        
        Args:
            partner_email: Partner's external email address
            partner_name: Partner's full name (First Last)
            filevine_email: New Filevine email address for the partner
            partner_company: Partner's company name
            
        Returns:
            User ID if successful, None otherwise
        """
        try:
            # Parse name
            first_name, last_name = self._split_name(partner_name)
            
            # Create user profile
            profile = {
                "firstName": first_name,
                "lastName": last_name,
                "email": filevine_email,  # Primary email is the new Filevine email
                "login": filevine_email,
                "displayName": partner_name,
                "title": f"{partner_company} - Partner",  # Format: "Company - Partner"
                "department": partner_company,  # Department field set to partner company
                "secondEmail": partner_email,  # Store original partner email as secondary
                "swrole": "Requester",  # Set to Requester for all partner users
                "preferredLanguage": "en",
                "primary": False  # Set to False for partner users
            }
            
            user_id = self.create_user(profile, activate=True)
            
            if user_id:
                log.info(f"Created partner user {partner_name} ({filevine_email}) for company {partner_company}")
                
                # Add to partner group
                partner_group_name = f"Partner - {partner_company}"
                partner_group_id = self.find_group_id(partner_group_name)
                if partner_group_id:
                    self.add_to_groups(user_id, [partner_group_id])
                    log.info(f"Added partner user to group {partner_group_name}")
                else:
                    log.warning(f"Partner group {partner_group_name} not found")
            
            return user_id
            
        except Exception as e:
            log.error(f"Error creating partner user {partner_name}: {e}")
            return None

    def _split_name(self, full_name: Optional[str]) -> tuple[str, str]:
        """Helper function to split full name into first and last name."""
        full_name = (full_name or "").strip()
        if not full_name:
            return "", ""
        parts = full_name.split()
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
        return parts[0], ""