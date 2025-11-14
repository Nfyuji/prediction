#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهة تدريب الذكاء الاصطناعي
"""

from flask import Blueprint, request, jsonify, session
from routes.auth import require_login, require_role
from ml_models.ml_trainer import ml_trainer

ml_training_bp = Blueprint('ml_training', __name__, url_prefix='/ml')

@ml_training_bp.route('/train', methods=['POST'])
@require_login
@require_role('admin', 'manager')
def train_model():
    """تدريب النموذج"""
    try:
        data = request.json or {}
        use_synthetic = data.get('use_synthetic', True)
        use_db = data.get('use_db', True)
        
        # تدريب النموذج
        success = ml_trainer.train_model(use_synthetic=use_synthetic, use_db=use_db)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'تم تدريب النموذج بنجاح',
                'model_info': ml_trainer.model_info
            })
        else:
            return jsonify({
                'success': False,
                'message': 'فشل في تدريب النموذج - لا توجد بيانات كافية'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تدريب النموذج: {str(e)}'
        }), 500

@ml_training_bp.route('/retrain', methods=['POST'])
@require_login
@require_role('admin', 'manager')
def retrain_model():
    """إعادة تدريب النموذج"""
    try:
        data = request.json or {}
        use_synthetic = data.get('use_synthetic', True)
        
        # إعادة تدريب النموذج
        success = ml_trainer.retrain_model(use_synthetic=use_synthetic)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'تم إعادة تدريب النموذج بنجاح',
                'model_info': ml_trainer.model_info
            })
        else:
            return jsonify({
                'success': False,
                'message': 'فشل في إعادة تدريب النموذج'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إعادة تدريب النموذج: {str(e)}'
        }), 500

@ml_training_bp.route('/status', methods=['GET'])
@require_login
def model_status():
    """الحصول على حالة النموذج"""
    try:
        return jsonify({
            'success': True,
            'model_info': ml_trainer.model_info,
            'model_loaded': ml_trainer.failure_classifier is not None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في الحصول على حالة النموذج: {str(e)}'
        }), 500

