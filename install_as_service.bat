@echo off
:: سكريبت لتثبيت device_client.py كخدمة Windows باستخدام NSSM
:: يتطلب: NSSM (Non-Sucking Service Manager)
:: تحميل NSSM من: https://nssm.cc/download

echo ============================================
echo تثبيت device_client.py كخدمة Windows
echo ============================================
echo.

:: التحقق من الصلاحيات
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo خطأ: يجب تشغيل هذا الملف بصلاحيات المسؤول!
    echo.
    echo انقر بزر الماوس الأيمن على هذا الملف واختر "Run as administrator"
    pause
    exit /b 1
)

:: التحقق من وجود Python
python --version >nul 2>&1
if errorlevel 1 (
    echo خطأ: Python غير مثبت أو غير موجود في PATH
    pause
    exit /b 1
)

:: الحصول على مسار Python
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
echo Python موجود في: %PYTHON_PATH%
echo.

:: الحصول على المسار الحالي
set CURRENT_DIR=%~dp0
echo المجلد الحالي: %CURRENT_DIR%
echo.

:: التحقق من وجود device_client.py
if not exist "%CURRENT_DIR%device_client.py" (
    echo خطأ: device_client.py غير موجود في المجلد الحالي
    pause
    exit /b 1
)

:: التحقق من وجود NSSM
set NSSM_PATH=
if exist "nssm.exe" (
    set NSSM_PATH=%CURRENT_DIR%nssm.exe
) else if exist "nssm\nssm.exe" (
    set NSSM_PATH=%CURRENT_DIR%nssm\nssm.exe
) else (
    echo تحذير: NSSM غير موجود
    echo.
    echo يرجى:
    echo 1. تحميل NSSM من: https://nssm.cc/download
    echo 2. استخراج nssm.exe في نفس مجلد هذا الملف
    echo 3. أو وضع nssm.exe في مجلد nssm\
    echo.
    echo أو يمكنك استخدام Task Scheduler يدوياً (راجع INSTALL_AS_SERVICE.md)
    pause
    exit /b 1
)

echo NSSM موجود في: %NSSM_PATH%
echo.

:: اسم الخدمة
set SERVICE_NAME=DeviceMonitorService
echo اسم الخدمة: %SERVICE_NAME%
echo.

:: إيقاف الخدمة إذا كانت موجودة
echo التحقق من وجود الخدمة...
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo الخدمة موجودة - جاري إيقافها...
    net stop %SERVICE_NAME%
    timeout /t 2 /nobreak >nul
)

:: حذف الخدمة القديمة إذا كانت موجودة
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo حذف الخدمة القديمة...
    %NSSM_PATH% remove %SERVICE_NAME% confirm
    timeout /t 2 /nobreak >nul
)

:: تثبيت الخدمة
echo.
echo تثبيت الخدمة...
%NSSM_PATH% install %SERVICE_NAME% "%PYTHON_PATH%" "%CURRENT_DIR%device_client.py"

:: تكوين الخدمة
echo.
echo تكوين الخدمة...
%NSSM_PATH% set %SERVICE_NAME% AppDirectory "%CURRENT_DIR%"
%NSSM_PATH% set %SERVICE_NAME% DisplayName "Device Monitor Client Service"
%NSSM_PATH% set %SERVICE_NAME% Description "خدمة مراقبة الأجهزة - تراقب حالة الجهاز وترسل البيانات إلى السيرفر"
%NSSM_PATH% set %SERVICE_NAME% Start SERVICE_AUTO_START
%NSSM_PATH% set %SERVICE_NAME% AppStdout "%CURRENT_DIR%service_log.txt"
%NSSM_PATH% set %SERVICE_NAME% AppStderr "%CURRENT_DIR%service_error.txt"
%NSSM_PATH% set %SERVICE_NAME% AppRotateFiles 1
%NSSM_PATH% set %SERVICE_NAME% AppRotateOnline 1
%NSSM_PATH% set %SERVICE_NAME% AppRotateSeconds 86400
%NSSM_PATH% set %SERVICE_NAME% AppRotateBytes 10485760

:: تعيين الخدمة لتشغيل كـ Local System (أعلى صلاحيات)
echo.
echo تعيين الخدمة لتشغيل كـ Local System (صلاحيات المسؤول)...
%NSSM_PATH% set %SERVICE_NAME% ObjectName LocalSystem

:: بدء الخدمة
echo.
echo بدء الخدمة...
net start %SERVICE_NAME%

:: التحقق من حالة الخدمة
echo.
echo التحقق من حالة الخدمة...
timeout /t 2 /nobreak >nul
sc query %SERVICE_NAME%

echo.
echo ============================================
echo اكتمل التثبيت!
echo ============================================
echo.
echo الخدمة: %SERVICE_NAME%
echo الحالة: 
sc query %SERVICE_NAME% | findstr "STATE"
echo.
echo لإدارة الخدمة:
echo   - إيقاف: net stop %SERVICE_NAME%
echo   - بدء: net start %SERVICE_NAME%
echo   - إلغاء التثبيت: %NSSM_PATH% remove %SERVICE_NAME% confirm
echo.
echo السجلات:
echo   - stdout: %CURRENT_DIR%service_log.txt
echo   - stderr: %CURRENT_DIR%service_error.txt
echo.
pause

