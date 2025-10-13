#!/usr/bin/env python3
"""
Test script for multiple ticket termination workflow.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.workflows.termination import TerminationWorkflow


def main():
    """Test multiple ticket processing."""
    print("Multiple Ticket Termination Test")
    print("=" * 40)
    
    # Example usage
    example_tickets = "12345,12346,12347"
    print(f"Example: python test_multiple_tickets.py \"{example_tickets}\"")
    print()
    
    if len(sys.argv) < 2:
        print("Please provide comma-separated ticket numbers:")
        ticket_numbers = input("Enter tickets (e.g., 12345,12346,12347): ").strip()
    else:
        ticket_numbers = sys.argv[1]
    
    if not ticket_numbers:
        print("No ticket numbers provided")
        return
    
    print(f"Processing tickets: {ticket_numbers}")
    print("-" * 40)
    
    # Initialize workflow
    workflow = TerminationWorkflow()
    
    # Process multiple tickets
    results = workflow.execute_multiple_ticket_terminations(ticket_numbers)
    
    # Display results
    print("\\nRESULTS SUMMARY:")
    print("=" * 40)
    print(f"Total Tickets: {results['total_tickets']}")
    print(f"Successful: {results['successful_tickets']}")
    print(f"Failed: {results['failed_tickets']}")
    print(f"Success Rate: {results.get('success_rate', 0):.1f}%")
    print(f"Duration: {results.get('duration', 0):.1f} seconds")
    
    print("\\nINDIVIDUAL RESULTS:")
    print("-" * 40)
    for ticket_id, result in results['ticket_results'].items():
        status = "SUCCESS" if result.get('overall_success') else "FAILED"
        user = result.get('user_email', 'Unknown')
        error_count = len(result.get('errors', []))
        print(f"{status}: Ticket {ticket_id} - {user} ({error_count} errors)")
    
    print("\\nSUMMARY:")
    for summary_line in results.get('summary', []):
        print(f"  {summary_line}")
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()