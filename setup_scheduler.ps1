# setup_scheduler.ps1
# Run this ONCE as Administrator to register the daily Task Scheduler job.
# Right-click this file → "Run with PowerShell" (as Admin)

$TaskName    = "Daily3DModelGenerator"
$ScriptPath  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile   = Join-Path $ScriptPath "run_daily.bat"
$PythonExe   = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $PythonExe) {
    # Try common install locations
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $PythonExe = $c; break }
    }
}

if (-not $PythonExe) {
    Write-Host "ERROR: Python not found. Please install Python first." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setting up Daily 3D Model Task Scheduler" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Task Name  : $TaskName"
Write-Host "Batch File : $BatchFile"
Write-Host "Python     : $PythonExe"
Write-Host ""

# ── Ask user for preferred time ──
$RunTime = Read-Host "What time should it run daily? (24h format, e.g. 03:00 for 3 AM)"
if (-not $RunTime) { $RunTime = "03:00" }

# ── Create the task action (runs the batch file) ──
$Action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatchFile`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $RunTime
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RunOnlyIfNetworkAvailable $false `
    -WakeToRun $false `
    -StartWhenAvailable $true

# ── Remove old task if exists ──
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# ── Register new task ──
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "✅ Task '$TaskName' registered!" -ForegroundColor Green
Write-Host "   Runs every day at $RunTime"
Write-Host ""
Write-Host "To run it NOW for testing, use:"
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Read-Host "Press Enter to close"
