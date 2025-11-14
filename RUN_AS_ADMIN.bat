@echo off
:: ملف batch لتشغيل device_client.py بصلاحيات المسؤول على Windows
:: استخدم هذا الملف لتشغيل device_client.py بصلاحيات المسؤول
:: مهم: يجب تشغيل هذا الملف بصلاحيات المسؤول (Run as administrator)

:: التحقق من الصلاحيات
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ============================================
    echo خطأ: لا توجد صلاحيات مسؤول!
    echo ============================================
    echo.
    echo يرجى تشغيل هذا الملف بصلاحيات المسؤول:
    echo 1. انقر بزر الماوس الأيمن على هذا الملف
    echo 2. اختر "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo ============================================
echo تشغيل device_client.py بصلاحيات المسؤول
echo ============================================
echo.

:: التحقق من وجود Python
python --version >nul 2>&1
if errorlevel 1 (
    echo خطأ: Python غير مثبت أو غير موجود في PATH
    echo.
    echo يرجى تثبيت Python أو إضافته إلى PATH
    pause
    exit /b 1
)

:: عرض إصدار Python
echo Python مثبت:
python --version
echo.

:: التحقق من وجود device_client.py
if not exist "device_client.py" (
    echo تحذير: ملف device_client.py غير موجود في المجلد الحالي
    echo المجلد الحالي: %CD%
    echo.
    echo يرجى التأكد من أن device_client.py موجود في نفس مجلد هذا الملف
    pause
    exit /b 1
)

:: تشغيل device_client.py
echo جاري تشغيل device_client.py...
echo.
echo ============================================
echo.

python device_client.py

:: إذا توقف البرنامج، انتظر
echo.
echo ============================================
echo توقف device_client.py
echo ============================================
pause

