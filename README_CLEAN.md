# Employee Termination Automation System

Enterprise-grade automation system for secure employee termination and offboarding processes.

## Overview

This system automates the critical security steps for employee terminations:
- **Immediate session clearing** in Okta (security critical)
- **Account deactivation** across all systems
- **Group membership removal** 
- **Data transfer coordination**
- **Audit logging and notifications**

## Quick Start

### 1. Prerequisites
- Python 3.8+
- 1Password CLI configured with Service Account
- Okta API access
- SolarWinds Service Desk API access

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Configuration
All credentials are securely managed via 1Password Service Account:
- Okta API token: `op://IT/okta-api-token/password`
- SolarWinds credentials: `op://IT/solarwinds-api/username` and password

### 4. Usage

**Process all active terminations:**
```bash
python termination_main.py
```

**Process specific termination tickets:**
```bash
python termination_okta_processor.py
```

**Extract termination data from tickets:**
```bash
python termination_extractor.py
```

## Core Components

### Security & Authentication
- **`config.py`** - Secure credential management via 1Password
- **`get_credential.ps1`** - PowerShell integration for 1Password CLI

### Termination Processing
- **`termination_main.py`** - Main orchestration and workflow
- **`termination_okta_processor.py`** - Okta user deactivation and session clearing
- **`okta_termination.py`** - Core Okta API functions

### Data Integration
- **`ticket_processor.py`** - SolarWinds Service Desk integration
- **`termination_extractor.py`** - Concurrent ticket parsing and data extraction

### Monitoring & Compliance
- **`logging_system.py`** - Comprehensive audit logging
- **`slack_notifications.py`** - Real-time notifications and reporting

## Security Features

- **Session Termination**: Immediately clears all active Okta sessions
- **Account Deactivation**: Disables access across all connected systems
- **Audit Trail**: Complete logging of all termination actions
- **Secure Credentials**: 1Password Service Account integration
- **Real-time Alerts**: Slack notifications for security team

## Production Deployment

1. **Test Mode**: All scripts run in safe test mode by default
2. **Production Mode**: Set `test_mode=False` when ready for live terminations
3. **Monitoring**: Check logs in `logs/` directory for audit trail
4. **Notifications**: Configure Slack webhooks for team alerts

## Integration Points

- **Okta**: Primary identity provider for session clearing and deactivation
- **SolarWinds**: Service desk ticket processing and status updates
- **Slack**: Security team notifications and reporting
- **1Password**: Secure credential management

## Compliance

- All actions are logged with timestamps and user details
- Complete audit trail for HR and security compliance
- Immediate session termination for security requirements
- Automated reporting for management oversight

---

**⚠️ Security Notice**: This system performs irreversible account deactivations. Always test thoroughly before production deployment.
