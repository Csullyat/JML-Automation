# test_single_ticket_workflow.py - Test the new integrated single ticket workflow

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.workflows.single_ticket import SingleTicketWorkflow

def test_dry_run():
    """Test the dry run functionality."""
    ticket_id = "64570"  # Marisa's ticket
    
    print(f"TESTING SINGLE TICKET DRY RUN WORKFLOW")
    print("=" * 50)
    
    workflow = SingleTicketWorkflow()
    results = workflow.execute_single_ticket_dry_run(ticket_id)
    
    # Print results
    workflow.print_dry_run_summary(results)
    
    return results['overall_success']

def test_production():
    """Test the production functionality (WARNING: This will do actual termination!)."""
    ticket_id = "64570"  # Marisa's ticket
    
    print(f"TESTING SINGLE TICKET PRODUCTION WORKFLOW")
    print("=" * 50)
    print("WARNING: THIS WILL PERFORM ACTUAL TERMINATION!")
    print("Only run this if you're sure you want to terminate the user!")
    
    confirm = input("Type 'YES' to continue with actual termination: ")
    if confirm != 'YES':
        print("Production test cancelled.")
        return False
    
    workflow = SingleTicketWorkflow()
    results = workflow.execute_single_ticket_production(ticket_id)
    
    # Print results
    workflow.print_production_summary(results)
    
    return results['overall_success']

if __name__ == "__main__":
    print("Single Ticket Workflow Test")
    print("=" * 30)
    print("1. Test Dry Run (safe)")
    print("2. Test Production (WARNING: ACTUAL TERMINATION)")
    print("3. Exit")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        success = test_dry_run()
        print(f"\nDry run test: {'PASSED' if success else 'FAILED'}")
    elif choice == "2":
        success = test_production()
        print(f"\nProduction test: {'PASSED' if success else 'FAILED'}")
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid choice!")