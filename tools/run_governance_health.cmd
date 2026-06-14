@echo off
rem Scheduled-task entry point for the governance health digest (see docs/artifact-entry-setup.md, Governance health digest).
rem Read-only; Task Scheduler discards stdout, so the digest is appended to logs\governance_health.log.
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs"
echo ---- %date% %time% ---- >> "%~dp0..\logs\governance_health.log"
"C:\Python314\python.exe" "%~dp0governance_health.py" >> "%~dp0..\logs\governance_health.log" 2>&1
echo exit code %errorlevel% >> "%~dp0..\logs\governance_health.log"
exit /b %errorlevel%
