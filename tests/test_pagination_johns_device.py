#!/usr/bin/env python3
"""
Test pagination and search for John Tall's MBP168-071 device.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_pagination_and_find_robert_hafen_device():
    """Test if pagination gets all devices and find Robert Hafen's devices."""
    from jml_automation.services.iru import IruService
    
    print("🔍 TESTING PAGINATION AND ROBERT HAFEN'S DEVICE SEARCH")
    print("=" * 60)
    
    iru = IruService(dry_run=False)
    
    try:
        # Test the new paginated device retrieval
        print("📡 Fetching ALL devices with pagination...")
        all_devices = iru._get_all_devices_paginated()
        
        print(f"✅ Total devices retrieved: {len(all_devices)}")
        
        if len(all_devices) >= 600:
            print("🎉 SUCCESS: Got all devices (600+)!")
        else:
            print(f"⚠️  WARNING: Only got {len(all_devices)} devices, expected ~600")
        
        # Look specifically for Robert Hafen's devices
        print(f"\n🎯 Searching for devices assigned to roberthafen@filevine.com...")
        roberts_devices = []
        
        for device in all_devices:
            # Check user assignment
            user_info = device.get('user', {})
            if isinstance(user_info, dict):
                user_email = user_info.get('email', '').lower()
                if user_email == 'roberthafen@filevine.com':
                    roberts_devices.append(device)
            
            # Also check primary_user
            primary_user_info = device.get('primary_user', {})
            if isinstance(primary_user_info, dict):
                primary_email = primary_user_info.get('email', '').lower()
                if primary_email == 'roberthafen@filevine.com' and device not in roberts_devices:
                    roberts_devices.append(device)
        
        if roberts_devices:
            print(f"🎉 FOUND {len(roberts_devices)} DEVICE(S) FOR ROBERT HAFEN!")
            for i, device in enumerate(roberts_devices):
                print(f"\n   Device {i+1}:")
                print(f"   Device Name: {device.get('device_name', device.get('name'))}")
                print(f"   Device ID: {device.get('device_id', device.get('id'))}")
                print(f"   User field: {device.get('user')}")
                print(f"   Primary User: {device.get('primary_user')}")
                print(f"   Asset Tag: {device.get('asset_tag')}")
                print(f"   Blueprint Name: {device.get('blueprint_name', 'Unknown')}")
                print(f"   Last Check-in: {device.get('last_check_in')}")
                
                # Check user assignment details
                user_info = device.get('user', {})
                if isinstance(user_info, dict):
                    user_email = user_info.get('email', '').lower()
                    user_active = user_info.get('active', 'Unknown')
                    print(f"   Assigned User Email: {user_email}")
                    print(f"   User Active Status: {user_active}")
        else:
            print("❌ NO DEVICES FOUND for roberthafen@filevine.com")
            
            # Sample a few device names to see what we're getting
            print("\n📋 Sample device names and users:")
            for i, device in enumerate(all_devices[:10]):
                device_name = device.get('device_name', device.get('name', 'NO NAME'))
                user_info = device.get('user', {})
                user_email = 'No User'
                if isinstance(user_info, dict):
                    user_email = user_info.get('email', 'No Email')
                print(f"   {i+1}: {device_name} -> {user_email}")
        
        # Now test the full lookup method
        print(f"\n🧪 Testing find_devices_by_user_email for roberthafen@filevine.com...")
        found_devices = iru.find_devices_by_user_email("roberthafen@filevine.com")
        
        print(f"📊 Found {len(found_devices)} devices for roberthafen@filevine.com")
        for device in found_devices:
            print(f"   - {device.get('device_name', 'Unknown')}: {device.get('device_id', device.get('id'))}")
        
        if found_devices:
            print("✅ SUCCESS: Device lookup works for Robert Hafen!")
        else:
            print("❌ DEVICE LOOKUP FAILED for roberthafen@filevine.com")
            
            # If we found Robert's devices manually but lookup failed, debug why
            if roberts_devices:
                print(f"\n🔍 DEBUGGING: Why weren't Robert's devices found by email lookup?")
                for i, device in enumerate(roberts_devices):
                    print(f"\n   Device {i+1} Analysis:")
                    user_field = device.get('user', {})
                    primary_user_field = device.get('primary_user', {})
                    
                    print(f"   User field type: {type(user_field)}")
                    print(f"   User field content: {user_field}")
                    print(f"   Primary user field type: {type(primary_user_field)}")
                    print(f"   Primary user field content: {primary_user_field}")
                    
                    # Test each condition used in the lookup
                    if isinstance(user_field, dict):
                        device_email = user_field.get("email", "").lower()
                        print(f"   Extracted user email: '{device_email}'")
                        print(f"   Matches 'roberthafen@filevine.com'? {device_email == 'roberthafen@filevine.com'}")
        
        return found_devices
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []

if __name__ == "__main__":
    test_pagination_and_find_robert_hafen_device()