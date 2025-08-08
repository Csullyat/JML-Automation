# Setup Certificate-Based Authentication for Exchange Online
# This script helps configure and validate certificate authentication

Write-Host "=== Exchange Online Certificate Authentication Setup ===" -ForegroundColor Green
Write-Host ""

# Certificate details
$certThumbprint = "DF8B5FA21923E56ABA0FC540CBC2056977999CF9"
$appId = "cdff53b5-c950-40cb-b9d2-fa6433dd942d"
$tenantId = "filevine.com"  # Replace with your actual tenant ID if different

Write-Host "1. Checking certificate exists in local store..." -ForegroundColor Yellow
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My" | Where-Object { $_.Thumbprint -eq $certThumbprint }
if ($cert) {
    Write-Host "✅ Certificate found:" -ForegroundColor Green
    Write-Host "   Subject: $($cert.Subject)"
    Write-Host "   Thumbprint: $($cert.Thumbprint)"
    Write-Host "   Expires: $($cert.NotAfter)"
} else {
    Write-Host "❌ Certificate not found in local store!" -ForegroundColor Red
    Write-Host "Please run the certificate creation script first."
    exit 1
}

Write-Host ""
Write-Host "2. Checking if certificate file exists for Azure upload..." -ForegroundColor Yellow
$certFile = ".\ExchangeOnline-Cert.cer"
if (Test-Path $certFile) {
    Write-Host "✅ Certificate file ready for upload: $certFile" -ForegroundColor Green
} else {
    Write-Host "❌ Certificate file not found: $certFile" -ForegroundColor Red
    Write-Host "Creating certificate file now..."
    Export-Certificate -Cert $cert -FilePath $certFile -Type CERT
    Write-Host "✅ Certificate file created: $certFile" -ForegroundColor Green
}

Write-Host ""
Write-Host "3. Azure AD Configuration Steps:" -ForegroundColor Yellow
Write-Host "   a. Go to Azure Portal > Azure Active Directory > App registrations"
Write-Host "   b. Find your app: 'M365 Termination Automation' (ID: $appId)"
Write-Host "   c. Click 'Certificates & secrets' in the left menu"
Write-Host "   d. Click 'Upload certificate' button"
Write-Host "   e. Select file: $certFile"
Write-Host "   f. Verify thumbprint matches: $certThumbprint"
Write-Host "   g. Click 'Add'"

Write-Host ""
Write-Host "4. Required API Permissions (verify these are granted):" -ForegroundColor Yellow
Write-Host "   - Microsoft Graph:"
Write-Host "     * User.ReadWrite.All"
Write-Host "     * Directory.Read.All" 
Write-Host "     * Sites.ReadWrite.All"
Write-Host "   - Exchange Online:"
Write-Host "     * Exchange.ManageAsApp"

Write-Host ""
Write-Host "5. Testing certificate authentication..." -ForegroundColor Yellow
try {
    Write-Host "   Importing Exchange Online module..."
    $modulePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Modules\ExchangeOnlineManagement\3.8.0\ExchangeOnlineManagement.psd1"
    if (Test-Path $modulePath) {
        Import-Module $modulePath -Force
    } else {
        Import-Module ExchangeOnlineManagement -Force
    }
    
    Write-Host "   Attempting certificate-based connection..."
    Connect-ExchangeOnline -AppId $appId -Organization $tenantId -CertificateThumbprint $certThumbprint -ShowBanner:$false
    
    Write-Host "   ✅ Successfully connected to Exchange Online!" -ForegroundColor Green
    Write-Host "   Testing basic command..."
    
    $orgConfig = Get-OrganizationConfig | Select-Object DisplayName, ExchangeVersion
    Write-Host "   Organization: $($orgConfig.DisplayName)"
    Write-Host "   Exchange Version: $($orgConfig.ExchangeVersion)"
    
    Disconnect-ExchangeOnline -Confirm:$false
    Write-Host "   ✅ Certificate authentication is working!" -ForegroundColor Green
    
} catch {
    Write-Host "   ❌ Certificate authentication failed:" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "   1. Ensure certificate is uploaded to Azure AD app"
    Write-Host "   2. Wait 5-10 minutes for Azure changes to propagate"
    Write-Host "   3. Verify Exchange.ManageAsApp permission is granted and admin consented"
    Write-Host "   4. Check tenant ID is correct: $tenantId"
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "If the test above passed, your certificate authentication is ready!"
Write-Host "The automation scripts will now use certificate-based authentication for unattended operation."
