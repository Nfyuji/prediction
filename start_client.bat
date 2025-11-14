@echo off
chcp 65001 >nul
:: ============================================
:: Simple Client Setup - English Only
:: Just enter Server URL and Token
:: ============================================

title Device Monitoring - Client

:: Check Python
python --version >nul 2>&1 || (echo [ERROR] Python not installed! && pause && exit /b 1)
if not exist "device_client.py" (echo [ERROR] device_client.py not found! && pause && exit /b 1)

cls
echo.
echo ============================================================
echo           Device Monitoring - Client Setup
echo ============================================================
echo.

:: If device_config.json exists, use it directly
if exist "device_config.json" (
    echo [OK] Found saved settings - Starting client...
    echo.
    goto :run
)

:: Just 2 questions
set /p SERVER_URL="1. Server URL (Press Enter for default): "
if "%SERVER_URL%"=="" set SERVER_URL=https://comment-tony-gifts-fabric.trycloudflare.com

set /p DEVICE_TOKEN="2. Device Token (Press Enter for auto-registration): "

echo.
echo 3. Saving settings and starting...
echo.

:: Save settings
if "%DEVICE_TOKEN%"=="" (
    (
        echo {
        echo   "server_url": "%SERVER_URL%"
        echo }
    ) > device_config.json
) else (
    (
        echo {
        echo   "device_token": "%DEVICE_TOKEN%",
        echo   "server_url": "%SERVER_URL%"
        echo }
    ) > device_config.json
)

:run
:: Run with admin privileges automatically
net session >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Administrator privileges: Enabled
    echo.
    echo ============================================================
    echo    Client is running - Do not close this window!
    echo ============================================================
    echo.
    python device_client.py
) else (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process python -ArgumentList 'device_client.py' -Verb RunAs -WorkingDirectory '%CD%'"
    echo.
    echo [OK] Client started in new window with administrator privileges
    echo.
)

pause

