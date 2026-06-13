@echo off
rem Scheduled-task entry point for the daily artifact sync (see docs/artifact-entry-setup.md).
rem Task Scheduler discards stdout, so all output is appended to logs\artifact_sync.log.
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs"
echo ---- %date% %time% ---- >> "%~dp0..\logs\artifact_sync.log"
"C:\Python314\python.exe" "%~dp0sync_artifacts.py" >> "%~dp0..\logs\artifact_sync.log" 2>&1
echo exit code %errorlevel% >> "%~dp0..\logs\artifact_sync.log"
exit /b %errorlevel%
