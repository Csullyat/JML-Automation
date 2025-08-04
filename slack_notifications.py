# slack_notifications.py - Slack integration for termination automation

import logging
import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import get_slack_webhook_url, get_slack_channel

logger = logging.getLogger(__name__)

def send_termination_notification(user_name: str, user_email: str, ticket_number: str, 
                                actions_taken: List[str]) -> bool:
    """
    Send immediate Slack notification for a completed termination.
    
    Args:
        user_name: Name of terminated user
        user_email: Email of terminated user
        ticket_number: Service desk ticket number
        actions_taken: List of actions performed during termination
        
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        webhook_url = get_slack_webhook_url()
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping notification")
            return False
        
        # Create the notification message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format actions taken
        actions_text = "\n".join([f"• {action}" for action in actions_taken])
        
        message = {
            "text": f"🔒 User Termination Completed",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔒 User Termination Completed"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*User:* {user_name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Email:* {user_email}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Ticket:* #{ticket_number}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Completed:* {timestamp}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Actions Taken:*\n{actions_text}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "🤖 Automated by Termination System"
                        }
                    ]
                }
            ]
        }
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=message,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Sent Slack notification for {user_email} termination")
            return True
        else:
            logger.error(f"Failed to send Slack notification: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception sending Slack notification: {str(e)}")
        return False

def send_termination_summary(successful_count: int, failed_count: int, total_processed: int,
                           duration: datetime, results: List[Dict[str, Any]]) -> bool:
    """
    Send a summary of termination automation run to Slack.
    
    Args:
        successful_count: Number of successful terminations
        failed_count: Number of failed terminations
        total_processed: Total number of requests processed
        duration: Time taken for the automation run
        results: Detailed results for each termination
        
    Returns:
        bool: True if summary sent successfully, False otherwise
    """
    try:
        webhook_url = get_slack_webhook_url()
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping summary")
            return False
        
        # Determine overall status
        if failed_count == 0:
            status_emoji = "✅"
            status_text = "All Successful"
            color = "good"
        elif successful_count > 0:
            status_emoji = "⚠️"
            status_text = "Partial Success"
            color = "warning"
        else:
            status_emoji = "❌"
            status_text = "All Failed"
            color = "danger"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duration_str = str(duration).split('.')[0]  # Remove microseconds
        
        # Create summary sections
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Termination Automation Summary"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:* {status_text}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:* {duration_str}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Successful:* {successful_count}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Failed:* {failed_count}"
                    }
                ]
            }
        ]
        
        # Add details for successful terminations
        if successful_count > 0:
            successful_users = [r for r in results if r.get('success')]
            success_text = "\n".join([
                f"• {r.get('name', 'Unknown')} ({r.get('email', 'Unknown')})"
                for r in successful_users[:5]  # Limit to first 5
            ])
            
            if len(successful_users) > 5:
                success_text += f"\n• ... and {len(successful_users) - 5} more"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ Successful Terminations:*\n{success_text}"
                }
            })
        
        # Add details for failed terminations
        if failed_count > 0:
            failed_users = [r for r in results if not r.get('success')]
            failed_text = "\n".join([
                f"• {r.get('name', 'Unknown')} ({r.get('email', 'Unknown')}) - {r.get('error', 'Unknown error')}"
                for r in failed_users[:3]  # Limit to first 3 failures
            ])
            
            if len(failed_users) > 3:
                failed_text += f"\n• ... and {len(failed_users) - 3} more failures"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*❌ Failed Terminations:*\n{failed_text}"
                }
            })
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🤖 Automated Termination Report • {timestamp}"
                }
            ]
        })
        
        message = {
            "text": f"{status_emoji} Termination Summary: {successful_count} successful, {failed_count} failed",
            "blocks": blocks
        }
        
        # Add color coding for attachments (fallback for older Slack clients)
        if color:
            message["attachments"] = [{
                "color": color,
                "fallback": f"Termination Summary: {successful_count} successful, {failed_count} failed"
            }]
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=message,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Sent termination summary to Slack: {successful_count} successful, {failed_count} failed")
            return True
        else:
            logger.error(f"Failed to send Slack summary: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception sending Slack summary: {str(e)}")
        return False

def send_error_notification(error_message: str, context: str = "") -> bool:
    """
    Send error notification to Slack for critical failures.
    
    Args:
        error_message: The error message to send
        context: Additional context about the error
        
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        webhook_url = get_slack_webhook_url()
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping error notification")
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = {
            "text": "🚨 Termination Automation Error",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Termination Automation Error"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:* {error_message}"
                    }
                }
            ]
        }
        
        if context:
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Context:* {context}"
                }
            })
        
        message["blocks"].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🤖 Termination System Alert • {timestamp}"
                }
            ]
        })
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=message,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("Sent error notification to Slack")
            return True
        else:
            logger.error(f"Failed to send error notification: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception sending error notification: {str(e)}")
        return False

def test_slack_connection() -> bool:
    """
    Test the Slack webhook connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        webhook_url = get_slack_webhook_url()
        if not webhook_url:
            logger.error("No Slack webhook URL configured")
            return False
        
        test_message = {
            "text": "🧪 Termination Automation - Test Message",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🧪 *Termination Automation Test*\n\nThis is a test message to verify Slack integration is working correctly."
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🤖 Test sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            webhook_url,
            json=test_message,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("Slack connection test successful")
            return True
        else:
            logger.error(f"Slack connection test failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception testing Slack connection: {str(e)}")
        return False
