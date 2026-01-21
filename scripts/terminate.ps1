#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run JML termination for a ticket

.DESCRIPTION
    Simple PowerShell wrapper for termination workflow

.PARAMETER TicketId
    The ticket ID to process

.PARAMETER DryRun
    Run in dry-run mode (no actual changes)

.EXAMPLE
    .\terminate.ps1 77543
    
.EXAMPLE
    .\terminate.ps1 77543 -DryRun
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TicketId,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $PSScriptRoot "terminate.py"

if ($DryRun) {
    & $VenvPython $ScriptPath $TicketId --dry-run
} else {
    & $VenvPython $ScriptPath $TicketId
}