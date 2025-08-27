#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
사용자 알림 프로필 관리 시스템 v1.0
개인화된 알림 설정과 프로필 관리
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class NotificationProfile:
    """개별 사용자 알림 프로필"""
    
    def __init__(self, profile_name: str, config: Dict[str, Any]):
        self.profile_name = profile_name
        self.config = config
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """프로필을 딕셔너리로 변환"""
        return {
            'profile_name': self.profile_name,
            'config': self.config,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationProfile':
        """딕셔너리에서 프로필 생성"""
        profile = cls(data['profile_name'], data['config'])
        profile.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        profile.last_updated = datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        return profile


class UserNotificationManager:
    """사용자별 알림 설정 관리자"""
    
    def __init__(self, config_file: str = 'user_profiles.json'):
        self.config_file = Path(config_file)
        self.profiles: Dict[str, NotificationProfile] = {}
        self.current_profile = None
        self.load_profiles()
        
    def load_profiles(self):
        """저장된 프로필들을 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for profile_data in data.get('profiles', []):
                        profile = NotificationProfile.from_dict(profile_data)
                        self.profiles[profile.profile_name] = profile
                    
                    # 현재 활성 프로필 설정
                    current_name = data.get('current_profile')
                    if current_name and current_name in self.profiles:
                        self.current_profile = self.profiles[current_name]
                        
                safe_print(f"✅ {len(self.profiles)}개 알림 프로필 로드 완료")
            except Exception as e:
                safe_print(f"❌ 프로필 로드 실패: {e}")
                self._create_default_profiles()
        else:
            self._create_default_profiles()
    
    def _create_default_profiles(self):
        """기본 프로필들 생성"""
        # 기본 프로필
        default_config = {
            'channels': {
                'web': {'enabled': True, 'sound': True, 'desktop': True},
                'telegram': {'enabled': False},
                'email': {'enabled': False},
                'tts': {'enabled': False}
            },
            'triggers': {
                'pair_detected': {'enabled': True, 'priority': 'high'},
                'long_streak': {'enabled': True, 'priority': 'medium', 'threshold': 5},
                'multiple_pairs': {'enabled': True, 'priority': 'high', 'threshold': 2},
                'hourly_summary': {'enabled': False}
            },
            'schedule': {
                'active_hours': {'start': '09:00', 'end': '23:00'},
                'weekend_enabled': True,
                'quiet_hours': {'start': '00:00', 'end': '08:00'}
            },
            'limits': {
                'max_per_hour': 20,
                'min_interval_seconds': 30,
                'cooldown_enabled': True
            }
        }
        
        # 조용한 프로필
        quiet_config = default_config.copy()
        quiet_config['channels']['web']['sound'] = False
        quiet_config['channels']['tts']['enabled'] = False
        quiet_config['triggers']['hourly_summary']['enabled'] = False
        quiet_config['limits']['max_per_hour'] = 10
        
        # 집중 모드 프로필
        focus_config = default_config.copy()
        focus_config['triggers'] = {
            'pair_detected': {'enabled': True, 'priority': 'high'},
            'long_streak': {'enabled': False},
            'multiple_pairs': {'enabled': True, 'priority': 'high', 'threshold': 3},
            'hourly_summary': {'enabled': False}
        }
        focus_config['limits']['max_per_hour'] = 5
        
        # 프로필 생성
        self.profiles['기본'] = NotificationProfile('기본', default_config)
        self.profiles['조용함'] = NotificationProfile('조용함', quiet_config)  
        self.profiles['집중모드'] = NotificationProfile('집중모드', focus_config)
        
        self.current_profile = self.profiles['기본']
        self.save_profiles()
        
        safe_print("✅ 기본 알림 프로필 3개 생성 완료")
    
    def create_profile(self, name: str, config: Dict[str, Any]) -> bool:
        """새 프로필 생성"""
        try:
            if name in self.profiles:
                safe_print(f"⚠️ 프로필 '{name}'이 이미 존재합니다")
                return False
                
            self.profiles[name] = NotificationProfile(name, config)
            self.save_profiles()
            safe_print(f"✅ 프로필 '{name}' 생성 완료")
            return True
        except Exception as e:
            safe_print(f"❌ 프로필 생성 실패: {e}")
            return False
    
    def switch_profile(self, name: str) -> bool:
        """프로필 변경"""
        if name not in self.profiles:
            safe_print(f"❌ 프로필 '{name}'을 찾을 수 없습니다")
            return False
            
        self.current_profile = self.profiles[name]
        self.save_profiles()
        safe_print(f"✅ 프로필을 '{name}'으로 변경했습니다")
        return True
    
    def update_profile(self, name: str, config: Dict[str, Any]) -> bool:
        """프로필 업데이트"""
        try:
            if name not in self.profiles:
                return self.create_profile(name, config)
                
            self.profiles[name].config = config
            self.profiles[name].last_updated = datetime.now()
            self.save_profiles()
            safe_print(f"✅ 프로필 '{name}' 업데이트 완료")
            return True
        except Exception as e:
            safe_print(f"❌ 프로필 업데이트 실패: {e}")
            return False
    
    def delete_profile(self, name: str) -> bool:
        """프로필 삭제"""
        if name not in self.profiles:
            return False
            
        if self.current_profile and self.current_profile.profile_name == name:
            # 현재 프로필이 삭제되는 경우 기본 프로필로 변경
            self.switch_profile('기본')
            
        del self.profiles[name]
        self.save_profiles()
        safe_print(f"✅ 프로필 '{name}' 삭제 완료")
        return True
    
    def get_current_config(self) -> Dict[str, Any]:
        """현재 활성 프로필의 설정 반환"""
        if not self.current_profile:
            return {}
        return self.current_profile.config
    
    def list_profiles(self) -> List[str]:
        """모든 프로필 이름 목록 반환"""
        return list(self.profiles.keys())
    
    def save_profiles(self):
        """프로필들을 파일에 저장"""
        try:
            data = {
                'current_profile': self.current_profile.profile_name if self.current_profile else None,
                'profiles': [profile.to_dict() for profile in self.profiles.values()],
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            safe_print(f"❌ 프로필 저장 실패: {e}")
    
    def should_send_notification(self, trigger_type: str, current_time: datetime = None) -> bool:
        """현재 설정에 따라 알림 전송 여부 결정"""
        if not self.current_profile:
            return True
            
        config = self.current_profile.config
        
        if current_time is None:
            current_time = datetime.now()
        
        # 트리거 활성화 확인
        triggers = config.get('triggers', {})
        if trigger_type not in triggers or not triggers[trigger_type].get('enabled', True):
            return False
        
        # 스케줄 확인
        schedule = config.get('schedule', {})
        if not self._is_in_schedule(current_time, schedule):
            return False
            
        return True
    
    def _is_in_schedule(self, current_time: datetime, schedule: Dict[str, Any]) -> bool:
        """현재 시간이 알림 스케줄 내인지 확인"""
        # 조용한 시간 확인
        quiet_hours = schedule.get('quiet_hours', {})
        if quiet_hours and self._is_in_time_range(current_time, quiet_hours):
            return False
        
        # 활성 시간 확인
        active_hours = schedule.get('active_hours', {})
        if active_hours and not self._is_in_time_range(current_time, active_hours):
            return False
        
        # 주말 확인
        if not schedule.get('weekend_enabled', True) and current_time.weekday() >= 5:
            return False
            
        return True
    
    def _is_in_time_range(self, current_time: datetime, time_range: Dict[str, str]) -> bool:
        """시간 범위 내인지 확인"""
        try:
            start_str = time_range.get('start', '00:00')
            end_str = time_range.get('end', '23:59')
            
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            current_time_only = current_time.time()
            
            if start_time <= end_time:
                return start_time <= current_time_only <= end_time
            else:  # 다음 날로 넘어가는 경우 (예: 23:00 - 06:00)
                return current_time_only >= start_time or current_time_only <= end_time
                
        except Exception:
            return True  # 파싱 오류 시 허용


# 전역 인스턴스
_notification_manager = None

def get_notification_manager() -> UserNotificationManager:
    """알림 관리자 인스턴스 반환"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = UserNotificationManager()
    return _notification_manager


if __name__ == "__main__":
    # 테스트 코드
    manager = get_notification_manager()
    
    safe_print("📋 사용 가능한 프로필:")
    for profile_name in manager.list_profiles():
        current = "★" if manager.current_profile and manager.current_profile.profile_name == profile_name else " "
        safe_print(f"{current} {profile_name}")
    
    safe_print(f"\n현재 프로필: {manager.current_profile.profile_name if manager.current_profile else '없음'}")
    
    # 알림 전송 테스트
    should_send = manager.should_send_notification('pair_detected')
    safe_print(f"페어 감지 알림 전송 가능: {'✅' if should_send else '❌'}")