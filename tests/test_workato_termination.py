#!/usr/bin/env python3
"""
Test Workato termination workflow with Okta integration.

This test:
1. Extracts termination email from a single ticket
2. Checks Okta groups (SSO-Workato and SSO-Workato_Operations)
3. Removes collaborator from respective Workato workspaces if in groups
4. Removes user from Okta groups after successful Workato removal

Supports dry run mode for safe testing.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from jml_automation.services.workato import WorkatoService
from jml_automation.parsers.solarwinds_parser import SolarWindsParser
from jml_automation.logger import setup_logger

def test_workato_termination_workflow(ticket_id: str = "63000", dry_run: bool = True):
    """
    Test the complete Workato termination workflow.
    
    Args:
        ticket_id: SolarWinds ticket ID to process
        dry_run: If True, run in dry run mode (safe for testing)
    """
    # Setup logging
    logger = setup_logger("workato_test", level=logging.INFO)
    
    logger.info("="*80)
    logger.info(f"WORKATO TERMINATION WORKFLOW TEST")
    logger.info(f"Ticket ID: {ticket_id}")
    logger.info(f"Dry Run Mode: {dry_run}")
    logger.info("="*80)
    
    try:
        # Step 1: Extract email from termination ticket
        logger.info("Step 1: Extracting email from termination ticket")
        parser = SolarWindsParser()
        
        # Parse the ticket to get termination details
        ticket_data = parser.parse_ticket(ticket_id)
        
        if not ticket_data:
            logger.error(f"Failed to parse ticket {ticket_id}")
            return False
        
        # Extract email from the parsed data
        email = None
        if hasattr(ticket_data, 'user_email') and ticket_data.user_email:
            email = ticket_data.user_email
        elif hasattr(ticket_data, 'employee_email') and ticket_data.employee_email:
            email = ticket_data.employee_email
        else:
            logger.error("No user email found in ticket data")
            logger.info(f"Available ticket data fields: {dir(ticket_data)}")
            return False
        
        logger.info(f"Successfully extracted email: {email}")
        
        # Step 2: Initialize Workato service with dry run mode
        logger.info("Step 2: Initializing Workato service")
        workato_service = WorkatoService(dry_run=dry_run)
        
        # Step 3: Test API connectivity
        logger.info("Step 3: Testing Workato API connectivity")
        if not workato_service.test_connection():
            logger.error("Workato API connectivity test failed")
            return False
        
        logger.info("Workato API connectivity test passed")
        
        # Step 4: Execute the complete termination workflow
        logger.info("Step 4: Executing Workato termination workflow")
        logger.info("-" * 60)
        
        success = workato_service.terminate_user(email)
        
        logger.info("-" * 60)
        
        if success:
            logger.info(f" Workato termination workflow completed successfully for {email}")
            
            if dry_run:
                logger.info(" DRY RUN MODE - No actual changes were made")
                logger.info("   • Okta group membership was checked (read-only)")
                logger.info("   • Workato collaborator removal was simulated")
                logger.info("   • Okta group removal was simulated")
            else:
                logger.info(" PRODUCTION MODE - Changes were applied")
                logger.info("   • User removed from Workato workspaces (if applicable)")
                logger.info("   • User removed from Okta groups (if applicable)")
        else:
            logger.error(f" Workato termination workflow failed for {email}")
            return False
        
        # Step 5: Summary
        logger.info("="*80)
        logger.info("WORKFLOW TEST SUMMARY")
        logger.info(f"Ticket ID: {ticket_id}")
        logger.info(f"User Email: {email}")
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Result: {'SUCCESS' if success else 'FAILED'}")
        logger.info("="*80)
        
        return success
        
    except Exception as e:
        logger.error(f"Fatal error in Workato workflow test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to run the Workato workflow test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Workato termination workflow")
    parser.add_argument(
        "--ticket-id", 
        default="63000", 
        help="SolarWinds ticket ID to test with (default: 63000)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        default=True,
        help="Run in dry run mode (default: True)"
    )
    parser.add_argument(
        "--execute", 
        action="store_true", 
        default=False,
        help="Run in production mode (WARNING: Makes actual changes)"
    )
    
    args = parser.parse_args()
    
    # Determine dry run mode
    dry_run = not args.execute  # If --execute is specified, dry_run is False
    
    if not dry_run:
        print("  WARNING: You are about to run in PRODUCTION mode!")
        print("   This will make actual changes to Workato and Okta.")
        response = input("   Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("   Operation cancelled.")
            return
    
    # Run the test
    success = test_workato_termination_workflow(
        ticket_id=args.ticket_id,
        dry_run=dry_run
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()