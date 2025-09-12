#!/usr/bin/env python3
"""
Manual debugging script for SYNQ Prox automation.
This will login and then pause, allowing manual navigation to see the UI.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.services.synqprox import SynqProxService
from jml_automation.logger import setup_logging

def manual_debug():
    setup_logging()
    print("=== Manual Debug Session for SYNQ Prox ===")
    
    synq_service = SynqProxService()
    
    try:
        # Login
        print("Logging in...")
        if synq_service._login():
            print("✅ Login successful!")
            
            # Pause for manual inspection
            print("\n🔍 Browser is now open and logged in.")
            print("You can now manually:")
            print("1. Click around to see what elements are available")
            print("2. Open DevTools (F12) to inspect the page")
            print("3. Look for the Users link in the sidebar")
            print("4. Navigate to the users page manually")
            print("5. See what the actual page structure looks like")
            
            input("\nPress ENTER when you want to continue with automation...")
            
            # Try to navigate to users
            print("\nNow attempting automated navigation...")
            if synq_service._navigate_to_users():
                print("✅ Navigation successful!")
            else:
                print("❌ Navigation failed")
                
            # Another pause to see the result
            input("\nPress ENTER to close the browser...")
            
        else:
            print("❌ Login failed")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if synq_service.driver:
            synq_service.driver.quit()

if __name__ == "__main__":
    manual_debug()
