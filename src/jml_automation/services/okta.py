"""
Okta service for user management.

This module handles all Okta operations including user creation,
group assignment, and user termination.
"""

from __future__ import annotations

import os
from typing import Optional, Iterable
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class OktaError(RuntimeError):
    pass


class OktaService:

    _group_name_id_cache = {}

    def create_user(self, profile: dict, activate: bool = True) -> str:
        """Create a new Okta user. Returns user_id."""
        # https://developer.okta.com/docs/reference/api/users/#create-user-with-password
        params = {"activate": str(activate).lower()}
        resp = self._post("/api/v1/users", params=params, json={"profile": profile})
        user = resp.json()
        return user["id"]

    def update_profile(self, user_id: str, profile: dict) -> None:
        """Update an Okta user's profile."""
        # https://developer.okta.com/docs/reference/api/users/#update-user
        self.client.post(f"/api/v1/users/{user_id}", json={"profile": profile})

    def find_group_id(self, name: str) -> Optional[str]:
        """Find Okta group ID by name, with in-memory cache."""
        cache = self._group_name_id_cache
        if name in cache:
            return cache[name]
        # https://developer.okta.com/docs/reference/api/groups/#list-groups
        resp = self._get("/api/v1/groups", params={"q": name})
        groups = resp.json()
        for group in groups:
            if group.get("profile", {}).get("name", "").lower() == name.lower():
                gid = group["id"]
                cache[name] = gid
                return gid
        return None

    def add_to_groups(self, user_id: str, group_ids: Iterable[str]) -> None:
        """Add user to one or more Okta groups."""
        # https://developer.okta.com/docs/reference/api/groups/#add-user-to-group
        for gid in group_ids:
            try:
                self._put(f"/api/v1/groups/{gid}/users/{user_id}")
                print(f"DEBUG: Successfully added user to group {gid}")
            except OktaError as e:
                if "501" in str(e) or "E0000060" in str(e):
                    # This is likely a dynamic/rule-based group
                    print(f"DEBUG: Group {gid} appears to be rule-based (assignment handled automatically)")
                    import logging
                    log = logging.getLogger("okta")
                    log.info(f"Group {gid} is rule-based, user will be added automatically via rules")
                else:
                    raise

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
    """
    Minimal Okta client used by termination/onboarding workflows.

    Requires:
      - OKTA_ORG_URL (e.g., https://your-org.okta.com)
      - OKTA_TOKEN   (SSWS token)
    """

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
        base = os.getenv("OKTA_ORG_URL") or "https://filevine.okta.com"
        token = config.get_secret("OKTA_TOKEN")
        if not token:
            raise OktaError("Missing OKTA_TOKEN (not found in environment or 1Password)")
        return cls(base_url=base, token=token)

    # ---- helpers -------------------------------------------------------------

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
    def _delete(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.delete(path, **kwargs)
        if resp.status_code >= 400:
            raise OktaError(f"DELETE {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    # ---- public --------------------------------------------------------------

    def find_user_by_email(self, email: str) -> Optional[str]:
        """Return Okta user id for email, or None if not found."""
        # https://developer.okta.com/docs/reference/api/users/#list-users
        resp = self._get("/api/v1/users", params={"search": f'profile.email eq "{email.lower()}"'})
        users = resp.json()
        if users:
            return users[0].get("id")
        return None

    def clear_sessions(self, user_id: str) -> None:
        # https://developer.okta.com/docs/reference/api/sessions/#end-all-sessions-for-a-user
        # Okta has a users/<id>/sessions endpoint; some orgs use an endpoint that kills all sessions.
        self._delete(f"/api/v1/users/{user_id}/sessions")

    def deactivate_user(self, user_id: str) -> None:
        # https://developer.okta.com/docs/reference/api/users/#deactivate-user
        self._post(f"/api/v1/users/{user_id}/lifecycle/deactivate")

    def remove_from_groups(self, user_id: str, group_ids: Iterable[str]) -> None:
        # https://developer.okta.com/docs/reference/api/groups/#remove-user-from-group
        for gid in group_ids:
            self._delete(f"/api/v1/groups/{gid}/users/{user_id}")
