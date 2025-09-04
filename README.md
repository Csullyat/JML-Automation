
---
# JML Automation (Joiner/Mover/Leaver)

Automated onboarding and offboarding for your organization, driven by SolarWinds Service Desk tickets. This system creates and manages Okta users, updates tickets, and sends Slack notifications—all in a unified, auditable workflow.

---

## What is JML (Joiner/Mover/Leaver)?

**JML** stands for **Joiner, Mover, Leaver**:
- **Joiner:** Automates onboarding for new employees (user creation, group assignment, notifications).
- **Mover:** (Planned) Handles role/department changes for existing users.
- **Leaver:** Automates offboarding/termination (user deactivation, access removal, ticket updates, notifications).

This system is designed to ensure secure, consistent, and auditable user lifecycle management across your IT stack.

---

## Features

- **Unified ticket-driven automation:** Both onboarding and termination are triggered by SolarWinds Service Desk tickets.
- **Okta integration:** Users are created, updated, or deactivated in Okta with correct profile fields and group assignments.
- **Slack notifications:** Key events (onboarding, offboarding) are posted to your chosen Slack channel.
- **Ticket updates:** SolarWinds tickets are updated with status and comments for full auditability.
- **Configurable group mapping:** Department-to-group logic is fully configurable.
- **Timezone and address handling:** Supports US and international users with correct formatting.

---

## How to Use

### 1. Prerequisites

- Python 3.11+
- 1Password CLI (for secure API token retrieval)
- API access: Okta, SolarWinds/Samanage, Slack

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Configure

- Store your API tokens in 1Password (see below).
- Edit `config/` YAML files for department/group mappings and settings.
- Set up your notification Slack channel in the config.

**Required 1Password vault items:**
- `op://IT/okta-api-token/password`
- `op://IT/samanage-api-token/password`
- `op://IT/slack-bot-token/password`

### 4. Run

**Onboarding:**
```bash
python src/jml_automation/cli/app.py onboard run --ticket-id <TICKET_ID> --no-dry-run
```

**Termination:**
```bash
python src/jml_automation/cli/app.py terminate run --ticket-id <TICKET_ID> --no-dry-run
```

Or schedule with Windows Task Scheduler for automation.

---

## Project Structure

- `src/jml_automation/workflows/` — Main onboarding and termination workflows
- `src/jml_automation/services/` — Integrations for Okta, SolarWinds, Slack, etc.
- `src/jml_automation/models/` — Data models for tickets and users
- `config/` — YAML config files for departments, groups, and settings
- `tests/` — Unit and integration tests, including `tests/workflows/` for workflow coverage

---

## Logging & Troubleshooting

- All actions are logged to `logs/jml_automation.log`
- See the Troubleshooting section below for common issues

---

## Troubleshooting

**1Password prompts for authentication?**
- Ensure Service Account token is stored in Windows Credential Manager
- Run `./get_credential.ps1` to configure unattended access

**Task Scheduler fails?**  
- Use full Python executable path
- Set working directory to project folder
- Verify Service Account credentials

**No Slack notifications?**
- Check bot token permissions
- Ensure bot is invited to notification channel
- Verify SLACK_CHANNEL setting


**Wrong timezone for international users?**
- Check address format in ticket (should include country name)
- Supported: "Slovakia", "Czech Republic", "Czechia"

---

## Exchange Online Setup

1. Create a 1Password item:
	```bash
	op item create --category="API Credential" \
	  --title="Exchange Online Automation" \
	  --vault="IT" \
	  certificate_thumbprint="YOUR_CERT_THUMBPRINT" \
	  app_id="YOUR_AZURE_APP_ID" \
	  tenant_id="your-tenant.com"
	```

2. Run the setup script:
	```powershell
	.\scripts\setup_exchange_auth.ps1
	```

3. For automated/CI environments with service account:
	```powershell
	.\scripts\setup_exchange_auth.ps1 -UseServiceAccount
	```

