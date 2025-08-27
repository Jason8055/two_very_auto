#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
웹 기반 설정 관리 시스템 v1.0
실시간 설정 변경, 알림 규칙 관리, AI 모델 파라미터 조정
"""

import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SettingsManager:
    """설정 관리 시스템"""
    
    def __init__(self, settings_file: str = "system_settings.json"):
        self.settings_file = Path(settings_file)
        self.settings_cache = {}
        self.change_listeners = []
        self.settings_history = []
        
        # 기본 설정 스키마
        self.default_settings = {
            "system": {
                "monitoring_interval": 1.0,
                "max_error_history": 1000,
                "log_level": "INFO",
                "auto_backup_enabled": True,
                "debug_mode": False
            },
            "notifications": {
                "enabled": True,
                "channels": {
                    "desktop": {"enabled": True},
                    "sound": {"enabled": True, "volume": 0.7},
                    "vibration": {"enabled": True},
                    "kakao": {"enabled": False, "api_key": ""},
                    "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
                    "email": {"enabled": False, "smtp_server": "", "username": "", "password": ""}
                },
                "alert_rules": {
                    "consecutive_pairs": {"limit": 3, "enabled": True},
                    "no_pairs_timeout": {"limit": 100, "enabled": True},
                    "high_activity": {"games_per_minute": 10, "enabled": True},
                    "table_inactive": {"minutes": 5, "enabled": True}
                }
            },
            "ai_model": {
                "tensorflow_enabled": True,
                "model_path": "pair_prediction_model.h5",
                "confidence_threshold": 0.7,
                "training_enabled": True,
                "auto_retrain_interval": 24,  # hours
                "feature_engineering": {
                    "sequence_length": 10,
                    "max_data_points": 50
                },
                "neural_network": {
                    "architecture": [64, 128, 64, 32],
                    "dropout_rate": 0.3,
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 100,
                    "early_stopping_patience": 10
                }
            },
            "charts": {
                "max_data_points": 50,
                "update_interval": 1000,  # ms
                "chart_types": {
                    "timeline": {"enabled": True, "hours_range": 24},
                    "hourly": {"enabled": True, "hours_range": 24},
                    "comparison": {"enabled": True},
                    "distribution": {"enabled": True}
                },
                "theme": {
                    "auto_theme": True,
                    "colors": {
                        "primary": "#3b82f6",
                        "secondary": "#ef4444",
                        "success": "#10b981",
                        "warning": "#f59e0b",
                        "danger": "#ef4444"
                    }
                }
            },
            "dashboard": {
                "websocket_ping_interval": 10,
                "websocket_timeout": 30,
                "max_connections": 100,
                "data_retention": {
                    "live_games": 100,
                    "pair_alerts": 50,
                    "alert_history": 200
                },
                "performance_thresholds": {
                    "cpu_warning": 80,
                    "cpu_critical": 90,
                    "memory_warning": 85,
                    "memory_critical": 95,
                    "prediction_time_warning": 0.1
                }
            },
            "database": {
                "path": "two_very_auto.db",
                "connection_timeout": 10,
                "auto_vacuum": True,
                "backup_interval": 300,  # seconds
                "max_backup_files": 10
            }
        }
        
        self._load_settings()
        safe_print("⚙️ 설정 관리 시스템 초기화 완료")
    
    def _load_settings(self):
        """설정 파일 로드"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                
                # 기본 설정과 병합
                self.settings_cache = self._merge_settings(self.default_settings, saved_settings)
                safe_print(f"✅ 설정 파일 로드 완료: {self.settings_file}")
            else:
                self.settings_cache = self.default_settings.copy()
                self._save_settings()
                safe_print(f"📝 기본 설정 파일 생성: {self.settings_file}")
                
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            self.settings_cache = self.default_settings.copy()
    
    def _merge_settings(self, default: Dict, saved: Dict) -> Dict:
        """기본 설정과 저장된 설정 병합"""
        result = default.copy()
        
        for key, value in saved.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_settings(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def _save_settings(self):
        """설정 파일 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings_cache, f, indent=2, ensure_ascii=False)
                
            safe_print(f"💾 설정 파일 저장 완료: {self.settings_file}")
            
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def get_setting(self, path: str, default=None):
        """설정 값 가져오기 (점 표기법 지원)"""
        try:
            keys = path.split('.')
            value = self.settings_cache
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"설정 값 가져오기 실패 ({path}): {e}")
            return default
    
    def set_setting(self, path: str, value: Any, save_immediately: bool = True) -> bool:
        """설정 값 변경 (점 표기법 지원)"""
        try:
            keys = path.split('.')
            target = self.settings_cache
            
            # 변경 전 값 저장
            old_value = self.get_setting(path)
            
            # 중첩 딕셔너리 탐색
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            
            # 값 설정
            target[keys[-1]] = value
            
            # 변경 기록
            change_record = {
                'timestamp': datetime.now().isoformat(),
                'path': path,
                'old_value': old_value,
                'new_value': value,
                'user': 'system'  # 향후 사용자 추적 가능
            }
            
            self.settings_history.append(change_record)
            
            # 변경 리스너 호출
            for listener in self.change_listeners:
                try:
                    listener(path, old_value, value)
                except Exception as e:
                    logger.error(f"설정 변경 리스너 오류: {e}")
            
            # 즉시 저장
            if save_immediately:
                self._save_settings()
            
            safe_print(f"⚙️ 설정 변경: {path} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"설정 값 변경 실패 ({path}): {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """모든 설정 반환"""
        return self.settings_cache.copy()
    
    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """카테고리별 설정 반환"""
        return self.settings_cache.get(category, {}).copy()
    
    def update_settings(self, settings: Dict[str, Any], save_immediately: bool = True) -> bool:
        """설정 일괄 업데이트"""
        try:
            for path, value in self._flatten_dict(settings).items():
                self.set_setting(path, value, save_immediately=False)
            
            if save_immediately:
                self._save_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"설정 일괄 업데이트 실패: {e}")
            return False
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """중첩 딕셔너리를 평면화"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def reset_to_default(self, category: Optional[str] = None) -> bool:
        """기본 설정으로 초기화"""
        try:
            if category:
                if category in self.default_settings:
                    self.settings_cache[category] = self.default_settings[category].copy()
                    safe_print(f"🔄 {category} 설정 초기화 완료")
                else:
                    return False
            else:
                self.settings_cache = self.default_settings.copy()
                safe_print("🔄 모든 설정 초기화 완료")
            
            self._save_settings()
            return True
            
        except Exception as e:
            logger.error(f"설정 초기화 실패: {e}")
            return False
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """설정 유효성 검사"""
        errors = {
            'system': [],
            'notifications': [],
            'ai_model': [],
            'charts': [],
            'dashboard': [],
            'database': []
        }
        
        # 시스템 설정 검사
        monitoring_interval = self.get_setting('system.monitoring_interval', 1.0)
        if not isinstance(monitoring_interval, (int, float)) or monitoring_interval <= 0:
            errors['system'].append('monitoring_interval은 양수여야 합니다')
        
        # 알림 설정 검사
        if self.get_setting('notifications.enabled', True):
            channels = self.get_setting('notifications.channels', {})
            if isinstance(channels, dict):
                # 카카오 설정 검사
                if channels.get('kakao', {}).get('enabled', False):
                    api_key = channels.get('kakao', {}).get('api_key', '')
                    if not api_key or not isinstance(api_key, str):
                        errors['notifications'].append('카카오 API 키가 필요합니다')
                
                # 텔레그램 설정 검사
                if channels.get('telegram', {}).get('enabled', False):
                    bot_token = channels.get('telegram', {}).get('bot_token', '')
                    chat_id = channels.get('telegram', {}).get('chat_id', '')
                    if not bot_token or not chat_id:
                        errors['notifications'].append('텔레그램 봇 토큰과 채팅 ID가 필요합니다')
        
        # AI 모델 설정 검사
        confidence_threshold = self.get_setting('ai_model.confidence_threshold', 0.7)
        if not isinstance(confidence_threshold, (int, float)) or not (0 <= confidence_threshold <= 1):
            errors['ai_model'].append('confidence_threshold는 0과 1 사이의 값이어야 합니다')
        
        learning_rate = self.get_setting('ai_model.neural_network.learning_rate', 0.001)
        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0:
            errors['ai_model'].append('learning_rate는 양수여야 합니다')
        
        # 차트 설정 검사
        max_data_points = self.get_setting('charts.max_data_points', 50)
        if not isinstance(max_data_points, int) or max_data_points <= 0:
            errors['charts'].append('max_data_points는 양의 정수여야 합니다')
        
        # 대시보드 설정 검사
        max_connections = self.get_setting('dashboard.max_connections', 100)
        if not isinstance(max_connections, int) or max_connections <= 0:
            errors['dashboard'].append('max_connections는 양의 정수여야 합니다')
        
        # 데이터베이스 설정 검사
        db_path = self.get_setting('database.path', 'two_very_auto.db')
        if not isinstance(db_path, str) or not db_path:
            errors['database'].append('데이터베이스 경로가 필요합니다')
        
        # 빈 오류 목록 제거
        return {k: v for k, v in errors.items() if v}
    
    def add_change_listener(self, listener: callable):
        """설정 변경 리스너 추가"""
        self.change_listeners.append(listener)
    
    def remove_change_listener(self, listener: callable):
        """설정 변경 리스너 제거"""
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)
    
    def get_change_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """설정 변경 히스토리 반환"""
        history = list(reversed(self.settings_history))
        return history[:limit] if limit else history
    
    def export_settings(self, file_path: Optional[str] = None) -> str:
        """설정 내보내기"""
        if file_path is None:
            file_path = f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'settings': self.settings_cache,
                'change_history': self.settings_history[-50:]  # 최근 50개 변경사항
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            safe_print(f"📤 설정 내보내기 완료: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"설정 내보내기 실패: {e}")
            return ""
    
    def import_settings(self, file_path: str) -> bool:
        """설정 가져오기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'settings' in import_data:
                self.settings_cache = import_data['settings']
                self._save_settings()
                
                safe_print(f"📥 설정 가져오기 완료: {file_path}")
                return True
            else:
                logger.error("유효하지 않은 설정 파일 형식")
                return False
                
        except Exception as e:
            logger.error(f"설정 가져오기 실패: {e}")
            return False


class WebSettingsAPI:
    """웹 인터페이스용 설정 API"""
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
        
    def get_settings_schema(self) -> Dict[str, Any]:
        """설정 스키마 반환 (웹 폼 생성용)"""
        return {
            "system": {
                "title": "시스템 설정",
                "fields": {
                    "monitoring_interval": {
                        "type": "number",
                        "title": "모니터링 간격 (초)",
                        "min": 0.1,
                        "max": 10.0,
                        "step": 0.1,
                        "description": "성능 모니터링 실행 간격"
                    },
                    "max_error_history": {
                        "type": "integer",
                        "title": "최대 에러 기록 수",
                        "min": 100,
                        "max": 10000,
                        "step": 100,
                        "description": "메모리에 보관할 에러 기록의 최대 개수"
                    },
                    "log_level": {
                        "type": "select",
                        "title": "로그 레벨",
                        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        "description": "시스템 로그 출력 레벨"
                    },
                    "auto_backup_enabled": {
                        "type": "boolean",
                        "title": "자동 백업 활성화",
                        "description": "자동 백업 시스템 사용 여부"
                    },
                    "debug_mode": {
                        "type": "boolean",
                        "title": "디버그 모드",
                        "description": "개발자 모드 활성화"
                    }
                }
            },
            "notifications": {
                "title": "알림 설정",
                "fields": {
                    "enabled": {
                        "type": "boolean",
                        "title": "알림 시스템 활성화",
                        "description": "전체 알림 시스템 사용 여부"
                    },
                    "channels.desktop.enabled": {
                        "type": "boolean",
                        "title": "데스크톱 알림",
                        "description": "브라우저 데스크톱 알림"
                    },
                    "channels.sound.enabled": {
                        "type": "boolean",
                        "title": "소리 알림",
                        "description": "알림음 재생"
                    },
                    "channels.sound.volume": {
                        "type": "number",
                        "title": "알림음 볼륨",
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.1,
                        "description": "알림음 볼륨 (0-1)"
                    },
                    "channels.vibration.enabled": {
                        "type": "boolean",
                        "title": "진동 알림",
                        "description": "모바일 기기 진동"
                    },
                    "channels.kakao.enabled": {
                        "type": "boolean",
                        "title": "카카오톡 알림",
                        "description": "카카오톡 메시지 발송"
                    },
                    "channels.kakao.api_key": {
                        "type": "password",
                        "title": "카카오톡 API 키",
                        "description": "카카오톡 개발자 API 키"
                    },
                    "channels.telegram.enabled": {
                        "type": "boolean",
                        "title": "텔레그램 알림",
                        "description": "텔레그램 메시지 발송"
                    },
                    "channels.telegram.bot_token": {
                        "type": "password",
                        "title": "텔레그램 봇 토큰",
                        "description": "텔레그램 봇 토큰"
                    },
                    "channels.telegram.chat_id": {
                        "type": "text",
                        "title": "텔레그램 채팅 ID",
                        "description": "메시지를 받을 채팅 ID"
                    }
                }
            },
            "ai_model": {
                "title": "AI 모델 설정",
                "fields": {
                    "tensorflow_enabled": {
                        "type": "boolean",
                        "title": "TensorFlow 사용",
                        "description": "딥러닝 모델 사용 여부"
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "title": "신뢰도 임계값",
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "description": "예측 신뢰도 최소값"
                    },
                    "training_enabled": {
                        "type": "boolean",
                        "title": "자동 훈련",
                        "description": "자동 모델 재훈련 사용 여부"
                    },
                    "auto_retrain_interval": {
                        "type": "integer",
                        "title": "재훈련 간격 (시간)",
                        "min": 1,
                        "max": 168,
                        "description": "자동 재훈련 주기"
                    },
                    "neural_network.learning_rate": {
                        "type": "number",
                        "title": "학습률",
                        "min": 0.0001,
                        "max": 0.1,
                        "step": 0.0001,
                        "description": "신경망 학습률"
                    },
                    "neural_network.dropout_rate": {
                        "type": "number",
                        "title": "드롭아웃 비율",
                        "min": 0.0,
                        "max": 0.9,
                        "step": 0.05,
                        "description": "과적합 방지용 드롭아웃 비율"
                    },
                    "neural_network.batch_size": {
                        "type": "integer",
                        "title": "배치 크기",
                        "options": [16, 32, 64, 128],
                        "description": "훈련 배치 크기"
                    },
                    "neural_network.epochs": {
                        "type": "integer",
                        "title": "훈련 에포크",
                        "min": 10,
                        "max": 500,
                        "step": 10,
                        "description": "최대 훈련 에포크 수"
                    }
                }
            },
            "charts": {
                "title": "차트 설정",
                "fields": {
                    "max_data_points": {
                        "type": "integer",
                        "title": "최대 데이터 포인트",
                        "min": 10,
                        "max": 200,
                        "step": 10,
                        "description": "차트에 표시할 최대 데이터 수"
                    },
                    "update_interval": {
                        "type": "integer",
                        "title": "업데이트 간격 (ms)",
                        "min": 500,
                        "max": 10000,
                        "step": 500,
                        "description": "차트 업데이트 주기"
                    },
                    "chart_types.timeline.enabled": {
                        "type": "boolean",
                        "title": "타임라인 차트",
                        "description": "페어 발생 타임라인 표시"
                    },
                    "chart_types.timeline.hours_range": {
                        "type": "integer",
                        "title": "타임라인 시간 범위",
                        "options": [1, 6, 12, 24, 48],
                        "description": "타임라인 차트 시간 범위"
                    },
                    "theme.auto_theme": {
                        "type": "boolean",
                        "title": "자동 테마",
                        "description": "시스템 테마에 따른 자동 전환"
                    }
                }
            },
            "dashboard": {
                "title": "대시보드 설정",
                "fields": {
                    "websocket_ping_interval": {
                        "type": "integer",
                        "title": "WebSocket Ping 간격 (초)",
                        "min": 5,
                        "max": 60,
                        "description": "WebSocket 연결 상태 확인 간격"
                    },
                    "websocket_timeout": {
                        "type": "integer",
                        "title": "WebSocket 타임아웃 (초)",
                        "min": 10,
                        "max": 120,
                        "description": "WebSocket 연결 타임아웃"
                    },
                    "max_connections": {
                        "type": "integer",
                        "title": "최대 동시 연결",
                        "min": 10,
                        "max": 1000,
                        "step": 10,
                        "description": "최대 동시 WebSocket 연결 수"
                    },
                    "performance_thresholds.cpu_warning": {
                        "type": "integer",
                        "title": "CPU 경고 임계값 (%)",
                        "min": 50,
                        "max": 95,
                        "description": "CPU 사용률 경고 임계값"
                    },
                    "performance_thresholds.memory_warning": {
                        "type": "integer",
                        "title": "메모리 경고 임계값 (%)",
                        "min": 50,
                        "max": 95,
                        "description": "메모리 사용률 경고 임계값"
                    }
                }
            }
        }
    
    def get_current_values(self, category: Optional[str] = None) -> Dict[str, Any]:
        """현재 설정값 반환"""
        if category:
            return self.settings_manager.get_settings_by_category(category)
        else:
            return self.settings_manager.get_all_settings()
    
    def update_setting(self, path: str, value: Any) -> Dict[str, Any]:
        """단일 설정 업데이트"""
        success = self.settings_manager.set_setting(path, value)
        return {
            'success': success,
            'path': path,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
    
    def validate_and_update(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 유효성 검사 후 업데이트"""
        # 임시로 설정 적용
        original_settings = self.settings_manager.get_all_settings()
        self.settings_manager.update_settings(settings, save_immediately=False)
        
        # 유효성 검사
        validation_errors = self.settings_manager.validate_settings()
        
        if validation_errors:
            # 유효성 검사 실패 시 원래 설정으로 복원
            self.settings_manager.settings_cache = original_settings
            return {
                'success': False,
                'errors': validation_errors,
                'message': '설정 유효성 검사 실패'
            }
        else:
            # 유효성 검사 통과 시 저장
            self.settings_manager._save_settings()
            return {
                'success': True,
                'message': '설정이 성공적으로 업데이트되었습니다',
                'timestamp': datetime.now().isoformat()
            }


# 전역 인스턴스
settings_manager = SettingsManager()
web_settings_api = WebSettingsAPI(settings_manager)

def get_settings_manager() -> SettingsManager:
    """전역 설정 관리자 인스턴스 반환"""
    return settings_manager

def get_web_settings_api() -> WebSettingsAPI:
    """웹 설정 API 인스턴스 반환"""
    return web_settings_api


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 설정 관리 시스템 테스트 ===")
    
    manager = SettingsManager()
    
    # 설정 값 가져오기
    monitoring_interval = manager.get_setting('system.monitoring_interval')
    safe_print(f"현재 모니터링 간격: {monitoring_interval}초")
    
    # 설정 값 변경
    manager.set_setting('system.monitoring_interval', 2.0)
    new_interval = manager.get_setting('system.monitoring_interval')
    safe_print(f"변경된 모니터링 간격: {new_interval}초")
    
    # 유효성 검사
    validation_errors = manager.validate_settings()
    if validation_errors:
        safe_print(f"설정 오류: {validation_errors}")
    else:
        safe_print("✅ 모든 설정이 유효합니다")
    
    # 설정 내보내기
    export_file = manager.export_settings()
    safe_print(f"설정 내보내기: {export_file}")
    
    # 웹 API 테스트
    api = WebSettingsAPI(manager)
    schema = api.get_settings_schema()
    safe_print(f"스키마 카테고리: {list(schema.keys())}")
    
    safe_print("🎯 설정 관리 시스템 테스트 완료!")