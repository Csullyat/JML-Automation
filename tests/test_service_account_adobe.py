"""
Test Adobe credentials using service account from Windows Credential Manager
"""

import logging
from jml_automation.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_service_account_adobe():
    """Test Adobe credentials using service account."""
    print("Testing Adobe credentials with service account...")
    print("=" * 60)
    
    try:
        config = Config()
        creds = config.get_adobe_credentials_dict()
        
        print(f"Client ID: {'✓' if creds.get('client_id') else '✗'}")
        print(f"Client Secret: {'✓' if creds.get('client_secret') else '✗'}")
        print(f"Org ID: {'✓' if creds.get('org_id') else '✗'}")
        
        if all([creds.get('client_id'), creds.get('client_secret'), creds.get('org_id')]):
            print("\n✓ All Adobe OAuth credentials retrieved successfully!")
            return True
        else:
            print("\n✗ Missing Adobe credentials")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_service_account_adobe()