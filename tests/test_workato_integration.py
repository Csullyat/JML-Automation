"""Test Workato termination workflow with Okta integration."""

import sys
import os
import pytest
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket
from jml_automation.services.workato import WorkatoService

def test_workato_dry_run():
    """Test Workato termination workflow in dry run mode."""
    ticket_id = "64570"  # Marisa's termination ticket
    
    # Fetch ticket and extract email
    solarwinds = SolarWindsService.from_config()
    ticket_data = solarwinds.fetch_ticket(ticket_id)
    assert ticket_data, f"Could not fetch ticket {ticket_id}"
    
    user_email = extract_user_email_from_ticket(ticket_data)
    assert user_email, "Could not extract user email from ticket"
    
    # Test Workato workflow in dry run mode
    workato = WorkatoService(dry_run=True)
    
    # Test connection
    assert workato.test_connection(), "Workato connection test failed"
    
    # Check Okta groups
    groups = workato.check_okta_groups(user_email)
    assert isinstance(groups, dict), "Failed to check Okta groups"
    
    # Run termination workflow
    result = workato.terminate_user(user_email)
    assert result, "Workato termination workflow failed"
    
    print(f"Workato test passed for {user_email}")
    return True

if __name__ == "__main__":
    test_workato_dry_run()