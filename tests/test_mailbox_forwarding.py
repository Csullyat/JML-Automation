#!/usr/bin/env python3
"""
Test script to check the current forwarding status of John's mailbox
and optionally fix it with the corrected ForwardingSmtpAddress parameter.
"""

from src.jml_automation.services.microsoft import MicrosoftService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def check_mailbox_forwarding():
    """Check current forwarding status"""
    microsoft = MicrosoftService()
    
    print("=== Current Mailbox Status ===")
    
    # Let's create a simple PowerShell script to check the current status
    ps_script = '''
    try {
        Import-Module ExchangeOnlineManagement -Force -ErrorAction SilentlyContinue
        
        # Get certificate thumbprint
        $certPath = "Cert:\\CurrentUser\\My\\*"
        $cert = Get-ChildItem -Path $certPath | Where-Object { $_.Subject -like "*CN=filevine.onmicrosoft.com*" } | Select-Object -First 1
        
        if ($cert) {
            $thumbprint = $cert.Thumbprint
            Write-Host "Found certificate: $thumbprint"
            
            Connect-ExchangeOnline -AppId 'ce7f9f3f-7c64-4a1d-8891-cb04704a9c3a' -Organization 'filevine.onmicrosoft.com' -CertificateThumbprint $thumbprint -ShowBanner:$false
            
            Write-Host "=== Checking johnhamster@filevine.com mailbox ==="
            $mailbox = Get-Mailbox -Identity "johnhamster@filevine.com"
            
            Write-Host "Display Name: $($mailbox.DisplayName)"
            Write-Host "Email Address: $($mailbox.PrimarySmtpAddress)"
            Write-Host "Recipient Type: $($mailbox.RecipientTypeDetails)"
            Write-Host "ForwardingAddress (internal): $($mailbox.ForwardingAddress)"
            Write-Host "ForwardingSmtpAddress (external): $($mailbox.ForwardingSmtpAddress)"
            Write-Host "DeliverToMailboxAndForward: $($mailbox.DeliverToMailboxAndForward)"
            
            Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
        } else {
            Write-Host "ERROR: Certificate not found"
        }
    } catch {
        Write-Host "ERROR: $($_.Exception.Message)"
        Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    }
    '''
    
    import subprocess
    import tempfile
    import os
    
    script_fd, script_path = tempfile.mkstemp(suffix=".ps1", prefix="check_mailbox_")
    
    try:
        with os.fdopen(script_fd, 'w', encoding='utf-8') as f:
            f.write(ps_script)
        
        cmd = [
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("=== PowerShell Output ===")
        print(result.stdout)
        if result.stderr:
            print("=== PowerShell Errors ===")
            print(result.stderr)
            
    finally:
        try:
            os.remove(script_path)
        except (FileNotFoundError, PermissionError, OSError):
            pass
    
def fix_mailbox_forwarding():
    """Fix the forwarding using the corrected method"""
    print("\n=== Fixing Mailbox Forwarding ===")
    microsoft = MicrosoftService()
    
    result = microsoft.setup_email_forwarding(
        mailbox_email="johnhamster@filevine.com",
        forward_to_email="john@hamsterwheel.com"
    )
    
    print("Fix result:")
    print(f"Success: {result.get('success', False)}")
    if result.get('success'):
        print(f"Output: {result.get('output', '')}")
    else:
        print(f"Error: {result.get('error', '')}")

if __name__ == "__main__":
    print("1. Checking current mailbox status...")
    check_mailbox_forwarding()
    
    print("\n" + "="*50)
    response = input("Would you like to fix the forwarding? (y/n): ")
    if response.lower() == 'y':
        fix_mailbox_forwarding()
        print("\n2. Checking status after fix...")
        check_mailbox_forwarding()