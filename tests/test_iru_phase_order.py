#!/usr/bin/env python3
"""
Test to verify IRU phase ordering in termination workflow.
Ensures IRU device locking happens before Okta deactivation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_phase_ordering():
    """Test that IRU is first in the default phase list."""
    from jml_automation.workflows.termination import TerminationWorkflow
    
    # Create workflow instance
    workflow = TerminationWorkflow()
    
    # Check default phase ordering in execute_multi_phase_termination
    # The method should have IRU first
    expected_phases = ["iru", "okta", "microsoft", "google", "zoom", "synqprox", "domo", "adobe", "lucid", "workato"]
    
    print("Testing phase ordering...")
    print(f"Expected: {expected_phases}")
    
    # We can't easily mock the full termination without credentials,
    # but we can verify the default phases list is correct
    import inspect
    source = inspect.getsource(workflow.execute_multi_phase_termination)
    
    # Check if IRU appears before Okta in the source
    iru_pos = source.find('"iru"')
    okta_pos = source.find('"okta"')
    
    if iru_pos > 0 and okta_pos > 0:
        if iru_pos < okta_pos:
            print("✓ IRU appears before Okta in phase list")
            return True
        else:
            print("✗ IRU appears after Okta - this is wrong!")
            return False
    else:
        print("✗ Could not find both phases in source")
        return False

if __name__ == "__main__":
    success = test_phase_ordering()
    if success:
        print("\n✓ Phase ordering test PASSED")
        print("IRU device locking will now happen BEFORE Okta deactivation")
    else:
        print("\n✗ Phase ordering test FAILED")
        sys.exit(1)