#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إدارة الأجهزة
معالجة عمليات الأجهزة والقياسات
"""

from flask import Blueprint, request, jsonify, render_template, session
from models.database import get_db, query_db, execute_db
from routes.auth import require_login, require_role
from datetime import datetime
import secrets
import hashlib

devices_bp = Blueprint('devices', __name__, url_prefix='/devices')

@devices_bp.route('')
@require_login
def devices_list():
    """صفحة قائمة الأجهزة"""
    return render_template('devices.html')

@devices_bp.route('/my-devices')
@require_login
def my_devices():
    """صفحة أجهزة المستخدم"""
    # إذا كان هناك new_device_token في session، نمرره للقالب
    # ثم نحذفه من session بعد عرضه (لن يظهر مرة أخرى بعد refresh)
    new_token = session.pop('new_device_token', None)
    new_device_id = session.pop('new_device_id', None)
    return render_template('my_devices.html', new_device_token=new_token, new_device_id=new_device_id)

@devices_bp.route('/api')
@require_login
def api_get_devices():
    """API للحصول على جميع الأجهزة (حسب الدور)"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'user')
        
        # بناء الاستعلام حسب الدور
        if user_role in ['admin', 'technician', 'manager']:
            # الأدمن والفنيون والمديرون يرون جميع الأجهزة
            query = '''
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
                WHERE d.is_active = 1
                ORDER BY d.id
            '''
            devices = query_db(query)
        else:
            # المستخدمون العاديون يرون فقط أجهزتهم
            query = '''
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
            '''
            devices = query_db(query, (user_id,))
        
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

