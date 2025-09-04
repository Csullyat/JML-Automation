# Setup Certificate-Based Authentication for Exchange Online
# This script helps configure and validate certificate authentication
# All sensitive values are retrieved from 1Password - safe for public repos

param(
    [Parameter(Mandatory=$false)]
    [string]$VaultName = "IT",  # 1Password vault name
    
    [Parameter(Mandatory=$false)]
    [string]$ItemName = "Exchange Online Automation",  # 1Password item name
    
    [Parameter(Mandatory=$false)]
    [string]$CertExportPath = ".\temp\ExchangeOnline-Cert.cer",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseServiceAccount  # Use 1Password service account instead of interactive
)

Write-Host "=== Exchange Online Certificate Authentication Setup ===" -ForegroundColor Green
Write-Host ""

# Function to get secrets from 1Password
function Get-OnePasswordSecret {
    param(
        [string]$Path,
        [bool]$UseServiceAccount = $false
    )
    
    try {
        if ($UseServiceAccount) {
            # Try to get service account token from Windows Credential Manager
            $scriptDir = Split-Path -Parent $PSScriptRoot
            $getCredScript = Join-Path $scriptDir "scripts\get_credential.ps1"
            
            if (Test-Path $getCredScript) {
                $serviceToken = & $getCredScript
                if ($serviceToken) {
                    $env:OP_SERVICE_ACCOUNT_TOKEN = $serviceToken
                    $result = op read $Path
                    Remove-Item env:OP_SERVICE_ACCOUNT_TOKEN -ErrorAction SilentlyContinue
                    return $result
                }
            }
            Write-Host "Service account not available, falling back to interactive mode" -ForegroundColor Yellow
        }
        
        # Interactive mode
        return op read $Path
    } catch {
        throw "Failed to retrieve secret from 1Password: $_"
    }
}

Write-Host "Retrieving configuration from 1Password..." -ForegroundColor Yellow
Write-Host "  Vault: $VaultName" -ForegroundColor Cyan
Write-Host "  Item: $ItemName" -ForegroundColor Cyan
Write-Host ""

try {
    # Test 1Password CLI availability
    $opVersion = op --version
    Write-Host "✅ 1Password CLI version: $opVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 1Password CLI not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install the 1Password CLI first:" -ForegroundColor Yellow
    Write-Host "  https://developer.1password.com/docs/cli/get-started#install" -ForegroundColor Cyan
    exit 1
}

# Retrieve values from 1Password
try {
    Write-Host "Retrieving Exchange Online configuration..." -ForegroundColor Yellow
    
    # Build 1Password paths
    $basePath = "op://$VaultName/$ItemName"
    
    # Retrieve each value
    $CertThumbprint = Get-OnePasswordSecret -Path "$basePath/certificate_thumbprint" -UseServiceAccount:$UseServiceAccount
    $AppId = Get-OnePasswordSecret -Path "$basePath/app_id" -UseServiceAccount:$UseServiceAccount
    $TenantId = Get-OnePasswordSecret -Path "$basePath/tenant_id" -UseServiceAccount:$UseServiceAccount
    
    Write-Host "✅ Configuration retrieved successfully" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "❌ Failed to retrieve configuration from 1Password" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Expected 1Password item structure:" -ForegroundColor Yellow
    Write-Host "  Vault: $VaultName"
    Write-Host "  Item: $ItemName"
    Write-Host "  Fields:"
    Write-Host "    - certificate_thumbprint: The certificate thumbprint"
    Write-Host "    - app_id: Azure AD application ID"
    Write-Host "    - tenant_id: Your tenant domain (e.g., company.com)"
    Write-Host ""
    Write-Host "To create this item in 1Password CLI:" -ForegroundColor Cyan
    Write-Host '  op item create --category="API Credential" --title="Exchange Online Automation" --vault="IT" \'
    Write-Host '    certificate_thumbprint="YOUR_THUMBPRINT" \'
    Write-Host '    app_id="YOUR_APP_ID" \'
    Write-Host '    tenant_id="your-tenant.com"'
    exit 1
}

Write-Host "Configuration loaded:" -ForegroundColor Cyan
Write-Host "  App ID: $AppId"
Write-Host "  Tenant: $TenantId"
Write-Host "  Certificate Thumbprint: $CertThumbprint"
Write-Host ""

