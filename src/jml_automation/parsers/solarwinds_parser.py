from __future__ import annotations
import logging
from datetime import datetime, date
from typing import Literal, Optional, TypedDict, Union, Dict, List
from unidecode import unidecode
from jml_automation.models.ticket import UserProfile, OnboardingTicket, TerminationTicket
from jml_automation.services.solarwinds import SolarWindsService, SWSDClientError

log = logging.getLogger(__name__)


# ---- Raw payload (simplified) -----------------------------------------------

class RawTicket(TypedDict, total=False):
    id: str
    subject: str
    body: str
    custom_fields: dict


# ---- Helpers ----------------------------------------------------------------

def _split_name(full_name: Optional[str]) -> tuple[str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""
    parts = full_name.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return parts[0], ""

def _norm_email(s: Optional[str]) -> Optional[str]:
    s = (s or "").strip().lower()
    return s or None

def _phone_dash_10(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:]}"
    return s

def _to_bool(v: object) -> Optional[bool]:
    if v in (True, False):
        return bool(v)
    if isinstance(v, str):
        vs = v.strip().lower()
        if vs in {"yes", "y", "true", "t", "1"}:
            return True
        if vs in {"no", "n", "false", "f", "0"}:
            return False
    return None

def _to_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except Exception:
            continue
    return None

def _safe_build(model_cls, data: dict):
    """
    Build a Pydantic model while ignoring unknown fields.
    Works with Pydantic v2 via model_fields.
    """
    try:
        allowed = set(getattr(model_cls, "model_fields", {}).keys())
        filtered = {k: v for k, v in data.items() if k in allowed}
        return model_cls(**filtered)
    except Exception as e:
        log.error("Failed to build %s with data=%s: %s", getattr(model_cls, "__name__", model_cls), list(data.keys()), e)
        raise


# ---- Enhanced Email Extraction (from ticket_processor.py) ------------------

def _extract_email_with_regex(text: str) -> Optional[str]:
    """
    Extract email address from text using regex.
    Returns the first valid email found.
    """
    import re
    
    # Regex pattern for email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    matches = re.findall(email_pattern, text)
    if matches:
        # Return the first match (most likely the correct email)
        return matches[0]
    
    return None

def extract_email_from_field(field_value: Union[str, Dict], field_name: str = "") -> Optional[str]:
    """
    Extract email from various field formats.
    Handles both string values and nested user objects.
    Prioritizes actual email addresses over name-to-email conversion.
    """
    import re
    
    try:
        # Handle nested user objects (from custom_fields_values)
        if isinstance(field_value, dict):
            user_obj = field_value.get('user')
            if user_obj and isinstance(user_obj, dict):
                email = user_obj.get('email')
                if email:
                    return _norm_email(email)
            # Check the value field
            value = field_value.get('value')
            if value:
                # First try to extract actual email from the value
                extracted_email = _extract_email_with_regex(str(value))
                if extracted_email:
                    return _norm_email(extracted_email)
                field_value = str(value)  # Continue processing as string
            else:
                return None
        
        if not field_value:
            return None
            
        field_str = str(field_value).strip()
        
        # PRIORITY 1: Look for actual email addresses in the text using regex
        extracted_email = _extract_email_with_regex(field_str)
        if extracted_email:
            log.info(f"Extracted email from {field_name}: '{extracted_email}' from text: '{field_str}'")
            return _norm_email(extracted_email)
        
        # PRIORITY 2: Simple @ check for direct email format
        if '@' in field_str and '.' in field_str:
            return _norm_email(field_str)
        
        # Employee ID format (all digits)
        if field_str.isdigit():
            # This will need Okta lookup
            log.debug(f"Found employee ID {field_str} in {field_name}, needs Okta lookup")
            return f"LOOKUP_EMPLOYEE_ID:{field_str}"  # Special marker for later processing
        
        # Username format (alphanumeric but not all digits)
        if field_str.isalnum() and not field_str.isdigit():
            # Normalize Unicode characters to ASCII for email generation
            username_ascii = unidecode(field_str).lower()
            email = f"{username_ascii}@filevine.com"
            log.info(f"Converted username '{field_str}' to email '{email}'")
            return email
        
        log.warning(f"Unrecognized format in {field_name}: '{field_str}'")
        return None
        
    except Exception as e:
        log.error(f"Error extracting email from {field_name}: {e}")
        return None


