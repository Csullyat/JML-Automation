# PowerShell script to convert mailbox to shared
param(
    [string]$UserEmail,
    [string]$ManagerEmail
)

# Import Exchange Online module
Import-Module ExchangeOnlineManagement

try {
    # Connect to Exchange Online (assumes you're already connected or have app-only auth)
    Write-Host "Converting mailbox $UserEmail to shared..."
    
    # Convert to shared mailbox
    Set-Mailbox -Identity $UserEmail -Type Shared
    
    Write-Host "Mailbox conversion completed successfully"
    
    # Grant manager full access
    if ($ManagerEmail) {
        Write-Host "Granting full access to $ManagerEmail..."
        Add-MailboxPermission -Identity $UserEmail -User $ManagerEmail -AccessRights FullAccess -InheritanceType All
        
        # Grant Send As permission
        Add-RecipientPermission -Identity $UserEmail -Trustee $ManagerEmail -AccessRights SendAs -Confirm:$false
        
        Write-Host "Permissions granted successfully"
    }
    
    # Verify the mailbox type
    $mailbox = Get-Mailbox -Identity $UserEmail
    Write-Host "Mailbox type is now: $($mailbox.RecipientTypeDetails)"
    
    exit 0
}
catch {
    Write-Error "Failed to convert mailbox: $_"
    exit 1
}
