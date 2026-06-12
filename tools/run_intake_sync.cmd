@echo off
rem Scheduled-task entry point for the daily intake sync (see docs/intake-setup.md C).
rem Task Scheduler discards stdout, so all output is appended to logs\intake_sync.log.
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs"
echo ---- %date% %time% ---- >> "%~dp0..\logs\intake_sync.log"
"C:\Python314\python.exe" "%~dp0sync_intake.py" >> "%~dp0..\logs\intake_sync.log" 2>&1
echo exit code %errorlevel% >> "%~dp0..\logs\intake_sync.log"
exit /b %errorlevel%
