#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
صفحة الإعدادات والضبط
إعدادات مختلفة حسب الدور (admin, technician, manager, user)
"""

from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for
from models.database import query_db, execute_db
from routes.auth import require_login, require_role
from datetime import datetime
import hashlib

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('')
@require_login
def settings_page():
    """صفحة الإعدادات الرئيسية - تعيد التوجيه حسب الدور"""
    role = session.get('role', 'user')
    
    if role in ['admin', 'technician', 'manager']:
        return redirect(url_for('settings.admin_settings'))
    else:
        return redirect(url_for('settings.user_settings'))

@settings_bp.route('/admin')
@require_login
@require_role('admin', 'technician', 'manager')
def admin_settings():
    """صفحة إعدادات الأدمن والمديرين"""
    try:
        user_id = session.get('user_id')
        user = query_db('SELECT * FROM users WHERE id = ?', (user_id,), one=True)
        
        # الحصول على إعدادات النظام
        system_settings_dict = {}
        try:
            settings_list = query_db('SELECT * FROM settings WHERE setting_key IN (?, ?, ?, ?)', 
                                    ('auto_refresh_interval', 'alert_threshold_cpu', 'alert_threshold_ram', 'alert_threshold_temp'))
            for setting in settings_list:
                system_settings_dict[setting['setting_key']] = setting['setting_value']
        except:
            pass
        
        # القيم الافتراضية
        system_settings_dict.setdefault('auto_refresh_interval', '5')
        system_settings_dict.setdefault('alert_threshold_cpu', '90')
        system_settings_dict.setdefault('alert_threshold_ram', '90')
        system_settings_dict.setdefault('alert_threshold_temp', '80')
        
        return render_template('settings/admin_settings.html', user=user, system_settings=system_settings_dict)
    except Exception as e:
        flash(f'خطأ في تحميل الإعدادات: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@settings_bp.route('/user')
@require_login
def user_settings():
    """صفحة إعدادات المستخدم العادي"""
    try:
        user_id = session.get('user_id')
        user = query_db('SELECT * FROM users WHERE id = ?', (user_id,), one=True)
        
        # الحصول على إعدادات الإشعارات للمستخدم
        notification_settings = {
            'email_notifications': True,
            'critical_alerts': True,
            'warning_alerts': False
        }
        
        try:
            settings_list = query_db('SELECT * FROM settings WHERE setting_key LIKE ?', (f'user_{user_id}_%',))
            for setting in settings_list:
                key = setting['setting_key'].replace(f'user_{user_id}_', '')
                notification_settings[key] = setting['setting_value'] == '1'
        except:
            pass
        
        return render_template('settings/user_settings.html', user=user, notification_settings=notification_settings)
    except Exception as e:
        flash(f'خطأ في تحميل الإعدادات: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@settings_bp.route('/api/profile', methods=['POST'])
@require_login
def api_update_profile():
    """API لتحديث الملف الشخصي"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        # التحقق من البيانات المطلوبة
        if not data.get('full_name') or not data.get('email'):
            return jsonify({'error': 'الاسم الكامل والبريد الإلكتروني مطلوبان'}), 400
        
        # تحديث الملف الشخصي
        execute_db('''
            UPDATE users 
            SET full_name = ?, email = ?, phone = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('full_name'),
            data.get('email'),
            data.get('phone'),
            user_id
        ))
        
        # تحديث session
        session['full_name'] = data.get('full_name')
        session['email'] = data.get('email')
        
        return jsonify({'success': True, 'message': 'تم تحديث الملف الشخصي بنجاح'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/password', methods=['POST'])
@require_login
def api_change_password():
    """API لتغيير كلمة المرور"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        # التحقق من البيانات
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            return jsonify({'error': 'جميع الحقول مطلوبة'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': 'كلمة المرور الجديدة غير متطابقة'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'}), 400
        
        # التحقق من كلمة المرور القديمة
        user = query_db('SELECT * FROM users WHERE id = ?', (user_id,), one=True)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # تحويل كلمة المرور إلى hash
        old_password_hash = hashlib.sha256(old_password.encode()).hexdigest()
        if user['password'] != old_password_hash:
            return jsonify({'error': 'كلمة المرور القديمة غير صحيحة'}), 400
        
        # تحديث كلمة المرور
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        execute_db('''
            UPDATE users 
            SET password = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_password_hash, user_id))
        
        return jsonify({'success': True, 'message': 'تم تغيير كلمة المرور بنجاح'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/notifications', methods=['POST'])
@require_login
def api_update_notifications():
    """API لتحديث إعدادات الإشعارات"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        # تحديث إعدادات الإشعارات للمستخدم
        # استخدام setting_key مع user_id للتمييز بين المستخدمين
        notification_settings = {
            f'user_{user_id}_email_notifications': '1' if data.get('email_notifications') else '0',
            f'user_{user_id}_critical_alerts': '1' if data.get('critical_alerts') else '0',
            f'user_{user_id}_warning_alerts': '1' if data.get('warning_alerts') else '0'
        }
        
        for key, value in notification_settings.items():
            # التحقق من وجود الإعداد
            existing = query_db('SELECT * FROM settings WHERE setting_key = ?', (key,), one=True)
            if existing:
                # تحديث الإعداد
                execute_db('''
                    UPDATE settings 
                    SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE setting_key = ?
                ''', (value, key))
            else:
                # إدراج إعداد جديد
                execute_db('''
                    INSERT INTO settings (setting_key, setting_value, description, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (key, value, f'إعداد إشعارات المستخدم {user_id}'))
        
        return jsonify({'success': True, 'message': 'تم تحديث إعدادات الإشعارات بنجاح'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/system', methods=['POST'])
@require_login
@require_role('admin')
def api_update_system_settings():
    """API لتحديث إعدادات النظام (للأدمن فقط)"""
    try:
        data = request.json
        
        # تحديث أو إدراج إعدادات النظام
        settings_to_update = {
            'auto_refresh_interval': data.get('auto_refresh_interval', '5'),
            'alert_threshold_cpu': data.get('alert_threshold_cpu', '90'),
            'alert_threshold_ram': data.get('alert_threshold_ram', '90'),
            'alert_threshold_temp': data.get('alert_threshold_temp', '80')
        }
        
        for key, value in settings_to_update.items():
            # التحقق من وجود الإعداد
            existing = query_db('SELECT * FROM settings WHERE setting_key = ?', (key,), one=True)
            if existing:
                # تحديث الإعداد
                execute_db('''
                    UPDATE settings 
                    SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE setting_key = ?
                ''', (str(value), key))
            else:
                # إدراج إعداد جديد
                execute_db('''
                    INSERT INTO settings (setting_key, setting_value, description, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (key, str(value), f'إعداد {key}'))
        
        return jsonify({'success': True, 'message': 'تم تحديث إعدادات النظام بنجاح'})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

