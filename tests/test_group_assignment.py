"""
Test script to validate Microsoft 365 group assignment improvements.
This script simulates the timing and retry logic improvements.
"""

import time
from jml_automation.services.microsoft import MicrosoftService

def test_group_assignment_timing():
    """Test the improved group assignment with better timing."""
    
    # Test with a known user (use a test account or existing user)
    test_user = "regismichaelstorey@filevine.com"  # Recent user from logs
    test_department = "SDR - Sales Development Reps"
    
    print(f"Testing Microsoft 365 group assignment for: {test_user}")
    print(f"Department: {test_department}")
    print("=" * 60)
    
    ms = MicrosoftService()
    
    try:
        results = ms.add_user_to_groups_by_department(test_user, test_department)
        
        print(f"Results: {results}")
        print(f"Success: {results.get('success', False)}")
        print(f"Groups added: {results.get('groups_added', [])}")
        print(f"Groups failed: {results.get('groups_failed', [])}")
        print(f"Errors: {results.get('errors', [])}")
        
        return results.get('success', False)
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_group_assignment_timing()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")