#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run JML onboarding for a ticket

.DESCRIPTION
    Simple PowerShell wrapper for onboarding workflow

.PARAMETER TicketId
    The ticket ID to process

.PARAMETER DryRun
    Run in dry-run mode (no actual changes)

.EXAMPLE
    .\onboard.ps1 12345
    
.EXAMPLE
    .\onboard.ps1 12345 -DryRun
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TicketId,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $PSScriptRoot "onboard.py"

if ($DryRun) {
    & $VenvPython $ScriptPath $TicketId --dry-run
} else {
    & $VenvPython $ScriptPath $TicketId
}