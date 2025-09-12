"""Windows Credential Manager utility for service account credentials."""

import subprocess
import keyring
from typing import Optional, Dict, Any
from ..logger import logger


class WindowsCredentialManager:
    """Windows Credential Manager interface for service account credentials."""
    
    def __init__(self):
        """Initialize credential manager."""
        self.service_account_name = "JML Service Account"
        logger.info("Windows Credential Manager initialized")
    
    def get_credential(self, target_name: str, username: Optional[str] = None) -> Optional[str]:
        """
        Get a credential from Windows Credential Manager using keyring.
        
        Args:
            target_name: The target name of the stored credential
            username: The username for the credential (optional)
            
        Returns:
            The credential value if found, None otherwise
        """
        try:
            # Try to get the credential using keyring
            password = keyring.get_password(target_name, username or 'token')
            
            if password:
                logger.info(f"Found credential for {target_name}")
                return password
            else:
                logger.warning(f"Credential not found for {target_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing credential {target_name}: {e}")
            return None
    
    def get_service_account_token(self) -> Optional[str]:
        """
        Get the service account token from Windows Credential Manager.
        
        Returns:
            The service account token if found, None otherwise
        """
        return self.get_credential(self.service_account_name, 'token')
    
    def get_synqprox_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get SYNQ Prox credentials from the service account token.
        
        Returns:
            Dictionary with username and password if found, None otherwise
        """
        try:
            # Get the service account token
            token = self.get_service_account_token()
            if not token:
                logger.error("No service account token found in Windows Credential Manager")
                return None
            
            # Use the token with 1Password CLI to get SYNQ Prox credentials
            return self._get_synqprox_from_onepassword(token)
            
        except Exception as e:
            logger.error(f"Error getting SYNQ Prox credentials: {e}")
            return None
    
    def _get_synqprox_from_onepassword(self, token: str) -> Optional[Dict[str, str]]:
        """
        Use 1Password CLI with service account token to get SYNQ Prox credentials.
        
        Args:
            token: The service account token
            
        Returns:
            Dictionary with username and password if successful, None otherwise
        """
        try:
            import os
            
            # Set the service account token environment variable
            env = os.environ.copy()
            env['OP_SERVICE_ACCOUNT_TOKEN'] = token
            
            # Get username from synqprox-admin entry in IT vault
            username_cmd = ["op", "read", "op://IT/synqprox-admin/username"]
            username_result = subprocess.run(
                username_cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            # Get password from synqprox-admin entry in IT vault
            password_cmd = ["op", "read", "op://IT/synqprox-admin/password"]
            password_result = subprocess.run(
                password_cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            if username_result.returncode == 0 and password_result.returncode == 0:
                username = username_result.stdout.strip()
                password = password_result.stdout.strip()
                
                if username and password:
                    logger.info("Successfully retrieved SYNQ Prox credentials from 1Password IT vault")
                    return {
                        'username': username,
                        'password': password
                    }
            
            logger.error("Failed to retrieve SYNQ Prox credentials from 1Password")
            logger.error(f"Username command: {' '.join(username_cmd)}")
            logger.error(f"Username result: {username_result.stderr}")
            logger.error(f"Password command: {' '.join(password_cmd)}")
            logger.error(f"Password result: {password_result.stderr}")
            return None
            
        except Exception as e:
            logger.error(f"Error using 1Password CLI: {e}")
            return None