def extract_user_email_from_ticket(ticket: Dict) -> Optional[str]:
    """
    Extract user email from a parsed termination ticket.
    Enhanced version from ticket_processor.py.
    """
    try:
        # Check custom_fields_values first (newer format)
        custom_fields_values = ticket.get('custom_fields_values', [])
        if custom_fields_values:
            for field in custom_fields_values:
                field_name = (field.get('name', '') or '').strip().lower()
                if field_name == 'employee to terminate':
                    email = extract_email_from_field(field, 'employee to terminate')
                    if email:
                        return email
        
        # Check custom_fields (older format)
        custom_fields = ticket.get('custom_fields', {})
        if custom_fields:
            # Try various field names
            for field_name in ['Employee to Terminate', 'employee_to_terminate', 'Employee Email']:
                if field_name in custom_fields:
                    email = extract_email_from_field(custom_fields[field_name], field_name)
                    if email:
                        return email
        
        # Legacy fallback
        employee_to_terminate = ticket.get('employee_to_terminate', '').strip()
        if employee_to_terminate:
            email = extract_email_from_field(employee_to_terminate, 'employee_to_terminate')
            if email:
                return email
        
        log.warning(f"No employee email found in ticket {ticket.get('id', 'unknown')}")
        return None
        
    except Exception as e:
        log.error(f"Error extracting user email from ticket: {e}")
        return None


def extract_manager_email_from_ticket(ticket: Dict) -> Optional[str]:
    """
    Extract manager email from a parsed termination ticket.
    Enhanced version from ticket_processor.py.
    """
    try:
        # Check custom_fields_values first (newer format)
        custom_fields_values = ticket.get('custom_fields_values', [])
        if custom_fields_values:
            for field in custom_fields_values:
                field_name = (field.get('name', '') or '').strip().lower()
                if field_name == 'transfer data':
                    email = extract_email_from_field(field, 'transfer data')
                    if email:
                        return email
        
        # Check custom_fields (older format)
        custom_fields = ticket.get('custom_fields', {})
        if custom_fields:
            # Try various field names
            for field_name in ['Transfer Data', 'transfer_data', 'Manager Email', 'Reports to Email']:
                if field_name in custom_fields:
                    email = extract_email_from_field(custom_fields[field_name], field_name)
                    if email:
                        return email
        
        # Legacy fallback fields
        transfer_data = ticket.get('transfer_data', '').strip()
        if transfer_data:
            email = extract_email_from_field(transfer_data, 'transfer_data')
            if email:
                return email
        
        # Check additional_info as last resort
        additional_info = ticket.get('additional_info', '').strip()
        if additional_info and '@' in additional_info:
            return _norm_email(additional_info)
        
        log.warning(f"No manager email found in ticket {ticket.get('id', 'unknown')}")
        return None
        
    except Exception as e:
        log.error(f"Error extracting manager email from ticket: {e}")
        return None


# ---- Public API -------------------------------------------------------------

def fetch_ticket(ticket_id: str) -> RawTicket:
    from jml_automation.services.solarwinds import SolarWindsService
    svc = SolarWindsService.from_config()
    return svc.fetch_ticket(ticket_id)  # type: ignore[return-value]


def detect_type(raw: RawTicket) -> Literal["onboarding", "termination", "unknown"]:
    cf = (raw.get("custom_fields") or {})

    onboarding_keys = {
        "New Employee Name",
        "New Employee Personal Email Address",
        "New Employee Department",
        "Start Date",
    }
    termination_keys = {
        "Employee to Terminate",
        "Termination Date",
        "Employee Department",
        "Term Type",
    }

    has_onboarding = any(k in cf for k in onboarding_keys)
    has_termination = any(k in cf for k in termination_keys)

    if has_onboarding and not has_termination:
        return "onboarding"
    if has_termination and not has_onboarding:
        return "termination"

    subject = (raw.get("subject") or "").lower()
    if "onboarding" in subject or "new employee" in subject:
        return "onboarding"
    if "termination" in subject or "offboarding" in subject:
        return "termination"
    return "unknown"


