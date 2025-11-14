#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إضافة عمود user_id إلى جدول devices لربط الأجهزة بالمستخدمين
"""

import sqlite3
import os

DATABASE_NAME = 'device_monitoring.db'

def add_user_id_column():
    """إضافة عمود user_id إلى جدول devices"""
    if not os.path.exists(DATABASE_NAME):
        print("قاعدة البيانات غير موجودة!")
        return
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # التحقق من وجود العمود
        cursor.execute("PRAGMA table_info(devices)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("إضافة عمود user_id إلى جدول devices...")
            cursor.execute('''
                ALTER TABLE devices 
                ADD COLUMN user_id INTEGER
            ''')
            
            # إضافة فهرس
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_devices_user_id 
                ON devices(user_id)
            ''')
            
            conn.commit()
            print("[+] تم إضافة عمود user_id بنجاح!")
        else:
            print("عمود user_id موجود بالفعل")
        
        # عرض الأجهزة الحالية
        cursor.execute('SELECT id, name, user_id FROM devices')
        devices = cursor.fetchall()
        if devices:
            print(f"\nالأجهزة الموجودة ({len(devices)}):")
            for device in devices:
                user_status = f"User ID: {device[2]}" if device[2] else "بدون مستخدم"
                print(f"  - {device[1]} (ID: {device[0]}) - {user_status}")
        else:
            print("\nلا توجد أجهزة في قاعدة البيانات")
        
    except Exception as e:
        print(f"خطأ: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_user_id_column()

