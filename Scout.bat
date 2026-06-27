@echo off
setlocal
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
title Athena Scout

echo Athena Scout
echo ============
echo Project root: %CD%
echo.

if not exist Logs mkdir Logs

echo Removing Python runtime caches...
for /d /r %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D"
echo.
echo Stopping any stale Scout listeners on ports 8765-8794...
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python Scout\stop_scout_windows.py --yes > Logs\scout_stop_log.txt 2>&1
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        py -3 Scout\stop_scout_windows.py --yes > Logs\scout_stop_log.txt 2>&1
    )
)

echo Starting Scout...
echo.
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -B launch.py
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        py -3 -B launch.py
    ) else (
        echo Python was not found. Launch Athena from Anaconda Prompt or install Python.
        pause
        exit /b 1
    )
)

echo.
echo Scout has stopped.
echo If Scout did not open, check Logs\scout_launch_error.txt
echo.
pause