def parse_onboarding(raw: RawTicket) -> OnboardingTicket:
    cf = (raw.get("custom_fields") or {})

    full_name = cf.get("New Employee Name") or ""
    first, last = _split_name(full_name)

    # Enhanced email extraction
    email = None
    # Check for explicit email field first
    if "New Employee Email" in cf:
        email = _norm_email(cf.get("New Employee Email"))
    # Otherwise infer from name
    if not email and first and last:
        # Normalize Unicode characters to ASCII for email generation
        first_ascii = unidecode(first).replace(" ", "").lower()
        last_ascii = unidecode(last).replace(" ", "").lower()
        email = f"{first_ascii}{last_ascii}@filevine.com"

    # Build a user profile
    reports_to_field = cf.get("Reports to")
    initial_manager_display = None
    manager_email = None
    
    if reports_to_field:
        if isinstance(reports_to_field, dict):
            initial_manager_display = reports_to_field.get("value")
            # Enhanced manager extraction
            manager_email = extract_email_from_field(reports_to_field, "Reports to")
        else:
            initial_manager_display = reports_to_field
            manager_email = extract_email_from_field(reports_to_field, "Reports to")
    
    # Fallback to explicit manager email field
    if not manager_email:
        manager_email = _norm_email(cf.get("Reports to Email"))

    user = UserProfile(
        first_name=first,
        last_name=last,
        email=email or "",
        personal_email=_norm_email(cf.get("New Employee Personal Email Address")),
        title=(cf.get("New Employee Title") or None),
        phone_mobile=_phone_dash_10(cf.get("New Employee Phone Number")),
        department=(cf.get("New Employee Department") or None),
        manager_email=manager_email,
        manager_display=initial_manager_display,
        street_address=(cf.get("streetAddress") or None),
        city=(cf.get("city") or None),
        state=None,  # Will be set below if present
        zip_code=(cf.get("zipCode") or None),
        country_code=None,  # Will be set below if present
        time_zone=None,
    )

    # Extract state and country_code from formatted field names
    for fname, fval in cf.items():
        if "state - Formatted" in fname and fval:
            user.state = fval.strip()
        elif "countryCode - Formatted" in fname and fval:
            user.country_code = fval.strip()

    # Handle Reports to field for manager lookup (enhanced)
    if reports_to_field and isinstance(reports_to_field, dict):
        user_obj = reports_to_field.get("user")
        if user_obj:
            user.manager_email = user_obj.get("email")
            manager_name = user_obj.get("name")
            if manager_name:
                parts = manager_name.split()
                if len(parts) >= 2:
                    user.manager_display = f"{parts[-1]}, {' '.join(parts[:-1])}"

    data = {
        "ticket_id": str(raw.get("id", "")),
        "start_date": _to_date(cf.get("Start Date")),
        "onboarding_location": (cf.get("Onboarding Location") or None),
        "user": user,
        "office_location_after": (cf.get("Office Location After Onboarding") or None),
        "laptop_style": (cf.get("Laptop Style") or None),
        "delivery_time": (cf.get("delivery time") or None),
    }

    return _safe_build(OnboardingTicket, data)


