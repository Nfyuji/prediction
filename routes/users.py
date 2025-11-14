#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إدارة المستخدمين
معالجة عمليات إدارة المستخدمين (للأدمن فقط)
"""

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from models.database import get_db, query_db, execute_db
from routes.auth import require_login, require_role
import hashlib

users_bp = Blueprint('users', __name__, url_prefix='/users')

def hash_password(password):
    """تشفير كلمة المرور باستخدام SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

@users_bp.route('')
@require_login
@require_role('admin', 'manager')
def users_list():
    """صفحة قائمة المستخدمين"""
    return render_template('users.html')

@users_bp.route('/api')
@require_login
@require_role('admin', 'manager')
def api_get_users():
    """API للحصول على جميع المستخدمين"""
    try:
        users = query_db('''
            SELECT id, username, full_name, email, phone, role, 
                   is_active, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        ''')
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'phone': user['phone'],
                'role': user['role'],
                'is_active': bool(user['is_active']),
                'created_at': user['created_at'],
                'last_login': user['last_login']
            })
        
        return jsonify(users_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api', methods=['POST'])
@require_login
@require_role('admin')
def api_create_user():
    """API لإنشاء مستخدم جديد"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        full_name = data.get('full_name', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        role = data.get('role', 'user')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'اسم المستخدم وكلمة المرور مطلوبان'}), 400
        
        # التحقق من وجود المستخدم
        existing_user = query_db(
            'SELECT id FROM users WHERE username = ?',
            (username,),
            one=True
        )
        
        if existing_user:
            return jsonify({'success': False, 'message': 'اسم المستخدم موجود بالفعل'}), 400
        
        # إنشاء المستخدم
        execute_db('''
            INSERT INTO users (username, password, full_name, email, phone, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (
            username,
            hash_password(password),
            full_name,
            email,
            phone,
            role
        ))
        
        # تسجيل النشاط
        get_db().execute(
            'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
            (session.get('user_id'), 'create_user', f'إنشاء مستخدم جديد: {username}', request.remote_addr)
        )
        get_db().commit()
        
        return jsonify({'success': True, 'message': 'تم إنشاء المستخدم بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@users_bp.route('/api/<int:user_id>', methods=['PUT'])
@require_login
@require_role('admin')
def api_update_user(user_id):
    """API لتحديث مستخدم"""
    try:
        data = request.json
        full_name = data.get('full_name')
        email = data.get('email')
        phone = data.get('phone')
        role = data.get('role')
        is_active = data.get('is_active')
        
        # تحديث البيانات
        update_fields = []
        params = []
        
        if full_name is not None:
            update_fields.append('full_name = ?')
            params.append(full_name)
        
        if email is not None:
            update_fields.append('email = ?')
            params.append(email)
        
        if phone is not None:
            update_fields.append('phone = ?')
            params.append(phone)
        
        if role is not None:
            update_fields.append('role = ?')
            params.append(role)
        
        if is_active is not None:
            update_fields.append('is_active = ?')
            params.append(1 if is_active else 0)
        
        if not update_fields:
            return jsonify({'success': False, 'message': 'لا توجد بيانات للتحديث'}), 400
        
        params.append(user_id)
        
        execute_db(f'''
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', tuple(params))
        
        # تسجيل النشاط
        get_db().execute(
            'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
            (session.get('user_id'), 'update_user', f'تحديث مستخدم: {user_id}', request.remote_addr)
        )
        get_db().commit()
        
        return jsonify({'success': True, 'message': 'تم تحديث المستخدم بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@users_bp.route('/api/<int:user_id>/password', methods=['PUT'])
@require_login
@require_role('admin')
def api_change_password(user_id):
    """API لتغيير كلمة مرور مستخدم"""
    try:
        data = request.json
        new_password = data.get('new_password')
        
        if not new_password or len(new_password) < 6:
            return jsonify({'success': False, 'message': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'}), 400
        
        execute_db('''
            UPDATE users 
            SET password = ?
            WHERE id = ?
        ''', (hash_password(new_password), user_id))
        
        # تسجيل النشاط
        get_db().execute(
            'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
            (session.get('user_id'), 'change_password', f'تغيير كلمة مرور مستخدم: {user_id}', request.remote_addr)
        )
        get_db().commit()
        
        return jsonify({'success': True, 'message': 'تم تغيير كلمة المرور بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@users_bp.route('/api/<int:user_id>', methods=['DELETE'])
@require_login
@require_role('admin')
def api_delete_user(user_id):
    """API لحذف مستخدم"""
    try:
        # منع حذف نفسك
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'message': 'لا يمكنك حذف حسابك الخاص'}), 400
        
        # التحقق من وجود المستخدم
        user = query_db('SELECT username FROM users WHERE id = ?', (user_id,), one=True)
        if not user:
            return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404
        
        # حذف المستخدم
        execute_db('DELETE FROM users WHERE id = ?', (user_id,))
        
        # تسجيل النشاط
        get_db().execute(
            'INSERT INTO activity_log (user_id, action, description, ip_address) VALUES (?, ?, ?, ?)',
            (session.get('user_id'), 'delete_user', f'حذف مستخدم: {user["username"]}', request.remote_addr)
        )
        get_db().commit()
        
        return jsonify({'success': True, 'message': 'تم حذف المستخدم بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

