#!/usr/bin/env python3
"""
Test script to verify that partner users don't trigger standard onboarding.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.okta import OktaService

def test_partner_detection():
    """Test the partner user detection functionality."""
    print("Testing partner user detection...")
    
    # Test with the existing partner user John Hamster
    okta = OktaService.from_env()
    test_email = "johnhamster@filevine.com"
    
    print(f"Testing partner detection for: {test_email}")
    
    # Check if user exists
    user_id = okta.find_user_by_email(test_email)
    if user_id:
        print(f"Found user with ID: {user_id}")
        
        # Test partner detection
        is_partner = okta.is_partner_user(user_id)
        print(f"Is partner user: {is_partner}")
        
        # Test by email method
        is_partner_by_email = okta.is_partner_user_by_email(test_email)
        print(f"Is partner user (by email): {is_partner_by_email}")
        
        # Get user groups
        user_groups = okta.get_user_groups(user_id)
        print(f"User groups:")
        for group in user_groups:
            group_name = group.get('profile', {}).get('name', '')
            print(f"  - {group_name}")
            
    else:
        print(f"User {test_email} not found in Okta")
        
if __name__ == "__main__":
    test_partner_detection()