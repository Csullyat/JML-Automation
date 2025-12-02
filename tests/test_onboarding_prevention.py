#!/usr/bin/env python3
"""
Test script to verify the onboarding prevention works by simulating onboarding workflow.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.okta import OktaService

def test_onboarding_detection():
    """Test if the onboarding workflow would detect John as a partner user."""
    print("Testing onboarding prevention detection...")
    
    # Test with the partner user John Hamster
    okta = OktaService.from_env()
    test_email = "johnhamster@filevine.com"
    
    print(f"Checking if onboarding would skip for: {test_email}")
    
    # Get user ID
    user_id = okta.find_user_by_email(test_email)
    if user_id:
        print(f"Found user with ID: {user_id}")
        
        # This is the exact check used in onboarding.py
        is_partner = okta.is_partner_user(user_id)
        
        if is_partner:
            print("✅ SUCCESS: Onboarding workflow would SKIP standard provisioning")
            print("   - No baseline groups would be added")
            print("   - No Microsoft 365 provisioning would occur")
            print("   - Access limited to partner groups only")
        else:
            print("❌ FAILURE: User would get full employee onboarding")
            
        # Check current groups to see what partner rules assigned
        user_groups = okta.get_user_groups(user_id)
        partner_groups = []
        employee_groups = []
        
        for group in user_groups:
            group_name = group.get('profile', {}).get('name', '')
            if group_name.startswith('Partner - ') or 'Partner' in group_name:
                partner_groups.append(group_name)
            elif group_name in ['Filevine Employees', 'All Employees', 'Everyone']:
                employee_groups.append(group_name)
                
        print(f"\nPartner-specific groups: {partner_groups}")
        print(f"Standard employee groups: {employee_groups}")
        
        if employee_groups:
            print("⚠️  WARNING: User has standard employee groups - may have been auto-assigned by rules")
            
    else:
        print(f"User {test_email} not found in Okta")
        
if __name__ == "__main__":
    test_onboarding_detection()