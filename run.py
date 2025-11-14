#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مراقبة الأجهزة - Device Monitoring System
ملف التشغيل السريع

استخدام:
    python run.py

أو:
    python app.py
"""

import os
import sys
import subprocess

def check_python_version():
    """التحقق من إصدار Python"""
    if sys.version_info < (3, 7):
        print("❌ خطأ: يتطلب Python 3.7 أو أحدث")
        print(f"الإصدار الحالي: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - جيد")
    return True

def check_requirements():
    """التحقق من وجود ملف المتطلبات"""
    if not os.path.exists('requirements.txt'):
        print("❌ خطأ: ملف requirements.txt غير موجود")
        return False
    print("✅ ملف requirements.txt موجود")
    return True

def install_requirements():
    """تثبيت المتطلبات"""
    try:
        print("📦 تثبيت المتطلبات...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ تم تثبيت المتطلبات بنجاح")
        return True
    except subprocess.CalledProcessError:
        print("❌ خطأ في تثبيت المتطلبات")
        return False

def run_app():
    """تشغيل التطبيق"""
    try:
        print("🚀 تشغيل التطبيق...")
        print("🌐 افتح المتصفح وانتقل إلى: http://localhost:5000")
        print("\n⏹️  لإيقاف التطبيق: اضغط Ctrl+C")
        print("-" * 50)
        
        # تشغيل التطبيق
        subprocess.run([sys.executable, 'app.py'])
        
    except KeyboardInterrupt:
        print("\n\n👋 تم إيقاف التطبيق")
    except Exception as e:
        print(f"❌ خطأ في تشغيل التطبيق: {e}")

def main():
    """الدالة الرئيسية"""
    print("=" * 50)
    print("🖥️  نظام مراقبة الأجهزة")
    print("=" * 50)
    
    # التحقق من Python
    if not check_python_version():
        return
    
    # التحقق من المتطلبات
    if not check_requirements():
        return
    
    # تثبيت المتطلبات
    if not install_requirements():
        return
    
    # تشغيل التطبيق
    run_app()

if __name__ == '__main__':
    main()