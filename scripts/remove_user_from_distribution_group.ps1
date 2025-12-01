# Remove user from Exchange Online distribution group using certificate authentication
param(
    [Parameter(Mandatory=$true)]
    [string]$UserEmail,
    
    [Parameter(Mandatory=$true)]
    [string]$GroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$CertThumbprint,
    
    [Parameter(Mandatory=$true)]
    [string]$AppId
)

$ErrorActionPreference = 'Stop'

try {
    # Import Exchange Online module with error handling
    try {
        Import-Module ExchangeOnlineManagement -Force -Global
        Write-Output "Exchange Online module loaded successfully"
    } catch {
        # Try alternative import approach
        $modulePath = Get-Module -ListAvailable ExchangeOnlineManagement | Select-Object -First 1 -ExpandProperty ModuleBase
        if ($modulePath) {
            Import-Module "$modulePath\ExchangeOnlineManagement.psd1" -Force -Global
            Write-Output "Exchange Online module loaded via explicit path"
        } else {
            throw "Could not find ExchangeOnlineManagement module"
        }
    }

    # Connect using certificate authentication (bypasses SSO/MFA)
    Connect-ExchangeOnline `
        -CertificateThumbprint $CertThumbprint `
        -AppId $AppId `
        -Organization 'filevineco.onmicrosoft.com' `
        -ShowBanner:$false
    
    Write-Output "Connected to Exchange Online successfully"
    
    # First try to identify the group type
    $group = Get-Group -Identity $GroupName -ErrorAction SilentlyContinue
    
    if ($group.RecipientTypeDetails -eq "GroupMailbox") {
        # This is a Microsoft 365 Group (formerly Office 365 Group)
        Write-Output "Detected Microsoft 365 Group: $GroupName"
        
        $maxRetries = 3
        $retryCount = 0
        $success = $false
        
        while ($retryCount -lt $maxRetries -and -not $success) {
            try {
                # First verify the user exists in Exchange Online for M365 groups
                $user = Get-User -Identity $UserEmail -ErrorAction SilentlyContinue
                if (-not $user) {
                    throw [System.Exception]::new("Couldn't find object `"$UserEmail`". Please make sure that it was spelled correctly or specify a different object.")
                }
                
                Remove-UnifiedGroupLinks -Identity $GroupName -LinkType Members -Links $UserEmail -Confirm:$false -ErrorAction Stop
                Write-Output "SUCCESS: Removed $UserEmail from Microsoft 365 Group $GroupName"
                $success = $true
            } catch {
                if ($_.Exception.Message -like "*Couldn't find object*" -or $_.Exception.Message -like "*not found*") {
                    $retryCount++
                    if ($retryCount -lt $maxRetries) {
                        $waitTime = 10 * $retryCount
                        Write-Output "User not found for M365 group, retrying in $waitTime seconds... (attempt $retryCount/$maxRetries)"
                        Start-Sleep -Seconds $waitTime
                    } else {
                        throw $_
                    }
                } else {
                    throw $_
                }
            }
        }
    } else {
        # This is a distribution group or mail-enabled security group
        Write-Output "Detected Distribution/Security Group: $GroupName"
        
        # For distribution groups, try with retry logic
        $maxRetries = 3
        $retryCount = 0
        $success = $false
        
        while ($retryCount -lt $maxRetries -and -not $success) {
            try {
                # First verify the user exists in Exchange Online
                $user = Get-User -Identity $UserEmail -ErrorAction SilentlyContinue
                if (-not $user) {
                    throw [System.Exception]::new("Couldn't find object `"$UserEmail`". Please make sure that it was spelled correctly or specify a different object.")
                }
                
                Remove-DistributionGroupMember -Identity $GroupName -Member $UserEmail -BypassSecurityGroupManagerCheck -Confirm:$false -ErrorAction Stop
                Write-Output "SUCCESS: Removed $UserEmail from Distribution Group $GroupName"
                $success = $true
            } catch {
                if ($_.Exception.Message -like "*Couldn't find object*") {
                    $retryCount++
                    if ($retryCount -lt $maxRetries) {
                        $waitTime = 10 * $retryCount
                        Write-Output "User not found in Exchange, retrying in $waitTime seconds... (attempt $retryCount/$maxRetries)"
                        Start-Sleep -Seconds $waitTime
                    } else {
                        throw $_
                    }
                } else {
                    throw $_
                }
            }
        }
    }
    
} catch {
    if ($_.Exception.Message -like "*not a member*" -or $_.Exception.Message -like "*not found in group*") {
        Write-Output "SUCCESS: User $UserEmail was not a member of group $GroupName (no action needed)"
    } elseif ($_.Exception.Message -like "*sufficient permissions*" -or $_.Exception.Message -like "*manager of the group*") {
        Write-Error "PERMISSIONS: App registration needs to be made a manager of group $GroupName"
    } else {
        Write-Error "FAILED: $($_.Exception.Message)"
        throw $_
    }
} finally {
    # Disconnect
    try { 
        Disconnect-ExchangeOnline -Confirm:$false 
        Write-Output "Disconnected from Exchange Online"
    } catch {
        Write-Warning "Could not disconnect cleanly: $($_.Exception.Message)"
    }
}