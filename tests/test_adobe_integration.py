"""
Test script for Adobe API integration
Allows manual testing of Adobe user deletion f        if success:
            print(f"Adobe termination completed for {email}")
            print("   - User deleted from Adobe account")
            print("   - User removed from SSO-Adobe Okta group")
            return True
        else:
            print(f"Adobe termination failed for {email}")
            return False
            
    except Exception as e:
        print(f"Error during Adobe termination: {e}")y
"""

import logging
from jml_automation.services.adobe import AdobeService

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_adobe_dry_run(email: str):
    """Test Adobe termination workflow in dry run mode."""
    print(f"\nTesting Adobe termination workflow for: {email}")
    print("=" * 60)
    
    try:
        # Initialize Adobe service in dry run mode
        adobe = AdobeService(dry_run=True)
        
        # Test 1: Basic connectivity
        print("\n1. Testing Adobe API connectivity...")
        connectivity = adobe.test_connection()
        if connectivity:
            print("Adobe API connection successful")
        else:
            print("Adobe API connection failed")
            return False
        
        # Test 2: Check Okta groups
        print(f"\n2. Checking Okta group membership for {email}...")
        group_membership = adobe.check_okta_groups(email)
        print(f"   Group membership: {group_membership}")
        
        # Test 3: Full termination workflow (dry run)
        print(f"\n3. Running Adobe termination workflow (DRY RUN)...")
        success = adobe.terminate_user(email)
        
        if success:
            print(f"Adobe test passed for {email}")
            print("   - Workflow completed successfully in dry run mode")
            return True
        else:
            print(f"Adobe test failed for {email}")
            return False
            
    except Exception as e:
        print(f"Error during Adobe test: {e}")
        return False

def test_adobe_production(email: str):
    """Test Adobe termination workflow in production mode (ACTUAL DELETION)."""
    print(f"\nPRODUCTION MODE: This will actually delete {email} from Adobe!")
    print("=" * 60)
    
    confirmation = input(f"Are you sure you want to delete {email} from Adobe? (yes/no): ")
    if confirmation.lower() != 'yes':
        print("Operation cancelled.")
        return False
    
    try:
        # Initialize Adobe service in production mode
        adobe = AdobeService(dry_run=False)
        
        # Test 1: Basic connectivity
        print("\n1. Testing Adobe API connectivity...")
        connectivity = adobe.test_connection()
        if connectivity:
            print("Adobe API connection successful")
        else:
            print("Adobe API connection failed")
            return False
        
        # Test 2: Check Okta groups
        print(f"\n2. Checking Okta group membership for {email}...")
        group_membership = adobe.check_okta_groups(email)
        print(f"   Group membership: {group_membership}")
        
        # Only proceed if user is in Adobe group
        if not group_membership.get("SSO-Adobe", False):
            print("User is not in SSO-Adobe group - no action needed")
            return True
        
        # Test 3: Full termination workflow (PRODUCTION)
        print(f"\n3. Running Adobe termination workflow (PRODUCTION)...")
        success = adobe.terminate_user(email)
        
        if success:
            print(f"Adobe termination completed for {email}")
            print("   - User deleted from Adobe account")
            print("   - User removed from SSO-Adobe group")
            return True
        else:
            print(f"Adobe termination failed for {email}")
            return False
            
    except Exception as e:
        print(f"Error during Adobe termination: {e}")
        return False

def main():
    """Main test function with user input."""
    print("Adobe API Integration Test")
    print("=" * 30)
    
    email = input("Enter email address to test: ").strip()
    if not email:
        print("No email provided. Exiting.")
        return
    
    print(f"\nSelected email: {email}")
    print("\nSelect test mode:")
    print("1. Dry run (safe testing, no actual changes)")
    print("2. Production (ACTUAL DELETION - use with caution)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        success = test_adobe_dry_run(email)
    elif choice == "2":
        success = test_adobe_production(email)
    else:
        print("Invalid choice. Exiting.")
        return
    
    print("\n" + "=" * 60)
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed - check logs for details")

if __name__ == "__main__":
    main()