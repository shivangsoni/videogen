@echo off
REM ============================================
REM YouTube Shorts - Publish All Languages
REM ============================================
REM Simple batch script to publish videos in all languages
REM
REM Usage:
REM   publish_video.bat "Early Dating Truth" ssoni
REM   publish_video.bat "Early Dating Truth" shison "English,Hindi,Spanish"
REM ============================================

setlocal EnableDelayedExpansion

set FOLDER=%~1
set ACCOUNT=%~2
set LANGUAGES=%~3

if "%FOLDER%"=="" (
    echo Usage: publish_video.bat "Folder Name" account [languages]
    echo.
    echo Example:
    echo   publish_video.bat "Early Dating Truth" ssoni
    echo   publish_video.bat "Early Dating Truth" ssoni "English,Hindi,Spanish"
    exit /b 1
)

if "%ACCOUNT%"=="" (
    echo Error: Account name required
    echo Available accounts: ssoni, shison
    exit /b 1
)

cd /d "%~dp0"

echo.
echo ============================================
echo   YouTube Shorts - Multi-Language Publisher
echo ============================================
echo.
echo Folder:  %FOLDER%
echo Account: %ACCOUNT%

if "%LANGUAGES%"=="" (
    echo Languages: ALL ^(19 languages^)
    echo.
    echo Starting video generation for ALL languages...
    echo This will take approximately 2-3 hours.
    echo.
    python batch_video_generator.py --folder "%FOLDER%" --publish --account %ACCOUNT%
) else (
    echo Languages: %LANGUAGES%
    echo.
    echo Starting video generation...
    echo.
    python batch_video_generator.py --folder "%FOLDER%" --languages "%LANGUAGES%" --publish --account %ACCOUNT%
)

echo.
echo ============================================
echo   COMPLETED
echo ============================================
echo.

REM List generated videos
echo Generated Videos:
dir /b "youtubeshorts\%FOLDER%\*.mp4" 2>nul

echo.
pause
