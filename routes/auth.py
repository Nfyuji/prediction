#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام المصادقة
معالجة تسجيل الدخول والخروج
"""

from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from models.database import get_db, query_db, execute_db
from datetime import datetime
import hashlib

auth_bp = Blueprint('auth', __name__)

def hash_password(password):
    """تشفير كلمة المرور باستخدام SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'يرجى إدخال اسم المستخدم وكلمة المرور'})
        
        # البحث عن المستخدم
        user = query_db(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, hash_password(password)),
            one=True
        )
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            # تحديث آخر تسجيل دخول
            get_db().execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user['id'],)
            )
            get_db().commit()
            
            # تسجيل النشاط
            get_db().execute(
                'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
                (user['id'], 'login', 'تسجيل الدخول', request.remote_addr)
            )
            get_db().commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user['full_name'],
                        'role': user['role']
                    }
                })
            else:
                # إعادة التوجيه حسب الدور
                user_role = user['role']
                if user_role == 'admin':
                    return redirect(url_for('dashboard.admin_dashboard'))
                elif user_role in ['technician', 'manager']:
                    return redirect(url_for('dashboard.admin_dashboard'))
                else:
                    return redirect(url_for('dashboard.user_dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'})
            else:
                flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    # GET request - عرض صفحة تسجيل الدخول
    return render_template('login.html')

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API لتسجيل الدخول"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'يرجى إدخال اسم المستخدم وكلمة المرور'})
    
    user = query_db(
        'SELECT * FROM users WHERE username = ? AND password = ?',
        (username, hash_password(password)),
        one=True
    )
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['full_name'] = user['full_name']
        
        # تحديث آخر تسجيل دخول
        get_db().execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
            (user['id'],)
        )
        get_db().commit()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role': user['role']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'بيانات الدخول غير صحيحة'})

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """تسجيل الخروج"""
    if 'user_id' in session:
        # تسجيل النشاط
        get_db().execute(
            'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
            (session['user_id'], 'logout', 'تسجيل الخروج', request.remote_addr)
        )
        get_db().commit()
    
    session.clear()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'تم تسجيل الخروج بنجاح'})
    else:
        return redirect(url_for('auth.login'))

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API لتسجيل الخروج"""
    if 'user_id' in session:
        get_db().execute(
            'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
            (session['user_id'], 'logout', 'تسجيل الخروج', request.remote_addr)
        )
        get_db().commit()
    
    session.clear()
    return jsonify({'success': True, 'message': 'تم تسجيل الخروج بنجاح'})

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """صفحة إنشاء حساب جديد"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # التحقق من البيانات
        if not username or not password or not confirm_password:
            flash('يرجى ملء جميع الحقول المطلوبة', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
            return render_template('register.html')
        
        # التحقق من وجود المستخدم
        existing_user = query_db(
            'SELECT id FROM users WHERE username = ?',
            (username,),
            one=True
        )
        
        if existing_user:
            flash('اسم المستخدم موجود بالفعل', 'error')
            return render_template('register.html')
        
        # إنشاء المستخدم الجديد
        try:
            user_id = execute_db('''
                INSERT INTO users (username, password, full_name, email, phone, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                username,
                hash_password(password),
                full_name or '',
                email or '',
                phone or '',
                'user'  # دور افتراضي
            ))
            
            # تسجيل الدخول التلقائي بعد إنشاء الحساب
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = 'user'
            
            # إنشاء جهاز تلقائياً وربطه بالمستخدم الجديد
            try:
                import secrets
                device_token = secrets.token_urlsafe(32)
                device_name = full_name or username or f"جهاز {username}"
                
                device_id = execute_db('''
                    INSERT INTO devices 
                    (name, device_type, location, ip_address, mac_address, operating_system, processor, ram_total, disk_total, status, device_token, is_active, user_id, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    device_name,
                    'computer',
                    'غير محدد',
                    None,  # سيتم تحديثه تلقائياً من device_client.py
                    None,  # سيتم تحديثه تلقائياً من device_client.py
                    None,
                    None,
                    None,
                    None,
                    'healthy',
                    device_token,
                    1,
                    user_id,  # ربط الجهاز بالمستخدم الجديد
                    datetime.now()
                ))
                
                # حفظ device_token في session لعرضه في صفحة "أجهزتي"
                session['new_device_token'] = device_token
                session['new_device_id'] = device_id
                
                flash('تم إنشاء الحساب بنجاح! تم ربط جهازك تلقائياً', 'success')
            except Exception as device_error:
                # إذا فشل إنشاء الجهاز، لا نوقف عملية التسجيل
                flash('تم إنشاء الحساب بنجاح! يمكنك ربط جهازك من صفحة "أجهزتي"', 'success')
            
            # توجيه إلى صفحة "أجهزتي" لعرض Token
            return redirect(url_for('my_devices.my_devices'))
        except Exception as e:
            flash('حدث خطأ أثناء إنشاء الحساب. يرجى المحاولة مرة أخرى', 'error')
            return render_template('register.html')
    
    # GET request - عرض صفحة التسجيل
    return render_template('register.html')

def require_login(f):
    """ديكوراتور للتحقق من تسجيل الدخول"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
            else:
                return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    """ديكوراتور للتحقق من الصلاحيات"""
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                if request.is_json:
                    return jsonify({'error': 'ليس لديك صلاحية للوصول إلى هذه الصفحة'}), 403
                else:
                    from flask import flash
                    flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'error')
                    return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

