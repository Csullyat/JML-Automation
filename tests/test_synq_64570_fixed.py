#!/usr/bin/env python3
"""
Test SYNQ Prox termination with fixed TAB login logic using ticket 64570.
"""

import sys
import os
sys.path.append('src')

from jml_automation.services.synqprox import SynqProxService
from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket

def test_synq_termination_64570():
    """Test complete SYNQ Prox termination for ticket 64570 with fixed login."""
    print(" Testing SYNQ Prox Termination for Ticket 64570")
    print("=" * 60)
    
    try:
        # Fetch ticket 64570
        print(" Step 1: Fetching termination ticket 64570...")
        solarwinds_service = SolarWindsService.from_config()
        ticket_data = solarwinds_service.fetch_ticket("64570")
        
        if not ticket_data:
            print("ERROR: Failed to fetch ticket 64570")
            return False
        
        print(f"SUCCESS: Ticket fetched: {ticket_data.get('subject', 'No subject')}")
        
        # Extract termination email
        print(" Step 2: Extracting termination email...")
        termination_email = extract_user_email_from_ticket(ticket_data)
        
        if not termination_email:
            print("ERROR: Could not extract termination email")
            return False
        
        print(f"SUCCESS: Termination email: {termination_email}")
        
        # Execute SYNQ Prox termination with fixed login
        print(" Step 3: Executing SYNQ Prox termination...")
        print(f"   Target user: {termination_email}")
        print("   Using: Fixed TAB login sequence")
        print("   Mode: Headless")
        
        synq_service = SynqProxService()
        result = synq_service.execute_termination(termination_email)
        
        # Display results
        print("\\n" + "=" * 60)
        print(" TERMINATION RESULTS")
        print("=" * 60)
        print(f"Target Email: {result.get('user_email', 'Unknown')}")
        print(f"Success: {result.get('success', False)}")
        print(f"Message: {result.get('message', 'No message')}")
        
        if result.get('error'):
            print(f"Error: {result.get('error')}")
        
        if result.get('success'):
            print("\\n SYNQ PROX TERMINATION COMPLETED SUCCESSFULLY!")
            print(" Check screenshots/ directory for process images")
        else:
            print("\\nFAILED: SYNQ PROX TERMINATION FAILED")
            print(" Check logs for detailed error information")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\\nERROR: Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_synq_termination_64570()
    print(f"\\n Final Result: {'SUCCESS' if success else 'FAILED'}")