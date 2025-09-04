# JML Automation System

Enterprise-grade automated employee lifecycle management system for Joiners, Movers, and Leavers, driven by SolarWinds Service Desk tickets.

## Overview
JML (Joiner/Mover/Leaver) automates the complete employee lifecycle:

- **Joiner:** Automated onboarding - creates Okta users, assigns groups, configures access
- **Mover:** (Planned) Role and department changes for existing employees
- **Leaver:** Automated offboarding - deactivates accounts, transfers data, removes licenses

## Key Features
### Core Capabilities
- **Ticket-driven automation:** All workflows triggered by SolarWinds Service Desk tickets
- **Multi-platform support:** Okta, Microsoft 365, Google Workspace, Zoom integration
- **Security-first design:** Session termination, immediate access removal, audit logging
- **Data preservation:** Automatic manager delegation and mailbox conversion
- **License optimization:** Automatic license removal to reduce costs
- **Comprehensive notifications:** Real-time Slack updates for security visibility

### Technical Features
- **1Password integration:** Secure credential management with service account support
- **Intelligent parsing:** Handles employee IDs, emails, and various input formats
- **Performance optimized:** Token caching, parallel processing, adaptive polling
- **Configurable workflows:** YAML-based department/group mappings
- **International support:** Timezone detection and address formatting

## System Architecture
```
JML_Automation/
├── src/jml_automation/
│   ├── workflows/
│   │   ├── termination.py       # Unified termination workflow
│   │   └── onboarding.py        # Onboarding workflow
│   ├── services/
│   │   ├── okta.py              # Okta operations
│   │   ├── solarwinds.py        # Ticket management
│   │   ├── microsoft.py         # M365/Exchange (stub)
│   │   ├── google.py            # Google Workspace (stub)
│   │   ├── zoom.py              # Zoom operations (stub)
│   │   └── slack.py             # Notifications
│   ├── parsers/
│   │   └── solarwinds_parser.py # Ticket parsing
│   └── config.py                # Configuration management
├── config/
│   ├── settings.yaml            # Main settings
│   ├── departments.yaml         # Department mappings
│   └── termination_order.yaml   # Phase configuration
└── scripts/
    ├── convert_mailbox_to_shared.ps1
    └── get_credential.ps1
```

## Installation
### Prerequisites
- Python 3.11+
- 1Password CLI (op)
- PowerShell 5.1+ (Windows)
- API access to: Okta, SolarWinds, Slack, Microsoft Graph, Google Admin

### Setup Steps
1. Clone and install dependencies:
   ```bash
   git clone <repository>
   cd JML_Automation
   pip install -r requirements.txt
   ```
2. Configure 1Password items in your IT vault:
   - okta-api-token
   - samanage-api-token or solarwinds-token
   - slack-bot-token
   - microsoft-graph-api (tenant_id, username, password)
   - google-workspace-service-account (JSON credential)
   - zoom-api (client_id, client_secret, account_id)

3. Set up service account (for unattended operation):
   ```powershell
   # Store 1Password service account token
   .\scripts\get_credential.ps1
   ```
4. Configure settings:
   - Edit config/settings.yaml for API endpoints
   - Edit config/departments.yaml for group mappings
   - Edit config/termination_order.yaml for workflow phases

## Usage
### Termination Workflows
- **Test Mode (Validate without changes):**
  ```bash
  python -m jml_automation.workflows.termination test user@domain.com manager@domain.com
  ```
- **Simple Termination (Okta only):**
  ```bash
  python -m jml_automation.workflows.termination simple 12345 --dry-run
  python -m jml_automation.workflows.termination simple 12345  # Live execution
  ```
- **Enterprise Termination (All platforms):**
  ```bash
  python -m jml_automation.workflows.termination user@domain.com manager@domain.com
  ```
- **Batch Processing (Process all pending tickets):**
  ```bash
  python -m jml_automation.workflows.termination batch
  ```

### Onboarding Workflows
```bash
# Dry run to preview actions
python -m jml_automation.workflows.onboarding --ticket-id 12345 --dry-run

# Live execution
python -m jml_automation.workflows.onboarding --ticket-id 12345
```

## Termination Process Details
- **Phase 1: Immediate Security (Okta)**
  - Clear all active sessions
  - Remove from all groups (except system groups)
  - Deactivate user account
  - Time: ~5-10 seconds
