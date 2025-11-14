#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نموذج الذكاء الاصطناعي المحسّن للتنبؤ بالمشاكل
نظام متقدم يستخدم خوارزميات التعلم الآلي للتنبؤ بالأعطال
"""

import numpy as np
from datetime import datetime, timedelta
import math
import json
import os

class AIEnhancedPredictor:
    """نموذج محسّن للتنبؤ بالمشاكل باستخدام خوارزميات متقدمة"""
    
    def __init__(self):
        # العتبات القابلة للتعديل (تتعلم من البيانات)
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
        
        # أوزان ديناميكية (تتحسن مع البيانات)
        self.weights = {
            'cpu': 0.25,
            'ram': 0.20,
            'temp': 0.30,
            'disk': 0.15,
            'battery': 0.10
        }
        
        # نماذج التعلم (يمكن إضافة نماذج sklearn هنا)
        self.models = {}
        self.training_data = []
        self.model_file = 'ml_models/trained_model.json'
        
        # تحميل النموذج المدرب إذا كان موجوداً
        self.load_model()
    
    def load_model(self):
        """تحميل النموذج المدرب"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.thresholds = data.get('thresholds', self.thresholds)
                    self.weights = data.get('weights', self.weights)
                    print("تم تحميل النموذج المدرب بنجاح")
            except Exception as e:
                print(f"خطأ في تحميل النموذج: {e}")
    
    def save_model(self):
        """حفظ النموذج المدرب"""
        try:
            os.makedirs(os.path.dirname(self.model_file), exist_ok=True)
            with open(self.model_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'thresholds': self.thresholds,
                    'weights': self.weights,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            print("تم حفظ النموذج بنجاح")
        except Exception as e:
            print(f"خطأ في حفظ النموذج: {e}")
    
    def calculate_advanced_risk_score(self, device_data, historical_data=None):
        """حساب درجة المخاطرة باستخدام خوارزميات متقدمة"""
        risk_factors = {}
        
        # تحليل متقدم للمعالج
        cpu_usage = device_data.get('cpu_usage', 0)
        cpu_risk = self._calculate_component_risk(
            cpu_usage, 
            self.thresholds['cpu_warning'], 
            self.thresholds['cpu_critical'],
            historical_data,
            'cpu_usage'
        )
        risk_factors['cpu'] = cpu_risk
        
        # تحليل متقدم للذاكرة
        ram_usage = device_data.get('ram_usage', 0)
        ram_risk = self._calculate_component_risk(
            ram_usage,
            self.thresholds['ram_warning'],
            self.thresholds['ram_critical'],
            historical_data,
            'ram_usage'
        )
        risk_factors['ram'] = ram_risk
        
        # تحليل متقدم لدرجة الحرارة
        temperature = device_data.get('temperature', 0)
        temp_risk = self._calculate_component_risk(
            temperature,
            self.thresholds['temp_warning'],
            self.thresholds['temp_critical'],
            historical_data,
            'temperature'
        )
        risk_factors['temp'] = temp_risk
        
        # تحليل متقدم للقرص الصلب
        disk_usage = device_data.get('disk_usage', 0)
        disk_risk = self._calculate_component_risk(
            disk_usage,
            self.thresholds['disk_warning'],
            self.thresholds['disk_critical'],
            historical_data,
            'disk_usage'
        )
        risk_factors['disk'] = disk_risk
        
        # تحليل البطارية
        battery_risk = 0
        if device_data.get('battery_level') is not None:
            battery_level = device_data['battery_level']
            battery_risk = self._calculate_battery_risk(battery_level)
        risk_factors['battery'] = battery_risk
        
        # حساب درجة المخاطرة الإجمالية مع مراعاة التفاعلات
        total_risk = self._calculate_weighted_risk(risk_factors, device_data)
        
        return {
            'total_risk': round(total_risk, 2),
            'risk_factors': risk_factors
        }
    
    def _calculate_component_risk(self, current_value, warning_threshold, critical_threshold, historical_data, metric_name):
        """حساب درجة الخطر لمكون معين مع مراعاة الاتجاهات"""
        base_risk = 0
        
        # حساب الخطر الأساسي
        if current_value > critical_threshold:
            base_risk = 100
        elif current_value > warning_threshold:
            base_risk = 50 + ((current_value - warning_threshold) / (critical_threshold - warning_threshold)) * 50
        else:
            base_risk = (current_value / warning_threshold) * 50
        
        # تعديل بناءً على الاتجاهات
        if historical_data and len(historical_data) > 1:
            trend_factor = self._calculate_trend_factor(historical_data, metric_name)
            # إذا كان الاتجاه تصاعدي، تزيد المخاطرة
            if trend_factor > 0:
                base_risk = min(100, base_risk + trend_factor * 20)
            # إذا كان الاتجاه تنازلي، تقل المخاطرة قليلاً
            elif trend_factor < 0:
                base_risk = max(0, base_risk + trend_factor * 10)
        
        # تعديل بناءً على التقلبات
        if historical_data and len(historical_data) > 3:
            volatility = self._calculate_volatility(historical_data, metric_name)
            if volatility > 0.3:  # تقلبات عالية
                base_risk = min(100, base_risk + 10)
        
        return min(100, max(0, base_risk))
    
    def _calculate_trend_factor(self, historical_data, metric_name):
        """حساب عامل الاتجاه (-1 إلى 1)"""
        if len(historical_data) < 2:
            return 0
        
        values = [d.get(metric_name, 0) for d in historical_data]
        if len(values) < 2:
            return 0
        
        # استخدام الانحدار الخطي البسيط
        x = np.arange(len(values))
        y = np.array(values)
        
        # حساب الميل
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - (np.sum(x))**2)
        
        # تطبيع الميل
        if len(values) > 0:
            avg_value = np.mean(values)
            if avg_value > 0:
                normalized_slope = slope / avg_value
                return np.tanh(normalized_slope * 10)  # تطبيع بين -1 و 1
        
        return 0
    
    def _calculate_volatility(self, historical_data, metric_name):
        """حساب التقلبات (0 إلى 1)"""
        if len(historical_data) < 2:
            return 0
        
        values = [d.get(metric_name, 0) for d in historical_data]
        if len(values) < 2:
            return 0
        
        std_dev = np.std(values)
        mean_value = np.mean(values)
        
        if mean_value > 0:
            coefficient_of_variation = std_dev / mean_value
            return min(1.0, coefficient_of_variation)
        
        return 0
    
    def _calculate_battery_risk(self, battery_level):
        """حساب خطر البطارية"""
        if battery_level < self.thresholds['battery_critical']:
            return 100
        elif battery_level < self.thresholds['battery_warning']:
            return 50 + ((self.thresholds['battery_warning'] - battery_level) / 
                        (self.thresholds['battery_warning'] - self.thresholds['battery_critical'])) * 50
        else:
            return (100 - battery_level) / 75 * 50
    
    def _calculate_weighted_risk(self, risk_factors, device_data):
        """حساب المخاطرة المرجحة مع مراعاة التفاعلات بين المكونات"""
        # حساب المخاطرة الأساسية
        base_risk = (
            risk_factors['cpu'] * self.weights['cpu'] +
            risk_factors['ram'] * self.weights['ram'] +
            risk_factors['temp'] * self.weights['temp'] +
            risk_factors['disk'] * self.weights['disk'] +
            risk_factors['battery'] * self.weights['battery']
        )
        
        # تعديل بناءً على التفاعلات الخطيرة
        interaction_penalty = 0
        
        # إذا كان CPU و RAM مرتفعين معاً
        if risk_factors['cpu'] > 70 and risk_factors['ram'] > 70:
            interaction_penalty += 10
        
        # إذا كانت الحرارة مرتفعة مع CPU مرتفع
        if risk_factors['temp'] > 70 and risk_factors['cpu'] > 70:
            interaction_penalty += 15
        
        # إذا كان القرص ممتلئ والذاكرة مرتفعة
        if risk_factors['disk'] > 80 and risk_factors['ram'] > 70:
            interaction_penalty += 5
        
        return min(100, base_risk + interaction_penalty)
    
    def predict_failure(self, device_data, historical_data=None):
        """التنبؤ باحتمالية الأعطال باستخدام خوارزميات متقدمة"""
        # حساب درجة المخاطرة
        risk_analysis = self.calculate_advanced_risk_score(device_data, historical_data)
        
        # تحليل الاتجاهات المتقدم
        trend_analysis = None
        if historical_data and len(historical_data) > 1:
            trend_analysis = self.analyze_advanced_trends(historical_data)
        
        # حساب احتمالية الأعطال
        total_risk = risk_analysis['total_risk']
        failure_probability = self._calculate_failure_probability(total_risk, trend_analysis, device_data)
        
        # تحديد مستوى الخطر
        if total_risk >= 80:
            risk_level = 'critical'
        elif total_risk >= 50:
            risk_level = 'warning'
        else:
            risk_level = 'low'
        
        # تحديد التوقعات
        prediction, time_to_failure = self._predict_failure_timing(failure_probability, trend_analysis)
        
        # توليد التنبيهات
        alerts = self.generate_smart_alerts(device_data, risk_analysis, trend_analysis)
        
        # التوصيات الذكية
        recommendations = self.generate_intelligent_recommendations(
            device_data, risk_analysis, risk_level, trend_analysis
        )
        
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
    
    def _calculate_failure_probability(self, total_risk, trend_analysis, device_data):
        """حساب احتمالية الأعطال باستخدام نموذج متقدم"""
        # نموذج احتمالي مبني على البيانات
        if total_risk >= 80:
            base_probability = 60 + (total_risk - 80) * 1.75
        elif total_risk >= 50:
            base_probability = 30 + (total_risk - 50) * 1.33
        else:
            base_probability = total_risk * 0.6
        
        # تعديل بناءً على الاتجاهات
        if trend_analysis:
            if trend_analysis['trend'] == 'increasing':
                base_probability += 15
            elif trend_analysis['trend'] == 'decreasing':
                base_probability -= 8
            elif trend_analysis['trend'] == 'volatile':
                base_probability += 5
        
        # تعديل بناءً على عمر البيانات
        # (يمكن إضافة معلومات عن آخر تحديث)
        
        return max(0, min(100, base_probability))
    
    def _predict_failure_timing(self, failure_probability, trend_analysis):
        """التنبؤ بوقت الأعطال المحتمل"""
        if failure_probability > 70:
            if trend_analysis and trend_analysis['trend'] == 'increasing':
                return 'failure_imminent', '1-2 أيام'
            else:
                return 'failure_imminent', '2-4 أيام'
        elif failure_probability > 40:
            return 'failure_likely', '3-7 أيام'
        elif failure_probability > 20:
            return 'failure_possible', '1-2 أسابيع'
        else:
            return 'normal', 'لا توجد مشاكل متوقعة'
    
    def analyze_advanced_trends(self, historical_data):
        """تحليل الاتجاهات المتقدم"""
        if len(historical_data) < 2:
            return None
        
        # حساب المتوسطات
        cpu_values = [d.get('cpu_usage', 0) for d in historical_data]
        ram_values = [d.get('ram_usage', 0) for d in historical_data]
        temp_values = [d.get('temperature', 0) for d in historical_data]
        
        cpu_avg = np.mean(cpu_values)
        ram_avg = np.mean(ram_values)
        temp_avg = np.mean(temp_values)
        
        # حساب الاتجاهات باستخدام الانحدار
        cpu_trend = self._calculate_trend_factor(historical_data, 'cpu_usage')
        ram_trend = self._calculate_trend_factor(historical_data, 'ram_usage')
        temp_trend = self._calculate_trend_factor(historical_data, 'temperature')
        
        # تحديد الاتجاه العام
        overall_trend_value = (cpu_trend + ram_trend + temp_trend) / 3
        
        if overall_trend_value > 0.3:
            trend = 'increasing'
        elif overall_trend_value < -0.3:
            trend = 'decreasing'
        elif abs(overall_trend_value) < 0.1:
            trend = 'stable'
        else:
            trend = 'volatile'
        
        # حساب التقلبات
        cpu_volatility = self._calculate_volatility(historical_data, 'cpu_usage')
        ram_volatility = self._calculate_volatility(historical_data, 'ram_usage')
        temp_volatility = self._calculate_volatility(historical_data, 'temperature')
        
        return {
            'trend': trend,
            'cpu_trend': round(cpu_trend, 3),
            'ram_trend': round(ram_trend, 3),
            'temp_trend': round(temp_trend, 3),
            'cpu_volatility': round(cpu_volatility, 3),
            'ram_volatility': round(ram_volatility, 3),
            'temp_volatility': round(temp_volatility, 3),
            'averages': {
                'cpu': round(cpu_avg, 2),
                'ram': round(ram_avg, 2),
                'temp': round(temp_avg, 2)
            }
        }
    
    def generate_smart_alerts(self, device_data, risk_analysis, trend_analysis):
        """توليد تنبيهات ذكية بناءً على التحليل المتقدم"""
        alerts = []
        risk_factors = risk_analysis['risk_factors']
        
        # تنبيهات المعالج
        cpu_usage = device_data.get('cpu_usage', 0)
        if risk_factors['cpu'] > 70:
            severity = 'critical' if risk_factors['cpu'] > 85 else 'warning'
            message = f'استخدام المعالج {severity == "critical" and "حرج" or "مرتفع"} ({cpu_usage}%)'
            if trend_analysis and trend_analysis['cpu_trend'] > 0.2:
                message += ' - الاتجاه تصاعدي!'
            alerts.append({
                'type': 'cpu',
                'severity': severity,
                'message': message,
                'action': 'فحص العمليات الثقيلة وإيقاف غير الضرورية'
            })
        
        # تنبيهات الذاكرة
        ram_usage = device_data.get('ram_usage', 0)
        if risk_factors['ram'] > 70:
            severity = 'critical' if risk_factors['ram'] > 85 else 'warning'
            message = f'استخدام الذاكرة {severity == "critical" and "حرج" or "مرتفع"} ({ram_usage}%)'
            alerts.append({
                'type': 'ram',
                'severity': severity,
                'message': message,
                'action': 'إيقاف التطبيقات غير الضرورية أو إضافة ذاكرة'
            })
        
        # تنبيهات درجة الحرارة
        temperature = device_data.get('temperature', 0)
        if risk_factors['temp'] > 70:
            severity = 'critical' if risk_factors['temp'] > 85 else 'warning'
            message = f'درجة الحرارة {severity == "critical" and "حرجة" or "مرتفعة"} ({temperature}°C)'
            alerts.append({
                'type': 'temperature',
                'severity': severity,
                'message': message,
                'action': 'فحص نظام التبريد فوراً'
            })
        
        # تنبيهات القرص الصلب
        disk_usage = device_data.get('disk_usage', 0)
        if risk_factors['disk'] > 70:
            severity = 'critical' if risk_factors['disk'] > 90 else 'warning'
            message = f'مساحة القرص الصلب {severity == "critical" and "منخفضة جداً" or "منخفضة"} ({disk_usage}%)'
            alerts.append({
                'type': 'disk',
                'severity': severity,
                'message': message,
                'action': 'حذف الملفات غير الضرورية أو توسيع السعة'
            })
        
        # تنبيهات البطارية
        if device_data.get('battery_level') is not None:
            battery_level = device_data['battery_level']
            if risk_factors['battery'] > 70:
                severity = 'critical' if risk_factors['battery'] > 85 else 'warning'
                message = f'مستوى البطارية {severity == "critical" and "حرج" or "منخفض"} ({battery_level}%)'
                alerts.append({
                    'type': 'battery',
                    'severity': severity,
                    'message': message,
                    'action': 'ربط الجهاز بالشاحن'
                })
        
        return alerts
    
    def generate_intelligent_recommendations(self, device_data, risk_analysis, risk_level, trend_analysis):
        """توليد توصيات ذكية بناءً على التحليل المتقدم"""
        recommendations = []
        
        if risk_level == 'critical':
            recommendations.append({
                'priority': 'high',
                'title': 'تدخل فوري مطلوب',
                'description': 'الجهاز في حالة حرجة ويحتاج إلى تدخل فوري',
                'actions': [
                    'فحص الجهاز شخصياً',
                    'إيقاف التطبيقات الثقيلة',
                    'فحص نظام التبريد',
                    'مراجعة السجلات'
                ]
            })
        
        # توصيات بناءً على عوامل الخطر
        risk_factors = risk_analysis['risk_factors']
        
        if risk_factors['cpu'] > 70:
            recommendations.append({
                'priority': 'medium',
                'title': 'تحسين أداء المعالج',
                'description': 'استخدام المعالج مرتفع',
                'actions': [
                    'إغلاق التطبيقات غير الضرورية',
                    'فحص العمليات الخلفية',
                    'تحديث برامج مكافحة الفيروسات'
                ]
            })
        
        if risk_factors['ram'] > 70:
            recommendations.append({
                'priority': 'medium',
                'title': 'تحسين استخدام الذاكرة',
                'description': 'استخدام الذاكرة مرتفع',
                'actions': [
                    'إغلاق التطبيقات المفتوحة',
                    'إعادة تشغيل الجهاز',
                    'تفكير في إضافة ذاكرة RAM'
                ]
            })
        
        if risk_factors['temp'] > 70:
            recommendations.append({
                'priority': 'high',
                'title': 'تحسين التبريد',
                'description': 'درجة الحرارة مرتفعة',
                'actions': [
                    'تنظيف المروحة والفتحات',
                    'فحص معجون المعالج',
                    'تحسين تدفق الهواء'
                ]
            })
        
        if risk_factors['disk'] > 70:
            recommendations.append({
                'priority': 'medium',
                'title': 'تحرير مساحة القرص',
                'description': 'مساحة القرص الصلب منخفضة',
                'actions': [
                    'حذف الملفات المؤقتة',
                    'تنظيف سلة المحذوفات',
                    'إلغاء تثبيت البرامج غير المستخدمة'
                ]
            })
        
        # توصيات بناءً على الاتجاهات
        if trend_analysis:
            if trend_analysis['trend'] == 'increasing':
                recommendations.append({
                    'priority': 'high',
                    'title': 'اتجاه تصاعدي في الاستخدام',
                    'description': 'يبدو أن الاستخدام في زيادة مستمرة',
                    'actions': [
                        'مراقبة مستمرة مطلوبة',
                        'التخطيط للترقية',
                        'فحص التطبيقات الجديدة'
                    ]
                })
            elif trend_analysis['trend'] == 'volatile':
                recommendations.append({
                    'priority': 'medium',
                    'title': 'تقلبات عالية في الأداء',
                    'description': 'هناك تقلبات كبيرة في استخدام الموارد',
                    'actions': [
                        'فحص البرامج الخلفية',
                        'مراجعة المهام المجدولة',
                        'فحص الفيروسات'
                    ]
                })
        
        return recommendations
    
    def train_model(self, training_data):
        """تدريب النموذج على البيانات (يمكن تطويره لاحقاً)"""
        # هذا يمكن تطويره لاستخدام sklearn أو tensorflow
        # حالياً، نحفظ البيانات للتحليل لاحقاً
        self.training_data.extend(training_data)
        
        # يمكن إضافة منطق التدريب هنا
        # مثال: تعديل الأوزان بناءً على البيانات
        
        return True

# إنشاء كائن التنبؤ المحسّن
ai_predictor = AIEnhancedPredictor()

