#!/usr/bin/env python3
"""
Test script to verify ticket extraction for "Awaiting Input" termination tickets.
Tests the exact same process used by the production system but in a safe test environment.
"""

import logging
from datetime import datetime
from typing import List, Dict
from termination_extractor import fetch_tickets, filter_termination_users
from ticket_processor import extract_user_email_from_ticket, extract_manager_email_from_ticket

# Set up basic logging for the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)def test_ticket_extraction():
    """Test the complete ticket extraction process."""
    print("="* 80)
    print("TESTING TICKET EXTRACTION FOR TERMINATION REQUESTS")
    print("=" * 80)
    
    try:
        # Step 1: Fetch all tickets (should get ~6000 total)
        print("\nStep 1: Fetching all termination tickets from SolarWinds...")
        start_time = datetime.now()
        
        all_tickets = fetch_tickets()
        
        fetch_duration = (datetime.now() - start_time).total_seconds()
        print(f"[SUCCESS] Fetched {len(all_tickets)} total tickets in {fetch_duration:.2f} seconds")
        
        if len(all_tickets) == 0:
            print("[ERROR] No tickets found - check SolarWinds connection")
            return False
            
        # Step 2: Filter for "Awaiting Input" Employee Termination tickets
        print("\nStep 2: Filtering for 'Awaiting Input' Employee Termination tickets...")
        
        filtered_users = filter_termination_users(all_tickets)
        
        print(f"[SUCCESS] Found {len(filtered_users)} actionable termination tickets")
        
        if len(filtered_users) == 0:
            print("[WARNING] No 'Awaiting Input' termination tickets found")
            print("[INFO] Analyzing ticket states and catalog items...")
            analyze_ticket_states(all_tickets)
            return True
            
        # Step 3: Test email extraction on filtered tickets
        print("\nStep 3: Testing email extraction from filtered tickets...")
        print("-" * 60)
        
        extraction_results = []
        
        for i, ticket in enumerate(filtered_users):
            if i >= 10:  # Limit to first 10 for readability
                print(f"... and {len(filtered_users) - 10} more tickets")
                break
                
            ticket_number = ticket.get('ticket_number', 'Unknown')
            ticket_state = ticket.get('ticket_state', 'Unknown')
            
            print(f"\n🎫 TICKET #{ticket_number} (State: {ticket_state})")
            
            # Extract user email
            user_email = extract_user_email_from_ticket(ticket)
            if user_email:
                print(f"   👤 User Email: {user_email}")
            else:
                print(f"   ❌ User Email: NOT FOUND")
            
            # Extract manager email
            manager_email = extract_manager_email_from_ticket(ticket)
            if manager_email:
                print(f"   👔 Manager Email: {manager_email}")
            else:
                print(f"   ❌ Manager Email: NOT FOUND")
            
            # Show raw ticket data for debugging
            employee_to_terminate = ticket.get('employee_to_terminate', 'NOT FOUND')
            transfer_data = ticket.get('transfer_data', 'NOT FOUND')
            additional_info = ticket.get('additional_info', 'NOT FOUND')
            
            print(f"   📋 Raw Data:")
            print(f"      Employee to Terminate: {employee_to_terminate}")
            print(f"      Transfer Data: {transfer_data}")
            print(f"      Additional Info: {additional_info}")
            
            # Store results for summary
            extraction_results.append({
                'ticket_number': ticket_number,
                'user_email': user_email,
                'manager_email': manager_email,
                'has_user': bool(user_email),
                'has_manager': bool(manager_email)
            })
        
        # Step 4: Summary statistics
        print("\n📊 EXTRACTION SUMMARY")
        print("=" * 60)
        
        total_tested = len(extraction_results)
        users_found = sum(1 for r in extraction_results if r['has_user'])
        managers_found = sum(1 for r in extraction_results if r['has_manager'])
        
        user_success_rate = (users_found / total_tested * 100) if total_tested > 0 else 0
        manager_success_rate = (managers_found / total_tested * 100) if total_tested > 0 else 0
        
        print(f"📋 Total Tickets Analyzed: {total_tested}")
        print(f"👤 User Emails Found: {users_found}/{total_tested} ({user_success_rate:.1f}%)")
        print(f"👔 Manager Emails Found: {managers_found}/{total_tested} ({manager_success_rate:.1f}%)")
        
        # Show successful extractions
        successful_extractions = [r for r in extraction_results if r['has_user'] and r['has_manager']]
        if successful_extractions:
            print(f"\n✅ COMPLETE EXTRACTIONS (Both user and manager found):")
            for result in successful_extractions:
                print(f"   🎫 #{result['ticket_number']}: {result['user_email']} -> {result['manager_email']}")
        
        # Show partial extractions
        partial_extractions = [r for r in extraction_results if r['has_user'] and not r['has_manager']]
        if partial_extractions:
            print(f"\n⚠️  PARTIAL EXTRACTIONS (User found, manager missing):")
            for result in partial_extractions:
                print(f"   🎫 #{result['ticket_number']}: {result['user_email']} (no manager)")
        
        # Show failed extractions
        failed_extractions = [r for r in extraction_results if not r['has_user']]
        if failed_extractions:
            print(f"\n❌ FAILED EXTRACTIONS (No user email found):")
            for result in failed_extractions:
                print(f"   🎫 #{result['ticket_number']}: No user email found")
        
        print(f"\n🎯 TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        logger.exception("Test failed with exception")
        return False

def analyze_ticket_states(all_tickets: List[Dict]):
    """Analyze the states and catalog items of all tickets to understand the data."""
    print("\n🔍 ANALYZING TICKET STATES AND CATALOG ITEMS")
    print("-" * 60)
    
    states = {}
    catalog_items = {}
    subcategories = {}
    
    for ticket in all_tickets:
        # Count states
        state = ticket.get('state', 'Unknown')
        states[state] = states.get(state, 0) + 1
        
        # Count catalog items
        catalog = ticket.get('category', {})
        if isinstance(catalog, dict):
            catalog_name = catalog.get('name', 'Unknown')
        else:
            catalog_name = str(catalog) if catalog else 'Unknown'
        catalog_items[catalog_name] = catalog_items.get(catalog_name, 0) + 1
        
        # Count subcategories
        subcategory = ticket.get('subcategory', {})
        if isinstance(subcategory, dict):
            subcat_name = subcategory.get('name', 'Unknown')
        else:
            subcat_name = str(subcategory) if subcategory else 'Unknown'
        subcategories[subcat_name] = subcategories.get(subcat_name, 0) + 1
    
    print(f"📊 TICKET STATES (Top 10):")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {state}: {count}")
    
    print(f"\n📊 CATALOG ITEMS (Top 10):")
    for catalog, count in sorted(catalog_items.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {catalog}: {count}")
    
    print(f"\n📊 SUBCATEGORIES (Top 10):")
    for subcat, count in sorted(subcategories.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {subcat}: {count}")
    
    # Look specifically for "Awaiting Input" tickets
    awaiting_input_tickets = [t for t in all_tickets if t.get('state') == 'Awaiting Input']
    print(f"\n🔍 'AWAITING INPUT' TICKETS: {len(awaiting_input_tickets)}")
    
    if awaiting_input_tickets:
        # Analyze subcategories of Awaiting Input tickets
        awaiting_subcats = {}
        for ticket in awaiting_input_tickets:
            subcategory = ticket.get('subcategory', {})
            if isinstance(subcategory, dict):
                subcat_name = subcategory.get('name', 'Unknown')
            else:
                subcat_name = str(subcategory) if subcategory else 'Unknown'
            awaiting_subcats[subcat_name] = awaiting_subcats.get(subcat_name, 0) + 1
        
        print("   Subcategories of 'Awaiting Input' tickets:")
        for subcat, count in sorted(awaiting_subcats.items(), key=lambda x: x[1], reverse=True):
            print(f"      {subcat}: {count}")

def main():
    """Main test function."""
    print("🧪 TERMINATION TICKET EXTRACTION TEST")
    print("This test will:")
    print("1. Fetch ~6000 termination tickets from SolarWinds")
    print("2. Filter for 'Awaiting Input' Employee Termination tickets")
    print("3. Test email extraction (user and manager)")
    print("4. Show detailed results and statistics")
    print()
    
    success = test_ticket_extraction()
    
    if success:
        print("\n🎉 Test completed successfully!")
        exit(0)
    else:
        print("\n❌ Test failed - check logs for details")
        exit(1)

if __name__ == "__main__":
    main()