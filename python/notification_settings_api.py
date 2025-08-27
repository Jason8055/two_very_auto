#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
알림 설정 API v1.0
웹 인터페이스용 알림 설정 관리 API
"""

from flask import Blueprint, request, jsonify
import json
import logging
from datetime import datetime
from user_notification_profiles import get_notification_manager
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

# Blueprint 생성
notification_api = Blueprint('notification_api', __name__, url_prefix='/api/notifications')


@notification_api.route('/profiles', methods=['GET'])
def get_profiles():
    """모든 알림 프로필 조회"""
    try:
        manager = get_notification_manager()
        profiles = []
        
        for name in manager.list_profiles():
            profile = manager.profiles[name]
            is_current = manager.current_profile and manager.current_profile.profile_name == name
            
            profiles.append({
                'name': name,
                'is_current': is_current,
                'config': profile.config,
                'created_at': profile.created_at.isoformat(),
                'last_updated': profile.last_updated.isoformat()
            })
        
        return jsonify({
            'success': True,
            'profiles': profiles,
            'current_profile': manager.current_profile.profile_name if manager.current_profile else None
        })
        
    except Exception as e:
        logger.error(f"프로필 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/profiles', methods=['POST'])
def create_profile():
    """새 알림 프로필 생성"""
    try:
        data = request.get_json()
        name = data.get('name')
        config = data.get('config')
        
        if not name or not config:
            return jsonify({'success': False, 'error': '프로필 이름과 설정이 필요합니다'}), 400
        
        manager = get_notification_manager()
        success = manager.create_profile(name, config)
        
        if success:
            return jsonify({'success': True, 'message': f'프로필 \'{name}\'이 생성되었습니다'})
        else:
            return jsonify({'success': False, 'error': '프로필 생성에 실패했습니다'}), 400
            
    except Exception as e:
        logger.error(f"프로필 생성 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/profiles/<profile_name>', methods=['PUT'])
def update_profile(profile_name):
    """기존 프로필 업데이트"""
    try:
        data = request.get_json()
        config = data.get('config')
        
        if not config:
            return jsonify({'success': False, 'error': '설정 정보가 필요합니다'}), 400
        
        manager = get_notification_manager()
        success = manager.update_profile(profile_name, config)
        
        if success:
            return jsonify({'success': True, 'message': f'프로필 \'{profile_name}\'이 업데이트되었습니다'})
        else:
            return jsonify({'success': False, 'error': '프로필 업데이트에 실패했습니다'}), 400
            
    except Exception as e:
        logger.error(f"프로필 업데이트 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/profiles/<profile_name>', methods=['DELETE'])
def delete_profile(profile_name):
    """프로필 삭제"""
    try:
        if profile_name == '기본':
            return jsonify({'success': False, 'error': '기본 프로필은 삭제할 수 없습니다'}), 400
        
        manager = get_notification_manager()
        success = manager.delete_profile(profile_name)
        
        if success:
            return jsonify({'success': True, 'message': f'프로필 \'{profile_name}\'이 삭제되었습니다'})
        else:
            return jsonify({'success': False, 'error': '프로필을 찾을 수 없습니다'}), 404
            
    except Exception as e:
        logger.error(f"프로필 삭제 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/current-profile', methods=['PUT'])
def switch_profile():
    """현재 활성 프로필 변경"""
    try:
        data = request.get_json()
        profile_name = data.get('profile_name')
        
        if not profile_name:
            return jsonify({'success': False, 'error': '프로필 이름이 필요합니다'}), 400
        
        manager = get_notification_manager()
        success = manager.switch_profile(profile_name)
        
        if success:
            return jsonify({'success': True, 'message': f'프로필을 \'{profile_name}\'으로 변경했습니다'})
        else:
            return jsonify({'success': False, 'error': '프로필을 찾을 수 없습니다'}), 404
            
    except Exception as e:
        logger.error(f"프로필 변경 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/test', methods=['POST'])
def test_notification():
    """테스트 알림 전송"""
    try:
        data = request.get_json()
        trigger_type = data.get('trigger_type', 'test')
        message = data.get('message', '테스트 알림입니다')
        
        manager = get_notification_manager()
        should_send = manager.should_send_notification(trigger_type)
        
        if should_send:
            # 실제 알림 전송 로직은 기존 시스템과 연동
            return jsonify({
                'success': True,
                'message': '테스트 알림이 전송되었습니다',
                'allowed': True
            })
        else:
            return jsonify({
                'success': True,
                'message': '현재 설정에 의해 알림이 차단되었습니다',
                'allowed': False
            })
            
    except Exception as e:
        logger.error(f"테스트 알림 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/status', methods=['GET'])
def get_notification_status():
    """현재 알림 시스템 상태 조회"""
    try:
        manager = get_notification_manager()
        current_time = datetime.now()
        
        # 각 트리거별 상태 확인
        trigger_status = {}
        if manager.current_profile:
            triggers = manager.current_profile.config.get('triggers', {})
            for trigger_name, trigger_config in triggers.items():
                trigger_status[trigger_name] = {
                    'enabled': trigger_config.get('enabled', False),
                    'allowed': manager.should_send_notification(trigger_name, current_time),
                    'priority': trigger_config.get('priority', 'medium'),
                    'threshold': trigger_config.get('threshold')
                }
        
        return jsonify({
            'success': True,
            'current_profile': manager.current_profile.profile_name if manager.current_profile else None,
            'current_time': current_time.isoformat(),
            'trigger_status': trigger_status,
            'total_profiles': len(manager.profiles)
        })
        
    except Exception as e:
        logger.error(f"알림 상태 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@notification_api.route('/default-templates', methods=['GET'])
def get_default_templates():
    """기본 프로필 템플릿 반환"""
    templates = {
        '게이밍_집중': {
            'description': '게임 중 집중을 위한 최소한의 알림',
            'config': {
                'channels': {
                    'web': {'enabled': True, 'sound': False, 'desktop': True},
                    'telegram': {'enabled': False},
                    'email': {'enabled': False},
                    'tts': {'enabled': False}
                },
                'triggers': {
                    'pair_detected': {'enabled': True, 'priority': 'high'},
                    'long_streak': {'enabled': False},
                    'multiple_pairs': {'enabled': True, 'priority': 'high', 'threshold': 3},
                    'hourly_summary': {'enabled': False}
                },
                'limits': {'max_per_hour': 5, 'min_interval_seconds': 60}
            }
        },
        '완전_알림': {
            'description': '모든 이벤트에 대한 완전한 알림',
            'config': {
                'channels': {
                    'web': {'enabled': True, 'sound': True, 'desktop': True},
                    'telegram': {'enabled': True},
                    'email': {'enabled': True},
                    'tts': {'enabled': True}
                },
                'triggers': {
                    'pair_detected': {'enabled': True, 'priority': 'high'},
                    'long_streak': {'enabled': True, 'priority': 'medium', 'threshold': 3},
                    'multiple_pairs': {'enabled': True, 'priority': 'high', 'threshold': 2},
                    'hourly_summary': {'enabled': True}
                },
                'limits': {'max_per_hour': 50, 'min_interval_seconds': 10}
            }
        },
        '수면_모드': {
            'description': '수면 시간을 위한 조용한 알림',
            'config': {
                'channels': {
                    'web': {'enabled': True, 'sound': False, 'desktop': False},
                    'telegram': {'enabled': False},
                    'email': {'enabled': True},
                    'tts': {'enabled': False}
                },
                'triggers': {
                    'pair_detected': {'enabled': True, 'priority': 'high'},
                    'long_streak': {'enabled': False},
                    'multiple_pairs': {'enabled': True, 'priority': 'high', 'threshold': 5},
                    'hourly_summary': {'enabled': False}
                },
                'schedule': {
                    'quiet_hours': {'start': '22:00', 'end': '08:00'}
                },
                'limits': {'max_per_hour': 3, 'min_interval_seconds': 300}
            }
        }
    }
    
    return jsonify({'success': True, 'templates': templates})


# 웹 인터페이스용 정적 파일들과 연동
def register_notification_api(app):
    """Flask 앱에 알림 API 등록"""
    app.register_blueprint(notification_api)
    safe_print("✅ 알림 설정 API 등록 완료")