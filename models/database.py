#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نموذج قاعدة البيانات
إدارة الاتصال بقاعدة البيانات وعملياتها الأساسية
"""

import sqlite3
from flask import g
from contextlib import closing

DATABASE = 'device_monitoring.db'

def get_db():
    """الحصول على اتصال قاعدة البيانات"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        # تفعيل المفاتيح الأجنبية
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

def init_db():
    """تهيئة قاعدة البيانات"""
    db = get_db()
    # التحقق من وجود الجداول
    try:
        db.execute('SELECT COUNT(*) FROM users').fetchone()
        print("قاعدة البيانات جاهزة!")
    except sqlite3.OperationalError:
        print("خطأ: قاعدة البيانات غير موجودة. يرجى تشغيل init_database.py أولاً")

def close_db(e=None):
    """إغلاق اتصال قاعدة البيانات"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """تنفيذ استعلام قاعدة البيانات"""
    db = get_db()
    cursor = db.execute(query, args)
    result = cursor.fetchall()
    # لا نستخدم commit هنا لأنها للقراءة فقط
    return (result[0] if result else None) if one else result

def execute_db(query, args=()):
    """تنفيذ أمر قاعدة البيانات"""
    db = get_db()
    cursor = db.execute(query, args)
    db.commit()
    return cursor.lastrowid

