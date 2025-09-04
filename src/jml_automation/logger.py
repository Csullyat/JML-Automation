# Centralized logging configuration for JML automation system

import logging
import logging.handlers
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

def setup_logging(log_level: str = "INFO", 
                 log_to_file: bool = True,
                 log_dir: str = "logs",
                 max_file_size: int = 50 * 1024 * 1024,  # 50MB
                 backup_count: int = 10) -> logging.Logger:
    """
    Set up comprehensive logging for the JML automation system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to files
        log_dir: Directory for log files
        max_file_size: Maximum size of each log file in bytes
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_to_file:
        # Main log file (rotating)
        main_log_file = log_path / "jml_automation.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error log file (only errors and critical)
        error_log_file = log_path / "jml_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # Daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        daily_log_file = log_path / f"jml_{today}.log"
        daily_handler = logging.FileHandler(
            daily_log_file,
            encoding='utf-8'
        )
        daily_handler.setLevel(getattr(logging, log_level.upper()))
        daily_handler.setFormatter(formatter)
        logger.addHandler(daily_handler)
    
    # Set up specific loggers for external libraries
    requests_logger = logging.getLogger('requests')
    requests_logger.setLevel(logging.WARNING)
    
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.WARNING)
    
    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.WARNING)
    
    # Log startup message
    logger.info("=" * 80)
    logger.info("JML AUTOMATION LOGGING INITIALIZED")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Log to File: {log_to_file}")
    if log_to_file:
        logger.info(f"Log Directory: {os.path.abspath(log_dir)}")
    logger.info("=" * 80)
    
    return logger

def log_jml_action(user_email: str, action: str, result: str, 
                   ticket_number: str = "", details: Optional[str] = None,
                   action_type: str = "TERMINATION"):
    """
    Log a specific JML action with structured format.
    
    Args:
        user_email: Email of the user being processed
        action: Action being performed (e.g., "DEACTIVATE", "CREATE_USER", "REMOVE_FROM_GROUP")
        result: Result of the action ("SUCCESS", "FAILED", "SKIPPED")
        ticket_number: Service desk ticket number
        details: Additional details about the action
        action_type: Type of action ("ONBOARDING", "TERMINATION", "MOVER")
    """
    logger = logging.getLogger(__name__)
    
    # Create structured log entry
    log_data = {
        'user_email': user_email,
        'action': action,
        'result': result,
        'ticket_number': ticket_number,
        'timestamp': datetime.now().isoformat(),
        'details': details or "",
        'action_type': action_type
    }
    
    # Format for human readability
    message = f"{action_type}_ACTION | {user_email} | {action} | {result}"
    if ticket_number:
        message += f" | Ticket: {ticket_number}"
    if details:
        message += f" | {details}"
    
    # Log at appropriate level based on result
    if result == "SUCCESS":
        logger.info(message)
    elif result == "FAILED":
        logger.error(message)
    else:
        logger.warning(message)

def log_termination_action(user_email: str, action: str, result: str, 
                          ticket_number: str = "", details: Optional[str] = None):
    """
    Log a specific termination action with structured format.
    Wrapper for log_jml_action for backward compatibility.
    """
    log_jml_action(user_email, action, result, ticket_number, details, "TERMINATION")

def log_onboarding_action(user_email: str, action: str, result: str, 
                         ticket_number: str = "", details: Optional[str] = None):
    """
    Log a specific onboarding action with structured format.
    """
    log_jml_action(user_email, action, result, ticket_number, details, "ONBOARDING")

def log_system_event(event_type: str, message: str, level: str = "INFO", 
                    user_email: str = "", ticket_number: str = ""):
    """
    Log a system event with consistent formatting.
    
    Args:
        event_type: Type of event (e.g., "STARTUP", "SHUTDOWN", "ERROR", "CONNECTION_TEST")
        message: Event message
        level: Log level (INFO, WARNING, ERROR, etc.)
        user_email: Associated user email (if applicable)
        ticket_number: Associated ticket number (if applicable)
    """
    logger = logging.getLogger(__name__)
    
    # Format system event message
    log_message = f"SYSTEM_EVENT | {event_type} | {message}"
    if user_email:
        log_message += f" | User: {user_email}"
    if ticket_number:
        log_message += f" | Ticket: {ticket_number}"
    
    # Log at specified level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, log_message)

def log_performance_metric(operation: str, duration_seconds: float, 
                          user_count: int = 0, success_count: int = 0):
    """
    Log performance metrics for analysis.
    
    Args:
        operation: Operation name (e.g., "FULL_TERMINATION_RUN", "TICKET_FETCH", "USER_ONBOARDING_BATCH")
        duration_seconds: Time taken in seconds
        user_count: Number of users processed
        success_count: Number of successful operations
    """
    logger = logging.getLogger(__name__)
    
    message = f"PERFORMANCE | {operation} | Duration: {duration_seconds:.2f}s"
    if user_count > 0:
        message += f" | Users: {user_count}"
        if success_count > 0:
            success_rate = (success_count / user_count) * 100
            message += f" | Success Rate: {success_rate:.1f}%"
    
    logger.info(message)

def get_log_summary(log_file_path: str, hours_back: int = 24) -> dict:
    """
    Get a summary of log entries from the specified time period.
    
    Args:
        log_file_path: Path to the log file to analyze
        hours_back: Number of hours to look back
        
    Returns:
        Dictionary with log summary statistics
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        summary = {
            'total_lines': 0,
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'termination_actions': 0,
            'onboarding_actions': 0,
            'successful_actions': 0,
            'failed_actions': 0,
            'system_events': 0
        }
        
        if not os.path.exists(log_file_path):
            return summary
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                summary['total_lines'] += 1
                
                # Parse timestamp and skip old entries
                try:
                    timestamp_str = line.split(' | ')[0]
                    line_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    if line_time < cutoff_time:
                        continue
                except (ValueError, IndexError):
                    continue
                
                # Count by log level
                if ' ERROR ' in line:
                    summary['error_count'] += 1
                elif ' WARNING ' in line:
                    summary['warning_count'] += 1
                elif ' INFO ' in line:
                    summary['info_count'] += 1
                
                # Count specific events
                if 'TERMINATION_ACTION' in line:
                    summary['termination_actions'] += 1
                elif 'ONBOARDING_ACTION' in line:
                    summary['onboarding_actions'] += 1
                
                if '| SUCCESS' in line:
                    summary['successful_actions'] += 1
                elif '| FAILED' in line:
                    summary['failed_actions'] += 1
                
                if 'SYSTEM_EVENT' in line:
                    summary['system_events'] += 1
        
        return summary
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating log summary: {str(e)}")
        return summary

def archive_old_logs(log_dir: str = "logs", days_to_keep: int = 30):
    """
    Archive or delete old log files to manage disk space.
    
    Args:
        log_dir: Directory containing log files
        days_to_keep: Number of days of logs to keep
    """
    try:
        import shutil
        
        logger = logging.getLogger(__name__)
        log_path = Path(log_dir)
        
        if not log_path.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        archived_count = 0
        
        # Create archive directory
        archive_path = log_path / "archived"
        archive_path.mkdir(exist_ok=True)
        
        for log_file in log_path.glob("*.log*"):
            if log_file.is_file() and log_file.stat().st_mtime < cutoff_date.timestamp():
                # Move to archive
                archive_file = archive_path / log_file.name
                shutil.move(str(log_file), str(archive_file))
                archived_count += 1
        
        if archived_count > 0:
            logger.info(f"Archived {archived_count} old log files to {archive_path}")
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error archiving old logs: {str(e)}")

# Initialize default logger when module is imported
logger = setup_logging()

# Provide backward compatibility
default_logger = logger
