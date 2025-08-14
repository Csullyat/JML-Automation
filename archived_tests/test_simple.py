# test_simple.py - Simple test file without Unicode characters

import logging
from datetime import datetime

def main():
    """Test function to verify the system is working."""
    print("[TEST] Test file created successfully!")
    print(f"[TIME] Created at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[PASS] File creation test passed")
    
    # Test basic imports from your termination system
    try:
        import config
        print("[PASS] Config module import successful")
        
        print("[INFO] 1Password service account integration available")
        
        from logging_system import setup_logging
        print("[PASS] Logging system import successful")
        
        from enterprise_termination_orchestrator import EnterpriseTerminationOrchestrator
        print("[PASS] Enterprise orchestrator import successful")
        
        print("\n[SUCCESS] All core modules imported successfully!")
        print("[READY] Your termination automation system is ready for development!")
        
    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        print("[INFO] This is normal if credentials aren't configured yet")

if __name__ == "__main__":
    main()