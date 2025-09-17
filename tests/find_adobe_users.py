"""
Find users in SSO-Adobe group for testing deletion
"""

import logging
from jml_automation.services.okta import OktaService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def find_adobe_users():
    """Find users in SSO-Adobe group."""
    print("Finding users in SSO-Adobe group...")
    print("=" * 60)
    
    try:
        # Initialize Okta service
        okta = OktaService.from_env()
        
        # Find the SSO-Adobe group
        group_id = okta.find_group_id("SSO-Adobe")
        if not group_id:
            print("SSO-Adobe group not found")
            return
            
        print(f"Found SSO-Adobe group ID: {group_id}")
        
        # Get group members
        print("\nGetting group members...")
        members = okta.get_group_members(group_id)
        
        if not members:
            print("No members found in SSO-Adobe group")
            return
            
        print(f"\nFound {len(members)} members in SSO-Adobe group:")
        print("-" * 40)
        
        for i, member in enumerate(members[:10], 1):  # Show first 10
            email = member.get('profile', {}).get('email', 'Unknown')
            status = member.get('status', 'Unknown')
            print(f"{i:2d}. {email:<35} ({status})")
            
        if len(members) > 10:
            print(f"    ... and {len(members) - 10} more")
            
        # Suggest a test candidate
        active_members = [m for m in members if m.get('status') == 'ACTIVE']
        if active_members:
            test_user = active_members[0].get('profile', {}).get('email', 'Unknown')
            print(f"\nSuggested test user: {test_user}")
        
        return members
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    find_adobe_users()