@echo off
chcp 65001 >nul
:: ============================================
:: ملف تشغيل العميل - بسيط وسهل
:: فقط أدخل السيرفر و Token والباقي تلقائي!
:: ============================================

title نظام مراقبة الأجهزة - العميل

:: التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ خطأ: Python غير مثبت!
    echo.
    echo يرجى تثبيت Python من: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: التحقق من device_client.py
if not exist "device_client.py" (
    echo.
    echo ❌ خطأ: device_client.py غير موجود!
    echo.
    echo يرجى التأكد من وجود device_client.py في نفس المجلد
    echo.
    pause
    exit /b 1
)

cls
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║     نظام مراقبة الأجهزة - إعداد وتشغيل العميل         ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

:: إذا كان device_config.json موجود، استخدمه
if exist "device_config.json" (
    echo ✓ تم العثور على إعدادات محفوظة
    echo.
    echo محتوى device_config.json:
    type device_config.json
    echo.
    set /p USE_EXISTING="هل تريد استخدام هذه الإعدادات؟ (y/n): "
    if /i "%USE_EXISTING%"=="y" (
        goto :run_client
    )
    echo.
)

:: طلب معلومات السيرفر
echo ──────────────────────────────────────────────────────────
echo الخطوة 1: إدخال عنوان السيرفر
echo ──────────────────────────────────────────────────────────
echo.
echo أمثلة:
echo   - https://comment-tony-gifts-fabric.trycloudflare.com
echo   - http://localhost:5000
echo.
set /p SERVER_URL="أدخل عنوان السيرفر: "
if "%SERVER_URL%"=="" (
    echo.
    echo ⚠️ لم يتم إدخال عنوان السيرفر
    set SERVER_URL=https://comment-tony-gifts-fabric.trycloudflare.com
    echo استخدام العنوان الافتراضي: %SERVER_URL%
)
echo.

:: طلب Device Token
echo ──────────────────────────────────────────────────────────
echo الخطوة 2: إدخال Device Token
echo ──────────────────────────────────────────────────────────
echo.
echo ملاحظة: يمكنك الحصول على Token من:
echo   - صفحة "أجهزتي" في السيرفر
echo   - أو اتركه فارغاً للتسجيل التلقائي
echo.
set /p DEVICE_TOKEN="أدخل Device Token (أو اتركه فارغاً): "
echo.

:: إنشاء device_config.json
echo ──────────────────────────────────────────────────────────
echo الخطوة 3: حفظ الإعدادات
echo ──────────────────────────────────────────────────────────
echo.

if "%DEVICE_TOKEN%"=="" (
    echo إنشاء device_config.json بدون Token (تسجيل تلقائي)...
    (
        echo {
        echo   "server_url": "%SERVER_URL%"
        echo }
    ) > device_config.json
    echo ✓ تم الحفظ بنجاح
) else (
    echo إنشاء device_config.json مع Token...
    (
        echo {
        echo   "device_token": "%DEVICE_TOKEN%",
        echo   "server_url": "%SERVER_URL%"
        echo }
    ) > device_config.json
    echo ✓ تم الحفظ بنجاح
)
echo.

:run_client
:: التحقق من الصلاحيات وتشغيل بصلاحيات المسؤول
echo ──────────────────────────────────────────────────────────
echo الخطوة 4: التحقق من الصلاحيات وتشغيل العميل
echo ──────────────────────────────────────────────────────────
echo.

net session >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ صلاحيات المسؤول مفعّلة
    echo.
    echo جاري تشغيل العميل...
    echo.
    echo ═══════════════════════════════════════════════════════════
    echo    العميل يعمل الآن - لا تغلق هذه النافذة!
    echo ═══════════════════════════════════════════════════════════
    echo.
    python device_client.py
) else (
    echo ⚠️ لا توجد صلاحيات مسؤول
    echo.
    echo جاري طلب الصلاحيات تلقائياً...
    echo (قد يطلب Windows تأكيد - اضغط "نعم")
    echo.
    timeout /t 2 /nobreak >nul
    
    :: محاولة تشغيل بصلاحيات المسؤول تلقائياً
    powershell -Command "Start-Process python -ArgumentList 'device_client.py' -Verb RunAs -WorkingDirectory '%CD%'"
    
    if errorlevel 1 (
        echo.
        echo ❌ فشل الحصول على الصلاحيات
        echo.
        echo يمكنك:
        echo   1. انقر بزر الماوس الأيمن على هذا الملف
        echo   2. اختر "Run as administrator"
        echo   3. أو شغّل device_client.py يدوياً
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo ✓ تم تشغيل العميل بصلاحيات المسؤول في نافذة جديدة
    echo.
    echo يمكنك إغلاق هذه النافذة الآن
    echo.
)

pause

