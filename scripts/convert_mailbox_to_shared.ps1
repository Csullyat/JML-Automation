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
        Write-Host "Mailbox conversion initiated"
        
        # Wait for propagation
        Start-Sleep -Seconds 10
        
        # Verify conversion
        $mailbox = Get-Mailbox -Identity $UserEmail
        Write-Host "Mailbox type is now: $($mailbox.RecipientTypeDetails)"
        
        if ($mailbox.RecipientTypeDetails -ne "SharedMailbox") {
            Write-Warning "Mailbox may still be converting. Current type: $($mailbox.RecipientTypeDetails)"
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