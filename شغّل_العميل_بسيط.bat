@echo off
chcp 65001 >nul
:: ============================================
:: النسخة البسيطة جداً - فقط 3 أسئلة!
:: ============================================

title مراقبة الأجهزة - العميل

:: فحص سريع
python --version >nul 2>&1 || (echo ❌ Python غير مثبت! && pause && exit /b 1)
if not exist "device_client.py" (echo ❌ device_client.py غير موجود! && pause && exit /b 1)

cls
echo.
echo ════════════════════════════════════════════════════════
echo           إعداد وتشغيل عميل المراقبة
echo ════════════════════════════════════════════════════════
echo.

:: إذا كان device_config.json موجود، استخدمه مباشرة
if exist "device_config.json" (
    echo ✓ إعدادات موجودة - جاري التشغيل...
    echo.
    goto :run
)

:: 3 أسئلة فقط
set /p SERVER_URL="1. عنوان السيرفر (Enter للافتراضي): "
if "%SERVER_URL%"=="" set SERVER_URL=https://comment-tony-gifts-fabric.trycloudflare.com

set /p DEVICE_TOKEN="2. Device Token (Enter للتسجيل التلقائي): "

echo.
echo 3. جاري الحفظ والتشغيل...
echo.

:: حفظ الإعدادات بشكل صحيح
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
:: تشغيل بصلاحيات المسؤول تلقائياً
net session >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ صلاحيات المسؤول: مفعّلة
    echo.
    echo ════════════════════════════════════════════════════════
    echo    العميل يعمل - لا تغلق هذه النافذة!
    echo ════════════════════════════════════════════════════════
    echo.
    python device_client.py
) else (
    echo ⚠️ طلب صلاحيات المسؤول...
    powershell -Command "Start-Process python -ArgumentList 'device_client.py' -Verb RunAs -WorkingDirectory '%CD%'"
    echo.
    echo ✓ تم التشغيل في نافذة جديدة بصلاحيات المسؤول
    echo.
)

pause