Write-Host "1. Checking certificate exists in local store..." -ForegroundColor Yellow
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My" | Where-Object { $_.Thumbprint -eq $CertThumbprint }
if ($cert) {
    Write-Host "✅ Certificate found:" -ForegroundColor Green
    Write-Host "   Subject: $($cert.Subject)"
    Write-Host "   Thumbprint: $($cert.Thumbprint)"
    Write-Host "   Expires: $($cert.NotAfter)"
    
    # Warn if certificate is expiring soon
    $daysToExpiry = ($cert.NotAfter - (Get-Date)).Days
    if ($daysToExpiry -lt 30) {
        Write-Host "   ⚠️  WARNING: Certificate expires in $daysToExpiry days!" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Certificate not found in local store!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To create a self-signed certificate for testing:" -ForegroundColor Yellow
    Write-Host '  $cert = New-SelfSignedCertificate -Subject "CN=ExchangeOnlineAutomation" -CertStoreLocation "Cert:\CurrentUser\My" -KeyExportPolicy Exportable -KeySpec Signature -KeyLength 2048 -KeyAlgorithm RSA -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(2)'
    Write-Host '  Write-Host "New certificate thumbprint: $($cert.Thumbprint)"'
    Write-Host ""
    Write-Host "Then update the thumbprint in 1Password:" -ForegroundColor Yellow
    Write-Host "  op item edit '$ItemName' certificate_thumbprint=NEW_THUMBPRINT --vault='$VaultName'"
    exit 1
}

Write-Host ""
Write-Host "2. Preparing certificate for Azure upload..." -ForegroundColor Yellow

# Create temp directory if it doesn't exist
$certDir = Split-Path -Parent $CertExportPath
if ($certDir -and !(Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
}

if (Test-Path $CertExportPath) {
    Write-Host "⚠️  Certificate file already exists: $CertExportPath" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -ne 'y') {
        Write-Host "Skipping certificate export"
    } else {
        Export-Certificate -Cert $cert -FilePath $CertExportPath -Type CERT -Force
        Write-Host "✅ Certificate file updated: $CertExportPath" -ForegroundColor Green
    }
} else {
    Export-Certificate -Cert $cert -FilePath $CertExportPath -Type CERT
    Write-Host "✅ Certificate file created: $CertExportPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "3. Azure AD Configuration Steps:" -ForegroundColor Yellow
Write-Host "   a. Go to Azure Portal > Azure Active Directory > App registrations"
Write-Host "   b. Find your app (ID: $AppId)"
Write-Host "   c. Click 'Certificates & secrets' in the left menu"
Write-Host "   d. Click 'Upload certificate' button"
Write-Host "   e. Select file: $CertExportPath"
Write-Host "   f. Verify thumbprint matches: $CertThumbprint"
Write-Host "   g. Click 'Add'"

Write-Host ""
Write-Host "4. Required API Permissions (verify these are granted):" -ForegroundColor Yellow
Write-Host "   - Microsoft Graph:"
Write-Host "     * User.ReadWrite.All (Application)"
Write-Host "     * Directory.Read.All (Application)"
Write-Host "     * Sites.ReadWrite.All (Application)"
Write-Host "   - Office 365 Exchange Online:"
Write-Host "     * Exchange.ManageAsApp (Application)"
Write-Host ""
Write-Host "   ⚠️  All permissions must be granted admin consent!" -ForegroundColor Yellow

Write-Host ""
$testNow = Read-Host "Ready to test the connection? (y/n)"
if ($testNow -ne 'y') {
    Write-Host "Skipping connection test. Run this script again after Azure configuration."
    exit 0
}

Write-Host ""
Write-Host "5. Testing certificate authentication..." -ForegroundColor Yellow
try {
    Write-Host "   Importing Exchange Online module..."
    if (!(Get-Module -Name ExchangeOnlineManagement)) {
        Import-Module ExchangeOnlineManagement -Force -ErrorAction Stop
    }
    
    Write-Host "   Attempting certificate-based connection..."
    Connect-ExchangeOnline -AppId $AppId -Organization $TenantId -CertificateThumbprint $CertThumbprint -ShowBanner:$false -ErrorAction Stop
    
    Write-Host "   ✅ Successfully connected to Exchange Online!" -ForegroundColor Green
    Write-Host "   Testing basic command..."
    
    $orgConfig = Get-OrganizationConfig | Select-Object DisplayName, ExchangeVersion
    Write-Host "   Organization: $($orgConfig.DisplayName)"
    Write-Host "   Exchange Version: $($orgConfig.ExchangeVersion)"
    
    # Test mailbox access
    Write-Host "   Testing mailbox access..."
    $testMailboxes = Get-Mailbox -ResultSize 1 -ErrorAction SilentlyContinue
    if ($testMailboxes) {
        Write-Host "   ✅ Can access mailboxes" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Cannot access mailboxes - check Exchange.ManageAsApp permission" -ForegroundColor Yellow
    }
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "   ✅ Certificate authentication is working!" -ForegroundColor Green
    
    # Store the connection command for future reference
    Write-Host ""
    Write-Host "To connect in your scripts, use:" -ForegroundColor Cyan
    Write-Host '  Connect-ExchangeOnline -AppId $AppId -Organization $TenantId -CertificateThumbprint $CertThumbprint -ShowBanner:$false'
    Write-Host ""
    Write-Host "Or retrieve from 1Password dynamically:" -ForegroundColor Cyan
    Write-Host '  $AppId = op read "op://IT/Exchange Online Automation/app_id"'
    Write-Host '  $TenantId = op read "op://IT/Exchange Online Automation/tenant_id"'
    Write-Host '  $CertThumbprint = op read "op://IT/Exchange Online Automation/certificate_thumbprint"'
    
} catch {
    Write-Host "   ❌ Certificate authentication failed:" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "   1. Ensure certificate is uploaded to Azure AD app"
    Write-Host "   2. Wait 5-10 minutes for Azure changes to propagate"
    Write-Host "   3. Verify Exchange.ManageAsApp permission is granted with admin consent"
    Write-Host "   4. Check tenant ID is correct: $TenantId"
    Write-Host "   5. Ensure the app has been assigned the Exchange Administrator role in Azure AD"
    Write-Host "   6. Verify the certificate thumbprint in 1Password matches the local certificate"
    
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
    exit 1
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "Certificate authentication is ready for automation!"
Write-Host ""
Write-Host "IMPORTANT Security Notes:" -ForegroundColor Yellow
Write-Host "  1. Delete the exported certificate file: $CertExportPath"
Write-Host "  2. All credentials are stored securely in 1Password"
Write-Host "  3. This script is safe to commit to public repositories"
Write-Host "  4. Team members need 1Password access to the '$VaultName' vault"
Write-Host ""
Write-Host "For automated/unattended execution:" -ForegroundColor Cyan
Write-Host "  .\setup_exchange_auth.ps1 -UseServiceAccount"