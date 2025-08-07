#!/usr/bin/env python3
"""
Performance Testing Script for Enterprise Termination Automation
Tests various optimization scenarios and measures performance improvements
"""

import time
import logging
from datetime import datetime
from enterprise_termination_orchestrator import EnterpriseTerminationOrchestrator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def time_function(func, *args, **kwargs):
    """Time a function execution and return duration and result."""
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        return duration, result, None
    except Exception as e:
        duration = time.time() - start_time
        return duration, None, str(e)

def test_ticket_processing_performance():
    """Test ticket processing performance."""
    logger.info("=" * 60)
    logger.info("PERFORMANCE TEST: Ticket Processing")
    logger.info("=" * 60)
    
    try:
        # Initialize orchestrator
        orchestrator = EnterpriseTerminationOrchestrator()
        
        # Test sequential processing (current method)
        logger.info("Testing sequential processing...")
        start_time = time.time()
        
        # Get tickets
        tickets = orchestrator.process_termination_tickets()
        ticket_fetch_time = time.time() - start_time
        
        logger.info(f"Ticket fetch time: {ticket_fetch_time:.2f} seconds")
        logger.info(f"Found {len(tickets)} tickets to process")
        
        if tickets:
            # Time a single termination
            first_ticket = tickets[0]
            user_email = first_ticket.get('employee_email')
            manager_email = first_ticket.get('manager_email')
            ticket_id = first_ticket.get('ticket_number')
            
            if user_email:
                logger.info(f"Testing single termination: {user_email}")
                duration, result, error = time_function(
                    orchestrator.execute_user_termination,
                    user_email, manager_email, ticket_id
                )
                
                if error:
                    logger.error(f"Termination failed: {error}")
                else:
                    logger.info(f"Single termination time: {duration:.2f} seconds")
                    logger.info(f"Success: {result.get('overall_success', False)}")
                    
                    # Estimate total time for all tickets
                    total_estimate = duration * len(tickets)
                    parallel_estimate = duration * (len(tickets) / 2)  # Assuming 2 workers
                    
                    logger.info(f"Estimated sequential time for {len(tickets)} tickets: {total_estimate:.2f} seconds")
                    logger.info(f"Estimated parallel time (2 workers): {parallel_estimate:.2f} seconds")
                    logger.info(f"Potential time savings: {total_estimate - parallel_estimate:.2f} seconds")
            
    except Exception as e:
        logger.error(f"Performance test failed: {e}")

def test_api_performance():
    """Test individual API performance."""
    logger.info("=" * 60)
    logger.info("PERFORMANCE TEST: Individual API Components")
    logger.info("=" * 60)
    
    try:
        from okta_termination import OktaTermination
        from microsoft_termination import MicrosoftTermination
        from google_termination import GoogleTerminationManager
        
        # Test Okta performance
        logger.info("Testing Okta API performance...")
        okta = OktaTermination()
        duration, result, error = time_function(okta.find_user_by_email, "test@filevine.com")
        logger.info(f"Okta user lookup: {duration:.3f} seconds")
        
        # Test Microsoft Graph performance
        logger.info("Testing Microsoft Graph API performance...")
        ms = MicrosoftTermination()
        duration, result, error = time_function(ms._get_access_token)
        logger.info(f"Microsoft Graph token: {duration:.3f} seconds")
        
        # Test token caching
        duration, result, error = time_function(ms._get_access_token)
        logger.info(f"Microsoft Graph cached token: {duration:.3f} seconds (should be much faster)")
        
        # Test Google API performance
        logger.info("Testing Google Workspace API performance...")
        google = GoogleTerminationManager()
        duration, result, error = time_function(google.find_user_by_email, "test@filevine.com")
        logger.info(f"Google user lookup: {duration:.3f} seconds")
        
    except Exception as e:
        logger.error(f"API performance test failed: {e}")

def display_optimization_summary():
    """Display summary of implemented optimizations."""
    logger.info("=" * 60)
    logger.info("OPTIMIZATION SUMMARY")
    logger.info("=" * 60)
    
    optimizations = [
        "✅ Google Data Transfer: Adaptive polling (5s → 10s → 15s)",
        "✅ Microsoft Graph: Token caching (1 hour lifetime)",
        "✅ Parallel Processing: 2 concurrent users (ThreadPoolExecutor)",
        "✅ Exchange PowerShell: Session reuse tracking",
        "✅ Error Handling: Graceful degradation and fallbacks"
    ]
    
    for opt in optimizations:
        logger.info(opt)
    
    logger.info("")
    logger.info("Expected Performance Improvements:")
    logger.info("• Data Transfer Monitoring: 50-70% faster")
    logger.info("• API Authentication: 90% faster (cached)")
    logger.info("• Multiple Users: 40-50% faster (parallel)")
    logger.info("• Overall Per-User: 30-50% improvement")
    
    logger.info("")
    logger.info("Bottlenecks Remaining:")
    logger.info("• PowerShell Exchange Operations: ~25-30 seconds")
    logger.info("• Google Data Transfer: Depends on data size")
    logger.info("• API Rate Limits: Google/Microsoft throttling")

def main():
    """Run performance tests."""
    logger.info("🚀 Enterprise Termination Performance Testing")
    logger.info(f"Test started at: {datetime.now()}")
    
    # Display optimization summary
    display_optimization_summary()
    
    # Test API performance
    test_api_performance()
    
    # Test ticket processing performance
    test_ticket_processing_performance()
    
    logger.info("🏁 Performance testing completed")

if __name__ == "__main__":
    main()
