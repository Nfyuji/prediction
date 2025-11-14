#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام تدريب الذكاء الاصطناعي
يتعلم من البيانات الفعلية ويتحسن مع الوقت
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error
import pickle
import os
import json
from datetime import datetime

# استيراد قاعدة البيانات بشكل آمن
try:
    from models.database import query_db
except ImportError:
    # إذا فشل الاستيراد، سنستخدم دالة بديلة
    query_db = None

class MLTrainer:
    """نظام تدريب التعلم الآلي"""
    
    def __init__(self):
        self.model_file = 'ml_models/trained_model.pkl'
        self.scaler_file = 'ml_models/scaler.pkl'
        self.model_info_file = 'ml_models/model_info.json'
        
        # النماذج
        self.failure_classifier = None  # للتنبؤ باحتمالية الأعطال
        self.risk_regressor = None  # لحساب درجة المخاطرة
        self.scaler = StandardScaler()
        
        # معلومات النموذج
        self.model_info = {
            'trained': False,
            'trained_at': None,
            'training_samples': 0,
            'accuracy': 0,
            'version': '1.0'
        }
        
        # تحميل النموذج إذا كان موجوداً
        self.load_model()
    
    def generate_synthetic_data(self, num_samples=1000):
        """إنشاء بيانات تدريب وهمية للبداية"""
        np.random.seed(42)  # للحصول على نتائج متسقة
        
        data = []
        labels = []  # 0 = healthy, 1 = warning, 2 = critical
        risk_scores = []
        
        for i in range(num_samples):
            # إنشاء بيانات واقعية
            cpu_usage = np.random.uniform(10, 100)
            ram_usage = np.random.uniform(20, 100)
            disk_usage = np.random.uniform(30, 100)
            temperature = np.random.uniform(40, 90)
            battery_level = np.random.choice([None, np.random.uniform(10, 100)])
            
            # حساب حالة الجهاز بناءً على البيانات
            risk_score = self._calculate_synthetic_risk(cpu_usage, ram_usage, disk_usage, temperature, battery_level)
            
            # تحديد التصنيف
            if risk_score >= 80:
                label = 2  # critical
            elif risk_score >= 50:
                label = 1  # warning
            else:
                label = 0  # healthy
            
            # إضافة بعض التباين
            if np.random.random() < 0.1:  # 10% أخطاء في التصنيف
                label = np.random.choice([0, 1, 2])
            
            data.append([cpu_usage, ram_usage, disk_usage, temperature, 
                        battery_level if battery_level else 100])  # 100 = desktop
            labels.append(label)
            risk_scores.append(risk_score)
        
        return np.array(data), np.array(labels), np.array(risk_scores)
    
    def _calculate_synthetic_risk(self, cpu, ram, disk, temp, battery):
        """حساب درجة المخاطرة للبيانات الوهمية"""
        risk = 0
        
        # CPU risk
        if cpu > 85:
            risk += 30
        elif cpu > 70:
            risk += 20
        else:
            risk += (cpu / 70) * 15
        
        # RAM risk
        if ram > 90:
            risk += 25
        elif ram > 75:
            risk += 15
        else:
            risk += (ram / 75) * 10
        
        # Temperature risk
        if temp > 80:
            risk += 25
        elif temp > 70:
            risk += 15
        else:
            risk += ((temp - 40) / 30) * 10
        
        # Disk risk
        if disk > 95:
            risk += 20
        elif disk > 85:
            risk += 10
        else:
            risk += ((disk - 30) / 55) * 10
        
        # Battery risk (if applicable)
        if battery is not None and battery < 100:
            if battery < 15:
                risk += 10
            elif battery < 25:
                risk += 5
            else:
                risk += ((100 - battery) / 75) * 5
        
        return min(100, risk)
    
    def load_training_data_from_db(self):
        """تحميل بيانات التدريب من قاعدة البيانات"""
        if query_db is None:
            return None, None, None
        
        try:
            # جلب جميع القياسات
            metrics = query_db('''
                SELECT dm.cpu_usage, dm.ram_usage, dm.disk_usage, 
                       dm.temperature, dm.battery_level, d.status
                FROM device_metrics dm
                JOIN devices d ON dm.device_id = d.id
                WHERE dm.cpu_usage IS NOT NULL 
                  AND dm.ram_usage IS NOT NULL
                  AND dm.disk_usage IS NOT NULL
                ORDER BY dm.timestamp DESC
                LIMIT 10000
            ''')
            
            if not metrics or len(metrics) < 10:
                return None, None, None
            
            data = []
            labels = []
            risk_scores = []
            
            for metric in metrics:
                cpu = metric['cpu_usage'] or 0
                ram = metric['ram_usage'] or 0
                disk = metric['disk_usage'] or 0
                temp = metric['temperature'] or 0
                battery = metric['battery_level'] if metric['battery_level'] is not None else 100
                status = metric['status']
                
                # تحويل الحالة إلى رقم
                if status == 'critical':
                    label = 2
                elif status == 'warning':
                    label = 1
                else:
                    label = 0
                
                # حساب درجة المخاطرة
                risk_score = self._calculate_synthetic_risk(cpu, ram, disk, temp, battery if battery < 100 else None)
                
                data.append([cpu, ram, disk, temp, battery])
                labels.append(label)
                risk_scores.append(risk_score)
            
            return np.array(data), np.array(labels), np.array(risk_scores)
        except Exception as e:
            print(f"خطأ في تحميل البيانات من قاعدة البيانات: {e}")
            return None, None, None
    
    def train_model(self, use_synthetic=False, use_db=True):
        """تدريب النموذج"""
        print("بدء تدريب النموذج...")
        
        # محاولة تحميل البيانات من قاعدة البيانات
        X, y, risk_scores = None, None, None
        
        if use_db:
            X, y, risk_scores = self.load_training_data_from_db()
            if X is not None and len(X) >= 10:
                print(f"تم تحميل {len(X)} عينة من قاعدة البيانات")
        
        # إذا لم تكن هناك بيانات كافية، استخدم البيانات الوهمية
        if X is None or len(X) < 10:
            if use_synthetic:
                print("استخدام بيانات تدريب وهمية...")
                X, y, risk_scores = self.generate_synthetic_data(1000)
                print(f"تم إنشاء {len(X)} عينة وهمية")
            else:
                print("لا توجد بيانات كافية للتدريب")
                return False
        
        # تقسيم البيانات
        if len(X) > 20:
            X_train, X_test, y_train, y_test, risk_train, risk_test = train_test_split(
                X, y, risk_scores, test_size=0.2, random_state=42
            )
        else:
            X_train, X_test = X, X
            y_train, y_test = y, y
            risk_train, risk_test = risk_scores, risk_scores
        
        # تطبيع البيانات
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # تدريب نموذج التصنيف (للتنبؤ بالحالة)
        print("تدريب نموذج التصنيف...")
        self.failure_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.failure_classifier.fit(X_train_scaled, y_train)
        
        # تقييم النموذج
        y_pred = self.failure_classifier.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"دقة النموذج: {accuracy:.2%}")
        
        # تدريب نموذج الانحدار (لحساب درجة المخاطرة)
        print("تدريب نموذج الانحدار...")
        self.risk_regressor = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            learning_rate=0.1
        )
        self.risk_regressor.fit(X_train_scaled, risk_train)
        
        # تقييم نموذج الانحدار
        risk_pred = self.risk_regressor.predict(X_test_scaled)
        mse = mean_squared_error(risk_test, risk_pred)
        rmse = np.sqrt(mse)
        print(f"خطأ النموذج (RMSE): {rmse:.2f}")
        
        # حفظ النموذج
        self.model_info = {
            'trained': True,
            'trained_at': datetime.now().isoformat(),
            'training_samples': len(X),
            'accuracy': float(accuracy),
            'rmse': float(rmse),
            'version': '1.0'
        }
        
        self.save_model()
        
        print("تم تدريب النموذج بنجاح!")
        return True
    
    def predict(self, device_data):
        """التنبؤ باستخدام النموذج المدرب"""
        if not self.model_info['trained'] or self.failure_classifier is None:
            # إذا لم يكن النموذج مدرباً، استخدم النظام الافتراضي
            return None
        
        try:
            # تحضير البيانات
            cpu = device_data.get('cpu_usage', 0) or 0
            ram = device_data.get('ram_usage', 0) or 0
            disk = device_data.get('disk_usage', 0) or 0
            temp = device_data.get('temperature', 0) or 0
            battery = device_data.get('battery_level', 100)
            if battery is None:
                battery = 100  # desktop
            
            X = np.array([[cpu, ram, disk, temp, battery]])
            X_scaled = self.scaler.transform(X)
            
            # التنبؤ بالحالة
            status_pred = self.failure_classifier.predict(X_scaled)[0]
            status_proba = self.failure_classifier.predict_proba(X_scaled)[0]
            
            # التنبؤ بدرجة المخاطرة
            risk_score = self.risk_regressor.predict(X_scaled)[0]
            risk_score = max(0, min(100, risk_score))
            
            # تحويل التصنيف إلى نص
            status_map = {0: 'healthy', 1: 'warning', 2: 'critical'}
            predicted_status = status_map[status_pred]
            
            # حساب احتمالية الأعطال
            failure_probability = status_proba[2] * 100  # احتمالية critical
            
            return {
                'predicted_status': predicted_status,
                'risk_score': round(float(risk_score), 2),
                'failure_probability': round(float(failure_probability), 2),
                'status_probabilities': {
                    'healthy': round(float(status_proba[0] * 100), 2),
                    'warning': round(float(status_proba[1] * 100), 2),
                    'critical': round(float(status_proba[2] * 100), 2)
                },
                'using_ml': True
            }
        except Exception as e:
            print(f"خطأ في التنبؤ: {e}")
            return None
    
    def save_model(self):
        """حفظ النموذج"""
        try:
            os.makedirs(os.path.dirname(self.model_file), exist_ok=True)
            
            # حفظ النماذج
            with open(self.model_file, 'wb') as f:
                pickle.dump({
                    'classifier': self.failure_classifier,
                    'regressor': self.risk_regressor
                }, f)
            
            # حفظ Scaler
            with open(self.scaler_file, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            # حفظ معلومات النموذج
            with open(self.model_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.model_info, f, ensure_ascii=False, indent=2)
            
            print("تم حفظ النموذج بنجاح")
        except Exception as e:
            print(f"خطأ في حفظ النموذج: {e}")
    
    def load_model(self):
        """تحميل النموذج"""
        try:
            if os.path.exists(self.model_file) and os.path.exists(self.scaler_file):
                # تحميل النماذج
                with open(self.model_file, 'rb') as f:
                    models = pickle.load(f)
                    self.failure_classifier = models['classifier']
                    self.risk_regressor = models['regressor']
                
                # تحميل Scaler
                with open(self.scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                # تحميل معلومات النموذج
                if os.path.exists(self.model_info_file):
                    with open(self.model_info_file, 'r', encoding='utf-8') as f:
                        self.model_info = json.load(f)
                
                print("تم تحميل النموذج بنجاح")
                return True
        except Exception as e:
            print(f"خطأ في تحميل النموذج: {e}")
        
        return False
    
    def retrain_model(self, use_synthetic=True):
        """إعادة تدريب النموذج"""
        return self.train_model(use_synthetic=use_synthetic, use_db=True)

# إنشاء كائن المدرب
ml_trainer = MLTrainer()

