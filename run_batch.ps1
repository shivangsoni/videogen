# =============================================================================
# run_batch.ps1 - Background Batch Video Generator
# =============================================================================
# Runs batch_video_generator.py as a background Windows process that:
#   - Survives terminal/VS Code window close
#   - Prevents Windows from sleeping during generation
#   - Logs output to batch_log.txt (real-time, unbuffered)
#   - Automatically skips already-generated videos on re-run
#   - Publishes each video to YouTube immediately after generation
#   - Retries failed YouTube uploads (3 attempts with backoff)
#
# Usage:
#   .\run_batch.ps1 -Folder "hydration_health" -Publish -Account "prity"
#   .\run_batch.ps1 -Folder "hydration_health"                            # no publish
#   .\run_batch.ps1 -Folder "hydration_health" -Languages "English,Hindi" # specific langs
#   .\run_batch.ps1 -Status                                               # check progress
#   .\run_batch.ps1 -Stop                                                 # stop & restore
# =============================================================================

param(
    [Parameter(HelpMessage = "Folder name inside youtubeshorts/ to process")]
    [string]$Folder = "",

    [Parameter(HelpMessage = "Publish generated videos to YouTube")]
    [switch]$Publish,

    [Parameter(HelpMessage = "YouTube account name for publishing")]
    [string]$Account = "",

    [Parameter(HelpMessage = "Comma-separated list of languages (default: all 27)")]
    [string]$Languages = "",

    [Parameter(HelpMessage = "Stop the running batch process and restore sleep settings")]
    [switch]$Stop,

    [Parameter(HelpMessage = "Show current batch progress from log")]
    [switch]$Status
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logFile = Join-Path $scriptDir "batch_log.txt"
$errFile = Join-Path $scriptDir "batch_error.txt"
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$batchScript = Join-Path $scriptDir "batch_video_generator.py"

# ---- Stop command ----
if ($Stop) {
    $procs = Get-Process python -ErrorAction SilentlyContinue
    if ($procs) {
        Stop-Process -Name python -Force
        Stop-Process -Name ffmpeg -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Batch process stopped." -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] No batch process running." -ForegroundColor Yellow
    }
    # Restore Windows sleep settings
    powercfg /change standby-timeout-ac 30
    powercfg /change standby-timeout-dc 15
    powercfg /change monitor-timeout-ac 15
    Write-Host "[OK] Windows sleep settings restored." -ForegroundColor Green
    exit
}

# ---- Status command ----
if ($Status) {
    if (Test-Path $logFile) {
        Write-Host "=== Published Videos ===" -ForegroundColor Cyan
        Select-String "Published to YouTube" $logFile | ForEach-Object { Write-Host $_.Line }
        Write-Host ""
        Write-Host "=== Errors ===" -ForegroundColor Red
        Select-String "ERROR|FAIL|Exception" $logFile | ForEach-Object { Write-Host $_.Line }
        Write-Host ""
        Write-Host "=== Latest Activity ===" -ForegroundColor Yellow
        Get-Content $logFile -Tail 15
        Write-Host ""
        $proc = Get-Process python -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "[RUNNING] Batch process active (PID: $($proc.Id))" -ForegroundColor Green
        }
        else {
            Write-Host "[STOPPED] No batch process running." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "No log file found. Start a batch first."
    }
    exit
}

# ---- Validate ----
if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Python venv not found: $pythonExe" -ForegroundColor Red
    Write-Host "Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

$existing = Get-Process python -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[WARN] Python process already running (PID: $($existing.Id))." -ForegroundColor Yellow
    Write-Host "Stop it first:  .\run_batch.ps1 -Stop"
    exit 1
}

if (-not $Folder) {
    Write-Host "[ERROR] -Folder is required." -ForegroundColor Red
    Write-Host "Usage: .\run_batch.ps1 -Folder `"hydration_health`" -Publish -Account `"prity`""
    exit 1
}

# ---- Build arguments ----
# -u = unbuffered stdout so log file updates in real-time
$pyArgs = @("-u", $batchScript)
if ($Folder) { $pyArgs += "--folder"; $pyArgs += $Folder }
if ($Publish) { $pyArgs += "--publish" }
if ($Account) { $pyArgs += "--account"; $pyArgs += $Account }
if ($Languages) { $pyArgs += "--languages"; $pyArgs += $Languages }

# ---- Clear old logs ----
"" | Set-Content $logFile -Encoding UTF8
"" | Set-Content $errFile -Encoding UTF8

# ---- Prevent Windows sleep ----
Write-Host "Disabling Windows sleep..." -ForegroundColor DarkGray
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change monitor-timeout-ac 0

# ---- Launch detached process ----
$proc = Start-Process -FilePath $pythonExe `
    -ArgumentList $pyArgs `
    -WorkingDirectory $scriptDir `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile `
    -WindowStyle Hidden `
    -PassThru

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " BATCH STARTED (background)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " PID:       $($proc.Id)"
Write-Host " Log:       batch_log.txt"
Write-Host " Errors:    batch_error.txt"
Write-Host ""
Write-Host " Monitor:   Get-Content batch_log.txt -Tail 20 -Wait"
Write-Host " Status:    .\run_batch.ps1 -Status"
Write-Host " Stop:      .\run_batch.ps1 -Stop"
Write-Host ""
Write-Host " Safe to close VS Code and terminal."
Write-Host " Windows will NOT sleep until batch finishes."
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tailing log (Ctrl+C to stop watching, batch keeps running)..."
Write-Host ""

# Wait for output to start, then tail the log
Start-Sleep 3
Get-Content $logFile -Tail 50 -Wait
