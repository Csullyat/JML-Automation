# execute_valerie_termination.py - Clear sessions and deactivate Valerie Baird

import logging
from config import get_okta_token, get_okta_domain
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Valerie's details from termination ticket and Okta search
EMPLOYEE_ID = "13431581"
EMPLOYEE_NAME = "Valerie Baird"
EMPLOYEE_EMAIL = "valeriebaird@filevine.com"  # Found in Okta

def execute_termination():
    """Execute termination for Valerie Baird - clear sessions and deactivate."""
    
    logger.info(f"Starting termination for {EMPLOYEE_NAME} (Employee ID: {EMPLOYEE_ID})")
    
    # Get Okta credentials
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Step 1: Find user by email (we know her email from search)
        logger.info(f"Looking up user {EMPLOYEE_EMAIL} in Okta...")
        
        response = requests.get(
            f"https://{okta_domain}/api/v1/users/{EMPLOYEE_EMAIL}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to find user {EMPLOYEE_EMAIL}: {response.status_code} - {response.text}")
            return False
        
        user = response.json()
        user_id = user['id']
        user_email = user.get('profile', {}).get('email', 'Unknown')
        user_status = user.get('status', 'Unknown')
        
        logger.info(f"Found user: {user_email} (Status: {user_status})")
        
        # Step 2: Clear all active sessions (CRITICAL SECURITY STEP)
        logger.info(f"CLEARING ALL ACTIVE SESSIONS for {user_email}...")
        
        session_response = requests.delete(
            f"https://{okta_domain}/api/v1/users/{user_id}/sessions",
            headers=headers,
            timeout=30
        )
        
        if session_response.status_code == 204:
            logger.info("✅ ALL SESSIONS CLEARED SUCCESSFULLY")
        else:
            logger.error(f"❌ FAILED TO CLEAR SESSIONS: {session_response.status_code} - {session_response.text}")
            return False
        
        # Step 3: Deactivate user account
        logger.info(f"DEACTIVATING user account for {user_email}...")
        
        deactivate_response = requests.post(
            f"https://{okta_domain}/api/v1/users/{user_id}/lifecycle/deactivate",
            headers=headers,
            timeout=30
        )
        
        if deactivate_response.status_code == 200:
            logger.info("✅ USER ACCOUNT DEACTIVATED SUCCESSFULLY")
        else:
            logger.error(f"❌ FAILED TO DEACTIVATE ACCOUNT: {deactivate_response.status_code} - {deactivate_response.text}")
            return False
        
        logger.info(f"🔒 TERMINATION COMPLETE: {EMPLOYEE_NAME} ({user_email}) - Sessions cleared and account deactivated")
        return True
        
    except Exception as e:
        logger.error(f"Exception during termination: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("EXECUTING TERMINATION FOR VALERIE BAIRD")
    print("Employee ID: 13431581")
    print("Actions: Clear all sessions + Deactivate account")
    print("=" * 70)
    
    success = execute_termination()
    
    if success:
        print("\n✅ TERMINATION EXECUTED SUCCESSFULLY")
    else:
        print("\n❌ TERMINATION FAILED - CHECK LOGS")
