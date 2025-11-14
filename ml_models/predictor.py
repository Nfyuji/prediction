#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نموذج الذكاء الاصطناعي للتنبؤ بالمشاكل
نظام متقدم للتنبؤ بالأعطال والمشاكل المحتملة
"""

import numpy as np
from datetime import datetime, timedelta
import math

class AdvancedPredictor:
    """نموذج متقدم للتنبؤ بالمشاكل"""
    
    def __init__(self):
        # العتبات الحرجة
        self.thresholds = {
            'cpu_critical': 85,
            'cpu_warning': 70,
            'ram_critical': 90,
            'ram_warning': 75,
            'temp_critical': 80,
            'temp_warning': 70,
            'disk_critical': 95,
            'disk_warning': 85,
            'battery_critical': 15,
            'battery_warning': 25
        }
        
        # أوزان العوامل
        self.weights = {
            'cpu': 0.25,
            'ram': 0.20,
            'temp': 0.30,
            'disk': 0.15,
            'battery': 0.10
        }
    
    def calculate_risk_score(self, device_data):
        """حساب درجة المخاطرة"""
        risk_factors = {}
        
        # تحليل المعالج
        cpu_risk = 0
        if device_data.get('cpu_usage', 0) > self.thresholds['cpu_critical']:
            cpu_risk = 100
        elif device_data.get('cpu_usage', 0) > self.thresholds['cpu_warning']:
            cpu_risk = 50 + (device_data['cpu_usage'] - self.thresholds['cpu_warning']) * 2
        else:
            cpu_risk = (device_data.get('cpu_usage', 0) / self.thresholds['cpu_warning']) * 50
        
        risk_factors['cpu'] = min(cpu_risk, 100)
        
        # تحليل الذاكرة
        ram_risk = 0
        if device_data.get('ram_usage', 0) > self.thresholds['ram_critical']:
            ram_risk = 100
        elif device_data.get('ram_usage', 0) > self.thresholds['ram_warning']:
            ram_risk = 50 + (device_data['ram_usage'] - self.thresholds['ram_warning']) * 2.67
        else:
            ram_risk = (device_data.get('ram_usage', 0) / self.thresholds['ram_warning']) * 50
        
        risk_factors['ram'] = min(ram_risk, 100)
        
        # تحليل درجة الحرارة
        temp_risk = 0
        if device_data.get('temperature', 0) > self.thresholds['temp_critical']:
            temp_risk = 100
        elif device_data.get('temperature', 0) > self.thresholds['temp_warning']:
            temp_risk = 50 + (device_data['temperature'] - self.thresholds['temp_warning']) * 5
        else:
            temp_risk = (device_data.get('temperature', 0) / self.thresholds['temp_warning']) * 50
        
        risk_factors['temp'] = min(temp_risk, 100)
        
        # تحليل القرص الصلب
        disk_risk = 0
        if device_data.get('disk_usage', 0) > self.thresholds['disk_critical']:
            disk_risk = 100
        elif device_data.get('disk_usage', 0) > self.thresholds['disk_warning']:
            disk_risk = 50 + (device_data['disk_usage'] - self.thresholds['disk_warning']) * 5
        else:
            disk_risk = (device_data.get('disk_usage', 0) / self.thresholds['disk_warning']) * 50
        
        risk_factors['disk'] = min(disk_risk, 100)
        
        # تحليل البطارية (إن وجدت)
        battery_risk = 0
        if device_data.get('battery_level') is not None:
            battery_level = device_data['battery_level']
            if battery_level < self.thresholds['battery_critical']:
                battery_risk = 100
            elif battery_level < self.thresholds['battery_warning']:
                battery_risk = 50 + (self.thresholds['battery_warning'] - battery_level) * 5
            else:
                battery_risk = (100 - battery_level) / 75 * 50
        
        risk_factors['battery'] = min(battery_risk, 100)
        
        # حساب درجة المخاطرة الإجمالية
        total_risk = (
            risk_factors['cpu'] * self.weights['cpu'] +
            risk_factors['ram'] * self.weights['ram'] +
            risk_factors['temp'] * self.weights['temp'] +
            risk_factors['disk'] * self.weights['disk'] +
            risk_factors['battery'] * self.weights['battery']
        )
        
        return {
            'total_risk': round(total_risk, 2),
            'risk_factors': risk_factors
        }
    
    def predict_failure(self, device_data, historical_data=None):
        """التنبؤ باحتمالية الأعطال"""
        # حساب درجة المخاطرة الحالية
        risk_analysis = self.calculate_risk_score(device_data)
        
        # تحليل الاتجاهات إذا كانت هناك بيانات تاريخية
        trend_analysis = None
        if historical_data and len(historical_data) > 1:
            trend_analysis = self.analyze_trends(historical_data)
        
        # تحديد مستوى الخطر
        total_risk = risk_analysis['total_risk']
        
        if total_risk >= 80:
            risk_level = 'critical'
            failure_probability = min(95, 60 + (total_risk - 80) * 1.75)
        elif total_risk >= 50:
            risk_level = 'warning'
            failure_probability = 30 + (total_risk - 50) * 1.33
        else:
            risk_level = 'low'
            failure_probability = total_risk * 0.6
        
        # تعديل الاحتمالية بناءً على الاتجاهات
        if trend_analysis:
            if trend_analysis['trend'] == 'increasing':
                failure_probability += 10
            elif trend_analysis['trend'] == 'decreasing':
                failure_probability -= 5
        
        failure_probability = max(0, min(100, failure_probability))
        
        # تحديد التوقعات
        if failure_probability > 70:
            prediction = 'failure_imminent'
            time_to_failure = '1-3 أيام'
        elif failure_probability > 40:
            prediction = 'failure_likely'
            time_to_failure = '3-7 أيام'
        elif failure_probability > 20:
            prediction = 'failure_possible'
            time_to_failure = '1-2 أسابيع'
        else:
            prediction = 'normal'
            time_to_failure = 'لا توجد مشاكل متوقعة'
        
        # توليد التنبيهات
        alerts = self.generate_alerts(device_data, risk_analysis)
        
        # التوصيات
        recommendations = self.generate_recommendations(device_data, risk_analysis, risk_level)
        
        return {
            'risk_score': round(total_risk, 2),
            'risk_level': risk_level,
            'failure_probability': round(failure_probability, 2),
            'prediction': prediction,
            'time_to_failure': time_to_failure,
            'alerts': alerts,
            'recommendations': recommendations,
            'risk_factors': risk_analysis['risk_factors'],
            'trend_analysis': trend_analysis
        }
    
    def analyze_trends(self, historical_data):
        """تحليل الاتجاهات في البيانات التاريخية"""
        if len(historical_data) < 2:
            return None
        
        # حساب متوسط القيم
        cpu_avg = np.mean([d.get('cpu_usage', 0) for d in historical_data])
        ram_avg = np.mean([d.get('ram_usage', 0) for d in historical_data])
        temp_avg = np.mean([d.get('temperature', 0) for d in historical_data])
        
        # حساب الاتجاه (بسيط - مقارنة أول وآخر قيمة)
        recent_data = historical_data[-1]
        old_data = historical_data[0]
        
        cpu_trend = recent_data.get('cpu_usage', 0) - old_data.get('cpu_usage', 0)
        ram_trend = recent_data.get('ram_usage', 0) - old_data.get('ram_usage', 0)
        temp_trend = recent_data.get('temperature', 0) - old_data.get('temperature', 0)
        
        # تحديد الاتجاه العام
        overall_trend_value = (cpu_trend + ram_trend + temp_trend) / 3
        
        if overall_trend_value > 5:
            trend = 'increasing'
        elif overall_trend_value < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'cpu_trend': round(cpu_trend, 2),
            'ram_trend': round(ram_trend, 2),
            'temp_trend': round(temp_trend, 2),
            'averages': {
                'cpu': round(cpu_avg, 2),
                'ram': round(ram_avg, 2),
                'temp': round(temp_avg, 2)
            }
        }
    
    def generate_alerts(self, device_data, risk_analysis):
        """توليد التنبيهات بناءً على البيانات"""
        alerts = []
        
        # تنبيهات المعالج
        cpu_usage = device_data.get('cpu_usage', 0)
        if cpu_usage > self.thresholds['cpu_critical']:
            alerts.append({
                'type': 'cpu',
                'severity': 'critical',
                'message': f'استخدام المعالج حرج ({cpu_usage}%) - يحتاج إلى تدخل فوري',
                'action': 'فحص العمليات الثقيلة وإيقاف غير الضرورية'
            })
        elif cpu_usage > self.thresholds['cpu_warning']:
            alerts.append({
                'type': 'cpu',
                'severity': 'warning',
                'message': f'استخدام المعالج مرتفع ({cpu_usage}%) - يحتاج إلى مراقبة',
                'action': 'مراقبة العمليات الجارية'
            })
        
        # تنبيهات الذاكرة
        ram_usage = device_data.get('ram_usage', 0)
        if ram_usage > self.thresholds['ram_critical']:
            alerts.append({
                'type': 'ram',
                'severity': 'critical',
                'message': f'استخدام الذاكرة حرج ({ram_usage}%) - خطر نفاد الذاكرة',
                'action': 'إيقاف التطبيقات غير الضرورية أو إضافة ذاكرة'
            })
        elif ram_usage > self.thresholds['ram_warning']:
            alerts.append({
                'type': 'ram',
                'severity': 'warning',
                'message': f'استخدام الذاكرة مرتفع ({ram_usage}%) - مراقبة مستمرة',
                'action': 'مراجعة التطبيقات المفتوحة'
            })
        
        # تنبيهات درجة الحرارة
        temperature = device_data.get('temperature', 0)
        if temperature > self.thresholds['temp_critical']:
            alerts.append({
                'type': 'temperature',
                'severity': 'critical',
                'message': f'درجة الحرارة حرجة ({temperature}°C) - خطر تلف المكونات',
                'action': 'إيقاف الجهاز فوراً وفحص نظام التبريد'
            })
        elif temperature > self.thresholds['temp_warning']:
            alerts.append({
                'type': 'temperature',
                'severity': 'warning',
                'message': f'درجة الحرارة مرتفعة ({temperature}°C) - مراقبة مستمرة',
                'action': 'تنظيف المروحة وفحص نظام التبريد'
            })
        
        # تنبيهات القرص الصلب
        disk_usage = device_data.get('disk_usage', 0)
        if disk_usage > self.thresholds['disk_critical']:
            alerts.append({
                'type': 'disk',
                'severity': 'critical',
                'message': f'مساحة القرص الصلب منخفضة جداً ({disk_usage}%) - خطر نفاد المساحة',
                'action': 'حذف الملفات غير الضرورية أو توسيع السعة'
            })
        elif disk_usage > self.thresholds['disk_warning']:
            alerts.append({
                'type': 'disk',
                'severity': 'warning',
                'message': f'مساحة القرص الصلب منخفضة ({disk_usage}%) - يحتاج إلى تنظيف',
                'action': 'مراجعة الملفات وحذف غير الضرورية'
            })
        
        # تنبيهات البطارية
        if device_data.get('battery_level') is not None:
            battery_level = device_data['battery_level']
            if battery_level < self.thresholds['battery_critical']:
                alerts.append({
                    'type': 'battery',
                    'severity': 'critical',
                    'message': f'مستوى البطارية حرج ({battery_level}%) - يحتاج إلى شحن فوري',
                    'action': 'ربط الجهاز بالشاحن فوراً'
                })
            elif battery_level < self.thresholds['battery_warning']:
                alerts.append({
                    'type': 'battery',
                    'severity': 'warning',
                    'message': f'مستوى البطارية منخفض ({battery_level}%) - يُنصح بالشحن',
                    'action': 'ربط الجهاز بالشاحن قريباً'
                })
        
        return alerts
    
    def generate_recommendations(self, device_data, risk_analysis, risk_level):
        """توليد التوصيات بناءً على التحليل"""
        recommendations = []
        
        if risk_level == 'critical':
            recommendations.append({
                'priority': 'high',
                'title': 'تدخل فوري مطلوب',
                'description': 'الجهاز في حالة حرجة ويحتاج إلى تدخل فوري من الفني',
                'actions': [
                    'فحص الجهاز شخصياً',
                    'إيقاف التطبيقات الثقيلة',
                    'فحص نظام التبريد',
                    'مراجعة السجلات'
                ]
            })
        
        # توصيات بناءً على عوامل الخطر
        if risk_analysis['risk_factors']['cpu'] > 70:
            recommendations.append({
                'priority': 'medium',
                'title': 'تحسين أداء المعالج',
                'description': 'استخدام المعالج مرتفع جداً',
                'actions': [
                    'إغلاق التطبيقات غير الضرورية',
                    'فحص العمليات الخلفية',
                    'تحديث برامج مكافحة الفيروسات',
                    'تفكير في ترقية المعالج'
                ]
            })
        
        if risk_analysis['risk_factors']['ram'] > 70:
            recommendations.append({
                'priority': 'medium',
                'title': 'تحسين استخدام الذاكرة',
                'description': 'استخدام الذاكرة مرتفع جداً',
                'actions': [
                    'إغلاق التطبيقات المفتوحة',
                    'إعادة تشغيل الجهاز',
                    'تفكير في إضافة ذاكرة RAM',
                    'فحص تسريبات الذاكرة'
                ]
            })
        
        if risk_analysis['risk_factors']['temp'] > 70:
            recommendations.append({
                'priority': 'high',
                'title': 'تحسين التبريد',
                'description': 'درجة الحرارة مرتفعة',
                'actions': [
                    'تنظيف المروحة والفتحات',
                    'فحص معجون المعالج',
                    'تحسين تدفق الهواء',
                    'تفكير في تبريد إضافي'
                ]
            })
        
        if risk_analysis['risk_factors']['disk'] > 70:
            recommendations.append({
                'priority': 'medium',
                'title': 'تحرير مساحة القرص',
                'description': 'مساحة القرص الصلب منخفضة',
                'actions': [
                    'حذف الملفات المؤقتة',
                    'تنظيف سلة المحذوفات',
                    'إلغاء تثبيت البرامج غير المستخدمة',
                    'تفكير في قرص صلب أكبر'
                ]
            })
        
        return recommendations

# إنشاء كائن التنبؤ العالمي
predictor = AdvancedPredictor()

