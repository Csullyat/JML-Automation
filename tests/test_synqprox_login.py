#!/usr/bin/env python3
"""Test script for SYNQ Prox login with Enter key method."""

import os
import sys
sys.path.insert(0, 'src')

from jml_automation.services.synqprox import SynqProxService
from jml_automation.logger import logger

def test_synqprox_login():
    """Test SYNQ Prox login process with screenshots."""
    logger.info("TEST: TESTING SYNQ PROX LOGIN WITH ENTER KEY METHOD")
    logger.info("=" * 60)
    
    # Create service instance
    service = SynqProxService()
    
    # Test email for deletion (use a test email that won't cause issues)
    test_email = "test@example.com"
    
    try:
        # Execute termination which includes login process
        logger.info(f"Testing SYNQ Prox termination process for: {test_email}")
        result = service.execute_termination(test_email)
        
        logger.info(" TERMINATION RESULT:")
        logger.info(f"   Success: {result.get('success', False)}")
        logger.info(f"   Message: {result.get('message', 'No message')}")
        if result.get('error'):
            logger.info(f"   Error: {result.get('error')}")
        
        # Check if screenshots were created
        screenshot_dir = "screenshots"
        if os.path.exists(screenshot_dir):
            screenshots = [f for f in os.listdir(screenshot_dir) if f.endswith('.png')]
            logger.info(f" SCREENSHOTS CREATED ({len(screenshots)} total):")
            for screenshot in sorted(screenshots):
                logger.info(f"   SUCCESS: {screenshot}")
        else:
            logger.warning("ERROR: No screenshots directory found")
        
        return result
        
    except Exception as e:
        logger.error(f"ERROR: Test failed with exception: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    # Ensure screenshots directory exists
    os.makedirs("screenshots", exist_ok=True)
    
    # Run the test
    result = test_synqprox_login()
    
    # Summary
    print("\n" + "=" * 60)
    if result.get('success'):
        print("SUCCESS: SYNQ PROX TEST COMPLETED SUCCESSFULLY")
    else:
        print("ERROR: SYNQ PROX TEST FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")
    print("=" * 60)