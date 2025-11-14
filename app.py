#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مراقبة الأجهزة - التطبيق الرئيسي
نظام متكامل مع ذكاء اصطناعي للتنبؤ بالمشاكل
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import os

# استيراد النماذج والمسارات
from models.database import init_db, close_db
from routes.auth import auth_bp
from routes.devices import devices_bp
from routes.alerts import alerts_bp
from routes.dashboard import dashboard_bp
from routes.users import users_bp
from routes.ml_training import ml_training_bp
from routes.my_devices import my_devices_bp
from routes.settings import settings_bp
from routes.actions import actions_bp
from routes.analytics import analytics_bp

# إنشاء التطبيق
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# إعداد قاعدة البيانات
app.config['DATABASE'] = 'device_monitoring.db'

# تسجيل Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(users_bp)
app.register_blueprint(ml_training_bp)
app.register_blueprint(my_devices_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(analytics_bp)

# تهيئة قاعدة البيانات عند بدء التطبيق
with app.app_context():
    init_db()

# إغلاق قاعدة البيانات بعد كل طلب
app.teardown_appcontext(close_db)

# الصفحة الرئيسية - إعادة توجيه إلى لوحة التحكم
# ملاحظة: route '/' يتم تسجيله في dashboard blueprint

# ملاحظة: جميع routes موجودة في blueprints الخاصة بها

# صفحة التقارير
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('reports.html')

# صفحة المساعدة
@app.route('/help')
def help():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('help.html')

# صفحة التحليلات المتقدمة - تم نقلها إلى analytics blueprint

# API للإحصائيات العامة (للوحة التحكم)
@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    """API للحصول على إحصائيات لوحة التحكم"""
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول'}), 401
    
    from models.database import query_db
    
    try:
        stats = {
            'total_devices': query_db('SELECT COUNT(*) as count FROM devices WHERE is_active = 1', one=True)['count'],
            'active_alerts': query_db('SELECT COUNT(*) as count FROM alerts WHERE status = "active"', one=True)['count'],
            'warning_devices': query_db('SELECT COUNT(*) as count FROM devices WHERE status = "warning" AND is_active = 1', one=True)['count'],
            'healthy_devices': query_db('SELECT COUNT(*) as count FROM devices WHERE status = "healthy" AND is_active = 1', one=True)['count'],
            'critical_devices': query_db('SELECT COUNT(*) as count FROM devices WHERE status = "critical" AND is_active = 1', one=True)['count']
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API للأجهزة (للتوافق مع الكود القديم)
@app.route('/api/devices')
def api_devices():
    """API للحصول على جميع الأجهزة"""
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول'}), 401
    
    from models.database import query_db
    
    try:
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
                    ORDER BY timestamp DESC LIMIT 1) as battery_level
            FROM devices d
            WHERE d.is_active = 1
            ORDER BY d.id
        ''')
        
        devices_list = []
        for device in devices:
            devices_list.append({
                'id': device['id'],
                'name': device['name'],
                'device_type': device['device_type'],
                'location': device['location'],
                'status': device['status'],
                'cpu_usage': device['cpu_usage'] or 0,
                'ram_usage': device['ram_usage'] or 0,
                'disk_usage': device['disk_usage'] or 0,
                'temperature': device['temperature'] or 0,
                'battery': device['battery_level'],
                'last_update': device.get('last_seen', '')
            })
        
        return jsonify(devices_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API للتنبيهات (للتوافق مع الكود القديم)
@app.route('/api/alerts')
def api_alerts():
    """API للحصول على جميع التنبيهات"""
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول'}), 401
    
    from models.database import query_db
    
    try:
        alerts = query_db('''
            SELECT a.*, d.name as device_name
            FROM alerts a
            JOIN devices d ON a.device_id = d.id
            WHERE a.status = "active"
            ORDER BY a.created_at DESC
        ''')
        
        alerts_list = []
        for alert in alerts:
            alerts_list.append({
                'id': alert['id'],
                'device_id': alert['device_id'],
                'device_name': alert['device_name'],
                'type': alert['alert_type'],
                'severity': alert['severity'],
                'message': alert['message'],
                'status': alert['status'],
                'timestamp': alert['created_at']
            })
        
        return jsonify(alerts_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# معالج الأخطاء
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("=" * 60)
    print("نظام مراقبة الاجهزة مع الذكاء الاصطناعي")
    print("=" * 60)
    print("\nالتطبيق يعمل على: http://localhost:5000")
    print("\n" + "=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
