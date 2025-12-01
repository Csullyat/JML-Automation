#!/usr/bin/env python3
"""
Test script to verify Microsoft group assignment works after fixes.
"""

import sys
import os
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.services.microsoft import MicrosoftService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_exists_check():
    """Test the user existence checking."""
    try:
        ms = MicrosoftService()
        test_email = "regismichaelstorey@filevine.com"  # The user from the failed logs
        
        logger.info(f"Testing user existence for {test_email}")
        exists = ms._check_user_exists_in_exchange(test_email, max_retries=2)
        
        if exists:
            logger.info(f"User {test_email} exists in Exchange")
            return True
        else:
            logger.warning(f"User {test_email} does not exist in Exchange yet")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    test_user_exists_check()