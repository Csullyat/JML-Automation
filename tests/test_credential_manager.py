"""Test Windows Credential Manager functionality."""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.utils.credential_manager import WindowsCredentialManager
from jml_automation.logger import logger

def test_credential_manager():
    """Test the Windows Credential Manager functionality."""
    logger.info("Testing Windows Credential Manager")
    
    cred_manager = WindowsCredentialManager()
    
    # Test getting the service account token
    logger.info("Testing service account token retrieval...")
    token = cred_manager.get_service_account_token()
    
    if token:
        logger.info("✓ Service account token found")
        logger.info(f"Token length: {len(token)} characters")
        
        # Test getting SYNQ Prox credentials
        logger.info("Testing SYNQ Prox credentials retrieval...")
        creds = cred_manager.get_synqprox_credentials()
        
        if creds:
            logger.info("✓ SYNQ Prox credentials retrieved successfully")
            logger.info(f"Username: {creds.get('username', 'Not found')}")
            logger.info(f"Password: {'*' * len(creds.get('password', '')) if creds.get('password') else 'Not found'}")
            return True
        else:
            logger.error("✗ Failed to retrieve SYNQ Prox credentials")
            return False
    else:
        logger.error("✗ No service account token found")
        logger.error("Make sure 'JML Service Account' is stored in Windows Credential Manager")
        return False

if __name__ == "__main__":
    success = test_credential_manager()
    if success:
        print("\n✓ Credential Manager test passed!")
    else:
        print("\n✗ Credential Manager test failed!")
        sys.exit(1)
