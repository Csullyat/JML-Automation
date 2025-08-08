# Manual Exchange Online Mailbox Conversion Script
# Updated to use certificate-based authentication for unattended operation

param(
    [Parameter(Mandatory=$false)]
    [string]$UserEmail = "valeriebaird@filevine.com"
)

Write-Host "=== Manual Mailbox Conversion to Shared ===" -ForegroundColor Green
Write-Host "Target User: $UserEmail"
Write-Host ""

# Certificate and app details for automated authentication
$appId = "cdff53b5-c950-40cb-b9d2-fa6433dd942d"
$tenantId = "filevine.com"
$certThumbprint = "DF8B5FA21923E56ABA0FC540CBC2056977999CF9"

try {
    Write-Host "1. Importing Exchange Online Management module..." -ForegroundColor Yellow
    $modulePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Modules\ExchangeOnlineManagement\3.8.0\ExchangeOnlineManagement.psd1"
    if (Test-Path $modulePath) {
        Import-Module $modulePath -Force
        Write-Host "   ✅ Module loaded from: $modulePath" -ForegroundColor Green
    } else {
        Import-Module ExchangeOnlineManagement -Force
        Write-Host "   ✅ Module loaded from default location" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "2. Connecting to Exchange Online with certificate authentication..." -ForegroundColor Yellow
    Connect-ExchangeOnline -AppId $appId -Organization $tenantId -CertificateThumbprint $certThumbprint -ShowBanner:$false
    Write-Host "   ✅ Connected successfully" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "3. Getting current mailbox information..." -ForegroundColor Yellow
    $currentMailbox = Get-Mailbox -Identity $UserEmail -ErrorAction Stop
    Write-Host "   Current mailbox type: $($currentMailbox.RecipientTypeDetails)" -ForegroundColor Cyan
    Write-Host "   Display Name: $($currentMailbox.DisplayName)" -ForegroundColor Cyan
    
    if ($currentMailbox.RecipientTypeDetails -eq "SharedMailbox") {
        Write-Host "   ✅ Mailbox is already a SharedMailbox" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "4. Converting mailbox to shared type..." -ForegroundColor Yellow
        Set-Mailbox -Identity $UserEmail -Type Shared -Confirm:$false -ErrorAction Stop
        Write-Host "   ✅ Conversion command completed" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "5. Waiting for changes to propagate..." -ForegroundColor Yellow
        Start-Sleep -Seconds 15
        
        Write-Host ""
        Write-Host "6. Verifying conversion..." -ForegroundColor Yellow
        $mailbox = Get-Mailbox -Identity $UserEmail -ErrorAction Stop
        Write-Host "   New mailbox type: $($mailbox.RecipientTypeDetails)" -ForegroundColor Cyan
        
        if ($mailbox.RecipientTypeDetails -eq "SharedMailbox") {
            Write-Host "   ✅ SUCCESS: Mailbox successfully converted to SharedMailbox" -ForegroundColor Green
        } else {
            Write-Host "   ❌ WARNING: Mailbox type is $($mailbox.RecipientTypeDetails), expected SharedMailbox" -ForegroundColor Red
            Write-Host "   This may take additional time to propagate. Check again in a few minutes." -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "7. Disconnecting from Exchange Online..." -ForegroundColor Yellow
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "   ✅ Disconnected" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "=== CONVERSION COMPLETED SUCCESSFULLY ===" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Full error details: $_" -ForegroundColor Red
    
    Write-Host ""
    Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "1. Verify the user email is correct: $UserEmail"
    Write-Host "2. Ensure you have Exchange admin permissions"
    Write-Host "3. Check that certificate authentication is properly configured"
    Write-Host "4. Run setup_certificate_auth.ps1 to validate your configuration"
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}

# Usage examples:
Write-Host ""
Write-Host "=== USAGE EXAMPLES ===" -ForegroundColor Cyan
Write-Host "To convert a specific user:"
Write-Host "   .\manual_convert.ps1 -UserEmail 'user@filevine.com'"
Write-Host ""
Write-Host "To convert the test user:"
Write-Host "   .\manual_convert.ps1 -UserEmail 'valeriebaird@filevine.com'"
