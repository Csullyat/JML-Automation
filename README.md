# Employee Termination Automation System

Enterprise-grade automated system for processing employee termination requests with comprehensive multi-platform user deactivation, data transfer, and license cleanup.

## Purpose

This system automatically:
- Extracts termination requests from SolarWinds Service Desk
- Deactivates user accounts across all enterprise platforms
- Transfers data and removes users from all systems
- Manages license cleanup and cost optimization
- Provides comprehensive logging and audit trails
- Sends real-time Slack notifications for security team visibility

## Architecture

### Core Components

- **`enterprise_termination_orchestrator.py`** - Main orchestration and workflow engine
- **`okta_termination.py`** - Okta user deactivation and group management
- **`google_termination.py`** - Google Workspace user termination and data transfer
- **`microsoft_termination.py`** - Microsoft 365/Exchange user termination and mailbox conversion
- **`zoom_termination.py`** - Zoom user deletion with data transfer and license cleanup
- **`termination_extractor.py`** - SolarWinds Service Desk ticket processing
- **`slack_notifications.py`** - Slack integration for audit notifications
- **`config.py`** - Secure credential management via 1Password Service Account
- **`logging_system.py`** - Enterprise logging framework with audit trails

### Security & Compliance Features

## Enterprise Termination Workflow

### 6-Phase Processing Pipeline

1. **Phase 1: Ticket Extraction**
   - Extract termination requests from SolarWinds Service Desk
   - Parse user details and manager information
   - Validate termination criteria

2. **Phase 2: Okta Deactivation**
   - Deactivate user account in Okta
   - Remove from all groups (preserve system groups)
   - Terminate active sessions

3. **Phase 3: Microsoft 365 Termination**
   - Convert mailbox to shared mailbox
   - Grant manager access to shared mailbox
   - Remove user licenses and disable account

4. **Phase 4: Zoom Termination**
   - Transfer meetings, recordings, and webinars to manager
   - Verify 90% data transfer success threshold
   - Delete user account to free expensive licenses
   - Remove from Zoom SSO groups in Okta

5. **Phase 5: Google Workspace Termination**
   - Suspend user account in Google Workspace
   - Transfer Google Drive ownership to manager
   - Remove from Google SSO groups

6. **Phase 6: Final Cleanup**
   - Send comprehensive Slack notifications
   - Update ticket status in Service Desk
   - Generate audit reports

### Performance Optimizations

- **Token Caching**: Credentials cached in memory for bulk operations
- **Parallel Processing**: Multiple terminations processed concurrently
- **Service Account**: No user interaction required for 1Password access
- **Efficient API Usage**: Minimized API calls through intelligent caching

## Setup Instructions

### Prerequisites

1. **1Password CLI** installed and configured with Service Account
2. **PowerShell CredentialManager module**:
   ```powershell
   Install-Module -Name CredentialManager -Force
   ```
3. **Python 3.8+** with required packages:
   ```bash
   pip install -r requirements.txt
   ```

### 1Password Configuration

Create the following items in your 1Password "IT" vault:

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

## ⚡ Performance Optimization

### Current Performance Characteristics
- **Ticket Processing**: ~20 seconds for 6000 tickets
- **Single User Termination**: ~45-70 seconds per user (optimized from 90-110s)
- **Google Data Transfer**: 15-45 seconds (adaptive polling)
- **Microsoft 365 Operations**: ~20-30 seconds per user (token caching)

### ✅ Implemented Optimizations
1. **Adaptive Polling**: Google data transfers now use 5s → 10s → 15s intervals
2. **Token Caching**: Microsoft Graph tokens cached for 1 hour (90% faster auth)
3. **Parallel Processing**: Support for 2 concurrent user terminations
4. **Session Reuse**: PowerShell Exchange session tracking
5. **Graceful Fallbacks**: Continue processing when non-critical steps fail

### Performance Testing
Run the performance test script to benchmark your environment:
```bash
python performance_test.py
```

### Optimization Opportunities (Future)
- **Connection Pooling**: Reuse HTTP connections
- **Bulk Operations**: Use batch APIs where available
- **Async Operations**: Non-blocking data transfers
- **Smart Caching**: Cache user/group lookups

### Bottlenecks Identified
- **PowerShell Exchange Operations**: ~25-30 seconds per mailbox
- **Data Transfer Size**: Varies with user data volume
- **API Rate Limits**: Google/Microsoft throttling
- **Sequential Steps**: Some operations must be performed in order

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run `test_termination.py` for diagnostic information
3. Review 1Password configuration
4. Contact IT automation team

---

**⚠️ Important**: Always test in test mode before running in production. This system permanently deactivates user accounts and removes group memberships.