def parse_termination(raw: RawTicket) -> TerminationTicket:
    """
    Parse termination ticket with enhanced field extraction.
    Handles all termination-specific custom fields from the extractor.
    """
    cf = (raw.get("custom_fields") or {})
    
    # Enhanced termination parsing with validation
    out = {
        "ticket_id": str(raw.get("id", "")),
        "ticket_number": raw.get("number"),
        "ticket_state": raw.get("state", "Unknown"),
        "ticket_created": raw.get("created_at", "Unknown"),
        "category": raw.get("category", {}).get("name") if raw.get("category") else None,
        "subcategory": raw.get("subcategory", {}).get("name") if raw.get("subcategory") else None
    }
    
    # Track required fields for termination
    required_fields = {"employee_to_terminate"}
    found_fields = set()
    
    # Parse custom fields for ALL termination data (enhanced from extractor)
    custom_fields_values = raw.get("custom_fields_values", [])
    if custom_fields_values:
        for f in custom_fields_values:
            try:
                label = f.get("name", "").strip()
                val = f.get("value", "").strip()
                
                if not val:
                    continue

                if label == "Employee to Terminate":
                    out["employee_to_terminate"] = val
                    found_fields.add("employee_to_terminate")
                elif label == "Employee Department":
                    out["employee_department"] = val
                elif label == "Termination Date":
                    out["termination_date"] = val
                elif label == "Date to remove access":
                    out["date_to_remove_access"] = val
                elif label == "Term Type":
                    out["term_type"] = val
                elif label == "Transfer Data":
                    out["transfer_data"] = val
                elif label == "Additional Information":
                    out["additional_info"] = val
                elif label == "Is this termination pre-hire date?":
                    out["is_pre_hire"] = val
                elif label == "CJIS Cleared? If yes, please inform Compliance (Kobe Andam or Sean Van Rooyen).":
                    out["cjis_cleared"] = val
                    
            except Exception as e:
                log.error(f"Error parsing field {label} for ticket {out.get('ticket_number', 'unknown')}: {e}")
                continue

    # Also check direct custom_fields dict (fallback)
    for label, val in cf.items():
        if not val:
            continue
            
        if label == "Employee to Terminate" and "employee_to_terminate" not in out:
            out["employee_to_terminate"] = str(val).strip()
            found_fields.add("employee_to_terminate")
        elif label == "Employee Department" and "employee_department" not in out:
            out["employee_department"] = str(val).strip()
        elif label == "Termination Date" and "termination_date" not in out:
            out["termination_date"] = str(val).strip()
        elif label == "Date to remove access" and "date_to_remove_access" not in out:
            out["date_to_remove_access"] = str(val).strip()
        elif label == "Term Type" and "term_type" not in out:
            out["term_type"] = str(val).strip()
        elif label == "Transfer Data" and "transfer_data" not in out:
            out["transfer_data"] = str(val).strip()

    # Extract employee name from ticket title if available (from extractor)
    ticket_name = raw.get("subject", "")
    if "Employee Termination" in ticket_name:
        # Extract name after "Employee Termination - "
        name_part = ticket_name.replace("Employee Termination - ", "").strip()
        if name_part:
            out["employee_name"] = name_part

    # Validate required fields (critical validation from extractor)
    missing_fields = required_fields - found_fields
    if missing_fields:
        log.warning(f"Ticket {out.get('ticket_number', 'unknown')} missing required fields: {', '.join(missing_fields)}")
        # Still proceed but log the issue

    # Enhanced email extraction for termination
    email = None
    employee_field = out.get("employee_to_terminate", "")
    
    if employee_field:
        email = extract_email_from_field(employee_field, "Employee to Terminate")
        # Handle employee ID lookups (marked with special prefix)
        if email and email.startswith("LOOKUP_EMPLOYEE_ID:"):
            employee_id = email.split(":", 1)[1]
            log.info(f"Employee ID {employee_id} needs Okta lookup")
            email = None  # Will be resolved later
    
    # Fallback to explicit email field
    if not email:
        email = _norm_email(cf.get("Employee Email"))
    
    # Extract name - enhanced logic
    full_name = out.get("employee_name") or employee_field or ""
    if '@' in full_name:  # If it's an email, extract name from email
        email_part = full_name.split('@')[0]
        parts = email_part.replace('.', ' ').split()
        if len(parts) >= 2:
            first, last = parts[0], parts[-1]
        else:
            first, last = email_part, ""
    else:
        first, last = _split_name(full_name)
    
    # If still no email and we have names, generate one
    if not email and first and last:
        # Normalize Unicode characters to ASCII for email generation
        first_ascii = unidecode(first).replace(" ", "").lower()
        last_ascii = unidecode(last).replace(" ", "").lower()
        email = f"{first_ascii}{last_ascii}@filevine.com"

    # Enhanced manager email extraction
    manager_email = None
    transfer_field = out.get("transfer_data")
    if transfer_field:
        manager_email = extract_email_from_field(transfer_field, "Transfer Data")
        # Handle employee ID lookups
        if manager_email and manager_email.startswith("LOOKUP_EMPLOYEE_ID:"):
            employee_id = manager_email.split(":", 1)[1]
            log.info(f"Manager ID {employee_id} needs Okta lookup")
            manager_email = None  # Will be resolved later

    user = UserProfile(
        first_name=first,
        last_name=last,
        email=email or "",
        department=out.get("employee_department"),
        manager_email=manager_email,
    )

    # Build final termination ticket with all enhanced fields
    data = {
        "ticket_id": str(raw.get("id", "")),
        "termination_date": _to_date(out.get("termination_date")),
        "remove_access_date": _to_date(out.get("date_to_remove_access")),
        "term_type": out.get("term_type"),
        "department": out.get("employee_department"),
        "pre_hire_termination": _to_bool(out.get("is_pre_hire")),
        "cjis_cleared": _to_bool(out.get("cjis_cleared")),
        "transfer_to_email": manager_email,
        "additional_info": out.get("additional_info"),
        "user": user,
        # Store raw parsed data for debugging
        "_raw_termination_data": out,
    }

    return _safe_build(TerminationTicket, data)


