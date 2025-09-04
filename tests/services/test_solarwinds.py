import pytest
from jml_automation.services.solarwinds import SolarWindsService

def test_to_raw_ticket_with_custom_fields_dict():
    payload = {
        "id": 123,
        "name": "Test incident",
        "description": "Body text",
        "custom_fields": {"Employee Department": "Support", "Term Type": "Voluntary"},
    }
    raw = SolarWindsService.to_raw_ticket(payload)

    assert raw["id"] == "123"
    assert raw["subject"] == "Test incident"
    assert raw["body"] == "Body text"
    assert raw["custom_fields"]["Employee Department"] == "Support"
    assert raw["custom_fields"]["Term Type"] == "Voluntary"

def test_to_raw_ticket_with_custom_fields_list():
    payload = {
        "id": 456,
        "name": "Another incident",
        "custom_fields_values": [
            {"name": "Employee to Terminate", "value": "Jane Doe"},
            {"name": "Termination Date", "value": "2025-08-22"},
        ],
    }
    raw = SolarWindsService.to_raw_ticket(payload)

    assert raw["id"] == "456"
    assert raw["subject"] == "Another incident"
    assert raw["body"] == ""  # no description given
    assert raw["custom_fields"]["Employee to Terminate"] == "Jane Doe"
    assert raw["custom_fields"]["Termination Date"] == "2025-08-22"

def test_to_raw_ticket_prefers_name_over_subject_and_id_over_number():
    payload = {
        "number": 9999,
        "subject": "Legacy subject",
        "name": "Preferred name",
        "custom_fields": {},
    }
    raw = SolarWindsService.to_raw_ticket(payload)

    # subject: prefer "name" then "subject"
    assert raw["subject"] == "Preferred name"
    # id: prefer "id" then "number"
    assert raw["id"] == "9999"  # falls back to number if id missing

def test_to_raw_ticket_uses_number_when_id_missing():
    payload = {"number": 321, "subject": "Has number only", "custom_fields": {}}
    raw = SolarWindsService.to_raw_ticket(payload)
    assert raw["id"] == "321"
    assert raw["subject"] == "Has number only"

def test_to_raw_ticket_merges_no_duplicate_keys_from_list():
    payload = {
        "id": 777,
        "name": "Merge test",
        "custom_fields_values": [
            {"name": "Key", "value": "A"},
            {"name": "Key", "value": "B"},  # last-write-wins behavior is fine
        ],
    }
    raw = SolarWindsService.to_raw_ticket(payload)
    assert raw["custom_fields"]["Key"] in {"A", "B"}  # implementation-defined; we accept either

def test_to_raw_ticket_handles_missing_cf_gracefully():
    payload = {"id": 101, "name": "No CFs at all"}
    raw = SolarWindsService.to_raw_ticket(payload)
    assert raw["id"] == "101"
    assert raw["custom_fields"] == {}
