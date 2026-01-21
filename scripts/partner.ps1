#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run JML partner workflow for a ticket

.DESCRIPTION
    Simple PowerShell wrapper for partner workflow

.PARAMETER TicketId
    The ticket ID to process

.PARAMETER DryRun
    Run in dry-run mode (no actual changes)

.EXAMPLE
    .\partner.ps1 67890
    
.EXAMPLE
    .\partner.ps1 67890 -DryRun
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$TicketId,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $PSScriptRoot "partner.py"

if ($DryRun) {
    & $VenvPython $ScriptPath $TicketId --dry-run
} else {
    & $VenvPython $ScriptPath $TicketId
}