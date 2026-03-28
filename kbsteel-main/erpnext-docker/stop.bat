@echo off
REM Stop Kumar Brothers Steel ERP
cd /d "%~dp0"
echo Stopping ERPNext services...
docker-compose down
echo Done.
pause
