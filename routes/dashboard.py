#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
لوحة التحكم
معالجة لوحة التحكم الرئيسية والإحصائيات
"""

from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from models.database import query_db
from routes.auth import require_login

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@require_login
def index():
    """صفحة لوحة التحكم الرئيسية - إعادة توجيه حسب الدور"""
    user_role = session.get('role', 'user')
    
    # إعادة التوجيه حسب الدور
    if user_role == 'admin':
        return redirect(url_for('dashboard.admin_dashboard'))
    elif user_role in ['technician', 'manager']:
        return redirect(url_for('dashboard.admin_dashboard'))  # التقني والمدير يروا لوحة الأدمن
    else:
        return redirect(url_for('dashboard.user_dashboard'))

@dashboard_bp.route('/admin')
@require_login
def admin_dashboard():
    """لوحة التحكم للأدمن"""
    from routes.auth import require_role
    
    # التحقق من الصلاحية
    user_role = session.get('role', 'user')
    if user_role not in ['admin', 'technician', 'manager']:
        return redirect(url_for('dashboard.user_dashboard'))
    
    try:
        # إحصائيات الأجهزة (الأجهزة النشطة فقط)
        total_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE is_active = 1', one=True)['count'] or 0
        healthy_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "healthy" AND is_active = 1', one=True)['count'] or 0
        warning_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "warning" AND is_active = 1', one=True)['count'] or 0
        critical_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "critical" AND is_active = 1', one=True)['count'] or 0
        
        # إحصائيات المستخدمين
        total_users = query_db('SELECT COUNT(*) as count FROM users', one=True)['count'] or 0
        active_users = query_db('SELECT COUNT(*) as count FROM users WHERE is_active = 1', one=True)['count'] or 0
        
        # إحصائيات التنبيهات
        total_alerts = query_db('SELECT COUNT(*) as count FROM alerts', one=True)['count'] or 0
        active_alerts = query_db('SELECT COUNT(*) as count FROM alerts WHERE status = "active"', one=True)['count'] or 0
        
        # إحصائيات النشاطات
        recent_activities = query_db('''
            SELECT COUNT(*) as count FROM activity_log 
            WHERE timestamp > datetime('now', '-24 hours')
        ''', one=True)['count'] or 0
        
        # إنشاء كائن stats للمرور إلى القالب
        stats = {
            'total_devices': total_devices,
            'healthy_devices': healthy_devices,
            'warning_devices': warning_devices,
            'critical_devices': critical_devices,
            'total_users': total_users,
            'active_users': active_users,
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'recent_activities': recent_activities
        }
        
        return render_template('admin_dashboard.html', stats=stats)
    except Exception as e:
        # في حالة حدوث خطأ، تمرير قيم افتراضية
        stats = {
            'total_devices': 0,
            'healthy_devices': 0,
            'warning_devices': 0,
            'critical_devices': 0,
            'total_users': 0,
            'active_users': 0,
            'total_alerts': 0,
            'active_alerts': 0,
            'recent_activities': 0
        }
        return render_template('admin_dashboard.html', stats=stats)

@dashboard_bp.route('/user')
@require_login
def user_dashboard():
    """لوحة التحكم للمستخدمين العاديين"""
    try:
        # إحصائيات الأجهزة (مبسطة للمستخدمين)
        total_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE is_active = 1', one=True)['count'] or 0
        healthy_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "healthy" AND is_active = 1', one=True)['count'] or 0
        warning_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "warning" AND is_active = 1', one=True)['count'] or 0
        critical_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "critical" AND is_active = 1', one=True)['count'] or 0
        
        # إنشاء كائن stats للمرور إلى القالب
        stats = {
            'total_devices': total_devices,
            'healthy_devices': healthy_devices,
            'warning_devices': warning_devices,
            'critical_devices': critical_devices
        }
        
        return render_template('user_dashboard.html', stats=stats)
    except Exception as e:
        # في حالة حدوث خطأ، تمرير قيم افتراضية
        stats = {
            'total_devices': 0,
            'healthy_devices': 0,
            'warning_devices': 0,
            'critical_devices': 0
        }
        return render_template('user_dashboard.html', stats=stats)

@dashboard_bp.route('/api/stats')
@require_login
def api_stats():
    """API للحصول على إحصائيات لوحة التحكم"""
    try:
        user_role = session.get('role', 'user')
        is_admin = user_role in ['admin', 'technician', 'manager']
        
        # إحصائيات الأجهزة (جميع الأجهزة النشطة فقط - بدون بيانات وهمية)
        total_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE is_active = 1', one=True)['count'] or 0
        healthy_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "healthy" AND is_active = 1', one=True)['count'] or 0
        warning_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "warning" AND is_active = 1', one=True)['count'] or 0
        critical_devices = query_db('SELECT COUNT(*) as count FROM devices WHERE status = "critical" AND is_active = 1', one=True)['count'] or 0
        
        # إحصائيات التنبيهات (من البيانات الحقيقية فقط)
        active_alerts_result = query_db('SELECT COUNT(*) as count FROM alerts WHERE status = "active"', one=True)
        active_alerts = active_alerts_result['count'] if active_alerts_result and active_alerts_result['count'] is not None else 0
        
        warning_alerts_result = query_db('SELECT COUNT(*) as count FROM alerts WHERE severity = "warning" AND status = "active"', one=True)
        warning_alerts = warning_alerts_result['count'] if warning_alerts_result and warning_alerts_result['count'] is not None else 0
        
        critical_alerts_result = query_db('SELECT COUNT(*) as count FROM alerts WHERE severity = "critical" AND status = "active"', one=True)
        critical_alerts = critical_alerts_result['count'] if critical_alerts_result and critical_alerts_result['count'] is not None else 0
        
        # إحصائيات الأداء المتوسطة (من البيانات الحقيقية فقط)
        avg_cpu = query_db('''
            SELECT AVG(cpu_usage) as avg 
            FROM device_metrics 
            WHERE timestamp > datetime('now', '-1 hour')
            AND cpu_usage IS NOT NULL
        ''', one=True)['avg']
        avg_cpu = round(avg_cpu, 2) if avg_cpu is not None else 0
        
        avg_ram = query_db('''
            SELECT AVG(ram_usage) as avg 
            FROM device_metrics 
            WHERE timestamp > datetime('now', '-1 hour')
            AND ram_usage IS NOT NULL
        ''', one=True)['avg']
        avg_ram = round(avg_ram, 2) if avg_ram is not None else 0
        
        avg_temp = query_db('''
            SELECT AVG(temperature) as avg 
            FROM device_metrics 
            WHERE timestamp > datetime('now', '-1 hour')
            AND temperature IS NOT NULL AND temperature > 0
        ''', one=True)['avg']
        avg_temp = round(avg_temp, 2) if avg_temp is not None else 0
        
        # حساب النسب الحقيقية للأجهزة
        healthy_percentage = round((healthy_devices / total_devices * 100) if total_devices > 0 else 0, 1)
        warning_percentage = round((warning_devices / total_devices * 100) if total_devices > 0 else 0, 1)
        critical_percentage = round((critical_devices / total_devices * 100) if total_devices > 0 else 0, 1)
        
        # حساب الاتجاهات (مقارنة آخر 24 ساعة مع الساعة الماضية)
        # عدد الأجهزة في آخر 24 ساعة
        devices_24h_ago = query_db('''
            SELECT COUNT(DISTINCT device_id) as count 
            FROM device_metrics 
            WHERE timestamp > datetime('now', '-24 hours')
            AND timestamp < datetime('now', '-23 hours')
        ''', one=True)['count'] or 0
        
        # عدد الأجهزة في الساعة الماضية
        devices_last_hour = query_db('''
            SELECT COUNT(DISTINCT device_id) as count 
            FROM device_metrics 
            WHERE timestamp > datetime('now', '-1 hour')
        ''', one=True)['count'] or 0
        
        # حساب نسبة التغيير في عدد الأجهزة
        devices_change_percentage = 0
        if devices_24h_ago > 0:
            devices_change_percentage = round(((devices_last_hour - devices_24h_ago) / devices_24h_ago * 100), 1)
        
        # حساب نسبة الأجهزة السليمة في آخر 24 ساعة
        healthy_24h_ago = query_db('''
            SELECT COUNT(*) as count 
            FROM devices 
            WHERE status = "healthy" 
            AND is_active = 1
            AND last_seen > datetime('now', '-24 hours')
        ''', one=True)['count'] or 0
        
        healthy_change_percentage = 0
        if total_devices > 0:
            healthy_change_percentage = round((healthy_devices / total_devices * 100), 1)
        
        # إحصائيات التنبيهات الإجمالية (من البيانات الحقيقية فقط)
        total_alerts_result = query_db('SELECT COUNT(*) as count FROM alerts', one=True)
        total_alerts = total_alerts_result['count'] if total_alerts_result and total_alerts_result['count'] is not None else 0
        
        stats = {
            'devices': {
                'total': total_devices,
                'healthy': healthy_devices,
                'warning': warning_devices,
                'critical': critical_devices,
                'healthy_percentage': round((healthy_devices / total_devices * 100) if total_devices > 0 else 0, 2)
            },
            'alerts': {
                'total_active': active_alerts,
                'warning': warning_alerts,
                'critical': critical_alerts
            },
            'performance': {
                'avg_cpu': avg_cpu,
                'avg_ram': avg_ram,
                'avg_temperature': avg_temp
            },
            # النسب الحقيقية
            'percentages': {
                'healthy': healthy_percentage,
                'warning': warning_percentage,
                'critical': critical_percentage,
                'devices_change': devices_change_percentage,
                'healthy_change': healthy_change_percentage
            },
            # إرجاع البيانات بشكل مباشر للتوافق مع الكود في dashboard.html
            'total_devices': total_devices,
            'healthy_devices': healthy_devices,
            'warning_devices': warning_devices,
            'critical_devices': critical_devices,
            'active_alerts': active_alerts,
            'total_alerts': total_alerts
        }
        
        # إحصائيات إضافية للأدمن فقط (من البيانات الحقيقية فقط)
        if is_admin:
            total_users_result = query_db('SELECT COUNT(*) as count FROM users', one=True)
            total_users = total_users_result['count'] if total_users_result and total_users_result['count'] is not None else 0
            
            active_users_result = query_db('SELECT COUNT(*) as count FROM users WHERE is_active = 1', one=True)
            active_users = active_users_result['count'] if active_users_result and active_users_result['count'] is not None else 0
            
            stats['users'] = {
                'total': total_users,
                'active': active_users
            }
            
            recent_activities_result = query_db('''
                SELECT COUNT(*) as count FROM activity_log 
                WHERE timestamp > datetime('now', '-24 hours')
            ''', one=True)
            stats['recent_activities'] = recent_activities_result['count'] if recent_activities_result and recent_activities_result['count'] is not None else 0
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/recent-alerts')
@require_login
def api_recent_alerts():
    """API للحصول على التنبيهات الحديثة"""
    try:
        limit = request.args.get('limit', 5, type=int)
        alerts = query_db('''
            SELECT a.*, d.name as device_name
            FROM alerts a
            JOIN devices d ON a.device_id = d.id
            WHERE a.status = "active"
            ORDER BY a.created_at DESC
            LIMIT ?
        ''', (limit,))
        
        alerts_list = []
        for alert in alerts:
            alerts_list.append({
                'id': alert['id'],
                'device_name': alert['device_name'],
                'severity': alert['severity'],
                'message': alert['message'],
                'created_at': alert['created_at']
            })
        
        return jsonify(alerts_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/recent-devices')
@require_login
def api_recent_devices():
    """API للحصول على الأجهزة الحديثة"""
    try:
        limit = request.args.get('limit', 5, type=int)
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
            WHERE d.is_active = 1
            ORDER BY COALESCE(d.last_seen, '1970-01-01') DESC, d.id DESC
            LIMIT ?
        ''', (limit,))
        
        devices_list = []
        for device in devices:
            devices_list.append({
                'id': device['id'],
                'name': device['name'],
                'location': device['location'],
                'status': device['status'],
                'cpu_usage': device['cpu_usage'] if device['cpu_usage'] is not None else None,
                'ram_usage': device['ram_usage'] if device['ram_usage'] is not None else None,
                'disk_usage': device['disk_usage'] if device['disk_usage'] is not None else None,
                'temperature': device['temperature'] if device['temperature'] is not None else None,
                'battery_level': device['battery_level'] if device['battery_level'] is not None else None,
                'last_seen': device['last_seen'],
                'last_update': device['last_update']
            })
        
        return jsonify(devices_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

