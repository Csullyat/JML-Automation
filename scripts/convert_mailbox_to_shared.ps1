# PowerShell script to convert mailbox to shared
# Used by JML Automation for termination workflow

param(
    [Parameter(Mandatory=$true)]
    [string]$UserEmail,
    
    [Parameter(Mandatory=$false)]
    [string]$ManagerEmail,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipConnection
)

$ErrorActionPreference = "Stop"

try {
    # Import Exchange Online module if not already loaded
    if (!(Get-Module -Name ExchangeOnlineManagement)) {
        Write-Host "Loading Exchange Online Management module..."
        Import-Module ExchangeOnlineManagement -Force
    }
    
    # Connect to Exchange Online if not already connected (and not skipped)
    if (!$SkipConnection) {
        # Check if already connected
        try {
            $testConnection = Get-OrganizationConfig -ErrorAction SilentlyContinue
        } catch {
            Write-Host "Not connected to Exchange Online. Please connect first or use app authentication."
            exit 1
        }
    }
    
    Write-Host "Converting mailbox $UserEmail to shared..."
    
    # Get current mailbox state
    $currentMailbox = Get-Mailbox -Identity $UserEmail -ErrorAction Stop
    Write-Host "Current mailbox type: $($currentMailbox.RecipientTypeDetails)"
    
    if ($currentMailbox.RecipientTypeDetails -eq "SharedMailbox") {
        Write-Host "Mailbox is already a SharedMailbox"
    } else {
        # Convert to shared mailbox
        Set-Mailbox -Identity $UserEmail -Type Shared -Confirm:$false
        Write-Host "Conversion command completed."
        
        # Wait for changes to propagate...
        Write-Host "Waiting for changes to propagate..."
        Start-Sleep -Seconds 15
        
        # Verify conversion with retry logic
        $maxRetries = 3
        $retryCount = 0
        $conversionSuccessful = $false
        
        while ($retryCount -lt $maxRetries -and -not $conversionSuccessful) {
            Write-Host "Verifying conversion..."
            $mailbox = Get-Mailbox -Identity $UserEmail
            
            if ($mailbox.RecipientTypeDetails -eq "SharedMailbox") {
                Write-Host "New mailbox type: SharedMailbox"
                Write-Host "SUCCESS: Mailbox successfully converted to SharedMailbox"
                $conversionSuccessful = $true
            } else {
                $retryCount++
                Write-Host "New mailbox type: $($mailbox.RecipientTypeDetails)"
                
                if ($retryCount -lt $maxRetries) {
                    Write-Host "Conversion still in progress, waiting 10 more seconds... (attempt $retryCount/$maxRetries)"
                    Start-Sleep -Seconds 10
                } else {
                    Write-Host "ERROR: Mailbox type is $($mailbox.RecipientTypeDetails), expected SharedMailbox"
                    exit 1
                }
            }
        }
    }
    
    # Grant manager permissions if specified
    if ($ManagerEmail) {
        Write-Host "Granting permissions to $ManagerEmail..."
        
        # Grant Full Access
        try {
            Add-MailboxPermission -Identity $UserEmail -User $ManagerEmail -AccessRights FullAccess -InheritanceType All -Confirm:$false | Out-Null
            Write-Host "  - Full Access granted"
        } catch {
            Write-Warning "  - Full Access may already exist or failed: $_"
        }
        
        # Grant Send As permission
        try {
            Add-RecipientPermission -Identity $UserEmail -Trustee $ManagerEmail -AccessRights SendAs -Confirm:$false | Out-Null
            Write-Host "  - Send As permission granted"
        } catch {
            Write-Warning "  - Send As permission may already exist or failed: $_"
        }
        
        Write-Host "Permissions processing completed"
    }
    
    Write-Host "SUCCESS: Mailbox conversion completed for $UserEmail"
    exit 0
    
} catch {
    Write-Error "Failed to convert mailbox: $_"
    Write-Host "Error details: $($_.Exception.Message)"
    exit 1
}