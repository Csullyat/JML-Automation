#!/usr/bin/env python3
"""
Comprehensive dry run test for the entire termination workflow.
This test will actually execute the dry run mode for each app to catch real errors.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.workflows.single_ticket import SingleTicketWorkflow


def test_comprehensive_dry_run():
    """Test the complete workflow with a real ticket in dry run mode."""
    print("=" * 70)
    print("COMPREHENSIVE DRY RUN TEST - ALL APPS")
    print("=" * 70)
    
    # Use a real ticket ID for testing
    # Replace with an actual ticket ID that you want to test with
    test_ticket_id = "64570"  # Update this to a real ticket ID
    
    print(f"Testing with ticket: {test_ticket_id}")
    print("This will test connectivity and workflow for ALL apps:")
    print("1. Okta (deactivate user, clear sessions)")
    print("2. Microsoft 365 (convert mailbox, delegate, revoke licenses)")
    print("3. Google Workspace (transfer data, delete account)")
    print("4. Zoom (transfer data, delete account)")
    print("5. Domo (delete user)")
    print("6. Lucidchart (transfer data, delete account, remove groups)")
    print("7. SYNQ Prox (delete user)")
    print("8. Adobe (delete from account, remove from SSO-Adobe group)")
    print("9. Workato (remove from workspaces, remove from groups)")
    print("\n" + "=" * 70)
    
    try:
        # Initialize the workflow
        workflow = SingleTicketWorkflow()
        
        # Execute the dry run - this will test ALL systems
        print("🧪 STARTING COMPREHENSIVE DRY RUN...")
        results = workflow.execute_single_ticket_dry_run(test_ticket_id)
        
        # Print the detailed results
        workflow.print_dry_run_summary(results)
        
        # Analyze results for each system
        print("\n" + "=" * 70)
        print("DETAILED SYSTEM ANALYSIS")
        print("=" * 70)
        
        systems_tested = results.get('systems_tested', {})
        user_email = results.get('user_email', 'Unknown')
        
        print(f"📧 Target User: {user_email}")
        print(f"📊 Systems Tested: {len(systems_tested)}")
        
        # Check each system
        for system_name, system_data in systems_tested.items():
            status = system_data.get('status', 'unknown')
            
            print(f"\n🔍 {system_name.upper()}:")
            if status == 'connected':
                print(f"   ✅ Status: CONNECTED")
                
                # Check for conditional logic
                if 'actions_needed' in system_data:
                    if system_data['actions_needed']:
                        print(f"   🎯 Actions Needed: YES")
                        print(f"   📋 Reason: {system_data.get('message', 'No details')}")
                    else:
                        print(f"   ⏭️  Actions Needed: NO (conditional logic working)")
                        print(f"   📋 Reason: {system_data.get('message', 'No details')}")
                
                # Check for user found status
                if 'user_found' in system_data:
                    user_found = system_data['user_found']
                    print(f"   👤 User Found: {'YES' if user_found else 'NO'}")
                
                # Check for group membership info
                if 'okta_groups' in system_data:
                    groups = system_data['okta_groups']
                    print(f"   👥 Okta Groups: {groups}")
                
            elif status == 'failed':
                print(f"   ❌ Status: FAILED")
                error = system_data.get('error', 'No error details')
                print(f"   🚫 Error: {error}")
            else:
                print(f"   ❓ Status: {status}")
        
        # Summary
        connected_count = len([s for s in systems_tested.values() if s.get('status') == 'connected'])
        failed_count = len([s for s in systems_tested.values() if s.get('status') == 'failed'])
        
        print("\n" + "=" * 70)
        print("DRY RUN SUMMARY")
        print("=" * 70)
        print(f"✅ Connected Systems: {connected_count}")
        print(f"❌ Failed Systems: {failed_count}")
        print(f"📈 Success Rate: {connected_count}/{len(systems_tested)} ({(connected_count/len(systems_tested)*100):.1f}%)")
        
        if results.get('errors'):
            print(f"\n🚨 ERRORS FOUND ({len(results['errors'])}):")
            for i, error in enumerate(results['errors'], 1):
                print(f"   {i}. {error}")
        
        if results.get('warnings'):
            print(f"\n⚠️  WARNINGS FOUND ({len(results['warnings'])}):")
            for i, warning in enumerate(results['warnings'], 1):
                print(f"   {i}. {warning}")
        
        # Overall result
        overall_success = results.get('overall_success', False)
        print(f"\n🎯 OVERALL DRY RUN RESULT: {'SUCCESS' if overall_success else 'PARTIAL/FAILED'}")
        
        if overall_success:
            print("🎉 ALL SYSTEMS READY - Production termination can proceed!")
        else:
            print("⚠️  SOME ISSUES FOUND - Review errors before production run")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ DRY RUN TEST FAILED: {e}")
        print(f"🔍 Exception Type: {type(e).__name__}")
        import traceback
        print(f"📋 Full Error:\n{traceback.format_exc()}")
        return False


def test_individual_app_dry_runs():
    """Test individual app services in dry run mode."""
    print("\n" + "=" * 70)
    print("INDIVIDUAL APP SERVICE TESTS")
    print("=" * 70)
    
    test_email = "test@filevine.com"  # Use a test email
    
    apps_to_test = [
        ("Adobe", "jml_automation.services.adobe", "AdobeService"),
        ("Workato", "jml_automation.services.workato", "WorkatoService"),
        ("Domo", "jml_automation.services.domo", "DomoService"),
        ("Lucid", "jml_automation.services.lucid", "LucidService"),
        ("SYNQ", "jml_automation.services.synqprox", "SynqProxService"),
    ]
    
    results = {}
    
    for app_name, module_name, class_name in apps_to_test:
        print(f"\n🧪 Testing {app_name} Service...")
        try:
            # Import the module dynamically
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)
            
            # Initialize with dry run
            if app_name in ["Adobe", "Workato"]:
                service = service_class(dry_run=True)
            else:
                service = service_class()
            
            # Test basic connectivity
            if hasattr(service, 'test_connectivity'):
                connectivity = service.test_connectivity()
                print(f"   ✅ Connectivity Test: {connectivity}")
                results[app_name] = {'connectivity': connectivity}
            elif hasattr(service, 'test_connection'):
                connectivity = service.test_connection()
                print(f"   ✅ Connection Test: {connectivity}")
                results[app_name] = {'connectivity': connectivity}
            else:
                print(f"   ⚠️  No connectivity test method found")
                results[app_name] = {'connectivity': 'No test method'}
            
        except Exception as e:
            print(f"   ❌ {app_name} Test Failed: {e}")
            results[app_name] = {'error': str(e)}
    
    print("\n📊 Individual App Test Summary:")
    for app_name, result in results.items():
        if 'error' in result:
            print(f"   ❌ {app_name}: {result['error']}")
        else:
            print(f"   ✅ {app_name}: {result.get('connectivity', 'Unknown')}")
    
    return results


def main():
    """Run all dry run tests."""
    print("🧪 COMPREHENSIVE WORKFLOW DRY RUN TEST")
    print("=" * 70)
    print("This test will:")
    print("1. Test the complete single ticket workflow in dry run mode")
    print("2. Test individual app services")
    print("3. Verify conditional logic for each app")
    print("4. Check for any configuration or connectivity issues")
    print("\n⚠️  NOTE: This is a DRY RUN - no actual changes will be made")
    
    # Test 1: Comprehensive workflow dry run
    workflow_success = test_comprehensive_dry_run()
    
    # Test 2: Individual app service tests
    app_results = test_individual_app_dry_runs()
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)
    
    if workflow_success:
        print("✅ Comprehensive workflow dry run: PASSED")
    else:
        print("❌ Comprehensive workflow dry run: FAILED")
    
    app_success_count = len([r for r in app_results.values() if 'error' not in r])
    app_total_count = len(app_results)
    
    print(f"📊 Individual app tests: {app_success_count}/{app_total_count} passed")
    
    overall_success = workflow_success and (app_success_count == app_total_count)
    
    print(f"\n🎯 OVERALL TEST RESULT: {'SUCCESS' if overall_success else 'FAILED'}")
    
    if overall_success:
        print("🎉 All systems tested successfully - workflow is ready!")
    else:
        print("⚠️  Some issues found - review the errors above")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)