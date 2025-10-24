"""
Test file for Iru (Device Management) Service.

Run this to validate Iru service integration and functionality.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from jml_automation.services.iru import IruService


def test_iru_service_initialization():
    """Test that Iru service can be initialized."""
    print("Testing Iru service initialization...")
    
    try:
        # Test with dry_run=True to avoid making actual API calls
        iru = IruService(dry_run=True)
        print("✅ Iru service initialized successfully in dry-run mode")
        return True
    except Exception as e:
        print(f"❌ Iru service initialization failed: {e}")
        return False


def test_iru_termination_dry_run():
    """Test Iru termination workflow in dry-run mode."""
    print("\nTesting Iru termination workflow (dry-run)...")
    
    test_email = "test.user@filevine.com"
    
    try:
        iru = IruService(dry_run=True)
        results = iru.execute_complete_termination(test_email)
        
        print(f"✅ Dry-run termination completed for {test_email}")
        print(f"   Results: {results}")
        
        # Validate expected result structure
        expected_keys = ['success', 'user_email', 'devices_found', 'devices_processed', 'errors']
        missing_keys = [key for key in expected_keys if key not in results]
        
        if missing_keys:
            print(f"⚠️  Missing expected keys in results: {missing_keys}")
            return False
        
        print("✅ Result structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Dry-run termination failed: {e}")
        return False


def test_individual_methods():
    """Test individual Iru service methods."""
    print("\nTesting individual Iru service methods (dry-run)...")
    
    test_email = "test.user@filevine.com"
    test_device_id = "test-device-123"
    
    try:
        iru = IruService(dry_run=True)
        
        # Test device lookup
        print("  Testing device lookup...")
        devices = iru.find_devices_by_user_email(test_email)
        print(f"  ✅ Device lookup completed (found {len(devices)} devices)")
        
        # Test unassignment
        print("  Testing user unassignment...")
        unassign_result = iru.unassign_user_from_device(test_device_id)
        print(f"  ✅ Unassignment completed (result: {unassign_result})")
        
        # Test blueprint change
        print("  Testing blueprint change...")
        blueprint_result = iru.change_device_blueprint(test_device_id, "Inventory Only")
        print(f"  ✅ Blueprint change completed (result: {blueprint_result})")
        
        # Test lock command
        print("  Testing lock command...")
        lock_result = iru.lock_device(test_device_id)
        print(f"  ✅ Lock command completed (result: {lock_result})")
        
        return True
        
    except Exception as e:
        print(f"❌ Individual method testing failed: {e}")
        return False


def main():
    """Run all Iru service tests."""
    print("🔧 IRU (DEVICE MANAGEMENT) SERVICE TEST")
    print("=" * 50)
    
    tests = [
        test_iru_service_initialization,
        test_iru_termination_dry_run,
        test_individual_methods
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Iru service is ready for integration.")
    else:
        print("⚠️  Some tests failed. Review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)