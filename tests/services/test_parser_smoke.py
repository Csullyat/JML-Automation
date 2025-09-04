from jml_automation.parsers.solarwinds_parser import parse_ticket, detect_type

def test_detect_and_parse_onboarding():
    raw = {
        "id": "1",
        "subject": "New Employee",
        "custom_fields": {
            "New Employee Name": "Jane Doe",
            "New Employee Personal Email Address": "jane@example.com",
            "New Employee Department": "Support",
            "Start Date": "2025-08-25",
        },
    }
    assert detect_type(raw) == "onboarding"
    t = parse_ticket(raw)
    assert t.user and t.user.email.endswith("@filevine.com")

def test_detect_and_parse_termination():
    raw = {
        "id": "2",
        "subject": "Termination",
        "custom_fields": {
            "Employee to Terminate": "John Doe",
            "Employee Department": "Support",
            "Termination Date": "2025-08-22",
            "Term Type": "Voluntary",
        },
    }
    assert detect_type(raw) == "termination"
    t = parse_ticket(raw)
    assert t.user and t.user.email.endswith("@filevine.com")
