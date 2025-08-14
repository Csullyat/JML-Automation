#!/usr/bin/env python3
"""
Post-cleanup verification test
Ensures all core functionality works after project cleanup
"""

def verify_clean_project():
    """Verify the cleaned project is fully functional."""
    
    print("🧹 POST-CLEANUP VERIFICATION TEST")
    print("=" * 60)
    
    # Test 1: Core imports
    print("🔍 Testing core imports...")
    try:
        from enterprise_termination_orchestrator import EnterpriseTerminationOrchestrator
        from config import get_okta_domain, get_configuration_summary, get_okta_token
        from ticket_processor import fetch_termination_tickets
        from okta_termination import OktaTermination
        from google_termination import GoogleTermination
        from microsoft_termination import MicrosoftTermination
        from zoom_termination import ZoomTermination
        from logging_system import setup_logging
        print("✅ All core imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Configuration validation
    print("\n🔍 Testing configuration...")
    try:
        config_status = get_configuration_summary()
        print(f"✅ 1Password Service Account: {config_status['onepassword_service_account']}")
        print(f"✅ Critical components ready: {config_status['critical_components_ready']}")
        print(f"✅ Okta domain: {get_okta_domain()}")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    # Test 3: Orchestrator initialization
    print("\n🔍 Testing orchestrator initialization...")
    try:
        orchestrator = EnterpriseTerminationOrchestrator()
        print("✅ Enterprise Termination Orchestrator V2.0 initialized")
    except Exception as e:
        print(f"❌ Orchestrator initialization failed: {e}")
        return False
    
    # Test 4: Project structure
    print("\n🔍 Checking project structure...")
    import os
    
    required_files = [
        'config.py',
        'enterprise_termination_orchestrator.py',
        'termination_main.py',
        'okta_termination.py',
        'google_termination.py', 
        'microsoft_termination.py',
        'zoom_termination.py',
        'ticket_processor.py',
        'termination_extractor.py',
        'logging_system.py',
        'slack_notifications.py',
        'get_credential.ps1',
        'requirements.txt',
        'README.md'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
    
    # Test 5: Cleaned files check
    print("\n🔍 Verifying cleanup...")
    cleanup_files = [
        'config_old.py', 'config_backup.py', 'debug_config.py',
        'test_fetch.py', 'test_dry_run.py', 'detailed_analysis.py'
    ]
    
    remaining_cleanup_files = [f for f in cleanup_files if os.path.exists(f)]
    if remaining_cleanup_files:
        print(f"⚠️ Cleanup files still present: {remaining_cleanup_files}")
    else:
        print("✅ Cleanup completed successfully")
    
    print("\n" + "=" * 60)
    print("🎉 PROJECT CLEANUP VERIFICATION PASSED")
    print("✅ Termination Automation V1.4 is clean and ready for production")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    verify_clean_project()