def parse_ticket(raw: RawTicket) -> Union[OnboardingTicket, TerminationTicket]:
    kind = detect_type(raw)
    if kind == "onboarding":
        return parse_onboarding(raw)
    if kind == "termination":
        return parse_termination(raw)
    raise ValueError(f"Unknown ticket type for id={raw.get('id')}")


# ---- Enhanced Termination Processing Functions (from extractor) -----------

def filter_termination_users(tickets: List[Dict]) -> List[Dict]:
    """
    Filter and parse termination tickets for active terminations.
    Enhanced version from termination_extractor.py.
    """
    # Active states for termination (more restrictive than service default)
    ACTIVE_STATES = {"Awaiting Input"}
    
    def should_parse(t: Dict) -> bool:
        return t.get("state") in ACTIVE_STATES

    filtered = [t for t in tickets if should_parse(t)]
    log.info(f"Filtered to {len(filtered)} active termination tickets")

    users = []
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(parse_termination_ticket_raw, t): t for t in filtered}
        for future in as_completed(futures):
            try:
                u = future.result()
                if u and "employee_to_terminate" in u:
                    users.append(u)
            except Exception as e:
                log.error(f"Parse error: {e}")

    log.info(f"Final parsed termination users: {len(users)} of {len(tickets)} tickets")
    return users


