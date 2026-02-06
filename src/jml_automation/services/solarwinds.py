"""
SolarWinds Service Desk service.

This module handles all SolarWinds Service Desk operations including
ticket fetching, status updates, and comment management.
"""

import os
import time
import logging
from typing import Any, Dict, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from jml_automation.config import Config

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)


class SWSDClientError(RuntimeError):
    pass


def _auth_headers(token: str) -> Dict[str, str]:
    """Generate authentication headers for SolarWinds/Samanage API."""
    return {
        "X-Samanage-Authorization": f"Bearer {token}",
        "Accept": "application/vnd.samanage.v2.1+json",
        "Content-Type": "application/json",
    }


class SolarWindsService:
    """
    Client for SolarWinds Service Desk (formerly Samanage).

    Required configuration:
      - SWSD_BASE_URL or solarwinds.base_url in settings
      - SWSD_API_TOKEN or SAMANAGE_TOKEN/SOLARWINDS_TOKEN in 1Password
    """

    # Constants for termination processing
    TERMINATION_SUBCATEGORY_ID = 1574220  # "Termination" subcategory in Human Resources
    ACTIVE_STATES = {"Awaiting Input"}  # More restrictive - only for employee termination
    ACTIVE_STATES_BROAD = {"Awaiting Input", "New", "Assigned"}  # Broader for other use cases
    DEFAULT_MAX_PAGES = 60
    DEFAULT_PER_PAGE = 100
    DEFAULT_MAX_WORKERS = 15

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers=_auth_headers(self.token),
            timeout=timeout,
        )
        # Cache for ticket lookups
        self._ticket_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def from_config(cls) -> "SolarWindsService":
        """Create service instance from configuration."""
        config = Config()
        base = config.solarwinds_url or os.getenv("SWSD_BASE_URL")
        token = config.get_secret("SAMANAGE_TOKEN") or config.get_secret("SOLARWINDS_TOKEN") or os.getenv("SWSD_API_TOKEN")
        if not base or not token:
            raise SWSDClientError("Missing SolarWinds base URL and/or API token")
        log.debug(f"SolarWinds service initialized with base URL: {base}")
        return cls(base_url=base, token=token)

    @classmethod
    def from_env(cls) -> "SolarWindsService":
        """Alias for from_config for compatibility."""
        return cls.from_config()

    # ---- HTTP helpers --------------------------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _get(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.get(path, **kwargs)
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    time.sleep(float(ra))
                except ValueError:
                    time.sleep(1.0)
            raise httpx.HTTPError("Rate limited", request=resp.request)
        if resp.status_code >= 400:
            raise SWSDClientError(f"GET {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _post(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.post(path, **kwargs)
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    time.sleep(float(ra))
                except ValueError:
                    time.sleep(1.0)
            raise httpx.HTTPError("Rate limited", request=resp.request)
        if resp.status_code >= 400:
            raise SWSDClientError(f"POST {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _put(self, path: str, **kwargs) -> httpx.Response:
        resp = self.client.put(path, **kwargs)
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    time.sleep(float(ra))
                except ValueError:
                    time.sleep(1.0)
            raise httpx.HTTPError("Rate limited", request=resp.request)
        if resp.status_code >= 400:
            raise SWSDClientError(f"PUT {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    # ---- Ticket Operations ---------------------------------------------------

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Fetch a single incident JSON by ID.
        Results are cached for performance.
        """
        if incident_id in self._ticket_cache:
            log.debug(f"Returning cached ticket {incident_id}")
            return self._ticket_cache[incident_id]
        
        resp = self._get(f"/incidents/{incident_id}.json")
        ticket = resp.json()
        self._ticket_cache[incident_id] = ticket
        return ticket

    def search_by_display_number(self, display_number: str) -> Optional[str]:
        """Search for internal incident ID by display number with concurrent paging for speed."""
        log.debug(f"Searching for ticket with display number: {display_number}")
        
        # Check cache first
        for ticket_id, ticket in self._ticket_cache.items():
            if str(ticket.get("number")) == str(display_number):
                log.debug(f"Found ticket {display_number} in cache with ID {ticket_id}")
                return ticket_id
        
        # Use concurrent search for speed
        return self._concurrent_search_by_number(display_number)

    def _concurrent_search_by_number(self, display_number: str) -> Optional[str]:
        """Concurrent search for ticket by display number across multiple pages."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        max_pages = 90  # Increased to 9,000 tickets to stay under SolarWinds 10k API limit
        per_page = 100
        max_workers = 25  # High concurrency for speed
        
        log.debug(f"Starting concurrent search for ticket {display_number} across {max_pages} pages with {max_workers} workers")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all page requests concurrently
            future_to_page = {
                executor.submit(self._search_page_for_number, page, per_page, display_number): page 
                for page in range(1, max_pages + 1)
            }
            
            # Process results as they complete
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    result = future.result()
                    if result:  # Found the ticket
                        elapsed = time.time() - start_time
                        log.debug(f"Found ticket {display_number} on page {page} in {elapsed:.1f}s")
                        return result
                except Exception as e:
                    log.warning(f"Error searching page {page}: {e}")
        
        elapsed = time.time() - start_time
        log.debug(f"Ticket {display_number} not found after searching {max_pages} pages in {elapsed:.1f}s")
        return None

    def _search_page_for_number(self, page: int, per_page: int, display_number: str) -> Optional[str]:
        """Search a single page for the display number."""
        try:
            resp = self._get("/incidents.json", params={
                "page": page,
                "per_page": per_page,
                "sort_order": "desc"
            })
            incidents = resp.json()
            
            for incident in incidents:
                inc_number = incident.get("number")
                if str(inc_number) == str(display_number):
                    internal_id = str(incident.get("id"))
                    log.debug(f"Found ticket #{display_number} -> Internal ID: {internal_id} on page {page}")
                    # Cache the ticket
                    self._ticket_cache[internal_id] = incident
                    return internal_id
            
            return None
            
        except Exception as e:
            log.error(f"Error searching page {page}: {e}")
            return None

    def fetch_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Fetch ticket - try as internal ID first, then search by display number.
        Returns ticket in RawTicket format for parser compatibility.
        """
        try:
            payload = self.get_incident(ticket_id)
            return self.to_raw_ticket(payload)
        except SWSDClientError as e:
            if "404" in str(e):
                log.debug(f"Ticket {ticket_id} not found as internal ID, searching by display number...")
                internal_id = self.search_by_display_number(ticket_id)
                if internal_id:
                    payload = self.get_incident(internal_id)
                    return self.to_raw_ticket(payload)
                log.error(f"No ticket found for {ticket_id}")
                raise SWSDClientError(f"Ticket {ticket_id} not found")
            raise


    @staticmethod
    def to_raw_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map SWSD payload → parser RawTicket shape: {id, subject, body, custom_fields}.
        Handles both dict custom_fields and list-based custom_fields_values.
        """
        subject = payload.get("name") or payload.get("subject") or ""
        body = payload.get("description") or payload.get("body") or ""

        cf: Dict[str, Any] = {}
        if isinstance(payload.get("custom_fields"), dict):
            cf.update(payload["custom_fields"])
        elif isinstance(payload.get("custom_fields_values"), list):
            for item in payload["custom_fields_values"]:
                name = (item.get("name") or "").strip()
                val = item.get("value")
                if name:
                    if name == "Reports to" and "user" in item:
                        # Preserve the full structure for Reports to
                        cf[name] = {"value": val, "user": item.get("user")}
                    else:
                        cf[name] = val

        return {
            "id": str(payload.get("id") or payload.get("number") or ""),
            "subject": subject,
            "body": body,
            "custom_fields": cf,
            # Include original fields for backward compatibility
            "custom_fields_values": payload.get("custom_fields_values", [])
        }

    # ---- Ticket Status Management (Enhanced from ticket_processor.py) --------

    def update_ticket_status(self, ticket_id: str, status: str, notes: Optional[str] = None) -> bool:
        """
        Update ticket status in SolarWinds Service Desk.
        
        Args:
            ticket_id: Ticket ID (internal or display number)
            status: New status (e.g., "In Progress", "Resolved", "Closed")
            notes: Optional notes to add to ticket
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Resolve ticket ID if it's a display number
            internal_id = ticket_id
            if not ticket_id.isdigit() or len(ticket_id) < 6:
                # Likely a display number, search for internal ID
                found_id = self.search_by_display_number(ticket_id)
                if found_id:
                    internal_id = found_id
                else:
                    log.error(f"Cannot find ticket {ticket_id} to update")
                    return False
            
            # Update the ticket state
            update_data = {"incident": {"state": status}}
            log.info(f"Updating ticket {ticket_id} to status '{status}'")
            
            resp = self._put(f"/incidents/{internal_id}.json", json=update_data)
            
            if resp.status_code in (200, 204):
                log.info(f"Successfully updated ticket {ticket_id} status to '{status}'")
                # Invalidate cache for this ticket
                if internal_id in self._ticket_cache:
                    del self._ticket_cache[internal_id]
                
                # Add notes if provided
                if notes:
                    return self.add_ticket_comment(internal_id, notes)
                return True
            else:
                log.error(f"Failed to update ticket {ticket_id}: {resp.status_code}")
                return False
                
        except Exception as e:
            log.error(f"Error updating ticket {ticket_id}: {e}")
            return False

    def update_ticket_state(self, ticket_id: str, state: str) -> None:
        """
        Update the state of a ticket (incident) in SolarWinds.
        Compatibility method that wraps update_ticket_status.
        """
        success = self.update_ticket_status(ticket_id, state)
        if not success:
            raise SWSDClientError(f"Failed to update ticket {ticket_id} state to '{state}'")

    def reassign_ticket_to_group(self, ticket_id: str, group_name: str) -> bool:
        """
        Reassign ticket to a different group.
        
        Args:
            ticket_id: Ticket ID (internal or display number)
            group_name: Name of group to assign to (e.g., "Laptop Setup")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Map group names to their IDs
            group_ids = {
                "Laptop Setup": 14517342,
                "New Users": 13668308,
                # Add more as needed
            }
            
            group_id = group_ids.get(group_name)
            if not group_id:
                log.error(f"Unknown group name: {group_name}. Available groups: {list(group_ids.keys())}")
                return False
            
            # Resolve ticket ID if it's a display number
            internal_id = ticket_id
            if not ticket_id.isdigit() or len(ticket_id) < 6:
                found_id = self.search_by_display_number(ticket_id)
                if found_id:
                    internal_id = found_id
                else:
                    log.error(f"Cannot find ticket {ticket_id} to reassign")
                    return False
            
            # Update the ticket with new group assignment using correct field name
            update_data = {
                "incident": {
                    "assignee_id": group_id
                }
            }
            log.info(f"Reassigning ticket {ticket_id} to group '{group_name}' (ID: {group_id})")
            
            resp = self._put(f"/incidents/{internal_id}.json", json=update_data)
            
            if resp.status_code in (200, 204):
                log.info(f"Successfully reassigned ticket {ticket_id} to group '{group_name}'")
                # Invalidate cache for this ticket
                if internal_id in self._ticket_cache:
                    del self._ticket_cache[internal_id]
                return True
            else:
                log.error(f"Failed to reassign ticket {ticket_id}: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            log.error(f"Error reassigning ticket {ticket_id}: {e}")
            return False

    def assign_and_resolve_ticket(self, ticket_id: str, assignee_email: str = "codyatkinson@filevine.com") -> bool:
        """
        Assign ticket to user and mark as resolved.
        
        Args:
            ticket_id: Ticket ID (internal or display number)
            assignee_email: Email of person to assign to (default: codyatkinson@filevine.com)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Resolve ticket ID if it's a display number
            internal_id = ticket_id
            if not ticket_id.isdigit() or len(ticket_id) < 6:
                found_id = self.search_by_display_number(ticket_id)
                if found_id:
                    internal_id = found_id
                else:
                    log.error(f"Cannot find ticket {ticket_id} to assign")
                    return False
            
            # Update the ticket with assignment and resolved state
            # Use assignee with email for user assignment
            update_data = {
                "incident": {
                    "state": "Resolved",
                    "assignee": {
                        "email": assignee_email
                    }
                }
            }
            log.info(f"Assigning ticket {ticket_id} to {assignee_email} and marking resolved")
            
            resp = self._put(f"/incidents/{internal_id}.json", json=update_data)
            
            if resp.status_code in (200, 204):
                log.info(f"Successfully assigned ticket {ticket_id} to {assignee_email} and marked resolved")
                # Invalidate cache for this ticket
                if internal_id in self._ticket_cache:
                    del self._ticket_cache[internal_id]
                return True
            else:
                log.error(f"Failed to assign ticket {ticket_id}: {resp.status_code} - {resp.text}")
                return False
                
        except Exception as e:
            log.error(f"Error assigning ticket {ticket_id}: {e}", exc_info=True)
            return False

    def add_ticket_comment(self, ticket_id: str, comment: str, is_private: bool = False) -> bool:
        """
        Add a comment to a ticket (incident) in SolarWinds.
        
        Args:
            ticket_id: Ticket ID (internal or display number)
            comment: Comment text to add
            is_private: Whether the comment should be private
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Resolve ticket ID if it's a display number
            internal_id = ticket_id
            if not ticket_id.isdigit() or len(ticket_id) < 6:
                found_id = self.search_by_display_number(ticket_id)
                if found_id:
                    internal_id = found_id
                else:
                    log.error(f"Cannot find ticket {ticket_id} to add comment")
                    return False
            
            log.info(f"Adding comment to ticket {ticket_id} (internal ID: {internal_id})")
            log.debug(f"Comment text: {comment[:100]}...")
            
            # Add the comment - try different API structures
            comment_data = {
                "comment": {
                    "body": comment,
                    "is_private": is_private
                }
            }
            
            resp = self._post(f"/incidents/{internal_id}/comments.json", json=comment_data)
            log.info(f"Comment API response: {resp.status_code} - {resp.text[:200]}")
            
            if resp.status_code in (200, 201):
                log.info(f"Successfully added comment to ticket {ticket_id}")
                return True
            else:
                log.error(f"Failed to add comment to ticket {ticket_id}: {resp.status_code} - {resp.text}")
                
                # Try alternative API structure if first fails
                log.info("Trying alternative comment structure...")
                alt_comment_data = {
                    "body": comment,
                    "is_private": is_private
                }
                
                resp2 = self._post(f"/incidents/{internal_id}/comments.json", json=alt_comment_data)
                log.info(f"Alternative comment API response: {resp2.status_code} - {resp2.text[:200]}")
                
                if resp2.status_code in (200, 201):
                    log.info(f"Successfully added comment to ticket {ticket_id} (alternative structure)")
                    return True
                else:
                    log.error(f"Both comment structures failed for ticket {ticket_id}")
                    return False
                
        except Exception as e:
            log.error(f"Error adding comment to ticket {ticket_id}: {e}", exc_info=True)
            return False

    # ---- User Operations -----------------------------------------------------

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Fetch a single user's details by ID."""
        resp = self._get(f"/users/{user_id}.json")
        return resp.json()

    # ---- Batch Operations ----------------------------------------------------

    def fetch_termination_tickets(self) -> List[Dict[str, Any]]:
        """
        Fetch and filter termination tickets for processing.
        Returns list of tickets in RawTicket format.
        """
        try:
            log.info("Fetching termination tickets from SolarWinds")
            
            # This would typically filter by catalog item ID or other criteria
            # For now, return empty list as placeholder
            # You would implement the actual filtering logic based on your needs
            
            tickets = []
            page = 1
            per_page = 100
            max_pages = 5
            
            config = Config()
            catalog_item_id = config.settings.get('solarwinds', {}).get('catalog_item_id')
            
            while page <= max_pages:
                params = {
                    "page": page,
                    "per_page": per_page,
                    "sort_order": "desc"
                }
                
                if catalog_item_id:
                    params["catalog_item_id"] = catalog_item_id
                
                resp = self._get("/incidents.json", params=params)
                incidents = resp.json()
                
                if not incidents:
                    break
                
                for incident in incidents:
                    # Convert to RawTicket format
                    raw_ticket = self.to_raw_ticket(incident)
                    # You could add additional filtering here
                    tickets.append(raw_ticket)
                
                page += 1
            
            log.info(f"Found {len(tickets)} tickets")
            return tickets
            
        except Exception as e:
            log.error(f"Failed to fetch termination tickets: {e}")
            return []

    # ---- Enhanced Concurrent Fetching Methods --------------------------------

    def _fetch_page_concurrent(self, page: int, per_page: int, subcategory_id: Optional[int] = None) -> List[Dict]:
        """Fetch a single page of tickets with retry logic for concurrent operations."""
        params = {
            "per_page": per_page,
            "page": page,
            "sort": "created_at",
            "sort_order": "desc"
        }
        
        if subcategory_id:
            params["subcategory_id"] = subcategory_id

        log.debug(f"Fetching page {page}...")
        retries = 0
        max_retries = 5
        
        while retries < max_retries:
            try:
                resp = self._get("/incidents.json", params=params)
                return resp.json()
            except Exception as e:
                if "429" in str(e) or "Rate limit" in str(e):
                    # Rate limit hit, exponential backoff
                    wait_time = (2 ** retries) + (page % 5)  # Add jitter based on page
                    log.debug(f"Rate limit hit on page {page}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    retries += 1
                    continue
                else:
                    log.error(f"Error on page {page}: {e}")
                    return []
        
        log.warning(f"Failed to fetch page {page} after {max_retries} retries")
        return []

    def fetch_termination_tickets_concurrent(
        self, 
        max_pages: Optional[int] = None, 
        per_page: Optional[int] = None, 
        max_workers: Optional[int] = None,
        subcategory_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch termination tickets using concurrent requests for high performance.
        
        Args:
            max_pages: Maximum pages to fetch (default: 60)
            per_page: Items per page (default: 100) 
            max_workers: Concurrent workers (default: 15)
            subcategory_id: Filter by subcategory (default: TERMINATION_SUBCATEGORY_ID)
            
        Returns:
            List of tickets in RawTicket format, deduplicated
        """
        max_pages = max_pages or self.DEFAULT_MAX_PAGES
        per_page = per_page or self.DEFAULT_PER_PAGE
        max_workers = max_workers or self.DEFAULT_MAX_WORKERS
        subcategory_id = subcategory_id or self.TERMINATION_SUBCATEGORY_ID
        
        log.info(f"Fetching termination tickets (concurrent) - pages: {max_pages}, workers: {max_workers}")
        start_time = time.time()
        
        all_tickets = []
        seen_ids: Set[str] = set()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all page requests
            futures = {
                executor.submit(self._fetch_page_concurrent, page, per_page, subcategory_id): page 
                for page in range(1, max_pages + 1)
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                page = futures[future]
                try:
                    incidents = future.result()
                    if not incidents:
                        continue
                    
                    # Deduplicate and convert to RawTicket format
                    for incident in incidents:
                        inc_id = str(incident.get('id', ''))
                        if inc_id and inc_id not in seen_ids:
                            raw_ticket = self.to_raw_ticket(incident)
                            all_tickets.append(raw_ticket)
                            seen_ids.add(inc_id)
                            
                except Exception as e:
                    log.error(f"Thread error on page {page}: {e}")

        elapsed = time.time() - start_time
        log.info(f"Concurrent fetch completed: {len(all_tickets)} tickets in {elapsed:.1f}s")
        return all_tickets

    def fetch_termination_tickets_enhanced(
        self,
        concurrent: bool = True,
        active_only: bool = True,
        subcategory_filter: bool = True,
        strict_active_filter: bool = True,  # New parameter for restrictive filtering
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Enhanced termination ticket fetching with multiple options.
        
        Args:
            concurrent: Use concurrent fetching (default: True)
            active_only: Filter to active states only (default: True) 
            subcategory_filter: Filter by termination subcategory (default: True)
            strict_active_filter: Use restrictive "Awaiting Input" only vs broader states
            **kwargs: Additional arguments passed to fetch method
            
        Returns:
            List of filtered tickets in RawTicket format
        """
        # Choose fetching method
        if concurrent:
            subcategory_id = self.TERMINATION_SUBCATEGORY_ID if subcategory_filter else None
            tickets = self.fetch_termination_tickets_concurrent(
                subcategory_id=subcategory_id,
                **kwargs
            )
        else:
            tickets = self.fetch_termination_tickets()
        
        # Apply state filtering if requested
        if active_only:
            original_count = len(tickets)
            # Choose strict or broad active states
            active_states = self.ACTIVE_STATES if strict_active_filter else self.ACTIVE_STATES_BROAD
            tickets = [
                ticket for ticket in tickets 
                if self._get_ticket_state(ticket) in active_states
            ]
            log.info(f"State filtering ({'strict' if strict_active_filter else 'broad'}): {original_count} -> {len(tickets)} active tickets")
        
        return tickets

    def _get_ticket_state(self, ticket: Dict[str, Any]) -> str:
        """Extract state from a ticket dict, handling various formats."""
        # Try direct state field first
        if 'state' in ticket:
            return ticket['state']
        
        # Try custom fields
        custom_fields = ticket.get('custom_fields', {})
        if isinstance(custom_fields, dict) and 'state' in custom_fields:
            return custom_fields['state']
        
        # Default fallback
        return "Unknown"

    def get_termination_statistics(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics about termination tickets.
        
        Args:
            tickets: List of tickets to analyze
            
        Returns:
            Dictionary with statistics including counts by department, state, etc.
        """
        if not tickets:
            return {"total": 0}
        
        stats = {
            "total": len(tickets),
            "by_state": {},
            "by_department": {},
            "by_subcategory": {},
            "processing_time": time.time()
        }
        
        for ticket in tickets:
            # State analysis
            state = self._get_ticket_state(ticket)
            stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
            
            # Department analysis (from custom fields)
            custom_fields = ticket.get('custom_fields', {})
            dept = custom_fields.get('Employee Department', 'Unknown')
            stats["by_department"][dept] = stats["by_department"].get(dept, 0) + 1
            
            # Subcategory analysis
            subcat = custom_fields.get('subcategory', 'Unknown')
            stats["by_subcategory"][subcat] = stats["by_subcategory"].get(subcat, 0) + 1
        
        return stats

    # ---- Utility Methods -----------------------------------------------------

    def clear_cache(self) -> None:
        """Clear the ticket cache."""
        self._ticket_cache.clear()
        log.debug("Cleared SolarWinds ticket cache")

    def test_connection(self) -> bool:
        """Test the SolarWinds connection by fetching incidents."""
        try:
            resp = self._get("/incidents.json", params={"page": 1, "per_page": 1})
            return resp.status_code == 200
        except:
            return False


# ---- Legacy Direct API Functions (for backward compatibility) ---------------

def get_solarwinds_headers() -> Dict[str, str]:
    """Get headers for SolarWinds Service Desk API (legacy)."""
    config = Config()
    token = config.get_secret("SAMANAGE_TOKEN") or config.get_secret("SOLARWINDS_TOKEN")
    return _auth_headers(token)


def update_ticket_status_direct(ticket_id: str, ticket_number: str, new_status: str = "In Progress") -> bool:
    """
    Update a ticket status using the ticket ID directly (legacy compatibility).
    
    Args:
        ticket_id: Internal ticket ID
        ticket_number: Display number (for logging)
        new_status: New status to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        service = SolarWindsService.from_config()
        return service.update_ticket_status(ticket_id, new_status)
    except Exception as e:
        log.error(f"Error updating ticket {ticket_number}: {e}")
        return False


def add_ticket_comment_direct(ticket_id: str, ticket_number: str, comment: str) -> bool:
    """
    Add a comment to a ticket using the ticket ID directly (legacy compatibility).
    
    Args:
        ticket_id: Internal ticket ID
        ticket_number: Display number (for logging)
        comment: Comment text
        
    Returns:
        True if successful, False otherwise
    """
    try:
        service = SolarWindsService.from_config()
        return service.add_ticket_comment(ticket_id, comment)
    except Exception as e:
        log.error(f"Error adding comment to ticket {ticket_number}: {e}")
        return False