## Additional Benefits:

- **Team collaboration** - Any team member with 1Password access can run the setup
- **Credential rotation** - Easy to update credentials by editing the 1Password item
- **Audit trail** - 1Password logs all access to credentials
- **No accidental commits** - Even if someone modifies the script locally, there's nothing sensitive to accidentally commit

Save this as `scripts/setup_exchange_auth.ps1` in your project. It's completely safe for public GitHub repositories.

---

**For more details, see the inline comments in each workflow and service file.**

**Key Department-to-Group Logic:**
- `SDR - Sales Development Reps` → **Sales** group (ID: 00gc4fuf3wQXRIzqN297)
- `AE - Account Executives` → **Sales** group (ID: 00gc4fuf3wQXRIzqN297)
- All other departments: see `DEPARTMENT_GROUP_MAPPING` in `config.py` for details

> **Note:** The group assignment logic for SDR and AE is hardcoded for compliance and auditability. If you need to change the group, update the group ID in `config.py`.

## Run

### Manual
```bash
python okta_batch_create.py
```

### Automated (Recommended)
Set up Windows Task Scheduler for 3x daily execution:
```powershell
.\setup_task_scheduler.ps1
```

**Schedule:** 10:00 AM, 2:00 PM, 5:00 PM daily


## Files

- `config.py` - Credentials & configuration with department-to-group mappings
- `okta_batch_create.py` - Main automation script with comprehensive logging
- `okta_groups.py` - Automatic group assignment based on department
- `ticket_extractor.py` - Ticket processing with address/timezone parsing
- `solarwinds_integration.py` - Ticket updates
- `slack_integration.py` - Notifications
- `get_okta_groups.py` - Helper to fetch group IDs for configuration (now ignored by git)
- `get_credential.ps1` - Service account setup
- `setup_task_scheduler.ps1` - Task Scheduler configuration

**Removed/ignored files:**
- `log_reporter.py`, `send_reports.py` (reporting scripts, now ignored)
- `fix_monthly_schedule.ps1`, `fix_monthly_simple.ps1` (one-time fix scripts, now ignored)
- All test scripts (see `.gitignore`)


## Logging

All activities are logged to `logs/okta_automation_YYYY-MM-DD.log`:
-  **Successful user creations** with ticket numbers and group assignments
-  **Group assignments** by department with success/failure status
-  **Duplicate users** and validation issues
-  **Errors** with detailed error messages
-  **Performance metrics** and runtime statistics

> **Note:** Reporting scripts and scheduled Slack reports have been removed from this workflow. For audit or reporting, use the log files directly.

## Features

### Automatic Group Assignment
- **Department-based:** Users automatically added to Okta groups based on SolarWinds department field
- **Flexible mapping:** Supports variations like "CS - Customer Success" and "AE - Account Executives"
- **Validation:** Group IDs validated on startup to catch configuration errors
- **Comprehensive logging:** All group assignments logged for audit purposes

### Address Support
- **US addresses:** Standard format with state and 5-digit ZIP
- **European addresses:** Slovakia, Czech Republic with proper IANA timezones
- **Automatic timezone mapping:** Country detection sets correct timezone

### Phone Formatting
- **US numbers:** `555-123-4567`
- **US with country code:** `1-555-123-4567`
- **International:** `421-948-873-023` (Slovakia format)

## Troubleshooting

**1Password prompts for authentication?**
- Ensure Service Account token is stored in Windows Credential Manager
- Run `.\get_credential.ps1` to configure unattended access

**Task Scheduler fails?**  
- Use full Python executable path
- Set working directory to project folder
- Verify Service Account credentials

**No Slack notifications?**
- Check bot token permissions
- Ensure bot is invited to notification channel
- Verify SLACK_CHANNEL setting

**Wrong timezone for international users?**
- Check address format in ticket (should include country name)
- Supported: "Slovakia", "Czech Republic", "Czechia"
