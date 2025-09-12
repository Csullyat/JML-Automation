$ErrorActionPreference = "Stop"

# Add the user's PowerShell module path to ensure CredentialManager is found
$userModulePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Modules"
if ($env:PSModulePath -notlike "*$userModulePath*") {
    $env:PSModulePath = "$userModulePath;$env:PSModulePath"
}

try {
    Import-Module CredentialManager -Force
    $cred = Get-StoredCredential -Target 'JML Service Account'
    if ($cred) {
        $token = $cred.GetNetworkCredential().Password
        # Clean the token - extract the real ops_ token if it has placeholder text
        if (($token -split 'ops_').Length -gt 2) {
            $parts = $token -split 'ops_'
            $token = 'ops_' + $parts[2]
        }
        $token
    } else {
        Write-Error "Credential not found"
    }
} catch {
    Write-Error "Failed to retrieve credential: $_"
}
