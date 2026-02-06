"""
Slack service for notifications.

This module handles sending notifications and reports to Slack channels.
"""

import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jml_automation.config import Config
from jml_automation.models.ticket import UserProfile
from jml_automation.services.base import BaseService

logger = logging.getLogger(__name__)

class SlackService(BaseService):

    def create_user(self, *args, **kwargs):
        """Not applicable for Slack service."""
        raise NotImplementedError("SlackService doesn't create users")

    def terminate_user(self, *args, **kwargs):
        """Not applicable for Slack service."""
        raise NotImplementedError("SlackService doesn't terminate users")

    def test_connection(self) -> bool:
        """Test Slack API connection."""
        try:
            response = self.session.get(
                f"{self.SLACK_API_URL}/auth.test",
                timeout=5
            )
            return response.json().get("ok", False)
        except Exception:
            return False
    """
    Service for sending notifications to Slack.
    Handles user creation notifications, reports, and general messaging.
    """
    DEFAULT_CHANNEL = "codybot_notifications"
    SLACK_API_URL = "https://slack.com/api"
    
    def __init__(self, config: Optional[Config] = None, channel: Optional[str] = None):
        super().__init__()
        self.config = config or Config()
        self.token = self.config.get_secret('SLACK_TOKEN')
        if not self.token:
            raise ValueError("SLACK_TOKEN not found in configuration")
        self.channel = channel or self.DEFAULT_CHANNEL
        if not self.channel.startswith('#'):
            self.channel = f"#{self.channel}"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)

    def send_onboarding_notification(
        self,
        user: UserProfile,
        ticket: Any,  # Accept any ticket-like object
        okta_user_id: str,
        display_number: Optional[str] = None
    ) -> bool:
        """Send notification for successful Okta user creation (old integration style)."""
        try:
            user_name = f"{user.first_name} {user.last_name}".strip()
            work_email = user.email
            title = user.title or "Not specified"
            ticket_number = display_number or getattr(ticket, "ticket_id", None) or getattr(ticket, "display_number", None) or "?"
            ticket_id = getattr(ticket, "ticket_id", None) or ticket_number
            user_slug = user_name.lower().replace(" ", "-")
            # Try to get the internal incident ID for the correct URL format
            try:
                from jml_automation.services.solarwinds import SolarWindsService
                solarwinds = SolarWindsService.from_config()
                internal_incident_id = solarwinds.search_by_display_number(str(ticket_id))
                if internal_incident_id:
                    ticket_url = f"https://it.filevine.com/incidents/{internal_incident_id}-employee-onboarding-{user_slug}"
                else:
                    # Fallback to old format if internal ID not found
                    incident_id = ticket_id if ticket_id else ticket_number
                    ticket_url = f"https://it.filevine.com/incidents/{incident_id}-{user_slug}-new-user-request"
            except Exception as e:
                # Fallback to old format on any error
                incident_id = ticket_id if ticket_id else ticket_number
                ticket_url = f"https://it.filevine.com/incidents/{incident_id}-{user_slug}-new-user-request"
            message = {
                "channel": self.channel,
                "text": "New Okta User Created",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Okta User Created Successfully"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Name:*\n{user_name}"},
                            {"type": "mrkdwn", "text": f"*Email:*\n{work_email}"},
                            {"type": "mrkdwn", "text": f"*Title:*\n{title}"},
                            {"type": "mrkdwn", "text": f"*Ticket:*\n<{ticket_url}|#{ticket_number}>"}
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": "Ticket status updated to 'In Progress'"}
                        ]
                    }
                ]
            }
            response = self.session.post(
                f"{self.SLACK_API_URL}/chat.postMessage",
                json=message,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Slack notification sent for {user_name}")
                    return True
                else:
                    logger.error(f"Slack API error: {result.get('error')}")
                    return False
            else:
                logger.error(f"Slack HTTP error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def send_termination_notification(
        self,
        user_email: str,
        user_name: Optional[str] = None,
        ticket_id: Optional[str] = None,
        manager_email: Optional[str] = None,
        phase_results: Optional[Dict[str, bool]] = None,
        overall_success: bool = True,
        duration_seconds: Optional[float] = None
    ) -> bool:
        """Send notification for completed termination."""
        try:
            # Extract name from email if not provided
            if not user_name:
                # Try to get display name from Okta first
                try:
                    from jml_automation.services.okta import OktaService
                    okta_base_url = self.config.get_secret('OKTA_ORG_URL')
                    okta_token = self.config.get_secret('OKTA_TOKEN')
                    if okta_base_url and okta_token:
                        okta_service = OktaService(base_url=okta_base_url, token=okta_token)
                        user_info = okta_service.find_user_by_email(user_email)
                        if user_info:
                            user_name = user_info.get('profile', {}).get('displayName')
                            # Use display name if available
                            pass
                        else:
                            # Fallback to firstName + lastName if displayName is not available
                            first_name = user_info.get('profile', {}).get('firstName', '')
                            last_name = user_info.get('profile', {}).get('lastName', '')
                            if first_name or last_name:
                                user_name = f"{first_name} {last_name}".strip()
                except Exception as e:
                    # Okta lookup failed, will use email fallback
                    pass
                
                # Fallback to email parsing if Okta lookup failed
                if not user_name:
                    import re
                    name_part = user_email.split('@')[0].replace('.', ' ')
                    
                    if ' ' in name_part:
                        # Already has spaces (like firstname.lastname)
                        user_name = name_part.title()
                    else:
                        # Try camelCase split (e.g., "firstName" -> "First Name")
                        name_with_camel = re.sub(r'([a-z])([A-Z])', r'\1 \2', name_part)
                        if ' ' in name_with_camel:
                            user_name = name_with_camel.title()
                        else:
                            # Fallback: just capitalize
                            user_name = name_part.title()
            
            # Additional cleanup for user_name if it was provided and still needs splitting
            elif user_name and ' ' not in user_name:
                import re
                user_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', user_name).title()
            
            # Build status summary
            if overall_success:
                status_text = "Termination Completed Successfully"
                status_color = "good"
            else:
                status_text = "⚠️ Termination Completed with Issues"
                status_color = "warning"
            

            
            # Build ticket info
            ticket_text = f"#{ticket_id}" if ticket_id else "No ticket ID"
            ticket_url = None
            if ticket_id:
                user_slug = user_name.lower().replace(" ", "-")
                # Try to get the internal incident ID for the correct URL format
                try:
                    from jml_automation.services.solarwinds import SolarWindsService
                    solarwinds = SolarWindsService.from_config()
                    internal_incident_id = solarwinds.search_by_display_number(str(ticket_id))
                    if internal_incident_id:
                        ticket_url = f"https://it.filevine.com/incidents/{internal_incident_id}-employee-termination-{user_slug}"
                    else:
                        # Fallback to old format if internal ID not found
                        ticket_url = f"https://it.filevine.com/incidents/{ticket_id}-{user_slug}-termination"
                except Exception as e:
                    # Fallback to old format on any error
                    ticket_url = f"https://it.filevine.com/incidents/{ticket_id}-{user_slug}-termination"
            
            # Build duration text
            duration_text = f"{duration_seconds:.1f}s" if duration_seconds else "Unknown"
            
            message = {
                "channel": self.channel,
                "text": "User Termination Completed",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": status_text
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*User:*\n{user_name}"},
                            {"type": "mrkdwn", "text": f"*Email:*\n{user_email}"},
                            {"type": "mrkdwn", "text": f"*Manager:*\n{manager_email or 'Not specified'}"},
                            {"type": "mrkdwn", "text": f"*Ticket:*\n{f'<{ticket_url}|{ticket_text}>' if ticket_url else ticket_text}"}
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"Duration: {duration_text} | Status: {'Complete' if overall_success else 'Issues detected'}"}
                        ]
                    }
                ]
            }
            
            response = self.session.post(
                f"{self.SLACK_API_URL}/chat.postMessage",
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Slack termination notification sent for {user_email}")
                    return True
                else:
                    logger.error(f"Slack API error: {result.get('error')}")
                    return False
            else:
                logger.error(f"Slack HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Slack termination notification: {e}")
            return False

    def send_outlaw_termination_notification(self, user_email: str) -> bool:
        """Send simple email notification to outlaw_termination_removals channel."""
        try:
            message = {
                "channel": "#outlaw_termination_removals",
                "text": user_email
            }
            
            response = self.session.post(
                f"{self.SLACK_API_URL}/chat.postMessage",
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Outlaw termination notification sent for {user_email}")
                    return True
                else:
                    logger.error(f"Slack API error for outlaw notification: {result.get('error')}")
                    return False
            else:
                logger.error(f"Slack HTTP error for outlaw notification: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send outlaw termination notification: {e}")
            return False