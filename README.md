# JML Automation - Employee Lifecycle Management

Automated employee onboarding, termination, and partner provisioning system for Filevine. Integrates with Okta, Microsoft 365, Google Workspace, Zoom, and other enterprise applications.

## Features

- **Web Portal**: Flask-based interface for IT team
- **Onboarding**: Automated user creation across Okta, M365, Google, Zoom
- **Termination**: 10-phase comprehensive termination with data delegation
- **Partner Management**: Automated partner user provisioning
- **SolarWinds Integration**: Pulls tickets and auto-closes on completion
- **Slack Notifications**: Real-time updates on onboarding/termination status

## Architecture

- **Backend**: Python 3.11+ with Flask web framework
- **Authentication**: Okta OAuth2 for portal access
- **Secrets**: 1Password CLI for credential management
- **Services**: REST APIs + PowerShell automation for Exchange
- **Logging**: Centralized logging to `logs/` directory

## Prerequisites

### Required Software
- Python 3.11+
- PowerShell 7 (recommended) or Windows PowerShell 5.1
- 1Password CLI (`op`) - [Install guide](https://developer.1password.com/docs/cli/get-started/)
- Git

### Required PowerShell Modules
```powershell
Install-Module -Name ExchangeOnlineManagement -Force
Install-Module -Name Microsoft.Graph -Force
```

### Required Credentials (stored in 1Password)
- Okta API token
- Microsoft Graph API credentials + Exchange certificate
- Google Workspace service account
- Zoom OAuth credentials
- SolarWinds API key
- Slack webhook URLs
- Adobe, Domo, Lucid, Workato API keys

## Installation

### 1. Clone Repository
```bash
git clone <repo-url>
cd JML_Automation
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Configure Environment
Create `.env` file in project root:
```bash
# Okta OAuth for Flask
OKTA_DOMAIN=filevine.okta.com
OKTA_CLIENT_ID=<from-1password>
OKTA_CLIENT_SECRET=<from-1password>
SECRET_KEY=<random-secret-for-flask-sessions>
```

### 5. Test 1Password Integration
```bash
op signin
op item get "okta-api-token" --vault IT
```

## Running the Application

### Start Flask Web Portal
```bash
python app.py
```

Access at: `http://localhost:5000`

### CLI Commands (Optional)
```bash
# Dry-run onboarding
jml onboard 12345

# Live termination
jml terminate 12346 --live
```

## Project Structure
```
JML_Automation/
├── app.py                      # Flask web application
├── src/jml_automation/
│   ├── services/               # API integrations (Okta, M365, Google, etc.)
│   ├── workflows/              # Onboarding, termination, partner workflows
│   ├── parsers/                # SolarWinds ticket parsing
│   ├── models/                 # Data models
│   └── config.py               # 1Password integration
├── config/
│   ├── groups.yaml             # Okta group mappings
│   └── termination_order.yaml  # Service termination order
├── scripts/                    # PowerShell scripts for Exchange
├── logs/                       # Application logs
└── requirements.txt            # Python dependencies
```

## Key Workflows

### Onboarding (2 minutes)
1. Create user in Okta with profile data
2. Add to baseline + department Okta groups
3. Wait 80s for Okta → Exchange sync
4. Add to Microsoft 365 distribution groups
5. Update ticket → assign to Laptop Setup
6. Send Slack notification

### Termination (2 minutes)
**Phase 0**: Iru - Lock devices BEFORE Okta deactivation  
**Phase 1**: Okta - Clear sessions, deactivate  
**Phase 2**: Microsoft - Convert mailbox, delegate, remove licenses, remove from groups  
**Phase 3**: Google - Transfer Drive, delete user, remove from groups  
**Phase 4**: Zoom - Transfer meetings/recordings, delete, remove from groups  
**Phase 5**: SynQ Prox - Web automation deletion (mandatory)  
**Phase 6-9**: Domo/Adobe/Lucid/Workato - Delete if in groups, remove from groups  
**Final**: Close ticket, send Slack notifications

## Deployment to AWS EC2

### 1. Launch Windows Server 2025 Instance
- Instance type: t3.medium or larger
- Security group: Allow inbound 5000 (or use ALB)
- IAM role: None required (uses 1Password)

### 2. Install Prerequisites on EC2
```powershell
# Install Python 3.11+
# Install PowerShell 7
# Install 1Password CLI
# Install Exchange/Graph modules
```

### 3. Deploy Application
```bash
git clone <repo-url>
cd JML_Automation
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 4. Configure as Windows Service
Use NSSM or Task Scheduler to run Flask on startup.

### 5. Setup Reverse Proxy (Optional)
Use IIS or nginx to proxy requests to Flask.

## Configuration Files

### `config/groups.yaml`
Maps departments to Okta groups:
```yaml
baseline:
  - "Filevine Employees"
dept:
  Sales:
    - "Sales Department"
  Development:
    - "Development"
zoom:
  default: "SSO-Zoom_Member_Basic"
  ae: "SSO-Zoom_Member_Premier"
```

### `config/termination_order.yaml`
Defines Okta groups to remove per service:
```yaml
termination:
  okta_groups_to_remove:
    microsoft:
      - "SSO-Microsoft 365 E3 - User"
    google:
      - "SSO-Google_Workspace_EnterpriseUsers"
```

## Troubleshooting

### Common Issues

**SSL Certificate Errors (Domo)**
- Ensure `pip-system-certs` is installed
- Windows certificate store must trust api.domo.com

**Exchange PowerShell Failures**
- Verify certificate installed: `certutil -user -store My`
- Check app registration has correct permissions
- Ensure ExchangeOnlineManagement module installed

**User Not Found in Exchange After 80s Wait**
- Increase wait time in `onboarding.py` (line 180)
- Check Okta → M365 provisioning is enabled

**Double Submissions in Flask**
- Fixed with button disable on submit (v1.1+)

## Security Notes

- All credentials stored in 1Password (never in code)
- Certificate-based auth for Exchange (no passwords)
- Flask sessions encrypted with SECRET_KEY
- Okta OAuth2 for portal authentication
- Logs sanitized (no credentials logged)

## Maintenance

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### View Logs
```bash
tail -f logs/jml_automation_<date>.log
```

### Clear Temp Files
```bash
del temp_*.ps1
```

## Support

**Author**: Cody Atkinson (codyatkinson@filevine.com)  
**Department**: IT - Enterprise Systems  
**Version**: 1.0.0  
**Last Updated**: February 2026