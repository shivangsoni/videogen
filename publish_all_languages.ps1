# ============================================
# YouTube Shorts - Publish All Languages Script
# ============================================
# This script generates and publishes YouTube Shorts
# in all supported languages for a given folder.
#
# Usage:
#   .\publish_all_languages.ps1 -Folder "Early Dating Truth" -Account ssoni
#   .\publish_all_languages.ps1 -Folder "Early Dating Truth" -Account shison -Languages "English,Hindi,Spanish"
#
# ============================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Folder,
    
    [Parameter(Mandatory=$true)]
    [string]$Account,
    
    [string]$Languages = "",  # Empty = all languages
    
    [switch]$NoPublish,
    
    [switch]$Force  # Regenerate even if exists
)

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  YouTube Shorts - Multi-Language Publisher" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Folder:  $Folder" -ForegroundColor Yellow
Write-Host "Account: $Account" -ForegroundColor Yellow

# Build command arguments
$args = @(
    "batch_video_generator.py",
    "--folder", "`"$Folder`""
)

if ($Languages -ne "") {
    Write-Host "Languages: $Languages" -ForegroundColor Yellow
    $args += "--languages", "`"$Languages`""
} else {
    Write-Host "Languages: ALL (19 languages)" -ForegroundColor Yellow
}

if (-not $NoPublish) {
    $args += "--publish", "--account", $Account
    Write-Host "Publish:  Yes" -ForegroundColor Green
} else {
    Write-Host "Publish:  No (generate only)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Starting video generation..." -ForegroundColor Cyan
Write-Host "This may take 5-10 minutes per language." -ForegroundColor Gray
Write-Host ""

# Run the batch video generator
$startTime = Get-Date
python @args
$exitCode = $LASTEXITCODE
$duration = (Get-Date) - $startTime

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  COMPLETED" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Duration: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Yellow
Write-Host "Exit Code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
Write-Host ""

# List generated videos
$videoPath = Join-Path $scriptDir "youtubeshorts\$Folder"
if (Test-Path $videoPath) {
    Write-Host "Generated Videos:" -ForegroundColor Cyan
    Get-ChildItem "$videoPath\*.mp4" | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  - $($_.Name) ($size MB)" -ForegroundColor Green
    }
}

Write-Host ""