def parse_termination_ticket_raw(ticket: Dict) -> Dict:
    """
    Parse a raw termination ticket and extract employee information.
    Enhanced version from termination_extractor.py for raw ticket processing.
    """
    try:
        # Validate ticket has minimum required fields
        if not isinstance(ticket, dict):
            raise ValueError(f"Invalid ticket format: expected dict, got {type(ticket)}")
        
        if not ticket.get("number"):
            raise ValueError("Ticket is missing required field: number")
            
        out = {
            "ticket_id": ticket.get("id"),
            "ticket_number": ticket.get("number"),
            "ticket_state": ticket.get("state", "Unknown"),
            "ticket_created": ticket.get("created_at", "Unknown"),
            "category": ticket.get("category", {}).get("name") if ticket.get("category") else None,
            "subcategory": ticket.get("subcategory", {}).get("name") if ticket.get("subcategory") else None
        }
        
        # Track required fields for termination
        required_fields = {"employee_to_terminate"}
        found_fields = set()
        
        # Parse custom fields for termination data
        for f in ticket.get("custom_fields_values", []):
            try:
                label = f.get("name", "").strip()
                val = f.get("value", "").strip()
                
                if not val:
                    continue

                if label == "Employee to Terminate":
                    out["employee_to_terminate"] = val
                    found_fields.add("employee_to_terminate")
                elif label == "Employee Department":
                    out["employee_department"] = val
                elif label == "Termination Date":
                    out["termination_date"] = val
                elif label == "Date to remove access":
                    out["date_to_remove_access"] = val
                elif label == "Term Type":
                    out["term_type"] = val
                elif label == "Transfer Data":
                    out["transfer_data"] = val
                elif label == "Additional Information":
                    out["additional_info"] = val
                elif label == "Is this termination pre-hire date?":
                    out["is_pre_hire"] = val
                elif label == "CJIS Cleared? If yes, please inform Compliance (Kobe Andam or Sean Van Rooyen).":
                    out["cjis_cleared"] = val
                    
            except Exception as e:
                log.error(f"Error parsing field {label} for ticket {out['ticket_number']}: {e}")
                continue

        # Extract employee name from ticket title if available
        ticket_name = ticket.get("name", "")
        if "Employee Termination" in ticket_name:
            # Extract name after "Employee Termination - "
            name_part = ticket_name.replace("Employee Termination - ", "").strip()
            if name_part:
                out["employee_name"] = name_part

        # Validate required fields
        missing_fields = required_fields - found_fields
        if missing_fields:
            log.warning(f"Ticket {out['ticket_number']} missing required fields: {', '.join(missing_fields)}")
            return {}  # Return empty dict for invalid tickets

        return out
        
    except Exception as e:
        log.error(f"Critical error parsing ticket {ticket.get('number', 'Unknown')}: {str(e)}")
        return {}


def print_terminations(users: List[Dict]):
    """
    Print termination information in a readable format.
    Enhanced version from termination_extractor.py.
    """
    if not users:
        print("No active termination tickets found.")
        return
        
    print(f"\nACTIVE TERMINATION REQUESTS ({len(users)}):")
    print("=" * 80)
    
    for i, u in enumerate(users, 1):
        print(f"\nTERMINATION #{i}")
        print(f"Ticket: #{u.get('ticket_number')} | State: {u.get('ticket_state')} | Created: {u.get('ticket_created')}")
        print(f"Employee Name: {u.get('employee_name', 'Unknown')}")
        print(f"Employee ID: {u.get('employee_to_terminate', 'Unknown')}")
        print(f"Department: {u.get('employee_department', 'Unknown')}")
        print(f"Termination Date: {u.get('termination_date', 'Unknown')}")
        print(f"Remove Access Date: {u.get('date_to_remove_access', 'Unknown')}")
        print(f"Term Type: {u.get('term_type', 'Unknown')}")
        
        if u.get('additional_info'):
            print(f"Additional Info: {u.get('additional_info')}")
        if u.get('transfer_data'):
            print(f"Transfer Data: {u.get('transfer_data')}")
        if u.get('cjis_cleared'):
            print(f"CJIS Cleared: {u.get('cjis_cleared')}")
            
        print("-" * 60)


def get_termination_summary(users: List[Dict]) -> Dict:
    """
    Get enhanced summary statistics about terminations.
    Enhanced version from termination_extractor.py.
    """
    if not users:
        return {}
        
    summary = {
        "total_terminations": len(users),
        "departments": {},
        "term_types": {},
        "states": {},
        "has_cjis_cleared": 0,
        "pre_hire_terminations": 0,
        "missing_transfer_data": 0,
    }
    
    for user in users:
        dept = user.get('employee_department', 'Unknown')
        term_type = user.get('term_type', 'Unknown')
        state = user.get('ticket_state', 'Unknown')
        
        summary["departments"][dept] = summary["departments"].get(dept, 0) + 1
        summary["term_types"][term_type] = summary["term_types"].get(term_type, 0) + 1
        summary["states"][state] = summary["states"].get(state, 0) + 1
        
        # Enhanced metrics
        if user.get('cjis_cleared'):
            summary["has_cjis_cleared"] += 1
        if user.get('is_pre_hire'):
            summary["pre_hire_terminations"] += 1
        if not user.get('transfer_data'):
            summary["missing_transfer_data"] += 1
    
    return summary


