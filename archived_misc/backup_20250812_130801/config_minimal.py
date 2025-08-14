# config_minimal.py - Test version
import subprocess
import os

OKTA_ORG_URL = "https://filevine.okta.com"
SAMANAGE_BASE_URL = "https://api.samanage.com"

def get_okta_domain() -> str:
    """Get Okta domain."""
    return "filevine.okta.com"

def get_okta_token() -> str:
    """Get the Okta API token from 1Password."""
    return "test"
