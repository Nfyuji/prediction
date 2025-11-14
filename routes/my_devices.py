#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API لأجهزة المستخدم
"""

from flask import Blueprint, request, jsonify, session
from models.database import query_db, execute_db
from routes.auth import require_login
from datetime import datetime
import secrets

my_devices_bp = Blueprint('my_devices', __name__, url_prefix='/my-devices')

@my_devices_bp.route('/api/register', methods=['POST'])
@require_login
def api_register_my_device():
    """API لإنشاء جهاز جديد مع token (بدون MAC/IP - سيأتيان تلقائياً من device_client.py)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        data = request.json or {}
        
        # إنشاء token فريد للجهاز
        device_token = secrets.token_urlsafe(32)
        device_name = data.get('name', f"جهاز المستخدم {user_id}")
        
        # إنشاء الجهاز (بدون MAC/IP - سيتم تحديثهما تلقائياً عندما يشغل المستخدم device_client.py)
        device_id = execute_db('''
            INSERT INTO devices 
            (name, device_type, location, ip_address, mac_address, operating_system, processor, ram_total, disk_total, status, device_token, is_active, user_id, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            device_name,
            data.get('device_type', 'computer'),
            data.get('location', 'غير محدد'),
            None,  # سيتم تحديثه تلقائياً من device_client.py
            None,  # سيتم تحديثه تلقائياً من device_client.py
            None,  # سيتم تحديثه تلقائياً من device_client.py
            None,  # سيتم تحديثه تلقائياً من device_client.py
            None,  # سيتم تحديثه تلقائياً من device_client.py
            None,  # سيتم تحديثه تلقائياً من device_client.py
            'healthy',
            device_token,
            1,
            user_id,  # ربط الجهاز بالمستخدم
            datetime.now()
        ))
        
        device = query_db('SELECT * FROM devices WHERE id = ?', (device_id,), one=True)
        
        return jsonify({
            'success': True,
            'device_id': device['id'],
            'device_token': device['device_token'],
            'message': 'تم إنشاء الجهاز بنجاح. استخدم device_token لتسجيل الجهاز. سيتم جلب MAC و IP تلقائياً عند تشغيل device_client.py'
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

@my_devices_bp.route('/api/list', methods=['GET'])
@require_login
def api_get_my_devices():
    """API للحصول على أجهزة المستخدم"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        devices = query_db('''
            SELECT d.*, 
                   (SELECT cpu_usage FROM device_metrics 
                    WHERE device_id = d.id 
                    ORDER BY timestamp DESC LIMIT 1) as cpu_usage,
                   (SELECT ram_usage FROM device_metrics 
                    WHERE device_id = d.id 
                    ORDER BY timestamp DESC LIMIT 1) as ram_usage,
                   (SELECT disk_usage FROM device_metrics 
                    WHERE device_id = d.id 
                    ORDER BY timestamp DESC LIMIT 1) as disk_usage,
                   (SELECT temperature FROM device_metrics 
                    WHERE device_id = d.id 
                    ORDER BY timestamp DESC LIMIT 1) as temperature,
                   (SELECT battery_level FROM device_metrics 
                    WHERE device_id = d.id 
                    ORDER BY timestamp DESC LIMIT 1) as battery_level,
                   (SELECT timestamp FROM device_metrics 
                    WHERE device_id = d.id 
                    ORDER BY timestamp DESC LIMIT 1) as last_update
            FROM devices d
            WHERE d.is_active = 1 AND d.user_id = ?
            ORDER BY d.id
        ''', (user_id,))
        
        devices_list = []
        for device in devices:
            devices_list.append({
                'id': device['id'],
                'name': device['name'],
                'device_type': device['device_type'],
                'location': device['location'],
                'ip_address': device['ip_address'],
                'mac_address': device['mac_address'],
                'operating_system': device['operating_system'],
                'processor': device['processor'],
                'ram_total': device['ram_total'],
                'disk_total': device['disk_total'],
                'status': device['status'],
                'device_token': device['device_token'],
                'cpu_usage': device['cpu_usage'] if device['cpu_usage'] is not None else None,
                'ram_usage': device['ram_usage'] if device['ram_usage'] is not None else None,
                'disk_usage': device['disk_usage'] if device['disk_usage'] is not None else None,
                'temperature': device['temperature'] if (device['temperature'] is not None and device['temperature'] > 0) else None,
                'battery_level': device['battery_level'] if device['battery_level'] is not None else None,
                'last_seen': device['last_seen'],
                'last_update': device['last_update']
            })
        
        return jsonify(devices_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@my_devices_bp.route('/api/connect', methods=['POST'])
@require_login
def api_connect_device():
    """API لربط الجهاز بضغطة زر (يستخدم device_token من session)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        data = request.json
        device_token = data.get('device_token')
        
        if not device_token:
            return jsonify({'error': 'يجب توفير device_token'}), 400
        
        # البحث عن الجهاز باستخدام token
        device = query_db('SELECT * FROM devices WHERE device_token = ?', (device_token,), one=True)
        
        if not device:
            return jsonify({'error': 'الجهاز غير موجود'}), 404
        
        # ربط الجهاز بالمستخدم الحالي
        execute_db('''
            UPDATE devices 
            SET user_id = ?, is_active = 1, last_seen = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id, device['id']))
        
        return jsonify({
            'success': True,
            'device_id': device['id'],
            'message': 'تم ربط الجهاز بنجاح'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@my_devices_bp.route('/api/delete/<int:device_id>', methods=['DELETE'])
@require_login
def api_delete_device(device_id):
    """API لحذف جهاز المستخدم"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        # التحقق من أن الجهاز يخص المستخدم
        device = query_db('SELECT * FROM devices WHERE id = ? AND user_id = ?', (device_id, user_id), one=True)
        
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مخصص لك'}), 404
        
        # حذف القياسات المرتبطة بالجهاز
        execute_db('DELETE FROM device_metrics WHERE device_id = ?', (device_id,))
        
        # حذف التنبيهات المرتبطة بالجهاز
        execute_db('DELETE FROM alerts WHERE device_id = ?', (device_id,))
        
        # حذف الجهاز (أو تعطيله بدلاً من الحذف)
        execute_db('''
            UPDATE devices 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (device_id,))
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الجهاز بنجاح'
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

