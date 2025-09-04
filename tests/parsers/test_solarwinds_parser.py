import pytest
from jml_automation.parsers import parse_ticket, detect_type
from jml_automation.models.ticket import OnboardingTicket, TerminationTicket
from jml_automation.services.solarwinds import SolarWindsService

def test_parse_onboarding_from_dict_fields():
    payload = {
        "id": 101,
        "name": "New Employee",
        "description": "Onboarding description",
        "custom_fields": {
            "New Employee Name": "Jane Doe",
            "New Employee Personal Email Address": "jane@example.com",
            "New Employee Department": "Support",
            "Start Date": "2025-08-25",
        },
    }
    raw = SolarWindsService.to_raw_ticket(payload)
    assert detect_type(raw) == "onboarding"
    t = parse_ticket(raw)
    assert isinstance(t, OnboardingTicket)
    assert t.user.first_name == "Jane"
    assert t.user.last_name == "Doe"
    assert t.user.email.endswith("@filevine.com")

def test_parse_termination_from_list_fields():
    payload = {
        "id": 202,
        "name": "Termination",
        "custom_fields_values": [
            {"name": "Employee to Terminate", "value": "John Doe"},
            {"name": "Employee Department", "value": "Support"},
            {"name": "Termination Date", "value": "2025-08-22"},
            {"name": "Term Type", "value": "Voluntary"},
            {"name": "CJIS Cleared?", "value": "No"},
        ],
    }
    raw = SolarWindsService.to_raw_ticket(payload)
    assert detect_type(raw) == "termination"
    t = parse_ticket(raw)
    assert isinstance(t, TerminationTicket)
    assert t.user.first_name == "John"
    assert t.user.last_name == "Doe"
    assert t.term_type == "Voluntary"
    assert t.cjis_cleared is False
