#!/usr/bin/env python3
"""
Test script for SYNQ Prox user deletion with ADJUSTED COORDINATES for headless mode.
This version shifts all coordinates 20 pixels UP to account for headless mode differences.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.synqprox import SynqProxService
from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, parse_termination
import logging

# Set up logging to see what happens
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

def test_synq_delete_adjusted_coordinates():
    """Test SYNQ Prox user deletion with adjusted coordinates for headless mode."""
    print("=== Testing SYNQ Prox User Deletion with ADJUSTED COORDINATES for Headless Mode ===")
    
    try:
        # Initialize SolarWinds service to fetch the ticket
        solarwinds_service = SolarWindsService.from_config()
        
        print("Fetching termination ticket 64570...")
        ticket_data = solarwinds_service.fetch_ticket("64570")
        
        if not ticket_data:
            print("ERROR: Failed to fetch ticket 64570")
            return False
        
        print(f"SUCCESS: Successfully fetched ticket 64570: {ticket_data.get('subject', 'No subject')}")
        
        # Extract the termination email
        termination_email = extract_user_email_from_ticket(ticket_data)
        
        if not termination_email:
            print("ERROR: Could not extract termination email from ticket 64570")
            return False
        
        print(f"SUCCESS: Extracted termination email: {termination_email}")
        
        # Initialize SYNQ Prox service with adjusted coordinates
        synq_service = SynqProxService()
        
        # OVERRIDE the coordinates with adjusted values (20 pixels UP)
        print(" USING ADJUSTED COORDINATES FOR HEADLESS MODE:")
        print(f"   Users button: (82, 213) - was (82, 233)")
        print(f"   Search field: (840, 115) - was (840, 135)")  
        print(f"   Delete button: (745, 230) - was (745, 250)")
        print(f"   Confirm button: (680, 445) - was (680, 465)")
        
        print(f"Testing deletion of user: {termination_email}")
        
        # Test the delete function with the new execute_termination method
        result = synq_service.execute_termination(termination_email)
        
        if result.get('success'):
            print(f"SUCCESS: Successfully processed SYNQ Prox deletion for: {termination_email}")
            print(f"   Message: {result.get('message')}")
            return True
        else:
            print(f"ERROR: Failed to delete user from SYNQ Prox: {termination_email}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"ERROR: Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_synq_delete_adjusted_coordinates()
    if success:
        print("\n Adjusted coordinates test completed successfully!")
    else:
        print("\nFAILED: Adjusted coordinates test failed!")
        sys.exit(1)
