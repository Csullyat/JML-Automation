# Test Exchange Online connection with certificate authentication
param(
    [Parameter(Mandatory=$true)]
    [string]$CertThumbprint,
    
    [Parameter(Mandatory=$true)]
    [string]$AppId
)

$ErrorActionPreference = 'Stop'

try {
    Write-Host "Starting Exchange Online connection test..."
    
    # Import module with explicit path
    Write-Host "Importing ExchangeOnlineManagement module..."
    Import-Module ExchangeOnlineManagement -Force -Verbose
    
    Write-Host "Module imported successfully. Attempting connection..."
    
    # Connect using certificate authentication
    Connect-ExchangeOnline `
        -CertificateThumbprint $CertThumbprint `
        -AppId $AppId `
        -Organization 'filevineco.onmicrosoft.com' `
        -ShowBanner:$false `
        -Verbose
    
    Write-Host "Connection successful! Testing basic command..."
    
    # Test a basic command
    $mailboxes = Get-Mailbox -ResultSize 1
    Write-Host "Test command successful. Found mailbox: $($mailboxes[0].PrimarySmtpAddress)"
    
    Write-Host "SUCCESS: Certificate authentication is working"
    
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    Write-Host "Full error details:"
    Write-Host $_.Exception.ToString()
} finally {
    try { 
        Disconnect-ExchangeOnline -Confirm:$false 
        Write-Host "Disconnected from Exchange Online"
    } catch {
        Write-Host "Could not disconnect: $($_.Exception.Message)"
    }
}