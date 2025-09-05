"""
Test script for individual application termination.

This test allows you to:
1. Provide a termination ticket number
2. Choose which application to terminate
3. Follow the correct termination process:
   - Transfer data to transfer_to_email if possible
   - Delete user from the app
   - Remove user from app-specific Okta groups
"""

import sys
from pathlib import Path
import logging
from typing import Optional
import yaml

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from jml_automation.workflows.termination import TerminationWorkflow
from jml_automation.parsers import fetch_ticket, parse_ticket
from jml_automation.models.ticket import TerminationTicket
from jml_automation.services.okta import OktaService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SingleAppTerminator:
    """Handle termination for individual applications following the correct process."""
    
    def __init__(self):
        self.okta = OktaService.from_config()
        from jml_automation.utils.yaml_loader import load_yaml
        
        # Fix the path - load from absolute path
        config_path = Path(__file__).parent.parent / "config" / "termination_order.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            import yaml
            self.termination_config = yaml.safe_load(f)
        self.app_group_mapping = self.termination_config.get("termination", {}).get("okta_groups_to_remove", {})
        
    def terminate_user_from_app(self, ticket_id: str, app_name: str, dry_run: bool = True):
        """
        Terminate a user from a specific application.
        
        Args:
            ticket_id: SolarWinds ticket ID
            app_name: Application name (microsoft, google, zoom, etc.)
            dry_run: If True, just show what would happen
        """
        logger.info(f"Starting {app_name} termination for ticket {ticket_id}")
        
        # Step 1: Fetch and parse ticket
        try:
            raw_ticket = fetch_ticket(ticket_id)
            ticket = parse_ticket(raw_ticket)
            
            if not isinstance(ticket, TerminationTicket):
                logger.error(f"Ticket {ticket_id} is not a termination ticket")
                return {"success": False, "error": "Not a termination ticket"}
                
        except Exception as e:
            logger.error(f"Failed to fetch/parse ticket {ticket_id}: {e}")
            return {"success": False, "error": f"Ticket fetch/parse failed: {e}"}
        
        # Extract user info
        if not ticket.user or not ticket.user.email:
            logger.error("No user email found in ticket")
            return {"success": False, "error": "No user email found"}
            
        user_email = ticket.user.email
        transfer_email = ticket.transfer_to_email
        
        logger.info(f"User: {user_email}")
        logger.info(f"Transfer email: {transfer_email or 'None specified'}")
        
        if dry_run:
            logger.info("=== DRY RUN - No actual changes will be made ===")
            
        # Step 2: Get Okta user ID
        try:
            okta_user = self.okta.get_user_by_email(user_email)
            if not okta_user:
                logger.error(f"User {user_email} not found in Okta")
                return {"success": False, "error": "User not found in Okta"}
            user_id = okta_user.get("id")
            if not user_id:
                logger.error("No user ID returned from Okta")
                return {"success": False, "error": "No user ID found"}
        except Exception as e:
            logger.error(f"Failed to find user in Okta: {e}")
            return {"success": False, "error": f"Okta lookup failed: {e}"}
        
        # Step 3: Execute termination process
        result = {
            "success": True,
            "user_email": user_email,
            "app": app_name,
            "transfer_email": transfer_email,
            "actions": [],
            "errors": []
        }
        
        # Step 3a: Data transfer (only for apps that have transferable data)
        apps_with_data_transfer = ["microsoft", "google", "zoom"]
        
        if app_name in apps_with_data_transfer:
            if not transfer_email:
                # For applications that need manager email, try to extract from ticket
                from jml_automation.parsers.solarwinds_parser import extract_manager_email_from_ticket
                manager_email = extract_manager_email_from_ticket(dict(raw_ticket))
                if manager_email:
                    transfer_email = manager_email
                    result["transfer_email"] = transfer_email
                    logger.info(f"Using manager email as transfer target: {manager_email}")
                else:
                    # Fallback to Okta lookup for apps that support it
                    if app_name in ["microsoft", "google"]:
                        manager_email = self._get_manager_email(user_email)
                        if manager_email:
                            transfer_email = manager_email
                            result["transfer_email"] = transfer_email
                            logger.info(f"Using manager email from Okta as transfer target: {manager_email}")
        
            if transfer_email:
                transfer_result = self._transfer_data(app_name, user_email, transfer_email, dry_run)
                result["actions"].append(f"Data transfer: {transfer_result}")
            else:
                result["actions"].append("Data transfer: Skipped (no transfer email)")
        else:
            result["actions"].append(f"Data transfer: Not applicable for {app_name}")
            
        # Step 3b: Delete user from application
        delete_result = self._delete_from_app(app_name, user_email, transfer_email, user_id, dry_run)
        result["actions"].append(f"User deletion: {delete_result}")
        
        # Step 3c: Remove from app-specific Okta groups
        groups_result = self._remove_from_app_groups(app_name, user_id, dry_run)
        result["actions"].append(f"Group removal: {groups_result}")
        
        logger.info(f"Termination completed for {app_name}")
        return result
    
    def _get_manager_email(self, user_email: str) -> Optional[str]:
        """Get manager email for the user from Okta."""
        try:
            user = self.okta.get_user_by_email(user_email)
            if user and user.get("profile", {}).get("manager"):
                manager_info = user["profile"]["manager"]
                # If manager_info is a display name like "Peay, Matthew", we need to look it up
                if "@" not in manager_info:
                    # Try to find the manager by display name or lookup
                    logger.info(f"Manager display name found: {manager_info}, looking up email...")
                    # This is a display name, we need to find the actual email
                    # For now, return None and let the user know we need the email address
                    logger.warning(f"Manager info '{manager_info}' is not an email address")
                    return None
                else:
                    return manager_info
        except Exception as e:
            logger.warning(f"Could not get manager email for {user_email}: {e}")
        return None
    
    def _transfer_data(self, app_name: str, user_email: str, transfer_email: str, dry_run: bool) -> str:
        """Transfer user data to specified email."""
        if dry_run:
            return f"Would transfer {app_name} data from {user_email} to {transfer_email}"
            
        # TODO: Implement actual data transfer logic for each app
        if app_name == "microsoft":
            # Use Microsoft service to transfer OneDrive, Exchange, etc.
            # Special process: Convert mailbox to shared, add manager as delegate
            return f"Microsoft: Convert mailbox to shared, add manager as delegate, transfer OneDrive"
        elif app_name == "google":
            # Use Google service to transfer Drive, Calendar, etc.
            return f"Google data transfer initiated (Drive, Calendar, Gmail)"
        elif app_name == "zoom":
            # Transfer recordings, contacts
            return f"Zoom data transfer initiated (recordings, contacts)"
        else:
            return f"Data transfer not implemented for {app_name}"
    
    def _delete_from_app(self, app_name: str, user_email: str, transfer_email: Optional[str], user_id: str, dry_run: bool) -> str:
        """Delete user from the specific application."""
        if dry_run:
            if app_name == "microsoft":
                return f"Would execute Microsoft termination: convert {user_email} mailbox to shared, add delegate access, remove M365 license"
            elif app_name == "domo":
                # Check if user is in Domo groups for dry run
                domo_groups = self.app_group_mapping.get(app_name, [])
                if domo_groups:
                    user_domo_groups = self.okta.get_user_groups_by_names(user_id, domo_groups)
                    if user_domo_groups:
                        return f"Would execute Domo termination: user in groups {', '.join(user_domo_groups)}, would delete from Domo"
                    else:
                        return "Would skip Domo termination: user not in Domo groups"
                return "Would check Domo groups and conditionally terminate"
            else:
                return f"Would delete user {user_email} from {app_name}"
            
        # Implement actual deletion logic for each app
        if app_name == "microsoft":
            try:
                from jml_automation.services.microsoft import MicrosoftTermination
                microsoft_service = MicrosoftTermination()
                
                # Use provided transfer_email (manager email)
                if not transfer_email:
                    return f"ERROR: No transfer email provided for {user_email}, cannot delegate mailbox"
                
                results = []
                
                # Step 1: Convert mailbox to shared
                try:
                    microsoft_service.convert_mailbox_to_shared(user_email)
                    results.append("✅ Mailbox converted to shared")
                except Exception as e:
                    results.append(f"❌ Mailbox conversion failed: {e}")
                
                # Step 2: Add manager as delegate
                try:
                    success = microsoft_service.delegate_mailbox_access(user_email, transfer_email)
                    if success:
                        results.append(f"✅ Delegated mailbox access to {transfer_email}")
                    else:
                        results.append(f"❌ Failed to delegate mailbox access to {transfer_email}")
                except Exception as e:
                    results.append(f"❌ Delegation failed: {e}")
                
                # Step 3: Remove M365 licenses
                try:
                    license_result = microsoft_service.remove_user_licenses(user_email)
                    if license_result.get("success"):
                        results.append(f"✅ Removed M365 licenses")
                    else:
                        results.append(f"❌ License removal failed: {license_result.get('error', 'Unknown error')}")
                except Exception as e:
                    results.append(f"❌ License removal failed: {e}")
                
                return "; ".join(results)
                
            except Exception as e:
                return f"ERROR: Microsoft termination failed: {e}"
                
        elif app_name == "google":
            try:
                from jml_automation.services.google import GoogleTerminationManager
                google_service = GoogleTerminationManager()
                
                # Use provided transfer_email (manager email)
                if not transfer_email:
                    return f"ERROR: No transfer email provided for {user_email}, cannot transfer Google data"
                
                results = []
                
                # Step 1: Transfer Google Drive data
                try:
                    transfer_success = google_service.transfer_user_data(user_email, transfer_email)
                    if transfer_success:
                        results.append("✅ Google Drive data transfer initiated")
                    else:
                        results.append("❌ Drive transfer failed")
                except Exception as e:
                    results.append(f"❌ Drive transfer failed: {e}")
                
                # Step 2: Delete user from Google Admin
                try:
                    delete_success = google_service.delete_user(user_email)
                    if delete_success:
                        results.append("✅ User deleted from Google Admin")
                    else:
                        results.append("❌ Failed to delete user from Google Admin")
                except Exception as e:
                    results.append(f"❌ User deletion failed: {e}")
                
                return "; ".join(results)
                
            except Exception as e:
                return f"ERROR: Google termination failed: {e}"
        elif app_name == "zoom":
            try:
                from jml_automation.services.zoom import ZoomTerminationManager
                zoom_service = ZoomTerminationManager()
                
                # Use provided transfer_email (manager email)
                if not transfer_email:
                    return f"ERROR: No transfer email provided for {user_email}, cannot transfer Zoom data"
                
                results = []
                
                # Step 1: Transfer Zoom data (recordings, webinars, meetings)
                try:
                    transfer_success = zoom_service.transfer_user_data(user_email, transfer_email)
                    if transfer_success:
                        results.append("✅ Zoom data transfer initiated (recordings, webinars, meetings)")
                    else:
                        results.append("❌ Zoom data transfer failed")
                except Exception as e:
                    results.append(f"❌ Zoom data transfer failed: {e}")
                
                # Step 2: Delete user from Zoom (frees license)
                try:
                    delete_success = zoom_service.delete_user(user_email, transfer_email)
                    if delete_success:
                        results.append("✅ User deleted from Zoom (license freed)")
                    else:
                        results.append("❌ Failed to delete user from Zoom")
                except Exception as e:
                    results.append(f"❌ User deletion failed: {e}")
                
                return "; ".join(results)
                
            except Exception as e:
                return f"ERROR: Zoom termination failed: {e}"
        elif app_name == "domo":
            # CONDITIONAL TERMINATION: Only process if user is in Domo group
            try:
                # Step 1: Check if user is in Domo Okta group
                domo_groups = self.app_group_mapping.get(app_name, [])
                if not domo_groups:
                    return "No Domo groups configured"
                
                # Check which Domo groups user is actually in
                user_domo_groups = self.okta.get_user_groups_by_names(user_id, domo_groups)
                
                if not user_domo_groups:
                    return "✅ User not in Domo groups, skipping termination"
                
                results = []
                results.append(f"🔍 User found in groups: {', '.join(user_domo_groups)}")
                
                # Step 2: Delete from Domo (if user was in groups)
                try:
                    from jml_automation.services.domo import DomoService
                    domo_service = DomoService()
                    termination_result = domo_service.execute_termination(user_email)
                    
                    if termination_result.get("success"):
                        verified = termination_result.get("verified", False)
                        if verified:
                            results.append("✅ User deleted from Domo and verified")
                        else:
                            results.append("⚠️ User deleted from Domo but verification failed")
                    else:
                        results.append(f"❌ Domo deletion failed: {termination_result.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    results.append(f"❌ Domo deletion failed: {e}")
                
                return "; ".join(results)
                
            except Exception as e:
                return f"ERROR: Domo conditional termination failed: {e}"
        else:
            return f"User deletion not implemented for {app_name}"
    
    def _remove_from_app_groups(self, app_name: str, user_id: str, dry_run: bool) -> str:
        """Remove user from app-specific Okta groups."""
        app_groups = self.app_group_mapping.get(app_name, [])
        
        if not app_groups:
            return f"No Okta groups configured for {app_name}"
            
        if dry_run:
            return f"Would remove from groups: {', '.join(app_groups)}"
            
        removed_groups = []
        failed_groups = []
        
        for group_name in app_groups:
            try:
                group_id = self.okta.find_group_id(group_name)
                if group_id:
                    self.okta.remove_from_groups(user_id, [group_id])
                    removed_groups.append(group_name)
                else:
                    failed_groups.append(f"{group_name} (not found)")
            except Exception as e:
                failed_groups.append(f"{group_name} (error: {e})")
        
        result_parts = []
        if removed_groups:
            result_parts.append(f"Removed from: {', '.join(removed_groups)}")
        if failed_groups:
            result_parts.append(f"Failed: {', '.join(failed_groups)}")
            
        return "; ".join(result_parts) if result_parts else "No groups processed"


def main():
    """Interactive test for single app termination."""
    print("=== Single Application Termination Test ===")
    
    # Get ticket ID
    ticket_id = input("Enter termination ticket ID: ").strip()
    if not ticket_id:
        print("No ticket ID provided.")
        return
    
    # Get application name
    available_apps = ["microsoft", "google", "zoom", "domo", "lucid", "adobe", "workato"]
    print(f"Available applications: {', '.join(available_apps)}")
    app_name = input("Enter application name: ").strip().lower()
    
    if app_name not in available_apps:
        print(f"Invalid application. Choose from: {', '.join(available_apps)}")
        return
    
    # Get dry run preference
    dry_run_input = input("Dry run? (y/n, default=y): ").strip().lower()
    dry_run = dry_run_input not in ['n', 'no', 'false']
    
    # Execute termination
    terminator = SingleAppTerminator()
    result = terminator.terminate_user_from_app(ticket_id, app_name, dry_run)
    
    # Display results
    print("\n=== TERMINATION RESULTS ===")
    print(f"Success: {result.get('success', False)}")
    print(f"User: {result.get('user_email', 'Unknown')}")
    print(f"Application: {result.get('app', 'Unknown')}")
    print(f"Transfer Email: {result.get('transfer_email', 'None')}")
    
    if result.get('actions'):
        print("\nActions performed:")
        for action in result['actions']:
            print(f"  - {action}")
    
    if result.get('errors'):
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
