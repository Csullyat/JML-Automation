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
                name_part = user_email.split('@')[0].replace('.', ' ').title()
                # Split camelCase names properly (cristinaromero -> Cristina Romero)
                import re
                # Insert space before capital letters that follow lowercase letters
                name_with_spaces = re.sub(r'([a-z])([A-Z])', r'\1 \2', name_part)
                user_name = name_with_spaces
            
            # Additional cleanup for user_name if it was provided
            if user_name and ' ' not in user_name:
                import re
                user_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', user_name)
            
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