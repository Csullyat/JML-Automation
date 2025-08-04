# README.md - Termination Automation System

# Employee Termination Automation System

Automated system for processing employee termination requests from SolarWinds Service Desk and performing user deactivation in Okta with Slack notifications.

## 🎯 Purpose

This system automatically:
- Monitors SolarWinds Service Desk for termination requests
- Deactivates user accounts in Okta
- Removes users from all groups (except system groups)
- Sends real-time Slack notifications
- Provides comprehensive logging and audit trails

## 🏗️ Architecture

### Core Components

- **`termination_main.py`** - Main orchestration script
- **`okta_termination.py`** - Okta API integration for user deactivation
- **`ticket_processor.py`** - Service desk ticket processing
- **`slack_notifications.py`** - Slack integration for notifications
- **`config.py`** - Secure credential management via 1Password
- **`logging_system.py`** - Comprehensive logging framework

### Security Features

- **No hardcoded credentials** - All secrets stored in 1Password
- **Service Account integration** - Unattended operation via 1Password Service Account
- **Windows Credential Manager** - Secure local token storage
- **Comprehensive audit logs** - All actions logged with timestamps
- **Test mode** - Safe testing without affecting production data

## 🚀 Setup Instructions

### Prerequisites

1. **1Password CLI** installed and configured
2. **PowerShell CredentialManager module**:
   ```powershell
   Install-Module -Name CredentialManager -Force
   ```
3. **Python 3.8+** with required packages:
   ```bash
   pip install -r requirements.txt
   ```

### 1Password Configuration

Create the following items in your 1Password "Employee" vault:

- **Okta API Token** (field: `credential`)
- **Okta Domain** (field: `credential`) - e.g., `company.okta.com`
- **SolarWinds Service Desk API Token** (field: `credential`)
- **SolarWinds Service Desk Subdomain** (field: `credential`)
- **Slack Termination Webhook** (field: `credential`) - Optional
- **Slack Termination Channel** (field: `credential`) - Optional

### Service Account Setup

1. Store your 1Password Service Account token in Windows Credential Manager:
   ```powershell
   # Run setup_credentials.ps1 (to be created)
   .\setup_credentials.ps1
   ```

2. Test the configuration:
   ```bash
   python test_termination.py
   ```

## 🎮 Usage

### Test Mode (Recommended First)

```bash
# Test with first termination request only
python termination_main.py
```

### Production Mode

```bash
# Edit termination_main.py and change:
# main(test_mode=False)
python termination_main.py
```

### Manual Testing

```bash
# Test individual components
python test_termination.py
```

## 📋 Supported Termination Keywords

The system looks for these keywords in Service Desk tickets:
- termination, terminate
- offboard, off-board, offboarding
- departure, leaving
- disable account, deactivate account
- employee leaving, last day
- end employment, final day

## 🔒 Security Compliance

### Data Protection
- All credentials retrieved securely via 1Password
- No sensitive data stored in code or logs
- Service account token encrypted in Windows Credential Manager

### Audit Trail
- Every action logged with timestamp and user details
- Failed operations logged with error details
- Daily log files for compliance review

### Access Control
- Requires valid Okta API token with admin permissions
- Service account access controlled via 1Password policies
- PowerShell execution requires appropriate permissions

## 📊 Monitoring & Reporting

### Slack Notifications
- Real-time termination completion alerts
- Summary reports (when enabled)
- Error notifications for failed operations

### Log Files
- **`logs/termination_automation.log`** - Main rotating log
- **`logs/termination_errors.log`** - Error-only log
- **`logs/termination_YYYY-MM-DD.log`** - Daily logs

### Performance Metrics
- Execution duration tracking
- Success/failure rates
- User processing counts

## 🔧 Troubleshooting

### Common Issues

1. **1Password CLI not authenticated**
   ```bash
   op account list
   op signin
   ```

2. **Service account token expired**
   - Update token in Windows Credential Manager
   - Run `setup_credentials.ps1` again

3. **Okta API permissions**
   - Verify token has user admin permissions
   - Check Okta domain configuration

4. **Slack notifications not working**
   - Test webhook URL manually
   - Verify webhook has proper permissions

### Debug Mode

Enable debug logging by editing `logging_system.py`:
```python
logger = setup_logging(log_level="DEBUG")
```

## 🔄 Integration with User Creation System

This termination system is designed to complement the existing Okta user creation automation:

- **Shared infrastructure** - Same 1Password and credential management
- **Consistent logging** - Same log format and storage
- **Unified Slack integration** - Same notification patterns
- **Matching security** - Same security and compliance standards

## 📅 Automation Schedule

Recommended Task Scheduler configuration:
- **Frequency**: Every 4 hours during business hours
- **Account**: Service account with appropriate permissions
- **Error handling**: Log failures and send Slack alerts

## 🎯 Future Enhancements

- [ ] AD/Azure AD integration for complete account removal
- [ ] Asset management integration (laptop retrieval, etc.)
- [ ] Manager notification workflows
- [ ] Integration with HR systems for automated triggering
- [ ] Advanced reporting dashboard

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run `test_termination.py` for diagnostic information
3. Review 1Password configuration
4. Contact IT automation team

---

**⚠️ Important**: Always test in test mode before running in production. This system permanently deactivates user accounts and removes group memberships.
