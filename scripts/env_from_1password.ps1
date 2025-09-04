<# 
Reads SolarWinds Service Desk API secrets from 1Password and exports them
as env vars for the current PowerShell session.
Requires 'op signin' already done in this terminal.
#>

param(
  [string]$TokenRef = 'op://IT/samanage-api-token/password',
  [string]$BaseUrl  = 'https://it.filevine.com'
)

function Assert-OpAuth {
  # Works with Desktop app / biometric unlock (no OP_SESSION_* needed)
  $null = & op whoami 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "You're not signed in to 1Password CLI. Run:  op signin" -ForegroundColor Yellow
    throw "1Password CLI not authenticated."
  }
}

try {
  Assert-OpAuth

  $token = & op read $TokenRef
  if (-not $token) { throw "Failed to read token from $TokenRef" }

  # Export to CURRENT shell
  $env:SWSD_API_TOKEN = $token.Trim()
  $env:SWSD_BASE_URL  = $BaseUrl.Trim()

  Write-Host "Exported SWSD_BASE_URL=$($env:SWSD_BASE_URL)"
  Write-Host "Exported SWSD_API_TOKEN=[redacted]"
}
catch {
  Write-Error $_
  exit 1
}
