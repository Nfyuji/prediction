#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام التنبؤ الذكي
يجمع بين النظام القائم على القواعد والتعلم الآلي
"""

from ml_models.predictor import AdvancedPredictor
from ml_models.ml_trainer import ml_trainer
from ml_models.ai_enhanced_predictor import AIEnhancedPredictor
import numpy as np

class SmartPredictor:
    """نظام تنبؤ ذكي يجمع بين الطرق المختلفة"""
    
    def __init__(self):
        self.rule_based = AdvancedPredictor()
        self.ai_enhanced = AIEnhancedPredictor()
        self.use_ml = True  # استخدام التعلم الآلي إذا كان متاحاً
    
    def predict_failure(self, device_data, historical_data=None):
        """التنبؤ باستخدام أفضل طريقة متاحة"""
        # محاولة استخدام التعلم الآلي أولاً
        if self.use_ml and ml_trainer.model_info.get('trained', False):
            ml_prediction = ml_trainer.predict(device_data)
            if ml_prediction:
                # استخدام نتائج التعلم الآلي كأساس
                base_prediction = self.ai_enhanced.predict_failure(device_data, historical_data)
                
                # دمج النتائج
                return self._merge_predictions(ml_prediction, base_prediction)
        
        # إذا لم يكن التعلم الآلي متاحاً، استخدم النظام المحسّن
        return self.ai_enhanced.predict_failure(device_data, historical_data)
    
    def _merge_predictions(self, ml_prediction, rule_based_prediction):
        """دمج نتائج التعلم الآلي مع النظام القائم على القواعد"""
        # استخدام درجة المخاطرة من التعلم الآلي
        ml_risk = ml_prediction['risk_score']
        rule_risk = rule_based_prediction['risk_score']
        
        # المتوسط المرجح (70% تعلم آلي، 30% قواعد)
        combined_risk = ml_risk * 0.7 + rule_risk * 0.3
        
        # استخدام احتمالية الأعطال من التعلم الآلي
        failure_probability = ml_prediction['failure_probability']
        
        # تحديد مستوى الخطر
        if combined_risk >= 80:
            risk_level = 'critical'
        elif combined_risk >= 50:
            risk_level = 'warning'
        else:
            risk_level = 'low'
        
        # استخدام التنبيهات والتوصيات من النظام القائم على القواعد
        # (لأنها أكثر تفصيلاً)
        alerts = rule_based_prediction.get('alerts', [])
        recommendations = rule_based_prediction.get('recommendations', [])
        
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
        
        return {
            'risk_score': round(combined_risk, 2),
            'risk_level': risk_level,
            'failure_probability': round(failure_probability, 2),
            'prediction': prediction,
            'time_to_failure': time_to_failure,
            'alerts': alerts,
            'recommendations': recommendations,
            'risk_factors': rule_based_prediction.get('risk_factors', {}),
            'trend_analysis': rule_based_prediction.get('trend_analysis'),
            'status_probabilities': ml_prediction.get('status_probabilities', {}),
            'using_ml': True,
            'ml_accuracy': ml_trainer.model_info.get('accuracy', 0)
        }

# إنشاء كائن التنبؤ الذكي
smart_predictor = SmartPredictor()

