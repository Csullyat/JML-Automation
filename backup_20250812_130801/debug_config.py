#!/usr/bin/env python3
"""Debug config import issues"""

print("Testing config.py imports...")

# Test basic imports
try:
    import subprocess
    print("✓ subprocess import ok")
except Exception as e:
    print("✗ subprocess import failed:", e)

try:
    import os
    print("✓ os import ok")
except Exception as e:
    print("✗ os import failed:", e)

try:
    import json
    print("✓ json import ok")
except Exception as e:
    print("✗ json import failed:", e)

try:
    from google.oauth2 import service_account
    print("✓ google.oauth2.service_account import ok")
except Exception as e:
    print("✗ google.oauth2.service_account import failed:", e)

# Now test each function from config manually
print("\nTesting config functions...")

try:
    exec(open('config.py').read())
    print("✓ config.py executed successfully")
    
    # Check if get_okta_domain is defined
    if 'get_okta_domain' in locals():
        print("✓ get_okta_domain is defined")
        print("  Domain:", get_okta_domain())
    else:
        print("✗ get_okta_domain not found in locals")
        
except Exception as e:
    print("✗ config.py execution failed:", e)
    import traceback
    traceback.print_exc()
