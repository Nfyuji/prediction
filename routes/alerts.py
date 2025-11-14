#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إدارة التنبيهات
معالجة التنبيهات والفحص التلقائي
"""

from flask import Blueprint, request, jsonify, render_template
from models.database import get_db, query_db, execute_db
from routes.auth import require_login
from ml_models.smart_predictor import smart_predictor as predictor
from datetime import datetime

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

@alerts_bp.route('')
@require_login
def alerts_list():
    """صفحة قائمة التنبيهات"""
    # جلب التنبيهات من قاعدة البيانات لتمريرها للقالب (اختياري - يمكن جلبها عبر API)
    try:
        alerts = query_db('''
            SELECT a.*, d.name as device_name, d.location as device_location,
                   u.username as acknowledged_by_username
            FROM alerts a
            JOIN devices d ON a.device_id = d.id
            LEFT JOIN users u ON a.acknowledged_by = u.id
            ORDER BY a.created_at DESC
            LIMIT 100
        ''')
        
        # تحويل إلى قائمة dictionaries للقالب
        alerts_list = []
        for alert in alerts:
            alerts_list.append({
                'id': alert['id'],
                'device_id': alert['device_id'],
                'device_name': alert['device_name'],
                'device_location': alert['device_location'],
                'type': alert['severity'],  # استخدام severity كـ type
                'alert_type': alert['alert_type'],
                'severity': alert['severity'],
                'message': alert['message'],
                'status': alert['status'],
                'acknowledged_by': alert['acknowledged_by'],
                'acknowledged_by_username': alert['acknowledged_by_username'],
                'acknowledged_at': alert['acknowledged_at'],
                'resolved_at': alert['resolved_at'],
                'timestamp': alert['created_at']
            })
    except Exception as e:
        alerts_list = []
    
    return render_template('alerts.html', alerts=alerts_list)

@alerts_bp.route('/api')
@require_login
def api_get_alerts():
    """API للحصول على جميع التنبيهات"""
    try:
        status_filter = request.args.get('status', 'all')
        severity_filter = request.args.get('severity', 'all')
        device_filter = request.args.get('device', '')
        
        query = '''
            SELECT a.*, d.name as device_name, d.location as device_location,
                   u.username as acknowledged_by_username
            FROM alerts a
            JOIN devices d ON a.device_id = d.id
            LEFT JOIN users u ON a.acknowledged_by = u.id
            WHERE 1=1
        '''
        params = []
        
        if status_filter != 'all':
            query += ' AND a.status = ?'
            params.append(status_filter)
        
        if severity_filter != 'all':
            query += ' AND a.severity = ?'
            params.append(severity_filter)
        
        if device_filter:
            query += ' AND d.name = ?'
            params.append(device_filter)
        
        query += ' ORDER BY a.created_at DESC'
        
        alerts = query_db(query, tuple(params))
        
        alerts_list = []
        for alert in alerts:
            alerts_list.append({
                'id': alert['id'],
                'device_id': alert['device_id'],
                'device_name': alert['device_name'],
                'device_location': alert['device_location'],
                'alert_type': alert['alert_type'],
                'severity': alert['severity'],
                'message': alert['message'],
                'status': alert['status'],
                'acknowledged_by': alert['acknowledged_by'],
                'acknowledged_by_username': alert['acknowledged_by_username'],
                'acknowledged_at': alert['acknowledged_at'],
                'resolved_at': alert['resolved_at'],
                'created_at': alert['created_at']
            })
        
        return jsonify(alerts_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/api/devices', methods=['GET'])
@require_login
def api_get_devices_for_filter():
    """API للحصول على قائمة الأجهزة للفلتر"""
    try:
        devices = query_db('''
            SELECT DISTINCT d.id, d.name
            FROM devices d
            INNER JOIN alerts a ON d.id = a.device_id
            WHERE d.is_active = 1
            ORDER BY d.name
        ''')
        
        devices_list = [{'id': d['id'], 'name': d['name']} for d in devices]
        return jsonify(devices_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/api/<int:alert_id>/acknowledge', methods=['POST'])
@require_login
def api_acknowledge_alert(alert_id):
    """API لتأكيد تنبيه"""
    try:
        from flask import session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        
        execute_db('''
            UPDATE alerts 
            SET status = 'acknowledged', 
                acknowledged_by = ?,
                acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id, alert_id))
        
        return jsonify({'success': True, 'message': 'تم تأكيد التنبيه'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/api/<int:alert_id>/resolve', methods=['POST'])
@require_login
def api_resolve_alert(alert_id):
    """API لحل تنبيه"""
    try:
        execute_db('''
            UPDATE alerts 
            SET status = 'resolved', 
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (alert_id,))
        
        return jsonify({'success': True, 'message': 'تم حل التنبيه'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alerts_bp.route('/api/check-devices', methods=['POST'])
@require_login
def api_check_devices():
    """API لفحص الأجهزة تلقائياً باستخدام الذكاء الاصطناعي"""
    try:
        db = get_db()
        
        # جلب جميع الأجهزة النشطة فقط
        devices = query_db('SELECT * FROM devices WHERE is_active = 1')
        
        new_alerts = 0
        updated_devices = 0
        
        for device in devices:
            # الحصول على آخر القياسات
            latest_metric = query_db('''
                SELECT * FROM device_metrics 
                WHERE device_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (device['id'],), one=True)
            
            if not latest_metric:
                continue
            
            # تحضير بيانات الجهاز
            device_data = {
                'cpu_usage': latest_metric['cpu_usage'] or 0,
                'ram_usage': latest_metric['ram_usage'] or 0,
                'disk_usage': latest_metric['disk_usage'] or 0,
                'temperature': latest_metric['temperature'] or 0,
                'battery_level': latest_metric['battery_level']
            }
            
            # الحصول على القياسات التاريخية
            historical_metrics = query_db('''
                SELECT * FROM device_metrics 
                WHERE device_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', (device['id'],))
            
            historical_data = [
                {
                    'cpu_usage': m['cpu_usage'] or 0,
                    'ram_usage': m['ram_usage'] or 0,
                    'temperature': m['temperature'] or 0
                }
                for m in historical_metrics
            ] if len(historical_metrics) > 1 else None
            
            # استخدام النظام الذكي للتنبؤ (يتعلم من البيانات)
            prediction = predictor.predict_failure(device_data, historical_data)
            
            # تحديث حالة الجهاز
            new_status = prediction['risk_level'] if prediction['risk_level'] != 'low' else 'healthy'
            if new_status != device['status']:
                execute_db('UPDATE devices SET status = ? WHERE id = ?', (new_status, device['id']))
                updated_devices += 1
            
            # إنشاء التنبيهات
            for alert in prediction['alerts']:
                # التحقق إذا كان التنبيه موجود مسبقاً
                existing_alert = query_db('''
                    SELECT id FROM alerts 
                    WHERE device_id = ? 
                    AND message LIKE ? 
                    AND status IN ('active', 'acknowledged')
                ''', (device['id'], f'%{alert["message"].split(":")[-1].strip()}%'), one=True)
                
                if not existing_alert:
                    # إدخال التنبيه الجديد
                    execute_db('''
                        INSERT INTO alerts 
                        (device_id, alert_type, severity, message, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        device['id'],
                        alert['type'],
                        alert['severity'],
                        f'{device["name"]}: {alert["message"]}',
                        'active',
                        datetime.now()
                    ))
                    new_alerts += 1
        
        return jsonify({
            'success': True,
            'new_alerts': new_alerts,
            'updated_devices': updated_devices,
            'total_checked': len(devices),
            'message': f'تم فحص {len(devices)} جهاز وإنشاء {new_alerts} تنبيه جديد وتحديث {updated_devices} جهاز'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

