#!/usr/bin/env python3
"""
Integration test script for the Filevine automation system.

Run this from the project root:
    python test_integration.py

This will test each component and then run a test onboarding workflow.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from datetime import datetime
from typing import Dict, Any

# Import all our components
from jml_automation.config import Config
from jml_automation.extractors.solarwinds import SolarWindsExtractor
from jml_automation.services.okta import OktaService
from jml_automation.services.slack import SlackService
from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.workflows.onboarding import OnboardingWorkflow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_config() -> bool:
    """Test configuration loading."""
    print_header("Testing Configuration")
    
    try:
        print("Loading configuration...")
        config = Config()
        
        # Check if files loaded
        print(f"✓ Settings loaded: {len(config.settings)} keys")
        print(f"✓ Departments loaded: {len(config.departments)} keys")
        print(f"✓ Termination order loaded: {len(config.termination)} keys")
        
        # Test getting a URL
        okta_url = config.okta_url
        print(f"✓ Okta URL: {okta_url}")
        
        # Test getting SolarWinds config
        sw_config = config.get_solarwinds_config()
        print(f"✓ SolarWinds config: {len(sw_config)} settings")
        
        # Test secret retrieval (won't work without 1Password but will show attempt)
        print("\nTesting secret retrieval...")
        token = config.get_secret('SAMANAGE_TOKEN')
        if token:
            print(f"✓ Retrieved SAMANAGE_TOKEN (length: {len(token)})")
        else:
            print("⚠ SAMANAGE_TOKEN not found (check 1Password CLI)")
        
        print("\nSUCCESS: Configuration test passed!")
        return True
        
    except Exception as e:
        print(f"\nERROR: Configuration test failed: {e}")
        return False


def test_extractor(config: Config) -> bool:
    """Test SolarWinds extractor."""
    print_header("Testing SolarWinds Extractor")
    
    try:
        print("Initializing extractor...")
        extractor = SolarWindsExtractor(config)
        
        # Test phone formatting
        print("\nTesting phone formatter...")
        test_phones = [
            ("5551234567", "555-123-4567"),
            ("15551234567", "555-123-4567"),
        ]
        
        for input_phone, expected in test_phones:
            try:
                result = extractor.format_phone(input_phone)
                if result == expected:
                    print(f"✓ Phone format: {input_phone} → {result}")
                else:
                    print(f"✗ Phone format: {input_phone} → {result} (expected {expected})")
            except Exception as e:
                print(f"✗ Phone format error: {input_phone} - {e}")
        
        # Test timezone determination
        print("\nTesting timezone determination...")
        test_timezones = [
            ("UT", "US", "America/Denver"),
            ("NY", "US", "America/New_York"),
            ("CA", "US", "America/Los_Angeles"),
        ]
        
        for state, country, expected in test_timezones:
            result = extractor._determine_timezone(state, country)
            if result == expected:
                print(f"✓ Timezone: {state}, {country} → {result}")
            else:
                print(f"✗ Timezone: {state}, {country} → {result} (expected {expected})")
        
        # Try to fetch tickets (this will fail without valid token but shows attempt)
        print("\nAttempting to fetch tickets...")
        try:
            # Just test the connection, don't actually fetch all tickets
            page_1 = extractor._fetch_page(1)
            if page_1:
                print(f"✓ Can connect to SolarWinds (fetched {len(page_1)} tickets from page 1)")
            else:
                print("⚠ Could not fetch tickets (check token/connection)")
        except Exception as e:
            print(f"⚠ SolarWinds connection error: {e}")
        
        print("\nSUCCESS: Extractor test completed!")
        return True
        
    except Exception as e:
        print(f"\nERROR: Extractor test failed: {e}")
        return False


def test_services(config: Config) -> Dict[str, bool]:
    """Test all services."""
    print_header("Testing Services")
    
    results = {}
    
    # Test Okta Service
    print("\n1. Testing Okta Service...")
    try:
        okta = OktaService(config)
        if okta.test_connection():
            print("✓ Okta connection successful")
            results['okta'] = True
        else:
            print("✗ Okta connection failed")
            results['okta'] = False
    except Exception as e:
        print(f"✗ Okta initialization failed: {e}")
        results['okta'] = False
    
    # Test Slack Service
    print("\n2. Testing Slack Service...")
    try:
        slack = SlackService(config)
        if slack.test_connection():
            print("✓ Slack connection successful")
            results['slack'] = True
        else:
            print("✗ Slack connection failed")
            results['slack'] = False
    except Exception as e:
        print(f"✗ Slack initialization failed: {e}")
        results['slack'] = False
    
    # Test SolarWinds Service
    print("\n3. Testing SolarWinds Service...")
    try:
        solarwinds = SolarWindsService(config)
        if solarwinds.test_connection():
            print("✓ SolarWinds Service connection successful")
            results['solarwinds'] = True
        else:
            print("✗ SolarWinds Service connection failed")
            results['solarwinds'] = False
    except Exception as e:
        print(f"✗ SolarWinds Service initialization failed: {e}")
        results['solarwinds'] = False
    
    # Summary
    working = sum(1 for v in results.values() if v)
    total = len(results)
    
    if working == total:
        print(f"\nSUCCESS: All {total} services tested successfully!")
    else:
        print(f"\nWARNING: {working}/{total} services working")
    
    return results


def test_workflow(config: Config, skip_if_no_services: bool = True) -> bool:
    """Test the onboarding workflow."""
    print_header("Testing Onboarding Workflow")
    
    try:
        print("Initializing workflow in TEST MODE...")
        workflow = OnboardingWorkflow(config, test_mode=True)
        
        print("\nChecking service connections...")
        connections_ok = workflow._test_connections()
        
        if not connections_ok and skip_if_no_services:
            print("\nWARNING: Skipping workflow run due to service connection issues")
            print("   (This is expected if tokens are not configured)")
            return True
        
        if connections_ok:
            print("\n Running workflow (TEST MODE - will process 1 user max)...")
            print("-"*40)
            
            result = workflow.run()
            
            print("-"*40)
            print("\nWorkflow Result:")
            print(f"  Success: {result.get('success')}")
            print(f"  Duration: {result.get('duration')}")
            print(f"  Statistics: {result.get('statistics')}")
            
            return result.get('success', False)
        else:
            print("\nWARNING: Cannot run workflow - service connections failed")
            return False
            
    except Exception as e:
        print(f"\nERROR: Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("\n" + ""*30)
    print("  FILEVINE AUTOMATION INTEGRATION TEST")
    print(""*30)
    
    start_time = datetime.now()
    
    # Track results
    all_tests_passed = True
    
    # Test 1: Configuration
    if not test_config():
        print("\nWARNING: Configuration issues detected. Please check your config files.")
        all_tests_passed = False
        # Don't continue if config fails
        return
    
    # Load config for remaining tests
    config = Config()
    
    # Test 2: Extractor
    if not test_extractor(config):
        all_tests_passed = False
    
    # Test 3: Services
    service_results = test_services(config)
    if not all(service_results.values()):
        print("\nWARNING: Some services are not working. Check your tokens/credentials.")
        all_tests_passed = False
    
    # Test 4: Workflow (only if services are working)
    if all(service_results.values()):
        if not test_workflow(config, skip_if_no_services=False):
            all_tests_passed = False
    else:
        print_header("Workflow Test")
        print("WARNING: Skipping workflow test - services not fully configured")
    
    # Final Summary
    duration = datetime.now() - start_time
    
    print_header("INTEGRATION TEST COMPLETE")
    
    if all_tests_passed:
        print("SUCCESS: All tests passed successfully!")
    else:
        print("WARNING: Some tests failed or were skipped")
    
    print(f"\nTotal time: {duration}")
    
    print("\n" + "-"*60)
    print("Next Steps:")
    print("-"*60)
    
    if not config.get_secret('SAMANAGE_TOKEN'):
        print("1. Configure 1Password CLI and ensure tokens are accessible")
    
    if not all(service_results.values()):
        print("2. Check service credentials:")
        if not service_results.get('okta'):
            print("   - OKTA_TOKEN")
        if not service_results.get('slack'):
            print("   - SLACK_TOKEN")
        if not service_results.get('solarwinds'):
            print("   - SAMANAGE_TOKEN/SOLARWINDS_TOKEN")
    
    if all_tests_passed and all(service_results.values()):
        print("SUCCESS: System is ready for production use!")
        print("\nTo run onboarding:")
        print("  python -c \"from filevine.workflows.onboarding import run_onboarding; run_onboarding(test_mode=True)\"")


if __name__ == "__main__":
    main()
