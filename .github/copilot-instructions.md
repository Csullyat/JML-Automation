# Copilot Instructions for Termination Automation

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview
- This project automates employee termination/offboarding processes in enterprise environments
- The workflow: fetch termination tickets → disable Okta user → remove group memberships → update ticket status → send notifications
- All secrets (API tokens) are retrieved via 1Password CLI with Service Account integration for unattended automation
- Follows the same security patterns as the companion Okta user creation system

## Key Components
- `config.py`: Centralized configuration and secure credential management using 1Password CLI
- `termination_main.py`: Main orchestration script handling ticket processing and user deactivation
- `okta_termination.py`: Okta user deactivation and group removal logic
- `ticket_processor.py`: Service Desk ticket fetching and filtering for termination requests
- `slack_notifications.py`: Slack integration for audit notifications and reporting
- `logging_system.py`: Comprehensive logging and audit trail management

## Security & Compliance
- **Audit Trail**: Every action is logged with timestamps, user details, and system responses
- **Secure Credentials**: All API tokens retrieved via 1Password Service Account
- **Notifications**: Slack alerts for all termination actions for security team visibility
- **Compliance**: Detailed logs for HR and security compliance requirements

## Integration Points
- **Okta**: User deactivation, group removal, session termination
- **Service Desk**: Ticket processing and status updates (SolarWinds/Samanage)
- **Slack**: Real-time notifications and weekly termination reports
- **1Password**: Secure credential management with Service Account automation

## Development Guidelines
- Follow enterprise security best practices
- Maintain detailed logging for all operations
- Use defensive programming - handle all edge cases gracefully
- Never hardcode credentials - always use 1Password integration
- Include proper error handling and rollback capabilities where possible
- Test thoroughly in safe environments before production deployment
