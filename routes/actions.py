#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام الإجراءات على الأجهزة
تنفيذ إجراءات مثل إعادة التشغيل، الإيقاف، وغيرها
"""

from flask import Blueprint, request, jsonify, session
from models.database import query_db, execute_db
from routes.auth import require_login, require_role
from datetime import datetime
import traceback

actions_bp = Blueprint('actions', __name__, url_prefix='/actions')

@actions_bp.route('/api/device/<int:device_id>/execute', methods=['POST'])
@require_login
@require_role('admin', 'technician', 'manager')
def execute_device_action(device_id):
    """تنفيذ إجراء على جهاز معين (للأدمن والفنيين فقط)"""
    try:
        user_id = session.get('user_id')
        role = session.get('role')
        
        # التحقق من صلاحيات المستخدم
        if role not in ['admin', 'technician', 'manager']:
            return jsonify({'error': 'ليس لديك صلاحية لتنفيذ الإجراءات'}), 403
        
        # التحقق من وجود الجهاز
        device = query_db('SELECT * FROM devices WHERE id = ? AND is_active = 1', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # الحصول على نوع الإجراء
        data = request.json or {}
        action_type = data.get('action_type')
        action_description = data.get('action_description', '')
        
        # قائمة الإجراءات المسموحة
        allowed_actions = ['restart', 'shutdown', 'reboot', 'sleep', 'hibernate', 'update', 'scan', 'backup', 'emergency_alert']
        
        if not action_type or action_type not in allowed_actions:
            return jsonify({'error': f'نوع الإجراء غير صحيح. الإجراءات المسموحة: {", ".join(allowed_actions)}'}), 400
        
        # إنشاء وصف الإجراء
        action_descriptions = {
            'restart': 'إعادة تشغيل الجهاز',
            'shutdown': 'إيقاف تشغيل الجهاز',
            'reboot': 'إعادة تشغيل الجهاز',
            'sleep': 'وضع السكون',
            'hibernate': 'وضع السبات',
            'update': 'تحديث النظام',
            'scan': 'فحص الجهاز',
            'backup': 'نسخ احتياطي',
            'emergency_alert': 'تنبيه طارئ'
        }
        
        # للحصول على رسالة التنبيه الطارئ
        alert_message = data.get('alert_message', '')
        if action_type == 'emergency_alert':
            if not alert_message:
                alert_message = 'تنبيه طارئ من الإدارة'
            # للتنبيه الطارئ، نستخدم الرسالة مباشرة كوصف
            action_description = f'تنبيه طارئ: {alert_message}'
            
            # حفظ التنبيه الطارئ في جدول alerts
            try:
                execute_db('''
                    INSERT INTO alerts 
                    (device_id, alert_type, severity, message, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    device_id,
                    'emergency_alert',
                    'critical',  # التنبيهات الطارئة دائماً حرجة
                    f'{device["name"]}: {alert_message}',
                    'active',
                    datetime.now()
                ))
            except Exception as alert_error:
                # إذا فشل حفظ التنبيه، نتابع مع الإجراء
                print(f'خطأ في حفظ التنبيه: {alert_error}')
        elif not action_description:
            action_description = action_descriptions.get(action_type, f'إجراء {action_type}')
        
        # إنشاء سجل الإجراء
        # نحتاج إلى حفظ alert_message كجزء من action_description أو في حقل منفصل
        # سنستخدم action_description لحفظ الرسالة
        action_id = execute_db('''
            INSERT INTO system_actions 
            (device_id, action_type, action_description, performed_by, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            device_id,
            action_type,
            action_description,  # يحتوي على الرسالة للتنبيه الطارئ
            user_id,
            'pending',
            datetime.now()
        ))
        
        # تسجيل النشاط
        try:
            execute_db('''
                INSERT INTO activity_log (user_id, action, description, ip_address)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                'device_action',
                f'تنفيذ إجراء {action_description} على الجهاز {device["name"]}',
                request.remote_addr
            ))
        except:
            pass
        
        return jsonify({
            'success': True,
            'action_id': action_id,
            'message': f'تم إنشاء الإجراء "{action_description}" بنجاح. سيتم تنفيذه عند اتصال الجهاز بالخادم.',
            'action_type': action_type,
            'status': 'pending'
        })
    except Exception as e:
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

@actions_bp.route('/api/device/<int:device_id>/pending', methods=['GET'])
@require_login
def get_pending_actions(device_id):
    """الحصول على الإجراءات المعلقة لجهاز معين"""
    try:
        # التحقق من وجود الجهاز
        device = query_db('SELECT * FROM devices WHERE id = ? AND is_active = 1', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # الحصول على الإجراءات المعلقة
        pending_actions = query_db('''
            SELECT sa.*, u.username, u.full_name
            FROM system_actions sa
            LEFT JOIN users u ON sa.performed_by = u.id
            WHERE sa.device_id = ? AND sa.status = 'pending'
            ORDER BY sa.created_at DESC
        ''', (device_id,))
        
        actions_list = []
        for action in pending_actions:
            actions_list.append({
                'id': action['id'],
                'action_type': action['action_type'],
                'action_description': action['action_description'],
                'performed_by': action['username'] or 'غير معروف',
                'performed_by_name': action['full_name'] or 'غير معروف',
                'status': action['status'],
                'created_at': action['created_at'],
                'completed_at': action['completed_at']
            })
        
        return jsonify(actions_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@actions_bp.route('/api/device/<int:device_id>/actions', methods=['GET'])
@require_login
def get_device_actions(device_id):
    """الحصول على جميع الإجراءات لجهاز معين"""
    try:
        user_id = session.get('user_id')
        role = session.get('role')
        
        # التحقق من وجود الجهاز
        device = query_db('SELECT * FROM devices WHERE id = ? AND is_active = 1', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # التحقق من الصلاحيات (الأدمن والفنيين فقط يمكنهم رؤية جميع الإجراءات)
        if role not in ['admin', 'technician', 'manager']:
            return jsonify({'error': 'ليس لديك صلاحية لعرض الإجراءات'}), 403
        
        # الحصول على جميع الإجراءات
        actions = query_db('''
            SELECT sa.*, u.username, u.full_name
            FROM system_actions sa
            LEFT JOIN users u ON sa.performed_by = u.id
            WHERE sa.device_id = ?
            ORDER BY sa.created_at DESC
            LIMIT 50
        ''', (device_id,))
        
        actions_list = []
        for action in actions:
            actions_list.append({
                'id': action['id'],
                'action_type': action['action_type'],
                'action_description': action['action_description'],
                'performed_by': action['username'] or 'غير معروف',
                'performed_by_name': action['full_name'] or 'غير معروف',
                'status': action['status'],
                'created_at': action['created_at'],
                'completed_at': action['completed_at']
            })
        
        return jsonify(actions_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@actions_bp.route('/api/action/<int:action_id>/status', methods=['GET'])
@require_login
def get_action_status(action_id):
    """الحصول على حالة إجراء معين"""
    try:
        action = query_db('''
            SELECT sa.*, u.username, u.full_name, d.name as device_name
            FROM system_actions sa
            LEFT JOIN users u ON sa.performed_by = u.id
            LEFT JOIN devices d ON sa.device_id = d.id
            WHERE sa.id = ?
        ''', (action_id,), one=True)
        
        if not action:
            return jsonify({'error': 'الإجراء غير موجود'}), 404
        
        return jsonify({
            'id': action['id'],
            'action_type': action['action_type'],
            'action_description': action['action_description'],
            'device_id': action['device_id'],
            'device_name': action['device_name'],
            'performed_by': action['username'] or 'غير معروف',
            'performed_by_name': action['full_name'] or 'غير معروف',
            'status': action['status'],
            'created_at': action['created_at'],
            'completed_at': action['completed_at']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@actions_bp.route('/api/action/<int:action_id>/user-action', methods=['POST'])
def report_user_action(action_id):
    """تسجيل تصرف المستخدم مع التنبيه الطارئ (يُستدعى من device_client.py) - لا يتطلب تسجيل دخول"""
    try:
        # الحصول على device_token من header
        device_token = request.headers.get('X-Device-Token')
        if not device_token:
            return jsonify({'error': 'يجب توفير device_token'}), 401
        
        # التحقق من أن الإجراء يخص هذا الجهاز
        device = query_db('SELECT * FROM devices WHERE device_token = ? AND is_active = 1', (device_token,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # الحصول على الإجراء
        action = query_db('SELECT * FROM system_actions WHERE id = ? AND device_id = ?', (action_id, device['id']), one=True)
        if not action:
            return jsonify({'error': 'الإجراء غير موجود أو لا يخص هذا الجهاز'}), 404
        
        data = request.json or {}
        action_type = data.get('action_type', 'unknown')  # 'opened', 'closed', 'auto_closed', 'esc_pressed'
        details = data.get('details', '')
        opened_at = data.get('opened_at')
        duration_seconds = data.get('duration_seconds')
        
        # حفظ معلومات تفاعل المستخدم في action_description
        user_action_info = f" | تفاعل المستخدم: {action_type}"
        if details:
            user_action_info += f" ({details})"
        if opened_at:
            user_action_info += f" | وقت الفتح: {opened_at}"
        if duration_seconds:
            user_action_info += f" | المدة: {duration_seconds:.1f} ثانية"
        
        # تحديث action_description
        new_description = action['action_description'] + user_action_info
        
        execute_db('''
            UPDATE system_actions 
            SET action_description = ?
            WHERE id = ?
        ''', (new_description, action_id))
        
        # إذا كان التنبيه الطارئ، تحديث التنبيه في جدول alerts أيضاً
        if action['action_type'] == 'emergency_alert':
            # البحث عن التنبيه المرتبط
            alert = query_db('''
                SELECT * FROM alerts 
                WHERE device_id = ? 
                AND alert_type = 'emergency_alert'
                AND message LIKE ?
                AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (device['id'], f'%{action["action_description"].split(":")[-1].strip()}%'), one=True)
            
            if alert:
                # تحديث رسالة التنبيه لتشمل معلومات تفاعل المستخدم
                alert_message = alert['message']
                if action_type == 'opened':
                    alert_message += f" [تم فتح التنبيه]"
                elif action_type == 'closed':
                    alert_message += f" [تم إغلاق التنبيه بعد {duration_seconds:.1f} ثانية]"
                elif action_type == 'auto_closed':
                    alert_message += f" [تم إغلاقه تلقائياً بعد {duration_seconds:.1f} ثانية]"
                elif action_type == 'esc_pressed':
                    alert_message += f" [تم إغلاقه بالضغط على ESC بعد {duration_seconds:.1f} ثانية]"
                
                execute_db('''
                    UPDATE alerts 
                    SET message = ?
                    WHERE id = ?
                ''', (alert_message, alert['id']))
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل تصرف المستخدم بنجاح'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@actions_bp.route('/api/pending', methods=['GET'])
def get_pending_actions_for_device():
    """الحصول على الإجراءات المعلقة لجهاز معين (يُستدعى من device_client.py) - لا يتطلب تسجيل دخول"""
    try:
        # الحصول على device_token من header
        device_token = request.headers.get('X-Device-Token')
        if not device_token:
            return jsonify({'error': 'يجب توفير device_token'}), 401
        
        # البحث عن الجهاز
        device = query_db('SELECT * FROM devices WHERE device_token = ? AND is_active = 1', (device_token,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # الحصول على الإجراءات المعلقة
        pending_actions = query_db('''
            SELECT * FROM system_actions
            WHERE device_id = ? AND status = 'pending'
            ORDER BY created_at ASC
            LIMIT 10
        ''', (device['id'],))
        
        actions_list = []
        for action in pending_actions:
            # التأكد من أن action_type موجود وليس None
            action_type = action.get('action_type')
            if not action_type:
                # محاولة الوصول مباشرة إذا كان Row object
                try:
                    action_type = action['action_type']
                except:
                    pass
            
            if not action_type:
                continue  # تخطي الإجراءات بدون نوع
            
            actions_list.append({
                'id': action['id'],
                'action_type': str(action_type),  # التأكد من أنه string
                'action_description': action.get('action_description', '') or '',
                'created_at': action['created_at']
            })
        
        return jsonify(actions_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@actions_bp.route('/api/action/<int:action_id>/complete', methods=['POST'])
def complete_action_no_auth(action_id):
    """تحديث حالة الإجراء كمكتمل (يُستدعى من device_client.py) - لا يتطلب تسجيل دخول"""
    try:
        # الحصول على device_token من header
        device_token = request.headers.get('X-Device-Token')
        if not device_token:
            return jsonify({'error': 'يجب توفير device_token'}), 401
        
        # التحقق من أن الإجراء يخص هذا الجهاز
        device = query_db('SELECT * FROM devices WHERE device_token = ? AND is_active = 1', (device_token,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        data = request.json or {}
        status = data.get('status', 'completed')  # completed, failed
        error_message = data.get('error_message', '')
        
        # الحصول على الإجراء
        action = query_db('SELECT * FROM system_actions WHERE id = ? AND device_id = ?', (action_id, device['id']), one=True)
        if not action:
            return jsonify({'error': 'الإجراء غير موجود أو لا يخص هذا الجهاز'}), 404
        
        # تحديث حالة الإجراء
        # إذا كان status = 'completed' و error_message موجود، أضفه للوصف
        new_description = action['action_description']
        if status == 'completed' and error_message:
            new_description = f"{action['action_description']} - {error_message}"
        elif status == 'failed' and error_message:
            new_description = f"{action['action_description']} - فشل: {error_message}"
        
        execute_db('''
            UPDATE system_actions 
            SET status = ?, completed_at = ?, action_description = ?
            WHERE id = ?
        ''', (
            status,
            datetime.now(),
            new_description,
            action_id
        ))
        
        return jsonify({
            'success': True,
            'message': f'تم تحديث حالة الإجراء إلى {status}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