@devices_bp.route('/api/<int:device_id>')
@require_login
def api_get_device(device_id):
    """API للحصول على جهاز محدد"""
    try:
        device = query_db('SELECT * FROM devices WHERE id = ?', (device_id,), one=True)
        
        if not device:
            return jsonify({'error': 'الجهاز غير موجود'}), 404
        
        # الحصول على آخر القياسات
        latest_metric = query_db('''
            SELECT * FROM device_metrics 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (device_id,), one=True)
        
        # الحصول على القياسات التاريخية (آخر 10)
        historical_metrics = query_db('''
            SELECT * FROM device_metrics 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (device_id,))
        
        device_dict = {
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
            'device_token': device['device_token'] if device['device_token'] is not None else None,  # إضافة device_token
            'last_seen': device['last_seen'],
            'created_at': device['created_at'],
            'latest_metric': dict(latest_metric) if latest_metric else None,
            'historical_metrics': [dict(m) for m in historical_metrics]
        }
        
        return jsonify(device_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/<int:device_id>')
@require_login
def device_details(device_id):
    """صفحة تفاصيل الجهاز"""
    try:
        # جلب الجهاز مع معلومات المستخدم المالك
        device = query_db('''
            SELECT d.*, 
                   u.username as owner_username,
                   u.full_name as owner_full_name,
                   u.email as owner_email,
                   u.phone as owner_phone,
                   u.role as owner_role
            FROM devices d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.id = ?
        ''', (device_id,), one=True)
        if not device:
            from flask import abort
            abort(404)
        
        # الحصول على آخر القياسات
        latest_metric = query_db('''
            SELECT * FROM device_metrics 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (device_id,), one=True)
        
        # تحويل device إلى dict وإضافة القياسات
        device_dict = dict(device)
        
        # إضافة معلومات المستخدم المالك
        if device['user_id']:
            device_dict['owner'] = {
                'user_id': device['user_id'],
                'username': device['owner_username'] if device['owner_username'] else None,
                'full_name': device['owner_full_name'] if device['owner_full_name'] else None,
                'email': device['owner_email'] if device['owner_email'] else None,
                'phone': device['owner_phone'] if device['owner_phone'] else None,
                'role': device['owner_role'] if device['owner_role'] else None
            }
        else:
            device_dict['owner'] = {
                'user_id': None,
                'username': None,
                'full_name': None,
                'email': None,
                'phone': None,
                'role': None
            }
        
        # إضافة القياسات إلى device_dict
        if latest_metric:
            device_dict['cpu_usage'] = latest_metric['cpu_usage'] if latest_metric['cpu_usage'] is not None else None
            device_dict['ram_usage'] = latest_metric['ram_usage'] if latest_metric['ram_usage'] is not None else None
            device_dict['disk_usage'] = latest_metric['disk_usage'] if latest_metric['disk_usage'] is not None else None
            # temperature: عرض القيمة إذا كانت موجودة وصحيحة
            temp_value = latest_metric['temperature']
            if temp_value is not None:
                try:
                    temp_float = float(temp_value)
                    # عرض درجة الحرارة إذا كانت ضمن نطاق منطقي (بين 0 و 150)
                    device_dict['temperature'] = temp_float if (0 < temp_float <= 150) else None
                except (ValueError, TypeError):
                    device_dict['temperature'] = None
            else:
                device_dict['temperature'] = None
            device_dict['battery'] = latest_metric['battery_level'] if latest_metric['battery_level'] is not None else None
            device_dict['last_update'] = latest_metric['timestamp']
        else:
            device_dict['cpu_usage'] = None
            device_dict['ram_usage'] = None
            device_dict['disk_usage'] = None
            device_dict['temperature'] = None
            device_dict['battery'] = None
            device_dict['last_update'] = None
        
        return render_template('device_details.html', device_id=device_id, device=device_dict)
    except Exception as e:
        from flask import abort
        abort(404)

@devices_bp.route('/api/<int:device_id>/metrics', methods=['POST'])
@require_login
def api_update_metrics(device_id):
    """API لتحديث قياسات الجهاز (للمستخدمين المسجلين)"""
    try:
        data = request.json
        
        # التحقق من وجود الجهاز
        device = query_db('SELECT id FROM devices WHERE id = ?', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود'}), 404
        
        # إدراج القياسات الجديدة
        # معالجة temperature: إذا كانت 0 أو غير موجودة، استخدم None
        temperature = data.get('temperature')
        if temperature is not None and (temperature == 0 or temperature == '0'):
            temperature = None
        
        metric_id = execute_db('''
            INSERT INTO device_metrics 
            (device_id, cpu_usage, ram_usage, disk_usage, temperature, battery_level, network_in, network_out, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            device_id,
            data.get('cpu_usage'),
            data.get('ram_usage'),
            data.get('disk_usage'),
            temperature,  # None إذا كانت 0 أو غير موجودة
            data.get('battery_level'),
            data.get('network_in'),
            data.get('network_out'),
            datetime.now()
        ))
        
        # تحديث آخر ظهور
        execute_db('UPDATE devices SET last_seen = CURRENT_TIMESTAMP WHERE id = ?', (device_id,))
        
        return jsonify({'success': True, 'metric_id': metric_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API لإضافة جهاز جديد (من لوحة التحكم)
@devices_bp.route('/api/create', methods=['POST'])
@require_login
def api_create_device():
    """API لإضافة جهاز جديد"""
    try:
        data = request.json
        
        user_id = session.get('user_id')
        user_role = session.get('role', 'user')
        
        # التحقق من عدد الأجهزة للمستخدمين العاديين (جهاز واحد فقط)
        if user_role not in ['admin', 'technician', 'manager']:
            # التحقق من عدد الأجهزة النشطة للمستخدم
            device_count = query_db('''
                SELECT COUNT(*) as count 
                FROM devices 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,), one=True)
            
            if device_count and device_count['count'] >= 1:
                return jsonify({'error': 'يمكنك إضافة جهاز واحد فقط. يرجى حذف الجهاز الحالي أولاً لإضافة جهاز جديد.'}), 400
        
        # التحقق من الحقول المطلوبة (الاسم فقط مطلوب لجميع المستخدمين)
        if not data.get('name'):
            return jsonify({'error': 'يرجى إدخال اسم الجهاز'}), 400
        
        # التحقق من عدم وجود جهاز بنفس IP (إذا تم إدخال IP)
        if data.get('ip_address'):
            existing_device = query_db('SELECT id FROM devices WHERE ip_address = ? AND is_active = 1', (data.get('ip_address'),), one=True)
            if existing_device:
                return jsonify({'error': f'يوجد جهاز آخر بعنوان IP: {data.get("ip_address")}'}), 400
        
        # إنشاء token فريد للجهاز (مع التأكد من عدم التكرار)
        max_attempts = 5
        device_token = None
        for attempt in range(max_attempts):
            token = secrets.token_urlsafe(32)
            existing = query_db('SELECT id FROM devices WHERE device_token = ?', (token,), one=True)
            if not existing:
                device_token = token
                break
        
        if not device_token:
            return jsonify({'error': 'فشل في إنشاء token فريد للجهاز'}), 500
        
        # إدراج الجهاز الجديد
        try:
            # ربط الجهاز بالمستخدم الحالي
            device_id = execute_db('''
                INSERT INTO devices 
                (name, device_type, location, ip_address, mac_address, operating_system, processor, ram_total, disk_total, status, device_token, is_active, user_id, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('device_type', 'computer'),
                data.get('location') or 'غير محدد',
                data.get('ip_address') or None,
                data.get('mac_address') or None,
                data.get('operating_system') or None,
                data.get('processor') or None,
                data.get('ram_total') or None,
                data.get('disk_total') or None,
                data.get('status', 'healthy'),
                device_token,
                1,  # is_active
                user_id,  # ربط الجهاز بالمستخدم
                datetime.now()
            ))
        except Exception as db_error:
            return jsonify({'error': f'خطأ في قاعدة البيانات: {str(db_error)}'}), 500
        
        # الحصول على الجهاز المضاف
        device = query_db('SELECT * FROM devices WHERE id = ?', (device_id,), one=True)
        
        if not device:
            return jsonify({'error': 'فشل في إنشاء الجهاز أو استرجاعه'}), 500
        
        # لا نضيف قياسات تجريبية - البيانات يجب أن تأتي من الجهاز نفسه فقط
        # ستبقى القياسات فارغة حتى يرسل الجهاز بياناته الحقيقية
        
        device_dict = {
            'id': device['id'],
            'name': device['name'],
            'device_type': device['device_type'],
            'location': device['location'],
            'ip_address': device['ip_address'],
            'mac_address': device['mac_address'] if device['mac_address'] is not None else None,
            'operating_system': device['operating_system'] if device['operating_system'] is not None else None,
            'processor': device['processor'] if device['processor'] is not None else None,
            'ram_total': device['ram_total'] if device['ram_total'] is not None else None,
            'disk_total': device['disk_total'] if device['disk_total'] is not None else None,
            'status': device['status'],
            'device_token': device['device_token'] if device['device_token'] is not None else None,
            'last_seen': device['last_seen'] if device['last_seen'] is not None else None,
            'created_at': device['created_at'] if device['created_at'] is not None else None
        }
        
        return jsonify({'success': True, 'device': device_dict}), 201
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"خطأ في إنشاء الجهاز: {e}")
        print(f"تفاصيل الخطأ: {error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500

@devices_bp.route('/api/<int:device_id>/update', methods=['PUT', 'POST'])
@require_login
def api_update_device(device_id):
    """API لتعديل بيانات الجهاز"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'user')
        
        # التحقق من وجود الجهاز
        device = query_db('SELECT * FROM devices WHERE id = ? AND is_active = 1', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # التحقق من الصلاحيات (المستخدم يمكنه تعديل أجهزته فقط)
        if user_role not in ['admin', 'technician', 'manager']:
            if device['user_id'] != user_id:
                return jsonify({'error': 'ليس لديك صلاحية لتعديل هذا الجهاز'}), 403
        
        data = request.json or {}
        
        # تحديث البيانات
        update_fields = []
        update_values = []
        
        if 'name' in data:
            update_fields.append('name = ?')
            update_values.append(data['name'])
        
        if 'location' in data:
            update_fields.append('location = ?')
            update_values.append(data['location'])
        
        if 'device_type' in data:
            update_fields.append('device_type = ?')
            update_values.append(data['device_type'])
        
        # السماح لجميع المستخدمين بتعديل IP و MAC (لكن فقط لأجهزتهم الخاصة)
        if 'ip_address' in data:
            # التحقق من عدم وجود جهاز آخر بنفس IP (إذا تم إدخال IP)
            if data['ip_address']:
                existing_device = query_db('SELECT id FROM devices WHERE ip_address = ? AND id != ? AND is_active = 1', 
                                         (data['ip_address'], device_id), one=True)
                if existing_device:
                    return jsonify({'error': f'يوجد جهاز آخر بعنوان IP: {data["ip_address"]}'}), 400
            update_fields.append('ip_address = ?')
            update_values.append(data['ip_address'] if data['ip_address'] else None)
        
        if 'mac_address' in data:
            update_fields.append('mac_address = ?')
            update_values.append(data['mac_address'] if data['mac_address'] else None)
        
        if 'operating_system' in data:
            update_fields.append('operating_system = ?')
            update_values.append(data['operating_system'] if data['operating_system'] else None)
        
        if 'processor' in data:
            update_fields.append('processor = ?')
            update_values.append(data['processor'] if data['processor'] else None)
        
        if 'ram_total' in data:
            update_fields.append('ram_total = ?')
            update_values.append(data['ram_total'] if data['ram_total'] else None)
        
        if 'disk_total' in data:
            update_fields.append('disk_total = ?')
            update_values.append(data['disk_total'] if data['disk_total'] else None)
        
        # الحالة (Status) للأدمن فقط لأسباب أمنية
        if 'status' in data and user_role in ['admin', 'technician', 'manager']:
            update_fields.append('status = ?')
            update_values.append(data['status'])
        
        if not update_fields:
            return jsonify({'error': 'لا توجد بيانات للتعديل'}), 400
        
        # إضافة device_id للقيم
        update_values.append(device_id)
        
        # تنفيذ التحديث
        update_query = f'''
            UPDATE devices 
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        execute_db(update_query, tuple(update_values))
        
        # تسجيل النشاط
        try:
            execute_db('''
                INSERT INTO activity_log (user_id, action, description, ip_address)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                'device_update',
                f'تم تعديل بيانات الجهاز {device["name"]}',
                request.remote_addr
            ))
        except:
            pass
        
        # جلب الجهاز المحدث
        updated_device = query_db('SELECT * FROM devices WHERE id = ?', (device_id,), one=True)
        
        device_dict = {
            'id': updated_device['id'],
            'name': updated_device['name'],
            'device_type': updated_device['device_type'],
            'location': updated_device['location'],
            'ip_address': updated_device['ip_address'],
            'mac_address': updated_device['mac_address'] if updated_device['mac_address'] is not None else None,
            'operating_system': updated_device['operating_system'] if updated_device['operating_system'] is not None else None,
            'processor': updated_device['processor'] if updated_device['processor'] is not None else None,
            'ram_total': updated_device['ram_total'] if updated_device['ram_total'] is not None else None,
            'disk_total': updated_device['disk_total'] if updated_device['disk_total'] is not None else None,
            'status': updated_device['status'],
            'device_token': updated_device['device_token'] if updated_device['device_token'] is not None else None,
            'last_seen': updated_device['last_seen'] if updated_device['last_seen'] is not None else None,
            'updated_at': updated_device['updated_at'] if updated_device['updated_at'] is not None else None
        }
        
        return jsonify({'success': True, 'device': device_dict, 'message': 'تم تحديث بيانات الجهاز بنجاح'})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

@devices_bp.route('/api/<int:device_id>/delete', methods=['DELETE', 'POST'])
@require_login
def api_delete_device(device_id):
    """API لحذف الجهاز"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'user')
        
        # التحقق من وجود الجهاز
        device = query_db('SELECT * FROM devices WHERE id = ? AND is_active = 1', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # التحقق من الصلاحيات (المستخدم يمكنه حذف أجهزته فقط)
        if user_role not in ['admin', 'technician', 'manager']:
            if device['user_id'] != user_id:
                return jsonify({'error': 'ليس لديك صلاحية لحذف هذا الجهاز'}), 403
        
        # حذف القياسات المرتبطة بالجهاز
        execute_db('DELETE FROM device_metrics WHERE device_id = ?', (device_id,))
        
        # حذف التنبيهات المرتبطة بالجهاز
        execute_db('DELETE FROM alerts WHERE device_id = ?', (device_id,))
        
        # حذف الإجراءات المرتبطة بالجهاز
        execute_db('DELETE FROM system_actions WHERE device_id = ?', (device_id,))
        
        # تعطيل الجهاز (بدلاً من الحذف الفعلي)
        execute_db('''
            UPDATE devices 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (device_id,))
        
        # تسجيل النشاط
        try:
            execute_db('''
                INSERT INTO activity_log (user_id, action, description, ip_address)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                'device_delete',
                f'تم حذف الجهاز {device["name"]}',
                request.remote_addr
            ))
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الجهاز بنجاح'
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

# API للأجهزة لإرسال البيانات (بدون تسجيل دخول)
@devices_bp.route('/api/register', methods=['POST'])
def api_register_device():
    """API لتسجيل الجهاز تلقائياً عند الاتصال من device_client.py"""
    try:
        data = request.json
        
        # إذا كان هناك device_token، ابحث عن الجهاز وحدّث معلوماته
        device_token = data.get('device_token')
        device = None
        
        if device_token:
            # البحث عن الجهاز باستخدام token
            device = query_db('SELECT * FROM devices WHERE device_token = ?', (device_token,), one=True)
        
        # إذا لم يوجد الجهاز بالtoken، ابحث باستخدام MAC أو IP
        if not device:
            if data.get('mac_address'):
                device = query_db('SELECT * FROM devices WHERE mac_address = ?', (data.get('mac_address'),), one=True)
            if not device and data.get('ip_address'):
                device = query_db('SELECT * FROM devices WHERE ip_address = ?', (data.get('ip_address'),), one=True)
        
        # إذا لم يوجد الجهاز، إنشاؤه تلقائياً (للتوافق مع الأنظمة القديمة)
        if not device:
            device_token = device_token or secrets.token_urlsafe(32)
            device_name = data.get('name', f"جهاز {data.get('mac_address', data.get('ip_address', 'غير معروف'))}")
            
            device_id = execute_db('''
                INSERT INTO devices 
                (name, device_type, location, ip_address, mac_address, operating_system, processor, ram_total, disk_total, status, device_token, is_active, user_id, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_name,
                data.get('device_type', 'computer'),
                data.get('location', 'غير محدد'),
                data.get('ip_address'),
                data.get('mac_address'),
                data.get('operating_system'),
                data.get('processor'),
                data.get('ram_total'),
                data.get('disk_total'),
                'healthy',
                device_token,
                1,
                None,  # لا user_id في التسجيل التلقائي
                datetime.now()
            ))
            
            device = query_db('SELECT * FROM devices WHERE id = ?', (device_id,), one=True)
        else:
            # تحديث معلومات الجهاز بالمعلومات الجديدة من device_client.py
            execute_db('''
                UPDATE devices 
                SET ip_address = COALESCE(?, ip_address),
                    mac_address = COALESCE(?, mac_address),
                    operating_system = COALESCE(?, operating_system),
                    processor = COALESCE(?, processor),
                    ram_total = COALESCE(?, ram_total),
                    disk_total = COALESCE(?, disk_total),
                    name = COALESCE(?, name),
                    is_active = 1,
                    last_seen = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('ip_address'),
                data.get('mac_address'),
                data.get('operating_system'),
                data.get('processor'),
                data.get('ram_total'),
                data.get('disk_total'),
                data.get('name'),
                device['id']
            ))
            device = query_db('SELECT * FROM devices WHERE id = ?', (device['id'],), one=True)
        
        return jsonify({
            'success': True,
            'device_id': device['id'],
            'device_token': device['device_token'],
            'message': 'تم تسجيل/تحديث الجهاز بنجاح'
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

@devices_bp.route('/api/update-after-scan', methods=['POST'])
def api_update_after_scan():
    """API لتحديث معلومات الجهاز بعد فحص شامل (يُستدعى من device_client.py بعد scan)"""
    try:
        data = request.json
        device_token = request.headers.get('X-Device-Token')
        
        if not device_token:
            return jsonify({'error': 'يجب توفير device_token'}), 401
        
        # البحث عن الجهاز
        device = query_db('SELECT * FROM devices WHERE device_token = ? AND is_active = 1', (device_token,), one=True)
        
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # تحديث معلومات الجهاز بناءً على نتائج الفحص
        update_fields = []
        update_values = []
        
        # تحديث نظام التشغيل
        if data.get('operating_system'):
            update_fields.append('operating_system = ?')
            update_values.append(data['operating_system'])
        
        # تحديث المعالج
        if data.get('processor'):
            update_fields.append('processor = ?')
            update_values.append(data['processor'])
        
        # تحديث RAM
        if data.get('ram_total'):
            update_fields.append('ram_total = ?')
            update_values.append(data['ram_total'])
        
        # تحديث Disk
        if data.get('disk_total'):
            update_fields.append('disk_total = ?')
            update_values.append(data['disk_total'])
        
        # تحديث last_seen
        update_fields.append('last_seen = CURRENT_TIMESTAMP')
        
        # حفظ نتائج الفحص الكاملة في قاعدة البيانات (إذا كان هناك جدول scan_results)
        # أو يمكن حفظها كـ JSON في حقل scan_results إذا كان موجوداً
        scan_results = data.get('scan_results', {})
        
        # تحديث قاعدة البيانات
        if update_fields:
            update_values.append(device['id'])
            query = f'''
                UPDATE devices 
                SET {', '.join(update_fields)}
                WHERE id = ?
            '''
            execute_db(query, tuple(update_values))
        
        # حفظ نتائج الفحص في activity_log أو جدول منفصل
        try:
            # يمكن حفظ نتائج الفحص في activity_log كـ description
            warnings_count = len(scan_results.get('warnings', []))
            errors_count = len(scan_results.get('errors', []))
            
            execute_db('''
                INSERT INTO activity_log (user_id, action, description, ip_address)
                VALUES (?, ?, ?, ?)
            ''', (
                device.get('user_id') or 0,  # إذا كان user_id موجود
                'device_scan',
                f'تم فحص الجهاز {device["name"]}. التحذيرات: {warnings_count}، الأخطاء: {errors_count}',
                request.remote_addr
            ))
        except:
            pass  # تجاهل الأخطاء في حفظ activity_log
        
        # إرجاع رسالة نجاح
        return jsonify({
            'success': True,
            'message': 'تم تحديث معلومات الجهاز بعد الفحص بنجاح',
            'warnings_count': len(scan_results.get('warnings', [])),
            'errors_count': len(scan_results.get('errors', []))
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500

# API للأجهزة لإرسال البيانات باستخدام token
@devices_bp.route('/api/report', methods=['POST'])
def api_report_metrics():
    """API للأجهزة لإرسال القياسات (باستخدام device_token)"""
    try:
        data = request.json
        device_token = request.headers.get('X-Device-Token') or data.get('device_token')
        
        if not device_token:
            return jsonify({'error': 'يجب توفير device_token'}), 401
        
        # البحث عن الجهاز باستخدام token
        device = query_db('SELECT * FROM devices WHERE device_token = ? AND is_active = 1', (device_token,), one=True)
        
        if not device:
            return jsonify({'error': 'الجهاز غير موجود أو غير مفعل'}), 404
        
        # إدراج القياسات الجديدة
        # معالجة temperature: قبول القيم الصحيحة فقط
        temperature = data.get('temperature')
        # معالجة temperature: إذا كانت موجودة وتحويلها إلى float
        if temperature is not None:
            try:
                temp_float = float(temperature)
                # قبول القيم بين 0 و 150 (درجة حرارة منطقية)
                if temp_float > 0 and temp_float <= 150:
                    temperature = temp_float
                else:
                    # إذا كانت خارج النطاق، استخدم None
                    temperature = None
            except (ValueError, TypeError):
                temperature = None
        # إذا كانت temperature None أو غير موجودة، اتركها None (سيتم عرض "لا توجد بيانات")
        
        metric_id = execute_db('''
            INSERT INTO device_metrics 
            (device_id, cpu_usage, ram_usage, disk_usage, temperature, battery_level, network_in, network_out, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            device['id'],
            data.get('cpu_usage', 0),
            data.get('ram_usage', 0),
            data.get('disk_usage', 0),
            temperature,  # None إذا كانت 0 أو غير موجودة
            data.get('battery_level'),
            data.get('network_in', 0),
            data.get('network_out', 0),
            datetime.now()
        ))
        
        # تحديث آخر ظهور والحالة
        # تحديث الحالة بناءً على القياسات (استخدام temperature المحددة أعلاه)
        status = 'healthy'
        if (data.get('cpu_usage', 0) > 90 or data.get('ram_usage', 0) > 90 or 
            (temperature is not None and temperature > 80)):
            status = 'critical'
        elif (data.get('cpu_usage', 0) > 70 or data.get('ram_usage', 0) > 70 or 
              (temperature is not None and temperature > 65)):
            status = 'warning'
        
        execute_db('''
            UPDATE devices 
            SET last_seen = CURRENT_TIMESTAMP, 
                status = ?,
                is_active = 1
            WHERE id = ?
        ''', (status, device['id']))
        
        return jsonify({
            'success': True, 
            'metric_id': metric_id,
            'device_id': device['id'],
            'status': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/<int:device_id>/predict', methods=['GET'])
@require_login
def api_predict_device(device_id):
    """API للتنبؤ بمشاكل الجهاز"""
    try:
        # استخدام النظام الذكي الذي يجمع بين التعلم الآلي والقواعد
        from ml_models.smart_predictor import smart_predictor
        
        # الحصول على آخر القياسات
        latest_metric = query_db('''
            SELECT * FROM device_metrics 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (device_id,), one=True)
        
        if not latest_metric:
            return jsonify({'error': 'لا توجد قياسات متاحة'}), 404
        
        # الحصول على القياسات التاريخية
        historical_metrics = query_db('''
            SELECT * FROM device_metrics 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 20
        ''', (device_id,))
        
        device_data = {
            'cpu_usage': latest_metric['cpu_usage'] if latest_metric['cpu_usage'] is not None else 0,
            'ram_usage': latest_metric['ram_usage'] if latest_metric['ram_usage'] is not None else 0,
            'disk_usage': latest_metric['disk_usage'] if latest_metric['disk_usage'] is not None else 0,
            'temperature': latest_metric['temperature'] if (latest_metric['temperature'] is not None and latest_metric['temperature'] > 0) else None,
            'battery_level': latest_metric['battery_level']
        }
        
        historical_data = [
            {
                'cpu_usage': m['cpu_usage'] if m['cpu_usage'] is not None else 0,
                'ram_usage': m['ram_usage'] if m['ram_usage'] is not None else 0,
                'temperature': m['temperature'] if (m['temperature'] is not None and m['temperature'] > 0) else None
            }
            for m in historical_metrics
        ]
        
        # الحصول على التنبؤ باستخدام النظام الذكي
        prediction = smart_predictor.predict_failure(device_data, historical_data if len(historical_data) > 1 else None)
        
        return jsonify(prediction)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API لتحميل device_client.py
@devices_bp.route('/api/<int:device_id>/download-client')
@require_login
def download_client(device_id):
    """تحميل device_client.py"""
    try:
        device = query_db('SELECT device_token FROM devices WHERE id = ?', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود'}), 404
        
        # قراءة ملف device_client.py
        import os
        client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'device_client.py')
        
        if not os.path.exists(client_path):
            return jsonify({'error': 'ملف device_client.py غير موجود'}), 404
        
        from flask import send_file, make_response
        response = make_response(send_file(client_path, as_attachment=True, download_name='device_client.py'))
        response.headers['Content-Type'] = 'text/x-python'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API لتحميل دليل الإعداد
@devices_bp.route('/api/<int:device_id>/download-guide')
@require_login
def download_guide(device_id):
    """تحميل دليل الإعداد"""
    try:
        device = query_db('SELECT device_token FROM devices WHERE id = ?', (device_id,), one=True)
        if not device:
            return jsonify({'error': 'الجهاز غير موجود'}), 404
        
        from flask import request, make_response
        
        server_url = request.host_url.rstrip('/')
        device_token = device['device_token'] or 'غير_متوفر'
        
        guide_content = f"""دليل إعداد عميل المراقبة
========================

Device Token: {device_token}
Server URL: {server_url}

خطوات الإعداد:
1. تأكد من تثبيت Python 3.6 أو أحدث
2. ثبّت المكتبات المطلوبة:
   pip install requests psutil

3. ضع الملفات في مجلد واحد:
   - device_client.py
   - device_config.json

4. شغّل العميل:
   python device_client.py

5. ستبدأ البيانات في الظهور تلقائياً في لوحة التحكم!

ملاحظات:
- تأكد من أن عنوان IP في device_config.json صحيح
- العميل يرسل البيانات كل 60 ثانية
- تأكد من أن الجهاز يمكنه الوصول للسيرفر
"""
        
        response = make_response(guide_content)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename="دليل_الإعداد.txt"'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

