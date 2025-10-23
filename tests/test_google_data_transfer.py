#!/usr/bin/env python3
"""
Test Google Workspace data transfer functionality before full terminations.

This test verifies:
1. Google Workspace API connectivity
2. User lookup functionality
3. Real data transfer initiation and monitoring
4. Transfer status checking
5. Error handling for various scenarios

Usage:
    python tests/test_google_data_transfer.py --test-user <email> --manager <email>
    python tests/test_google_data_transfer.py --connectivity-only
    python tests/test_google_data_transfer.py --dry-run <email> <manager>
"""

import sys
import os
import logging
import argparse
from datetime import datetime
from typing import Dict, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from jml_automation.services.google import GoogleTerminationManager
from jml_automation.logger import setup_logging

# Setup logging
logger = setup_logging("INFO")
logger = logging.getLogger("google_transfer_test")

class GoogleDataTransferTester:
    """Test class for Google Workspace data transfer functionality."""
    
    def __init__(self):
        """Initialize the tester with Google Workspace client."""
        try:
            self.google_manager = GoogleTerminationManager()
            logger.info("Google Workspace test client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace client: {e}")
            raise
    
    def test_connectivity(self) -> Dict:
        """Test basic Google Workspace API connectivity."""
        logger.info("=" * 60)
        logger.info("TESTING: Google Workspace API Connectivity")
        logger.info("=" * 60)
        
        try:
            result = self.google_manager.test_connectivity()
            
            if result['success']:
                logger.info("✅ Google Workspace API connectivity: PASS")
                logger.info(f"   Message: {result['message']}")
            else:
                logger.error("❌ Google Workspace API connectivity: FAIL")
                logger.error(f"   Error: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Connectivity test failed with exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_user_lookup(self, user_email: str) -> Optional[Dict]:
        """Test user lookup functionality."""
        logger.info("=" * 60)
        logger.info(f"TESTING: User Lookup - {user_email}")
        logger.info("=" * 60)
        
        try:
            user = self.google_manager.find_user_by_email(user_email)
            
            if user:
                user_name = user.get('name', {}).get('fullName', 'Unknown')
                user_id = user.get('id', 'Unknown')
                is_suspended = user.get('suspended', False)
                
                logger.info(f"✅ User lookup: PASS")
                logger.info(f"   Name: {user_name}")
                logger.info(f"   ID: {user_id}")
                logger.info(f"   Email: {user_email}")
                logger.info(f"   Suspended: {is_suspended}")
                
                return user
            else:
                logger.warning(f"⚠️  User not found: {user_email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ User lookup failed: {e}")
            return None
    
    def test_manager_lookup(self, manager_email: str) -> Optional[Dict]:
        """Test manager lookup functionality."""
        logger.info("=" * 60)
        logger.info(f"TESTING: Manager Lookup - {manager_email}")
        logger.info("=" * 60)
        
        try:
            manager = self.google_manager.find_manager_by_email(manager_email)
            
            if manager:
                manager_name = manager.get('name', {}).get('fullName', 'Unknown')
                manager_id = manager.get('id', 'Unknown')
                
                logger.info(f"✅ Manager lookup: PASS")
                logger.info(f"   Name: {manager_name}")
                logger.info(f"   ID: {manager_id}")
                logger.info(f"   Email: {manager_email}")
                
                return manager
            else:
                logger.warning(f"⚠️  Manager not found: {manager_email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Manager lookup failed: {e}")
            return None
    
    def test_dry_run_transfer(self, user_email: str, manager_email: str) -> Dict:
        """Perform a dry run test - validate parameters but don't initiate transfer."""
        logger.info("=" * 60)
        logger.info(f"TESTING: Dry Run Transfer - {user_email} -> {manager_email}")
        logger.info("=" * 60)
        
        result = {
            'success': False,
            'user_found': False,
            'manager_found': False,
            'ready_for_transfer': False,
            'errors': []
        }
        
        try:
            # Test user lookup
            user = self.test_user_lookup(user_email)
            if user:
                result['user_found'] = True
                result['user_id'] = user['id']
            else:
                result['errors'].append(f"Source user not found: {user_email}")
            
            # Test manager lookup
            manager = self.test_manager_lookup(manager_email)
            if manager:
                result['manager_found'] = True
                result['manager_id'] = manager['id']
            else:
                result['errors'].append(f"Manager not found: {manager_email}")
            
            # Check if ready for transfer
            if result['user_found'] and result['manager_found']:
                result['ready_for_transfer'] = True
                result['success'] = True
                
                logger.info("✅ Dry run transfer: PASS")
                logger.info("   Both users found, ready for data transfer")
                logger.info(f"   Transfer would be: {result['user_id']} -> {result['manager_id']}")
                
                # Show what applications would be transferred
                applications = [
                    {'id': 55656082996, 'name': 'Drive and Docs'},
                    {'id': 435070579839, 'name': 'Gmail'}
                ]
                logger.info("   Applications to transfer:")
                for app in applications:
                    logger.info(f"     - {app['name']} (ID: {app['id']})")
            else:
                result['success'] = False
                logger.error("❌ Dry run transfer: FAIL")
                for error in result['errors']:
                    logger.error(f"   Error: {error}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Dry run test failed: {e}")
            result['errors'].append(str(e))
            return result
    
    def test_real_transfer(self, user_email: str, manager_email: str, confirm: bool = False) -> Dict:
        """Test real data transfer (requires confirmation)."""
        logger.info("=" * 60)
        logger.info(f"TESTING: REAL Data Transfer - {user_email} -> {manager_email}")
        logger.info("=" * 60)
        
        if not confirm:
            logger.warning("⚠️  Real transfer test requires explicit confirmation")
            logger.warning("   Use --confirm flag to proceed with real transfer")
            return {'success': False, 'error': 'Confirmation required for real transfer'}
        
        # First do a dry run
        dry_run = self.test_dry_run_transfer(user_email, manager_email)
        if not dry_run['success']:
            logger.error("❌ Real transfer aborted - dry run failed")
            return {'success': False, 'error': 'Dry run validation failed', 'dry_run': dry_run}
        
        logger.warning("🚨 INITIATING REAL DATA TRANSFER")
        logger.warning(f"   Source: {user_email}")
        logger.warning(f"   Target: {manager_email}")
        logger.warning("   This will transfer actual Google Workspace data!")
        
        try:
            start_time = datetime.now()
            success = self.google_manager.transfer_user_data(user_email, manager_email)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'success': success,
                'duration_seconds': duration,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
            if success:
                logger.info(f"✅ Real data transfer: SUCCESS")
                logger.info(f"   Duration: {duration:.1f} seconds")
                logger.info(f"   Transfer completed: {user_email} -> {manager_email}")
            else:
                logger.error(f"❌ Real data transfer: FAILED")
                logger.error(f"   Duration: {duration:.1f} seconds")
                result['error'] = 'Transfer failed or could not be verified'
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Real transfer test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_comprehensive_test(self, user_email: Optional[str] = None, manager_email: Optional[str] = None, 
                             real_transfer: bool = False, confirm: bool = False) -> Dict:
        """Run comprehensive test suite."""
        logger.info("🚀 Starting Google Workspace Data Transfer Test Suite")
        logger.info(f"   Test time: {datetime.now().isoformat()}")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'connectivity': None,
            'dry_run': None,
            'real_transfer': None,
            'overall_success': False
        }
        
        # Test 1: Connectivity
        results['connectivity'] = self.test_connectivity()
        if not results['connectivity']['success']:
            logger.error("🚨 Aborting tests - connectivity failed")
            return results
        
        # Test 2: Dry run (if users provided)
        if user_email and manager_email:
            results['dry_run'] = self.test_dry_run_transfer(user_email, manager_email)
            
            # Test 3: Real transfer (if requested and confirmed)
            if real_transfer and results['dry_run']['success']:
                results['real_transfer'] = self.test_real_transfer(
                    user_email, manager_email, confirm=confirm
                )
        
        # Determine overall success
        connectivity_ok = results['connectivity']['success']
        dry_run_ok = results['dry_run']['success'] if results['dry_run'] else True
        real_transfer_ok = results['real_transfer']['success'] if results['real_transfer'] else True
        
        results['overall_success'] = connectivity_ok and dry_run_ok and real_transfer_ok
        results['end_time'] = datetime.now().isoformat()
        
        # Summary
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Connectivity: {'✅ PASS' if connectivity_ok else '❌ FAIL'}")
        if results['dry_run']:
            logger.info(f"Dry Run:      {'✅ PASS' if dry_run_ok else '❌ FAIL'}")
        if results['real_transfer']:
            logger.info(f"Real Transfer: {'✅ PASS' if real_transfer_ok else '❌ FAIL'}")
        logger.info(f"Overall:      {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        
        return results

def main():
    """Main test function with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Google Workspace data transfer functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connectivity only
  python test_google_data_transfer.py --connectivity-only
  
  # Test dry run with specific users
  python test_google_data_transfer.py --dry-run testtestington@filevine.com codyatkinson@filevine.com
  
  # Test real transfer (requires confirmation)
  python test_google_data_transfer.py --real-transfer testtestington@filevine.com codyatkinson@filevine.com --confirm
        """
    )
    
    parser.add_argument('--connectivity-only', action='store_true',
                       help='Test only API connectivity')
    parser.add_argument('--dry-run', nargs=2, metavar=('USER_EMAIL', 'MANAGER_EMAIL'),
                       help='Test dry run with specified user and manager emails')
    parser.add_argument('--real-transfer', nargs=2, metavar=('USER_EMAIL', 'MANAGER_EMAIL'),
                       help='Test real data transfer (requires --confirm)')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirm real data transfer (required for --real-transfer)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        tester = GoogleDataTransferTester()
        
        if args.connectivity_only:
            # Test connectivity only
            result = tester.test_connectivity()
            sys.exit(0 if result['success'] else 1)
            
        elif args.dry_run:
            # Test dry run
            user_email, manager_email = args.dry_run
            result = tester.run_comprehensive_test(user_email, manager_email, real_transfer=False)
            sys.exit(0 if result['overall_success'] else 1)
            
        elif args.real_transfer:
            # Test real transfer
            user_email, manager_email = args.real_transfer
            if not args.confirm:
                logger.error("❌ Real transfer requires --confirm flag for safety")
                sys.exit(1)
            
            result = tester.run_comprehensive_test(
                user_email, manager_email, real_transfer=True, confirm=True
            )
            sys.exit(0 if result['overall_success'] else 1)
            
        else:
            # Default: connectivity test only
            logger.info("No specific test specified, running connectivity test")
            logger.info("Use --help for more options")
            result = tester.test_connectivity()
            sys.exit(0 if result['success'] else 1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"🚨 Test failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()