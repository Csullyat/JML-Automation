# PowerShell script to verify mailbox type
param(
    [Parameter(Mandatory=$true)]
    [string]$UserEmail
)

try {
    Write-Host "Importing Exchange Online Management module with full path..."
    $modulePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Modules\ExchangeOnlineManagement\3.8.0\ExchangeOnlineManagement.psd1"
    if (Test-Path $modulePath) {
        Import-Module $modulePath -Force
        Write-Host "Module imported successfully from: $modulePath"
    } else {
        Write-Host "Module not found at: $modulePath"
        exit 1
    }
    
    Write-Host "Connecting to Exchange Online (interactive authentication)..."
    Connect-ExchangeOnline -ShowBanner:$false
    
    Write-Host "Getting mailbox information for: $UserEmail"
    $mailbox = Get-Mailbox -Identity $UserEmail -ErrorAction Stop
    
    Write-Host "=== MAILBOX INFORMATION ==="
    Write-Host "Display Name: $($mailbox.DisplayName)"
    Write-Host "Email: $($mailbox.PrimarySmtpAddress)"
    Write-Host "Recipient Type: $($mailbox.RecipientType)"
    Write-Host "Recipient Type Details: $($mailbox.RecipientTypeDetails)"
    Write-Host "=========================="
    
    if ($mailbox.RecipientTypeDetails -eq "SharedMailbox") {
        Write-Host "RESULT: This IS a shared mailbox" -ForegroundColor Green
    } else {
        Write-Host "RESULT: This is NOT a shared mailbox (type: $($mailbox.RecipientTypeDetails))" -ForegroundColor Yellow
    }
    
    Disconnect-ExchangeOnline -Confirm:$false
    
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    try {
        Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    } catch {}
}
