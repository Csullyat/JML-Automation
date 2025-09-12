"""
Unified Termination Workflow
Combines simple termination.py and enterprise orchestrator functionality.
Supports both single-service and multi-phase termination execution.
"""

from __future__ import annotations

import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union

from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.services.okta import OktaService
from jml_automation.services.synqprox import SynqProxService
from jml_automation.config import Config
from jml_automation.logger import setup_logging
from jml_automation.models.ticket import TerminationTicket, UserProfile
from jml_automation.parsers.solarwinds_parser import (
    parse_ticket,
    fetch_ticket,
    extract_user_email_from_ticket,
    extract_manager_email_from_ticket,
)

logger = logging.getLogger(__name__)


# ========== Service Stubs (to be replaced with actual implementations) ==========

class MicrosoftService:
    """Stub for Microsoft 365 termination service."""
    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        logger.warning(f"Microsoft termination not yet implemented for {user_email}")
        return {
            'success': False,
            'error': 'Service not implemented',
            'errors': ['Microsoft service not yet implemented']
        }
    
    def test_connectivity(self) -> Dict:
        return {'success': False, 'error': 'Service not implemented'}


class GoogleService:
    """Stub for Google Workspace termination service."""
    def execute_complete_termination(self, user_email: str, manager_email: str) -> Dict:
        logger.warning(f"Google termination not yet implemented for {user_email}")
        return {
            'success': False,
            'error': 'Service not implemented',
            'errors': ['Google service not yet implemented']
        }
    
    def test_connectivity(self) -> Dict:
        return {'success': False, 'error': 'Service not implemented'}


class ZoomService:
    """Stub for Zoom termination service."""
    def execute_complete_termination(self, user_email: str, manager_email: Optional[str]) -> Dict:
        logger.warning(f"Zoom termination not yet implemented for {user_email}")
        return {
            'success': False,
            'error': 'Service not implemented',
            'errors': ['Zoom service not yet implemented']
        }
    
    def test_connectivity(self) -> Dict:
        return {'success': False, 'error': 'Service not implemented'}


# ========== Core Termination Class ==========

