@echo off
setlocal
cd /d "%~dp0"
title Athena Runtime Cleanup

echo Athena Runtime Cleanup
echo ======================
echo Project root: %CD%
echo.

echo Running canonical Python cleanup/quarantine...
python -B Tools\runtime_cleanup.py
if errorlevel 1 (
    echo.
    echo Runtime cleanup reported a failure.
    pause
    exit /b 1
)

echo.
echo Verifying canonical runtime files...
if exist "Core\version.py" echo   Core\version.py found
if exist "Scout\app.py" echo   Scout\app.py found
if exist "Scout\conversation\router.py" echo   Scout\conversation\router.py found

echo.
echo Keeping canonical launch files:
echo   Scout.bat
echo   Stop Scout Port 8765.bat
echo   Clean Athena Runtime.bat
echo   Athena Studio.bat
echo.
echo Done.
pause