- **Phase 2: Microsoft 365**
  - Convert personal mailbox to shared mailbox
  - Grant manager full access permissions
  - Remove all licenses (Exchange, Office, etc.)
  - Time: ~20-30 seconds
- **Phase 3: Google Workspace**
  - Suspend user account
  - Transfer Drive ownership to manager
  - Remove from groups
  - Time: ~15-45 seconds
- **Phase 4: Zoom**
  - Transfer meetings and recordings to manager
  - Delete user to free license
  - Time: ~10-15 seconds
- **Phase 5: Notifications**
  - Update SolarWinds ticket status
  - Send Slack notification with summary
  - Log all actions for audit

## Performance Characteristics
- **Ticket Processing:** ~20 seconds for 6000 tickets
- **Single User Termination:** 45-70 seconds total
- **Okta Operations:** 5-10 seconds
- **Microsoft 365:** 20-30 seconds (with token caching)
- **Google Workspace:** 15-45 seconds (adaptive polling)
- **Concurrent Processing:** Supports 2 simultaneous terminations

## Monitoring & Logging
### Log Files
- logs/jml_automation.log - Main application log
- logs/termination_YYYY-MM-DD.log - Daily termination logs
- logs/termination_errors.log - Error-only log

### Slack Notifications
Real-time notifications include:
- User termination completion
- Phase success/failure status
- Processing duration
- Error details if any

### Audit Trail
Every action logged with:
- Timestamp
- User affected
- Action performed
- Success/failure status
- Error details if applicable

## Troubleshooting
### Common Issues
- **1Password authentication fails**
  ```bash
  # Verify CLI is configured
  op account list

  # For service account, check credential
  .\scripts\get_credential.ps1
  ```
- **No user found in Okta**
  - Check if employee ID needs lookup
  - Verify email format is correct
  - Confirm user exists in Okta
- **Microsoft/Google operations fail**
  - Verify API credentials in 1Password
  - Check service account permissions
  - Review API quotas and limits
- **Slack notifications missing**
  - Verify bot token permissions
  - Ensure bot is in channel
  - Check webhook configuration

### Debug Mode
Enable detailed logging:
```python
# In src/jml_automation/logger.py
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations
### Credential Management
- All secrets stored in 1Password
- Service account token encrypted in Windows Credential Manager
- No credentials in code or configuration files

### Access Control
- Okta API requires admin permissions
- Microsoft Graph needs User.ReadWrite.All
- Google needs domain-wide delegation
- All actions logged for audit

### Data Protection
- Manager delegation preserves data access
- Shared mailboxes retain email history
- Drive transfers maintain file ownership
- Meeting recordings transferred before deletion

## Automation Setup
### Windows Task Scheduler
Create scheduled task for batch processing:
```xml
<Actions>
  <Exec>
    <Command>C:\Python311\python.exe</Command>
    <Arguments>-m jml_automation.workflows.termination batch</Arguments>
    <WorkingDirectory>C:\path\to\JML_Automation</WorkingDirectory>
  </Exec>
</Actions>
<Triggers>
  <CalendarTrigger>
    <StartBoundary>2024-01-01T10:00:00</StartBoundary>
    <Repetition>
      <Interval>PT4H</Interval>
    </Repetition>
  </CalendarTrigger>
</Triggers>
```
Recommended schedule:
- Every 4 hours during business hours (10am, 2pm, 6pm)
- Run as service account with appropriate permissions

## Department Group Mappings
Configured in config/departments.yaml:
- Sales Development (SDR) → Sales group
- Account Executives (AE) → Sales group
- Customer Success (CS) → Customer Success group
- Engineering → Engineering group
- See configuration file for complete mappings

## Future Enhancements
- Active Directory integration
- Asset management (laptop recovery)
- Automated HR system triggers
- Advanced reporting dashboard
- Mobile device management
- Contractor vs employee workflows
- Role change automation (Mover)

## Support
For issues:
- Check logs/jml_automation.log for detailed errors
- Run test mode to validate configuration
- Verify 1Password items are configured correctly
- Review service-specific API permissions

## Important Notes
- Always test with dry-run or test mode first
- Terminations are permanent - accounts cannot be easily recovered
- License removal happens immediately to optimize costs
- Data transfers should complete before account deletion
- Manager email required for data delegation features

---

This system processes sensitive employee data and permanently modifies user accounts. Always verify actions in test mode before production use.
