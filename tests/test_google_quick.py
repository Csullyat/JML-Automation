#!/usr/bin/env python3
"""
Quick Google Workspace data transfer test.

Simple test to validate Google Workspace connectivity and basic transfer functionality.
This is a lightweight version for quick validation.
"""

import sys
import os
import logging
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.services.google import GoogleTerminationManager
from jml_automation.logger import setup_logging

def quick_test():
    """Quick test of Google Workspace functionality."""
    
    # Setup logging
    logger = setup_logging("INFO")
    logger = logging.getLogger("google_quick_test")
    
    print("🚀 Quick Google Workspace Data Transfer Test")
    print("=" * 50)
    
    try:
        # Initialize Google client
        print("1. Initializing Google Workspace client...")
        google_manager = GoogleTerminationManager()
        print("   ✅ Client initialized successfully")
        
        # Test connectivity
        print("\n2. Testing API connectivity...")
        connectivity_result = google_manager.test_connectivity()
        
        if connectivity_result['success']:
            print(f"   ✅ Connectivity test passed")
            print(f"   Message: {connectivity_result['message']}")
        else:
            print(f"   ❌ Connectivity test failed")
            print(f"   Error: {connectivity_result['error']}")
            return False
        
        # Test user lookup (using a known admin user)
        print("\n3. Testing user lookup...")
        test_user = "codyatkinson@filevine.com"  # Known admin user
        
        user = google_manager.find_user_by_email(test_user)
        if user:
            user_name = user.get('name', {}).get('fullName', 'Unknown')
            print(f"   ✅ User lookup successful")
            print(f"   Found: {user_name} ({test_user})")
        else:
            print(f"   ⚠️  User not found: {test_user}")
        
        print("\n✅ Quick test completed successfully!")
        print("\n📋 Next steps:")
        print("   - Run full test with: python test_google_data_transfer.py --dry-run <user> <manager>")
        print("   - For real transfer: python test_google_data_transfer.py --real-transfer <user> <manager> --confirm")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Quick test failed: {e}")
        return False

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)