# ---- Termination Batch Processing Functions --------------------------------

def process_termination_batch(max_pages: int = 60, workers: int = 15) -> Dict:
    """
    Process a batch of termination tickets and return summary.
    Combines fetching, filtering, and summarizing in one function.
    """
    try:
        log.info("Starting termination batch processing...")
        
        # Fetch tickets using enhanced service
        from jml_automation.services.solarwinds import SolarWindsService
        service = SolarWindsService.from_config()
        
        tickets = service.fetch_termination_tickets_enhanced(
            concurrent=True,
            active_only=False,  # We'll filter ourselves for better control
            subcategory_filter=True,
            max_pages=max_pages,
            max_workers=workers
        )
        
        if not tickets:
            log.info("No termination tickets found.")
            return {"status": "no_tickets", "total": 0}
        
        # Convert to raw format and filter
        raw_tickets = []
        for ticket in tickets:
            # Convert RawTicket back to dict format for filtering
            raw_dict = {
                "id": ticket.get("id"),
                "number": ticket.get("id"),  # May need adjustment
                "state": ticket.get("custom_fields", {}).get("state", "Unknown"),
                "created_at": ticket.get("custom_fields", {}).get("created_at", "Unknown"),
                "name": ticket.get("subject", ""),
                "custom_fields_values": ticket.get("custom_fields_values", [])
            }
            raw_tickets.append(raw_dict)
        
        users = filter_termination_users(raw_tickets)
        summary = get_termination_summary(users)
        
        log.info(f"Termination batch processing completed: {summary.get('total_terminations', 0)} active terminations")
        
        return {
            "status": "success",
            "raw_tickets_count": len(tickets),
            "active_terminations": len(users),
            "summary": summary,
            "users": users
        }
        
    except Exception as e:
        log.error(f"Termination batch processing failed: {e}")
        return {"status": "error", "error": str(e)}


# ---- Command Line Interface for Testing ------------------------------------

def main():
    """
    Command line interface for testing termination parsing.
    Similar to the if __name__ == "__main__" block in termination_extractor.py
    """
    try:
        print("Fetching termination tickets from SolarWinds...")
        
        # Use the enhanced service for fetching
        from jml_automation.services.solarwinds import SolarWindsService
        service = SolarWindsService.from_config()
        
        # Fetch with strict filtering (like the extractor)
        tickets = service.fetch_termination_tickets_enhanced(
            concurrent=True,
            active_only=True,
            strict_active_filter=True,  # Use "Awaiting Input" only
            subcategory_filter=True,
            max_pages=60,
            max_workers=15
        )
        
        if not tickets:
            print("No termination tickets found.")
            return
        
        # Convert to raw format for processing
        raw_tickets = []
        for ticket in tickets:
            # Convert RawTicket back to dict format
            raw_dict = {
                "id": ticket.get("id"),
                "number": ticket.get("id"), 
                "state": service._get_ticket_state(ticket),
                "created_at": ticket.get("custom_fields", {}).get("created_at", "Unknown"),
                "name": ticket.get("subject", ""),
                "custom_fields_values": ticket.get("custom_fields_values", [])
            }
            raw_tickets.append(raw_dict)
        
        # Process using the enhanced functions
        users = filter_termination_users(raw_tickets)
        print_terminations(users)
        
        # Print summary (enhanced version)
        summary = get_termination_summary(users)
        if summary:
            print(f"\nTERMINATION SUMMARY:")
            print(f"Total Active Terminations: {summary['total_terminations']}")
            print(f"By Department: {dict(summary['departments'])}")
            print(f"By Term Type: {dict(summary['term_types'])}")
            print(f"By State: {dict(summary['states'])}")
            print(f"CJIS Cleared Count: {summary['has_cjis_cleared']}")
            print(f"Pre-hire Terminations: {summary['pre_hire_terminations']}")
            print(f"Missing Transfer Data: {summary['missing_transfer_data']}")
                
    except Exception as e:
        print(f"Script error: {e}")


if __name__ == "__main__":
    main()