# Single Application Termination Test

## Overview

I've created a new termination process that follows your specified workflow:

1. **Transfer data** to the email specified in the ticket's `transfer_to_email` field
2. **Delete the user** from the specific application  
3. **Remove the user from app-specific Okta groups** (not all groups)

## Files Created

### 1. `tests/test_single_app_termination.py`
- Main test class `SingleAppTerminator` 
- Interactive command-line interface
- Supports all configured applications: microsoft, google, zoom, domo, lucid, adobe, workato

### 2. `example_single_app_test.py`
- Simple example script showing how to use the terminator
- Easy to modify for your specific ticket ID and app

### 3. Enhanced `src/jml_automation/workflows/termination.py`
- Added `remove_from_app_specific_groups()` method
- Uses configuration from `config/termination_order.yaml` to map apps to their Okta groups

## Configuration Used

The system reads from `config/termination_order.yaml` which maps each application to its specific Okta groups:

```yaml
termination:
  okta_groups_to_remove:
    microsoft:
      - "SSO-Microsoft 365 E3 - User"
    google:
      - "SSO-G Suite_EnterpriseUsers"
    zoom:
      - "SSO-Zoom_Member_Basic"
      - "SSO_Zoom_Member_Premier"
      - "SSO-Zoom_Member_Pro_Phone"
    # ... etc
```

## How to Use

### Interactive Mode
```bash
cd /path/to/JML_Automation
python tests/test_single_app_termination.py
```

### Programmatic Mode
```python
from tests.test_single_app_termination import SingleAppTerminator

terminator = SingleAppTerminator()
result = terminator.terminate_user_from_app(
    ticket_id="63000", 
    app_name="zoom", 
    dry_run=True
)
```

### Example Script
```bash
python example_single_app_test.py
```

## Process Flow

1. **Fetch Ticket**: Gets termination ticket from SolarWinds
2. **Parse Data**: Extracts user email and transfer email
3. **Data Transfer**: Attempts to transfer data to `transfer_to_email` (if specified)
4. **User Deletion**: Deletes user from the specified application
5. **Group Removal**: Removes user from only the Okta groups associated with that application

## Key Improvements

- **Selective Group Removal**: No longer removes users from ALL Okta groups
- **Data Transfer Support**: Handles the `transfer_to_email` field from tickets
- **App-Specific Logic**: Each application can have its own termination logic
- **Dry Run Support**: Test without making actual changes
- **Detailed Logging**: Clear feedback on what actions were taken

## Next Steps

1. **Test with a real ticket**: Provide a ticket number and app name
2. **Implement data transfer logic**: Add actual data transfer code for each application
3. **Implement deletion logic**: Add actual user deletion code for each application
4. **Add error handling**: Enhance error handling for specific scenarios

## Example Usage

To test Zoom termination for ticket 63000:

```python
terminator = SingleAppTerminator()
result = terminator.terminate_user_from_app("63000", "zoom", dry_run=True)
```

This will:
- Fetch ticket 63000
- Extract user email and transfer email
- Show what data transfer would happen (dry run)
- Show what user deletion would happen (dry run) 
- Remove user from Zoom-specific Okta groups: "SSO-Zoom_Member_Basic", "SSO_Zoom_Member_Premier", "SSO-Zoom_Member_Pro_Phone"
