@echo off
setlocal
cd /d "%~dp0"
echo Athena Studio
=============
echo Project root: %CD%
echo.
python -B Tools\athena_studio.py
if errorlevel 1 (
  echo.
  echo Athena Studio exited with an error.
  pause
)
