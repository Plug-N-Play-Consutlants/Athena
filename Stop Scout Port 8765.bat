@echo off
setlocal
cd /d "%~dp0"
title Stop Athena Scout

echo Stop Athena Scout
echo =================
echo.
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -B Scout\stop_scout_windows.py --yes
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        py -3 -B Scout\stop_scout_windows.py --yes
    ) else (
        echo Python was not found.
        pause
        exit /b 1
    )
)
echo.
pause
