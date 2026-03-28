@echo off
REM Kumar Brothers Steel ERP - Deployment Script for Windows
REM =========================================================

echo.
echo ===========================================================
echo   Kumar Brothers Steel ERP - Docker Deployment
echo ===========================================================
echo.

cd /d "%~dp0"

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [1/3] Pulling Docker images...
docker-compose pull

echo.
echo [2/3] Starting all services...
docker-compose up -d

echo.
echo [3/3] Monitoring startup...
echo.
echo The site creation process takes 2-5 minutes on first run.
echo.
echo Run the following command to see logs:
echo   docker-compose logs -f erpnext
echo.
echo ===========================================================
echo   ACCESS INFORMATION
echo ===========================================================
echo.
echo   URL:      http://localhost:8080
echo   Username: Administrator
echo   Password: KumarAdmin@2026
echo.
echo ===========================================================
echo.

pause
