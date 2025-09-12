"""Test SYNQ coordinate mapping on Users page."""

import pytest
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.services.synqprox import SynqProxService


def test_synq_users_coordinate_mapping():
    """Test coordinate mapping on SYNQ Users page."""
    service = SynqProxService()
    
    # Use a dummy email since we're just doing coordinate mapping
    test_email = "test@example.com"
    
    # This will login, navigate to users, then do coordinate mapping
    result = service.delete_user(test_email)
    
    print(f"Coordinate mapping test completed: {result}")
    print("Check tests/screenshots/ for the mapping images")
    
    assert result == True


if __name__ == "__main__":
    test_synq_users_coordinate_mapping()
