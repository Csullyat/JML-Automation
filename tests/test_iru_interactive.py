"""
Interactive Iru Device Termination Test

This test allows you to provide a user email and perform real device operations:
1. Find devices assigned to the user
2. Unassign user from devices  
3. Change blueprint to "Inventory Only"
4. Send lock commands

Usage:
  python test_iru_interactive.py <user_email>
  
Example:
  python test_iru_interactive.py john.doe@filevine.com
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_iru_device_termination(user_email: str):
    """Test real Iru device termination for a specific user."""
    
    print("=" * 60)
    print("IRU DEVICE TERMINATION TEST")
    print("=" * 60)
    print(f"Target User: {user_email}")
    print(f"Operations: Find → Unassign → Blueprint Change → Lock")
    print("=" * 60)
    
    try:
        from jml_automation.services.iru import IruService
        
        # Initialize service in LIVE mode (dry_run=False)
        print("Initializing Iru service...")
        service = IruService(dry_run=False)
        print("Iru service initialized successfully")
        print(f"   Base URL: {service.base_url}")
        print()
        
        # Step 1: Find devices for user
        print(f"Step 1: Finding devices for {user_email}...")
        devices = service.find_devices_by_user_email(user_email)
        
        if not devices:
            print("No devices found for this user")
            return {"success": True, "message": "No devices found - nothing to process"}
        
        print(f"Found {len(devices)} device(s):")
        for i, device in enumerate(devices, 1):
            device_name = device.get('device_name') or device.get('name', 'Unknown Device')
            device_id = device.get('device_id') or device.get('id', 'No ID')
            serial = device.get('serial_number', 'N/A')
            print(f"   {i}. {device_name} (ID: {device_id}, Serial: {serial})")
        print()
        
        # Confirm before proceeding
        print("WARNING: This will perform REAL operations on the devices above!")
        print("   - Unassign user from devices")
        print("   - Change blueprint to 'Inventory Only'") 
        print("   - Send lock commands to devices")
        print()
        
        # Ask for confirmation
        confirm = input("Do you want to proceed? (yes/no): ").lower().strip()
        if confirm not in ['yes', 'y']:
            print("Operation cancelled by user")
            return {"success": False, "message": "Cancelled by user"}
        
        print()
        print("Proceeding with device termination...")
        
        # Execute the full termination workflow
        results = service.execute_complete_termination(user_email)
        
        # Display detailed results
        print()
        print("=" * 60)
        print("TERMINATION RESULTS")
        print("=" * 60)
        
        if results.get("success"):
            print("Overall Status: SUCCESS")
        else:
            print("Overall Status: FAILED")
        
        print(f"User Email: {results.get('user_email')}")
        print(f"Devices Found: {results.get('devices_found', 0)}")
        print(f"Devices Processed: {results.get('devices_processed', 0)}")
        print(f"Unassignments: {results.get('unassignment_success', 0)}")
        print(f"Blueprint Changes: {results.get('blueprint_change_success', 0)}")
        print(f"Lock Commands: {results.get('lock_command_success', 0)}")
        print(f"Duration: {results.get('duration', 0):.1f}s")
        
        # Show device details
        device_details = results.get('device_details', [])
        if device_details:
            print()
            print("DEVICE OPERATION DETAILS:")
            for i, device in enumerate(device_details, 1):
                print(f"   Device {i}: {device['device_name']} ({device['device_id']})")
                print(f"      Unassignment: {'SUCCESS' if device['unassignment'] else 'FAILED'}")
                print(f"      Blueprint Change: {'SUCCESS' if device['blueprint_change'] else 'FAILED'}")
                print(f"      Lock Command: {'SUCCESS' if device['lock_command'] else 'FAILED'}")
        
        # Show errors if any
        errors = results.get('errors', [])
        if errors:
            print()
            print("ERRORS ENCOUNTERED:")
            for error in errors:
                print(f"   - {error}")
        
        print("=" * 60)
        return results
        
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def main():
    """Main function to handle command line arguments."""
    
    if len(sys.argv) != 2:
        print("Usage: python test_iru_interactive.py <user_email>")
        print("Example: python test_iru_interactive.py john.doe@filevine.com")
        sys.exit(1)
    
    user_email = sys.argv[1].strip()
    
    # Basic email validation
    if '@' not in user_email or '.' not in user_email:
        print(f"Invalid email format: {user_email}")
        sys.exit(1)
    
    # Run the test
    result = test_iru_device_termination(user_email)
    
    # Exit with appropriate code
    if result.get("success"):
        print("\nTest completed successfully!")
        sys.exit(0)
    else:
        print("\nTest failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()