class TerminationWorkflow:
    """
    Unified termination workflow supporting both simple and enterprise modes.
    Can execute single-service or multi-phase terminations.
    """

    def __init__(self):
        """Initialize termination components."""
        setup_logging()
        
        logger.info("=" * 80)
        logger.info("TERMINATION WORKFLOW INITIALIZING")
        logger.info("=" * 80)
        
        # Validate configuration
        logger.info("Validating configuration...")
        self.config = Config()
        config_status = self.config.get_configuration_summary()
        
        if not config_status.get("onepassword_service_account"):
            logger.warning("1Password service account not accessible - some features may not work")
        else:
            logger.info("1Password service account validated")
        
        # Initialize services
        try:
            self.solarwinds = SolarWindsService.from_config()
            self.okta = OktaService.from_config()
            self.synqprox = SynqProxService()
            
            # Initialize other services (replace stubs with actual implementations when available)
            self.microsoft = MicrosoftService()
            self.google = GoogleService()
            self.zoom = ZoomService()
            
            logger.info("Core services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    # ========== Core Okta Termination (unified from both files) ==========
    
    def execute_okta_termination(
        self,
        user_email: str,
        ticket: Optional[TerminationTicket] = None
    ) -> Dict[str, Any]:
        """
        Execute complete Okta termination for a user.
        This is the best version, combining error handling from both implementations.
        
        Args:
            user_email: Email address of user to terminate
            ticket: Optional termination ticket object
            
        Returns:
            Dict with termination results
        """
        logger.info(f"Starting Okta termination for {user_email}")
        start_time = datetime.now()
        actions_completed = []
        actions_failed = []
        warnings = []
        
        try:
            # Step 1: Find the user
            logger.info(f"Looking up user {user_email}")
            user = self.okta.get_user_by_email(user_email)
            
            if not user:
                error_msg = f"User {user_email} not found in Okta"
                logger.error(error_msg)
                return {
                    'success': False,
                    'user_email': user_email,
                    'error': error_msg,
                    'errors': ['User not found in Okta'],
                    'actions_completed': actions_completed,
                    'actions_failed': ['User lookup failed'],
                    'warnings': warnings
                }
            
            user_id = user['id']
            user_name = user.get('profile', {}).get('displayName', user_email)
            user_status = user['status']
            logger.info(f"Found user: {user_name} (ID: {user_id}, Status: {user_status})")
            
            # Step 2: Clear all active sessions (CRITICAL for security)
            logger.info(f"Clearing all active sessions for {user_email}")
            try:
                self.okta.clear_sessions(user_id)
                actions_completed.append("All active sessions cleared")
                logger.info("All sessions cleared successfully")
            except Exception as e:
                actions_failed.append(f"Failed to clear sessions: {e}")
                logger.error(f"Failed to clear sessions - SECURITY RISK! {e}")
            
            # Step 3: Remove from all groups
            logger.info(f"Removing user from all groups...")
            try:
                result = self.okta.remove_from_all_groups(user_id)
                if result['success']:
                    actions_completed.append(f"Removed from {result['groups_removed']} groups")
                    if result.get('groups_skipped', 0) > 0:
                        logger.info(f"Skipped {result['groups_skipped']} system groups")
                    logger.info(f"Removed from {result['groups_removed']} groups")
                else:
                    actions_failed.append("Failed to remove from some groups")
                    if 'error' in result:
                        logger.error(f"Group removal error: {result['error']}")
            except Exception as e:
                actions_failed.append(f"Failed to remove groups: {e}")
                logger.error(f"Failed to remove from groups: {e}")
            
            # Step 3.5: SYNQ Prox Termination (Unconditional)
            logger.info(f"Processing SYNQ Prox termination for {user_email}")
            try:
                synq_result = self.synqprox.execute_termination(user_email)
                if synq_result.get('success'):
                    actions_completed.append("SYNQ Prox user deleted")
                    logger.info("SYNQ Prox termination completed successfully")
                else:
                    # SYNQ Prox failure is not critical - log as warning
                    warnings.append(f"SYNQ Prox termination failed: {synq_result.get('message', 'Unknown error')}")
                    logger.warning(f"SYNQ Prox termination failed: {synq_result.get('message', 'Unknown error')}")
            except Exception as e:
                warnings.append(f"SYNQ Prox termination error: {e}")
                logger.warning(f"SYNQ Prox termination error: {e}")
            
            # Step 4: Deactivate user (if not already deactivated)
            if user_status not in ['DEPROVISIONED', 'SUSPENDED']:
                logger.info(f"Deactivating user account")
                try:
                    self.okta.deactivate_user(user_id)
                    actions_completed.append("User account deactivated")
                    logger.info("User account deactivated")
                except Exception as e:
                    actions_failed.append(f"Failed to deactivate user: {e}")
                    logger.error(f"Failed to deactivate user: {e}")
            else:
                actions_completed.append(f"User already inactive (Status: {user_status})")
                logger.info(f"User already inactive (Status: {user_status})")
            
            # Determine overall success (sessions and deactivation are critical)
            critical_failures = [f for f in actions_failed if 'sessions' in f.lower() or 'deactivate' in f.lower()]
            success = len(critical_failures) == 0
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': success,
                'user_email': user_email,
                'user_name': user_name,
                'user_id': user_id,
                'user_status': user_status,
                'original_status': user_status,
                'actions_completed': actions_completed,
                'actions_failed': actions_failed,
                'errors': actions_failed,
                'warnings': warnings,
                'duration_seconds': duration
            }
            
            if success:
                logger.info(f"Okta termination completed successfully for {user_email} in {duration:.1f}s")
            else:
                logger.warning(f"Okta termination completed with issues for {user_email} in {duration:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Fatal error during Okta termination for {user_email}: {e}")
            
            return {
                'success': False,
                'user_email': user_email,
                'error': f"Fatal error: {str(e)}",
                'errors': [f"Fatal error: {str(e)}"],
                'actions_completed': actions_completed,
                'actions_failed': actions_failed + [f"Fatal error: {str(e)}"],
                'warnings': warnings,
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }

    def remove_from_app_specific_groups(
        self,
        user_email: str,
        app_name: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove user from app-specific Okta groups instead of all groups.
        
        Args:
            user_email: Email address of user
            app_name: Application name (microsoft, google, zoom, etc.)
            user_id: Optional Okta user ID (will lookup if not provided)
            
        Returns:
            Dict with removal results
        """
        from jml_automation.utils.yaml_loader import load_yaml
        
        logger.info(f"Removing {user_email} from {app_name}-specific Okta groups")
        
        try:
            # Load app-specific group mapping
            termination_config = load_yaml("config/termination_order.yaml")
            app_groups = termination_config.get("termination", {}).get("okta_groups_to_remove", {}).get(app_name, [])
            
            if not app_groups:
                logger.warning(f"No Okta groups configured for {app_name}")
                return {
                    'success': True,
                    'groups_removed': 0,
                    'groups_failed': 0,
                    'message': f'No groups configured for {app_name}'
                }
            
            # Get user ID if not provided
            if not user_id:
                user = self.okta.get_user_by_email(user_email)
                if not user:
                    return {
                        'success': False,
                        'error': f'User {user_email} not found in Okta'
                    }
                user_id = user.get("id")
                if not user_id:
                    return {
                        'success': False,
                        'error': f'No user ID found for {user_email}'
                    }
            
            # Remove from each app-specific group
            removed_groups = []
            failed_groups = []
            
            for group_name in app_groups:
                try:
                    group_id = self.okta.find_group_id(group_name)
                    if group_id:
                        self.okta.remove_from_groups(user_id, [group_id])
                        removed_groups.append(group_name)
                        logger.info(f"Removed from group: {group_name}")
                    else:
                        failed_groups.append(f"{group_name} (not found)")
                        logger.warning(f"Group not found: {group_name}")
                except Exception as e:
                    failed_groups.append(f"{group_name} (error: {e})")
                    logger.error(f"Failed to remove from group {group_name}: {e}")
            
            return {
                'success': len(failed_groups) == 0,
                'groups_removed': len(removed_groups),
                'groups_failed': len(failed_groups),
                'removed_groups': removed_groups,
                'failed_groups': failed_groups,
                'message': f'Removed from {len(removed_groups)} {app_name} groups'
            }
            
        except Exception as e:
            logger.error(f"Failed to remove from {app_name} groups: {e}")
            return {
                'success': False,
                'error': f'Failed to remove from {app_name} groups: {e}'
            }

    # ========== Multi-Phase Enterprise Termination ==========
    
    def execute_multi_phase_termination(
        self,
        user_email: str,
        manager_email: Optional[str] = None,
        ticket_id: Optional[str] = None,
        phases: Optional[List[str]] = None,
    ) -> Dict:
        """
        Execute complete multi-phase termination for a single user.
        Enterprise mode with all services.
        
        Args:
            user_email: User to terminate
            manager_email: Manager for data delegation
            ticket_id: Service desk ticket ID
            phases: List of phases to execute ['okta','microsoft','google','zoom','notifications']
        """
        if phases is None:
            phases = ["okta", "microsoft", "google", "zoom"]

        logger.info(f"Starting multi-phase termination for {user_email}")
        logger.info(f"Phases to execute: {', '.join(phases)}")
        if manager_email:
            logger.info(f"Manager for delegation: {manager_email}")

        termination_results: Dict = {
            "user_email": user_email,
            "manager_email": manager_email,
            "ticket_id": ticket_id,
            "start_time": datetime.now(),
            "phases_executed": phases,
            "okta_results": {},
            "microsoft_results": {},
            "google_results": {},
            "zoom_results": {},
            "overall_success": False,
            "phase_success": {},
            "summary": [],
            "errors": [],
            "warnings": [],
        }

        try:
            # Phase 1: Okta (highest priority - immediate security)
            if "okta" in phases:
                logger.info("🔒 PHASE 1: Okta user deactivation and security cleanup")
                try:
                    okta_results = self.execute_okta_termination(user_email)
                    termination_results["okta_results"] = okta_results
                    
                    if okta_results.get("success"):
                        termination_results["summary"].append("✅ Okta: User deactivated, groups removed, sessions cleared")
                        termination_results["phase_success"]["okta"] = True
                        logger.info("Okta termination phase completed successfully")
                    else:
                        termination_results["summary"].append("⚠️ Okta: Termination had issues")
                        termination_results["phase_success"]["okta"] = False
                        termination_results["errors"].extend(okta_results.get("errors", []))
                        logger.warning("Okta termination phase had issues")
                        
                except Exception as e:
                    logger.error(f"Okta termination failed: {e}")
                    termination_results["okta_results"] = {"success": False, "error": str(e)}
                    termination_results["phase_success"]["okta"] = False
                    termination_results["errors"].append(f"Okta termination failed: {e}")

            # Phase 2: Microsoft 365
            if "microsoft" in phases:
                logger.info("📧 PHASE 2: Microsoft 365 mailbox and license management")
                if manager_email:
                    try:
                        ms_results = self.microsoft.execute_complete_termination(
                            user_email, manager_email
                        )
                        termination_results["microsoft_results"] = ms_results
                        
                        if ms_results.get("success"):
                            termination_results["summary"].append("✅ Microsoft: Mailbox converted, licenses removed")
                            termination_results["phase_success"]["microsoft"] = True
                        else:
                            termination_results["summary"].append("⚠️ Microsoft: Not yet implemented")
                            termination_results["phase_success"]["microsoft"] = False
                            termination_results["warnings"].append("Microsoft service not yet implemented")
                    except Exception as e:
                        logger.error(f"Microsoft termination failed: {e}")
                        termination_results["phase_success"]["microsoft"] = False
                else:
                    logger.warning("No manager email - skipping Microsoft delegation")
                    termination_results["warnings"].append("Microsoft skipped - no manager")

            # Phase 3: Google Workspace
            if "google" in phases:
                logger.info("🌐 PHASE 3: Google Workspace termination and data transfer")
                if manager_email:
                    try:
                        g_results = self.google.execute_complete_termination(
                            user_email, manager_email
                        )
                        termination_results["google_results"] = g_results
                        
                        if g_results.get("success"):
                            termination_results["summary"].append("✅ Google: User suspended, data transferred")
                            termination_results["phase_success"]["google"] = True
                        else:
                            termination_results["summary"].append("⚠️ Google: Not yet implemented")
                            termination_results["phase_success"]["google"] = False
                            termination_results["warnings"].append("Google service not yet implemented")
                    except Exception as e:
                        logger.error(f"Google termination failed: {e}")
                        termination_results["phase_success"]["google"] = False
                else:
                    logger.warning("No manager email - skipping Google delegation")
                    termination_results["warnings"].append("Google skipped - no manager")

            # Phase 4: Zoom
            if "zoom" in phases:
                logger.info("📹 PHASE 4: Zoom account termination and cleanup")
                try:
                    z_results = self.zoom.execute_complete_termination(
                        user_email, manager_email
                    )
                    termination_results["zoom_results"] = z_results
                    
                    if z_results.get("success"):
                        termination_results["summary"].append("✅ Zoom: User deactivated")
                        termination_results["phase_success"]["zoom"] = True
                    else:
                        termination_results["summary"].append("⚠️ Zoom: Not yet implemented")
                        termination_results["phase_success"]["zoom"] = False
                        termination_results["warnings"].append("Zoom service not yet implemented")
                except Exception as e:
                    logger.error(f"Zoom termination failed: {e}")
                    termination_results["phase_success"]["zoom"] = False

            # Update ticket status
            if ticket_id:
                try:
                    logger.info(f"📋 Updating ticket {ticket_id} status")
                    self.solarwinds.update_ticket_status(
                        ticket_id,
                        "In Progress",
                        notes=f"Termination processing - Okta: {'✓' if termination_results['phase_success'].get('okta') else '✗'}"
                    )
                    termination_results["summary"].append(f"📋 Ticket {ticket_id} updated")
                except Exception as e:
                    logger.error(f"Failed to update ticket {ticket_id}: {e}")
                    termination_results["warnings"].append(f"Failed to update ticket {ticket_id}")

            # Determine overall success (Okta is always critical)
            critical_phases = ["okta"]
            critical_success = all(
                termination_results["phase_success"].get(phase, False)
                for phase in critical_phases if phase in phases
            )
            
            termination_results["overall_success"] = critical_success
            termination_results["end_time"] = datetime.now()
            duration = termination_results["end_time"] - termination_results["start_time"]
            termination_results["duration_seconds"] = duration.total_seconds()

            success_msg = "SUCCESSFUL" if termination_results["overall_success"] else "COMPLETED WITH ISSUES"
            logger.info(f"Multi-phase termination {success_msg} for {user_email} in {duration.total_seconds():.1f} seconds")
            
            # Log summary
            self._log_termination_summary(termination_results)
            
            return termination_results
            
        except Exception as e:
            logger.error(f"Fatal error during termination of {user_email}: {e}")
            termination_results["overall_success"] = False
            termination_results["errors"].append(f"Fatal error: {str(e)}")
            termination_results["end_time"] = datetime.now()
            return termination_results

    # ========== Simple Termination Mode (from termination.py) ==========
    
    def execute_simple_termination(
        self,
        ticket_id: Optional[str] = None,
        ticket_raw: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> int:
        """
        Execute simple termination workflow (Okta only).
        Compatible with the original termination.py interface.
        
        Args:
            ticket_id: Ticket ID to fetch
            ticket_raw: Raw ticket data (for testing)
            dry_run: If True, only show plan without executing
            
        Returns:
            Exit code (0 = success, non-zero = failure)
        """
        # Fetch or use provided ticket
        if ticket_raw is None:
            if not ticket_id:
                logger.error("Either ticket_raw or ticket_id must be provided.")
                return 2
            raw = fetch_ticket(ticket_id)
        else:
            raw = ticket_raw

        # Parse ticket
        ticket = parse_ticket(raw)
        if not isinstance(ticket, TerminationTicket):
            logger.error("Parsed ticket is not a TerminationTicket (id=%s)", raw.get("id"))
            return 3

        # Extract user email
        user_email = ticket.user.email if ticket.user else None
        if not user_email:
            user_email = extract_user_email_from_ticket(raw)
            
            # Handle employee ID lookups
            if user_email and user_email.startswith("LOOKUP_EMPLOYEE_ID:"):
                employee_id = user_email.split(":", 1)[1]
                logger.info(f"Looking up employee ID {employee_id} in Okta")
                user_email = self.okta.lookup_email_by_employee_id(employee_id)
                if not user_email:
                    logger.error(f"Could not find email for employee ID {employee_id}")
                    return 4
        
        if not user_email:
            logger.error("No user email found in ticket")
            return 5

        # Extract manager email for transfer
        manager_email = extract_manager_email_from_ticket(raw)

        # Generate plan for dry run
        if dry_run:
            print("=== Termination Plan ===")
            print(f"User: {user_email}")
            print(f"Ticket: {ticket.ticket_id}")
            print(f"Transfer to: {manager_email or 'Not specified'}")
            print("\nSteps:")
            print(" - Okta: Clear all active sessions")
            print(" - Okta: Remove from all groups")
            print(" - Okta: Deactivate user account")
            print(" - SolarWinds: Update ticket status")
            return 0

        # Execute live termination
        logger.info(f"Starting LIVE termination for {user_email}")
        
        # Execute Okta termination
        okta_result = self.execute_okta_termination(user_email, ticket)
        
        # Update SolarWinds ticket
        try:
            if okta_result['success']:
                self.solarwinds.update_ticket_status(
                    ticket.ticket_id,
                    "In Progress",
                    notes=f"Okta termination completed: {', '.join(okta_result['actions_completed'])}"
                )
            else:
                self.solarwinds.update_ticket_status(
                    ticket.ticket_id,
                    "Pending",
                    notes=f"Okta termination had issues: {', '.join(okta_result['actions_failed'])}"
                )
        except Exception as e:
            logger.error(f"Failed to update SolarWinds ticket: {e}")
        
        # Return success/failure code
        if okta_result['success']:
            logger.info(f"Termination workflow completed successfully for {user_email}")
            return 0
        else:
            logger.error(f"Termination workflow completed with errors for {user_email}")
            return 1

    # ========== Ticket Processing ==========
    
    def fetch_termination_tickets(self) -> List[Dict]:
        """Fetch termination tickets from SolarWinds."""
        try:
            logger.info("Fetching termination tickets from SolarWinds")
            return self.solarwinds.fetch_termination_tickets()
        except Exception as e:
            logger.error(f"Failed to fetch tickets: {e}")
            return []

    def process_termination_tickets(self) -> List[Dict]:
        """Fetch and filter actionable termination tickets."""
        try:
            tickets = self.fetch_termination_tickets()
            if not tickets:
                logger.info("No termination tickets found")
                return []

            logger.info(f"Found {len(tickets)} total termination tickets")
            
            actionable: List[Dict] = []
            for ticket in tickets:
                state = ticket.get("state", "").lower()
                catalog_item = str(ticket.get("catalog_item", "")).lower()
                
                actionable_states = ["awaiting input", "new", "assigned", "in progress"]
                if any(s in state for s in actionable_states) and "termination" in catalog_item:
                    actionable.append(ticket)
                    logger.info(f"Added ticket {ticket.get('id', 'unknown')} to processing queue")
                else:
                    logger.debug(f"Skipping ticket {ticket.get('id')} - state={state}, catalog={catalog_item}")
            
            logger.info(f"Found {len(actionable)} actionable termination tickets")
            return actionable
            
        except Exception as e:
            logger.error(f"Failed to process termination tickets: {e}")
            return []

    def run_batch_processing(self) -> None:
        """Process all pending termination tickets."""
        logger.info("Starting batch termination ticket processing")
        
        try:
            tickets = self.process_termination_tickets()
            
            if not tickets:
                logger.info("No termination tickets to process")
                return
            
            total_processed = 0
            total_successful = 0
            processed_users = []
            
            for ticket in tickets:
                try:
                    # Extract user and manager information
                    user_email = extract_user_email_from_ticket(ticket)
                    manager_email = extract_manager_email_from_ticket(ticket)
                    ticket_id = str(ticket.get("id", ""))
                    
                    if not user_email:
                        logger.error(f"Could not extract user email from ticket {ticket_id}")
                        continue
                    
                    # Handle employee ID lookups
                    if user_email and user_email.startswith("LOOKUP_EMPLOYEE_ID:"):
                        employee_id = user_email.split(":", 1)[1]
                        logger.info(f"Looking up employee ID {employee_id} in Okta")
                        user_email = self.okta.lookup_email_by_employee_id(employee_id)
                        if not user_email:
                            logger.error(f"Could not find email for employee ID {employee_id}")
                            continue
                    
                    logger.info(f"Processing termination for {user_email} (ticket {ticket_id})")
                    
                    # Execute multi-phase termination
                    results = self.execute_multi_phase_termination(user_email, manager_email, ticket_id)
                    
                    processed_users.append({
                        "user_email": user_email,
                        "ticket_id": ticket_id,
                        "success": results["overall_success"],
                        "phases": results["phase_success"]
                    })
                    
                    total_processed += 1
                    if results["overall_success"]:
                        total_successful += 1
                        logger.info(f"Termination successful for {user_email}")
                    else:
                        logger.warning(f"Termination had issues for {user_email}")
                    
                except Exception as e:
                    logger.error(f"Failed to process ticket {ticket.get('id', 'unknown')}: {e}")
                    total_processed += 1
            
            # Log batch summary
            self._log_batch_summary(total_processed, total_successful, processed_users)
            
            logger.info(f"Batch processing completed: {total_successful}/{total_processed} successful")
            
        except Exception as e:
            logger.error(f"Failed to run batch processing: {e}")
            raise

    # ========== Test Mode ==========
    
    def test_termination(self, user_email: str, manager_email: Optional[str] = None) -> Dict:
        """Execute termination in test mode (validation only)."""
        logger.info(f"🧪 RUNNING TEST MODE TERMINATION for {user_email}")
        
        test_results = {
            "user_email": user_email,
            "manager_email": manager_email,
            "test_mode": True,
            "start_time": datetime.now(),
            "validation_results": {},
            "would_execute": [],
            "potential_issues": [],
            "overall_ready": False
        }
        
        try:
            # Test Okta connectivity and user existence
            logger.info("Testing Okta connectivity and user lookup")
            okta_test = self.okta.test_user_lookup(user_email)
            test_results["validation_results"]["okta"] = okta_test
            
            if okta_test.get("user_exists", False):
                test_results["would_execute"].append(
                    f"Okta: Deactivate user, remove from {okta_test.get('groups_count', 0)} groups, clear sessions"
                )
            else:
                test_results["potential_issues"].append("Okta: User not found")
            
            # Test other services
            if manager_email:
                # Microsoft
                logger.info("Testing Microsoft Graph connectivity")
                ms_test = self.microsoft.test_connectivity()
                test_results["validation_results"]["microsoft"] = ms_test
                
                if ms_test.get("success", False):
                    test_results["would_execute"].append("Microsoft: Convert mailbox, delegate access, remove licenses")
                else:
                    test_results["potential_issues"].append("Microsoft: Service not yet implemented")
                
                # Google
                logger.info("Testing Google Workspace connectivity")
                google_test = self.google.test_connectivity()
                test_results["validation_results"]["google"] = google_test
                
                if google_test.get("success", False):
                    test_results["would_execute"].append("Google: Suspend user, transfer data, update groups")
                else:
                    test_results["potential_issues"].append("Google: Service not yet implemented")
            
            # Zoom
            logger.info("Testing Zoom API connectivity")
            zoom_test = self.zoom.test_connectivity()
            test_results["validation_results"]["zoom"] = zoom_test
            
            if zoom_test.get("success", False):
                test_results["would_execute"].append("Zoom: Deactivate user, transfer recordings")
            else:
                test_results["potential_issues"].append("Zoom: Service not yet implemented")
            
            # Determine overall readiness
            critical_tests = ["okta"]
            test_results["overall_ready"] = all(
                test_results["validation_results"].get(test, {}).get("success", False)
                or test_results["validation_results"].get(test, {}).get("user_exists", False)
                for test in critical_tests
            )
            
            test_results["end_time"] = datetime.now()
            duration = (test_results["end_time"] - test_results["start_time"]).total_seconds()
            
            logger.info(f"🧪 TEST MODE COMPLETED in {duration:.1f}s - Ready: {test_results['overall_ready']}")
            return test_results
            
        except Exception as e:
            logger.error(f"Test mode failed: {e}")
            test_results["potential_issues"].append(f"Test mode error: {e}")
            test_results["end_time"] = datetime.now()
            return test_results

    # ========== Helper Methods ==========
    
    def _log_termination_summary(self, results: Dict) -> None:
        """Log a comprehensive termination summary."""
        try:
            user_email = results["user_email"]
            overall_success = results["overall_success"]
            phase_success = results["phase_success"]
            
            if overall_success:
                status = "COMPLETED SUCCESSFULLY"
                emoji = "✅"
            elif any(phase_success.values()):
                status = "COMPLETED WITH ISSUES"
                emoji = "⚠️"
            else:
                status = "FAILED"
                emoji = "❌"
            
            logger.info(f"{emoji} TERMINATION {status}: {user_email}")
            
            # Log phase status
            phase_status = []
            for phase, success in phase_success.items():
                icon = "✅" if success else "❌"
                phase_status.append(f"{icon} {phase.title()}")
            
            if phase_status:
                logger.info(f"Phase Status: {' | '.join(phase_status)}")
            
            # Log summary
            for item in results.get("summary", []):
                logger.info(f"  {item}")
            
            # Log errors
            for error in results.get("errors", []):
                logger.error(f"  • {error}")
            
            # Log warnings
            for warning in results.get("warnings", []):
                logger.warning(f"  • {warning}")
            
            duration = results.get("duration_seconds", 0)
            logger.info(f"Duration: {duration:.1f} seconds")
            
        except Exception as e:
            logger.error(f"Failed to log termination summary: {e}")

    def _log_batch_summary(self, total_processed: int, total_successful: int, processed_users: List[Dict]) -> None:
        """Log batch processing summary."""
        try:
            success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
            
            if success_rate == 100:
                status = "ALL SUCCESSFUL ✅"
            elif success_rate >= 80:
                status = "MOSTLY SUCCESSFUL ⚠️"
            else:
                status = "ISSUES DETECTED ❌"
            
            logger.info(f"BATCH TERMINATION: {status}")
            logger.info(f"Total Processed: {total_processed}")
            logger.info(f"Successful: {total_successful}")
            logger.info(f"Success Rate: {success_rate:.1f}%")
            
            # Log user details (first 10)
            logger.info("User Results:")
            for user in processed_users[:10]:
                phases = user.get("phases", {})
                phase_icons = []
                for phase in ["okta", "microsoft", "google", "zoom"]:
                    if phase in phases:
                        icon = "✅" if phases[phase] else "❌"
                        phase_icons.append(f"{phase[0].upper()}{icon}")
                
                status_icon = "✅" if user["success"] else "❌"
                phase_summary = " ".join(phase_icons) if phase_icons else "No phases"
                logger.info(f"  {status_icon} {user['user_email']} ({phase_summary})")
            
            if len(processed_users) > 10:
                logger.info(f"  ... and {len(processed_users) - 10} more users")
            
        except Exception as e:
            logger.error(f"Failed to log batch summary: {e}")


# ========== Main Entry Points ==========

def run(
    *,
    ticket_id: Optional[str] = None,
    ticket_raw: Optional[Dict[str, Any]] = None,
    dry_run: bool = True,
    push_domo: bool = False,
) -> int:
    """
    Execute the termination workflow (backward compatibility).
    Simple mode - Okta only.
    """
    workflow = TerminationWorkflow()
    return workflow.execute_simple_termination(ticket_id, ticket_raw, dry_run)


def main():
    """Main entry point for termination automation."""
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("TERMINATION WORKFLOW STARTING")
    logger.info("=" * 80)
    
    try:
        # Initialize workflow
        workflow = TerminationWorkflow()
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "test" and len(sys.argv) > 2:
                # Test mode for single user
                user_email = sys.argv[2]
                manager_email = sys.argv[3] if len(sys.argv) > 3 else None
                
                logger.info(f"Running test mode for {user_email}")
                results = workflow.test_termination(user_email, manager_email)
                
                print(f"\n🧪 TEST MODE RESULTS for {user_email}")
                print(f"Overall Ready: {'✅ YES' if results['overall_ready'] else '❌ NO'}")
                print(f"\nWould Execute:")
                for action in results["would_execute"]:
                    print(f"  ✅ {action}")
                print(f"\nPotential Issues:")
                for issue in results["potential_issues"]:
                    print(f"  ⚠️ {issue}")
                
                sys.exit(0 if results["overall_ready"] else 1)
                
            elif command == "simple" and len(sys.argv) > 2:
                # Simple mode (Okta only)
                ticket_id = sys.argv[2]
                dry_run = "--dry-run" in sys.argv
                
                logger.info(f"Running simple termination for ticket {ticket_id}")
                exit_code = workflow.execute_simple_termination(ticket_id=ticket_id, dry_run=dry_run)
                sys.exit(exit_code)
                
            elif command == "batch":
                # Batch processing mode
                logger.info("Running batch termination processing")
                workflow.run_batch_processing()
                sys.exit(0)
                
            elif command not in ["test", "simple", "batch"]:
                # Single user termination (enterprise mode)
                user_email = sys.argv[1]
                manager_email = sys.argv[2] if len(sys.argv) > 2 else None
                phases = sys.argv[3].split(",") if len(sys.argv) > 3 else None
                
                logger.info(f"Running enterprise termination for {user_email}")
                results = workflow.execute_multi_phase_termination(user_email, manager_email, phases=phases)
                
                if results["overall_success"]:
                    print(f"✅ TERMINATION SUCCESSFUL for {user_email}")
                    sys.exit(0)
                else:
                    print(f"⚠️ TERMINATION COMPLETED WITH ISSUES for {user_email}")
                    sys.exit(1)
        else:
            # Default: Run batch processing
            logger.info("Running batch termination processing (default)")
            workflow.run_batch_processing()
            
    except KeyboardInterrupt:
        logger.info("Termination automation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in termination automation: {e}")
        sys.exit(1)
    
    logger.info("Termination automation completed")


if __name__ == "__main__":
    main()