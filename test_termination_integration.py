# test_termination_integration.py - TEST MODE integration of termination parsing with Okta automation
# WARNING: THIS IS TEST MODE ONLY - NO ACTUAL OKTA CHANGES WILL BE MADE

import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from termination_extractor import fetch_tickets, filter_termination_users, parse_termination_ticket
from okta_termination import find_okta_user, get_user_groups, validate_okta_connection
from config import get_okta_token
from logging_system import setup_logging

class TerminationIntegrationTest:
    """Test integration between SolarWinds termination tickets and Okta automation."""
    
    def __init__(self, test_mode: bool = True):
        setup_logging()  # Initialize logging
        self.logger = logging.getLogger("termination_integration_test")
        self.test_mode = test_mode  # ALWAYS True for this test
        self.okta_token = get_okta_token() if not test_mode else None
        self.test_results = {
            "total_terminations": 0,
            "processed": 0,
            "errors": 0,
            "test_actions": []
        }
        
        if not self.test_mode:
            raise ValueError("*** SAFETY CHECK: This test must run in test_mode=True ***")
    
    def find_user_by_employee_id(self, employee_id: str) -> Optional[Dict]:
        """Find Okta user by employee ID (test mode safe)."""
        try:
            if not self.okta_token:
                print(f"    TEST MODE: Would search for employee ID {employee_id}")
                return None
            
            # This is safe - it only reads data, doesn't modify anything
            okta_domain = "https://filevine.okta.com"  # Safe to hardcode for test
            headers = {
                'Authorization': f'SSWS {self.okta_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Search by employee ID in Okta profile
            search_url = f"{okta_domain}/api/v1/users?search=profile.employeeNumber eq \"{employee_id}\""
            
            print(f"    TEST MODE: Searching Okta for employee ID {employee_id}")
            
            response = requests.get(search_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    return users[0]  # Return first match
            
            return None
            
        except Exception as e:
            print(f"    ERROR searching for employee ID {employee_id}: {e}")
            return None
    
    def fetch_termination_data(self) -> List[Dict]:
        """Fetch and parse termination tickets."""
        self.logger.info("=== STARTING TERMINATION DATA FETCH (TEST MODE) ===")
        
        # Fetch tickets (6000 tickets for comprehensive testing)
        print("Fetching termination tickets for testing (6000 tickets)...")
        tickets = fetch_tickets(per_page=100, max_pages=60, workers=15)  # 6000 tickets
        
        # Filter to active terminations with employee data
        termination_users = filter_termination_users(tickets)
        
        self.test_results["total_terminations"] = len(termination_users)
        
        print(f"TEST MODE: Found {len(termination_users)} active terminations to process")
        return termination_users
    
    def test_okta_integration(self, termination_users: List[Dict]) -> None:
        """Test the Okta integration without making actual changes."""
        print("\n=== TESTING OKTA INTEGRATION ===")
        print("*** TEST MODE: NO ACTUAL OKTA CHANGES WILL BE MADE ***\n")
        
        # Sort by priority (urgent terminations first)
        priority_users = self.prioritize_terminations(termination_users)
        
        # Test first 10 users (increased from 5)
        test_sample = priority_users[:10]
        print(f"Testing sample of {len(test_sample)} highest priority terminations:")
        
        for i, user_data in enumerate(test_sample, 1):
            print(f"TEST {i}/{len(test_sample)}: Processing termination for {user_data.get('employee_name')}")
            print(f"Employee ID: {user_data.get('employee_to_terminate')}")  # Fixed field name
            print(f"Department: {user_data.get('employee_department')}")    # Fixed field name
            print(f"Termination Date: {user_data.get('termination_date')}")
            print(f"Remove Access Date: {user_data.get('date_to_remove_access')}")  # Fixed field name
            print(f"Term Type: {user_data.get('term_type')}")
            print(f"Priority Level: {user_data.get('priority_level', 'Normal')}")
            
            try:
                # TEST: Lookup user by employee ID
                employee_id = user_data.get('employee_to_terminate')  # Fixed field name
                if not employee_id:
                    print(f"  ERROR: No employee ID found")
                    self.test_results["errors"] += 1
                    continue
                
                # TEST: Find Okta user (this won't make changes, just lookup)
                print(f"  TEST: Looking up Okta user with employee ID {employee_id}")
                okta_user = self.find_user_by_employee_id(employee_id)
                
                if okta_user:
                    print(f"  ✓ FOUND: Okta user {okta_user.get('profile', {}).get('login')}")
                    print(f"    User ID: {okta_user.get('id')}")
                    print(f"    Status: {okta_user.get('status')}")
                    print(f"    Last Login: {okta_user.get('lastLogin', 'Never')}")
                    
                    # TEST: What would we do?
                    test_actions = []
                    
                    if okta_user.get('status') == 'ACTIVE':
                        test_actions.append("DEACTIVATE user")
                    elif okta_user.get('status') in ['DEPROVISIONED', 'SUSPENDED']:
                        test_actions.append(f"User already inactive ({okta_user.get('status')})")
                    
                    # Get user's groups (for removal) - safe read-only operation
                    if self.okta_token:
                        try:
                            groups = get_user_groups(okta_user['id'], self.okta_token)
                            if groups:
                                non_system_groups = [g for g in groups if not self.is_system_group(g)]
                                if non_system_groups:
                                    test_actions.append(f"REMOVE from {len(non_system_groups)} groups")
                                    for group in non_system_groups[:3]:  # Show first 3 groups
                                        print(f"    Group: {group.get('profile', {}).get('name')}")
                                    if len(non_system_groups) > 3:
                                        print(f"    ... and {len(non_system_groups) - 3} more groups")
                                else:
                                    test_actions.append("No non-system groups to remove")
                        except Exception as e:
                            print(f"    Warning: Could not fetch groups: {e}")
                    
                    # Clear user sessions
                    test_actions.append("CLEAR all user sessions")
                    
                    # Additional actions based on termination type
                    if user_data.get('term_type') == 'Involuntary':
                        test_actions.append("IMMEDIATE termination (involuntary)")
                    
                    print(f"  TEST ACTIONS WOULD BE: {', '.join(test_actions)}")
                    
                    self.test_results["test_actions"].append({
                        "employee_name": user_data.get('employee_name'),
                        "employee_id": employee_id,
                        "okta_login": okta_user.get('profile', {}).get('login'),
                        "current_status": okta_user.get('status'),
                        "planned_actions": test_actions,
                        "ticket_number": user_data.get('ticket_number'),
                        "priority_level": user_data.get('priority_level', 'Normal'),
                        "term_type": user_data.get('term_type'),
                        "department": user_data.get('employee_department'),  # Fixed field name
                        "termination_date": user_data.get('termination_date'),
                        "remove_access_date": user_data.get('date_to_remove_access')  # Fixed field name
                    })
                    
                    self.test_results["processed"] += 1
                    
                else:
                    print(f"  WARNING: No Okta user found with employee ID {employee_id}")
                    print(f"    This user may need manual investigation")
                    self.test_results["errors"] += 1
                
            except Exception as e:
                print(f"  ERROR processing {user_data.get('employee_name')}: {e}")
                self.test_results["errors"] += 1
            
            print("-" * 60)
    
    def prioritize_terminations(self, termination_users: List[Dict]) -> List[Dict]:
        """Prioritize terminations by urgency and type."""
        print("\n=== PRIORITIZING TERMINATIONS ===")
        
        for user in termination_users:
            priority_score = 0
            priority_reasons = []
            
            # High priority: Involuntary terminations
            if user.get('term_type') == 'Involuntary':
                priority_score += 100
                priority_reasons.append("Involuntary termination")
            
            # High priority: Past due access removal
            remove_date = user.get('date_to_remove_access', '')  # Fixed field name
            if remove_date and ('Jul 31' in remove_date or 'Jul 30' in remove_date):
                priority_score += 50
                priority_reasons.append("Past due access removal")
            
            # Medium priority: Today's terminations
            term_date = user.get('termination_date', '')
            if term_date and 'Aug 01' in term_date:
                priority_score += 25
                priority_reasons.append("Today's termination")
            
            # Medium priority: Security-sensitive departments
            dept = user.get('employee_department', '').lower()  # Fixed field name
            if any(sensitive in dept for sensitive in ['it', 'security', 'admin', 'legal', 'research']):
                priority_score += 20
                priority_reasons.append("Security-sensitive department")
            
            # Set priority level
            if priority_score >= 100:
                user['priority_level'] = 'URGENT'
            elif priority_score >= 50:
                user['priority_level'] = 'HIGH'
            elif priority_score >= 25:
                user['priority_level'] = 'MEDIUM'
            else:
                user['priority_level'] = 'NORMAL'
            
            user['priority_score'] = priority_score
            user['priority_reasons'] = priority_reasons
        
        # Sort by priority score (highest first)
        sorted_users = sorted(termination_users, key=lambda x: x.get('priority_score', 0), reverse=True)
        
        # Show priority summary
        priority_counts = {}
        for user in sorted_users:
            level = user.get('priority_level', 'NORMAL')
            priority_counts[level] = priority_counts.get(level, 0) + 1
        
        print("Priority Distribution:")
        for level in ['URGENT', 'HIGH', 'MEDIUM', 'NORMAL']:
            count = priority_counts.get(level, 0)
            if count > 0:
                print(f"  {level}: {count} terminations")
        
        return sorted_users
    
    def is_system_group(self, group: Dict) -> bool:
        """Check if a group is a system group that shouldn't be removed."""
        group_name = group.get('profile', {}).get('name', '').upper()
        system_indicators = ['EVERYONE', 'OKTA', 'SYSTEM', 'DEFAULT']
        return any(indicator in group_name for indicator in system_indicators)
    
    def generate_test_report(self) -> None:
        """Generate a test report showing what would happen."""
        print("\n" + "=" * 80)
        print("TERMINATION INTEGRATION TEST REPORT")
        print("=" * 80)
        print(f"Total terminations found: {self.test_results['total_terminations']}")
        print(f"Successfully processed (test): {self.test_results['processed']}")
        print(f"Errors encountered: {self.test_results['errors']}")
        print(f"Test sample size: {len(self.test_results['test_actions'])}")
        
        # Priority breakdown
        if self.test_results['test_actions']:
            priority_breakdown = {}
            term_type_breakdown = {}
            status_breakdown = {}
            
            for action in self.test_results['test_actions']:
                # Priority analysis
                priority = action.get('priority_level', 'NORMAL')
                priority_breakdown[priority] = priority_breakdown.get(priority, 0) + 1
                
                # Term type analysis
                term_type = action.get('term_type', 'Unknown')
                term_type_breakdown[term_type] = term_type_breakdown.get(term_type, 0) + 1
                
                # Status analysis
                status = action.get('current_status', 'Unknown')
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
            print(f"\nPRIORITY BREAKDOWN:")
            for priority in ['URGENT', 'HIGH', 'MEDIUM', 'NORMAL']:
                count = priority_breakdown.get(priority, 0)
                if count > 0:
                    print(f"  {priority}: {count} terminations")
            
            print(f"\nTERMINATION TYPE BREAKDOWN:")
            for term_type, count in term_type_breakdown.items():
                print(f"  {term_type}: {count} terminations")
            
            print(f"\nOKTA STATUS BREAKDOWN:")
            for status, count in status_breakdown.items():
                print(f"  {status}: {count} users")
            
            print(f"\nSAMPLE TERMINATION ACTIONS (TEST MODE):")
            
            # Show urgent cases first
            urgent_actions = [a for a in self.test_results['test_actions'] if a.get('priority_level') == 'URGENT']
            if urgent_actions:
                print(f"\n🚨 URGENT TERMINATIONS ({len(urgent_actions)}):")
                for action in urgent_actions:
                    print(f"  Employee: {action['employee_name']} (ID: {action['employee_id']})")
                    print(f"  Ticket: #{action['ticket_number']} | Type: {action.get('term_type', 'Unknown')}")
                    print(f"  Okta: {action['okta_login']} | Status: {action['current_status']}")
                    print(f"  Actions: {', '.join(action['planned_actions'])}")
                    print()
            
            # Show high priority cases
            high_actions = [a for a in self.test_results['test_actions'] if a.get('priority_level') == 'HIGH']
            if high_actions:
                print(f"\n⚠️ HIGH PRIORITY TERMINATIONS ({len(high_actions)}):")
                for action in high_actions[:3]:  # Show first 3
                    print(f"  Employee: {action['employee_name']} (ID: {action['employee_id']})")
                    print(f"  Ticket: #{action['ticket_number']} | Type: {action.get('term_type', 'Unknown')}")
                    print(f"  Okta: {action['okta_login']} | Status: {action['current_status']}")
                    print()
                if len(high_actions) > 3:
                    print(f"  ... and {len(high_actions) - 3} more high priority cases")
            
            # Show normal cases summary
            normal_actions = [a for a in self.test_results['test_actions'] 
                            if a.get('priority_level') in ['MEDIUM', 'NORMAL']]
            if normal_actions:
                print(f"\n📋 NORMAL PRIORITY TERMINATIONS: {len(normal_actions)} cases")
        
        # Calculate success rate
        if self.test_results['total_terminations'] > 0:
            success_rate = (self.test_results['processed'] / min(self.test_results['total_terminations'], 10)) * 100
            print(f"\nTEST SUCCESS RATE: {success_rate:.1f}% of sample processed successfully")
        
        print(f"\n*** THIS WAS TEST MODE - NO ACTUAL CHANGES WERE MADE ***")
        print(f"*** WHEN READY, THE SYSTEM CAN PROCESS ALL {self.test_results['total_terminations']} TERMINATIONS ***")
        print(f"*** RECOMMEND PROCESSING URGENT/HIGH PRIORITY CASES FIRST ***")
    
    def run_integration_test(self) -> None:
        """Run the complete integration test."""
        try:
            # Step 1: Fetch termination data
            termination_users = self.fetch_termination_data()
            
            if not termination_users:
                print("No termination data found. Test complete.")
                return
            
            # Step 2: Test Okta integration
            self.test_okta_integration(termination_users)
            
            # Step 3: Generate test report
            self.generate_test_report()
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            self.logger.error(f"Integration test failed: {e}")

if __name__ == "__main__":
    print("TERMINATION INTEGRATION TEST")
    print("=" * 50)
    print("*** TEST MODE: NO ACTUAL OKTA CHANGES WILL BE MADE ***")
    print("This will test the integration between SolarWinds and Okta")
    print("=" * 50)
    
    # Run the test
    test_integration = TerminationIntegrationTest()
    test_integration.run_integration_test()
