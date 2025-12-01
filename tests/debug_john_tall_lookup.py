#!/usr/bin/env python3
"""
Debug script to test IRU device lookup for John Tall specifically.
This will help us understand why the device wasn't found during termination.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_users_api_approach():
    """Test the new users API approach for finding John Tall's devices."""
    from jml_automation.services.iru import IruService
    
    print("🔍 TESTING NEW USERS API APPROACH")
    print("=" * 50)
    
    iru = IruService(dry_run=False)  # Use real API to debug
    test_email = "johntall@filevine.com"
    
    try:
        print(f"🎯 Looking up user: {test_email}")
        
        # Step 1: Test getting all users
        print("\n📡 Step 1: Getting all users from Kandji...")
        users_response = iru._make_api_request("GET", "/users")
        
        if isinstance(users_response, list):
            all_users = users_response
        elif isinstance(users_response, dict):
            all_users = users_response.get("results", users_response.get("data", []))
        else:
            all_users = []
            
        print(f"✅ Found {len(all_users)} total users")
        
        # Step 2: Look for John Tall
        john_user = None
        for i, user in enumerate(all_users):
            if i < 3:  # Show first few user structures
                print(f"\n� User {i+1} structure:")
                print(f"   Keys: {list(user.keys())}")
                print(f"   Email: {user.get('email', 'NO EMAIL')}")
                print(f"   Name: {user.get('name', 'NO NAME')}")
                print(f"   ID: {user.get('id', 'NO ID')}")
            
            user_email_from_api = user.get("email", "").lower()
            if user_email_from_api == test_email.lower():
                john_user = user
                print(f"\n🎯 FOUND JOHN TALL USER:")
                print(f"   User ID: {user.get('id')}")
                print(f"   Name: {user.get('name')}")
                print(f"   Email: {user.get('email')}")
                print(f"   Full user object: {user}")
                break
        
        if not john_user:
            print(f"❌ John Tall user ({test_email}) not found in users list")
            return []
        
        user_id = john_user.get("id")
        print(f"\n🔍 Step 3: Getting devices for user ID: {user_id}")
        
        # Step 3: Try to get John's devices via different endpoints
        devices_found = []
        
        # Method A: Try /users/{user_id}/devices
        try:
            print(f"🅰️ Trying GET /users/{user_id}/devices...")
            user_devices_response = iru._make_api_request("GET", f"/users/{user_id}/devices")
            print(f"   Response: {user_devices_response}")
            
            if user_devices_response:
                if isinstance(user_devices_response, list):
                    devices_found = user_devices_response
                elif isinstance(user_devices_response, dict):
                    devices_found = user_devices_response.get("results", user_devices_response.get("data", []))
                print(f"   ✅ Found {len(devices_found)} devices via users endpoint")
        except Exception as e:
            print(f"   ❌ /users/{user_id}/devices failed: {e}")
        
        # Method B: Get all devices and filter by user_id
        if not devices_found:
            print(f"\n🅱️ Trying device enumeration with user_id filter...")
            all_devices_response = iru._make_api_request("GET", "/devices")
            
            if isinstance(all_devices_response, list):
                all_devices = all_devices_response
            elif isinstance(all_devices_response, dict):
                all_devices = all_devices_response.get("results", all_devices_response.get("data", []))
            else:
                all_devices = []
            
            print(f"   Retrieved {len(all_devices)} total devices")
            
            # Look for devices assigned to John's user_id
            for device in all_devices:
                device_user_id = None
                
                # Check various user ID fields
                if isinstance(device.get("user"), dict):
                    device_user_id = device["user"].get("id")
                elif isinstance(device.get("user"), str):
                    device_user_id = device["user"]
                
                if not device_user_id and isinstance(device.get("primary_user"), dict):
                    device_user_id = device["primary_user"].get("id")
                elif not device_user_id and isinstance(device.get("primary_user"), str):
                    device_user_id = device["primary_user"]
                
                if not device_user_id:
                    device_user_id = device.get("user_id") or device.get("assigned_user_id")
                
                # Also check for MBP168-071 specifically
                device_name = device.get('device_name', device.get('name', ''))
                if 'MBP168-071' in device_name:
                    print(f"\n🔍 FOUND MBP168-071 DEVICE:")
                    print(f"   Device ID: {device.get('device_id', device.get('id'))}")
                    print(f"   Device Name: {device_name}")
                    print(f"   User field: {device.get('user')}")
                    print(f"   Primary user field: {device.get('primary_user')}")
                    print(f"   User ID extracted: {device_user_id}")
                    print(f"   Looking for user_id: {user_id}")
                    print(f"   Match: {device_user_id == user_id}")
                
                if device_user_id == user_id:
                    devices_found.append(device)
                    print(f"   ✅ Found device via user_id match: {device_name}")
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Total devices found for {test_email}: {len(devices_found)}")
        
        return devices_found
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []

def test_original_vs_new_method():
    """Compare original device enumeration vs new users API approach."""
    from jml_automation.services.iru import IruService
    
    print("\n🆚 COMPARING OLD VS NEW APPROACH")
    print("=" * 50)
    
    iru = IruService(dry_run=False)
    test_email = "johntall@filevine.com"
    
    # Test new method
    print("🔄 Testing NEW users API method...")
    new_devices = iru._find_devices_via_users_api(test_email)
    print(f"   New method found: {len(new_devices)} devices")
    
    # Test old method  
    print("\n🔄 Testing OLD device enumeration method...")
    old_devices = iru._find_devices_via_device_enumeration(test_email)
    print(f"   Old method found: {len(old_devices)} devices")
    
    # Test combined method
    print("\n🔄 Testing COMBINED method...")
    combined_devices = iru.find_devices_by_user_email(test_email)
    print(f"   Combined method found: {len(combined_devices)} devices")
    
    return new_devices, old_devices, combined_devices

if __name__ == "__main__":
    print("🚀 STARTING COMPREHENSIVE JOHN TALL DEBUG SESSION")
    print("=" * 70)
    
    # Test 1: Users API approach
    users_api_devices = test_users_api_approach()
    
    # Test 2: Compare methods
    new_devs, old_devs, combined_devs = test_original_vs_new_method()
    
    print(f"\n🎯 SUMMARY:")
    print(f"   Users API approach: {len(users_api_devices)} devices")
    print(f"   New method: {len(new_devs)} devices") 
    print(f"   Old method: {len(old_devs)} devices")
    print(f"   Combined method: {len(combined_devs)} devices")
    
    if combined_devs:
        print("\n✅ SUCCESS: John Tall's devices should now be found!")
        for device in combined_devs:
            print(f"   - {device.get('device_name', 'Unknown')}")
    else:
        print("\n❌ STILL NOT WORKING: Need to investigate API structure further")