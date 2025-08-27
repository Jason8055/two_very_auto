#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
고급 알림 시스템 v2.0
카카오톡, 텔레그램, TTS, 웹 푸시 통합 알림 시스템
"""

import json
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NotificationChannel:
    """알림 채널 추상 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.last_sent = {}
        
    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """알림 전송 (서브클래스에서 구현)"""
        raise NotImplementedError
        
    def is_cooldown_active(self, message_type: str, cooldown_seconds: int = 300) -> bool:
        """쿨다운 시간 확인"""
        if message_type not in self.last_sent:
            return False
            
        last_time = self.last_sent[message_type]
        return (datetime.now() - last_time).total_seconds() < cooldown_seconds
        
    def update_last_sent(self, message_type: str):
        """마지막 전송 시간 업데이트"""
        self.last_sent[message_type] = datetime.now()


class WebNotificationChannel(NotificationChannel):
    """웹 브라우저 알림"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("web", config)
        self.websocket_manager = None
        
    def set_websocket_manager(self, ws_manager):
        """WebSocket 매니저 설정"""
        self.websocket_manager = ws_manager
        
    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """웹소켓으로 실시간 알림 전송"""
        try:
            if not self.websocket_manager:
                return False
                
            # 알림 데이터 구성
            notification_data = {
                'type': 'pair_alert',
                'title': '🎯 Two Very Auto 페어 알림',
                'message': message.get('text', '새로운 페어가 감지되었습니다'),
                'data': message.get('data', {}),
                'timestamp': datetime.now().isoformat(),
                'priority': message.get('priority', 'normal'),
                'sound': message.get('sound', True),
                'vibrate': message.get('vibrate', [200, 100, 200])
            }
            
            # 브로드캐스트로 모든 연결된 클라이언트에게 전송
            self.websocket_manager.broadcast_pair_alert(notification_data)
            
            safe_print(f"✅ 웹 알림 전송 성공: {message.get('text')}")
            return True
            
        except Exception as e:
            logger.error(f"웹 알림 전송 실패: {e}")
            return False


class TTSNotificationChannel(NotificationChannel):
    """음성 알림 (TTS)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("tts", config)
        self.tts_engine = None
        self._init_tts_engine()
        
    def _init_tts_engine(self):
        """TTS 엔진 초기화"""
        try:
            import pyttsx3
            
            self.tts_engine = pyttsx3.init()
            
            # 한국어 음성 설정
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'korean' in voice.name.lower() or 'ko' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            # 음성 속도 설정
            self.tts_engine.setProperty('rate', self.config.get('speech_rate', 180))
            
            # 음량 설정 (0.0 ~ 1.0)
            self.tts_engine.setProperty('volume', self.config.get('volume', 0.8))
            
            logger.info("TTS 엔진 초기화 성공")
            
        except ImportError:
            logger.warning("pyttsx3 라이브러리가 설치되지 않았습니다. 음성 알림을 사용할 수 없습니다.")
        except Exception as e:
            logger.error(f"TTS 엔진 초기화 실패: {e}")
            
    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """TTS로 음성 알림 재생"""
        try:
            if not self.tts_engine or not self.enabled:
                return False
                
            # 쿨다운 확인
            message_type = message.get('type', 'default')
            if self.is_cooldown_active(message_type, self.config.get('cooldown', 60)):
                return False
                
            # 음성 메시지 준비
            text = message.get('text', '새로운 알림이 있습니다')
            
            # 페어 알림 특별 처리
            if message_type == 'pair_alert':
                data = message.get('data', {})
                table_name = data.get('table_name', '테이블')
                pair_type = data.get('pair_type', '페어')
                
                # 한국어 페어 타입 변환
                pair_names = {
                    'PP': '플레이어 페어',
                    'BP': '뱅커 페어', 
                    'BOTH': '양쪽 페어'
                }
                pair_korean = pair_names.get(pair_type, pair_type)
                
                text = f"{table_name}에서 {pair_korean}가 발생했습니다!"
            
            # 별도 스레드에서 TTS 실행 (블로킹 방지)
            def speak_text():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    logger.error(f"TTS 재생 오류: {e}")
            
            tts_thread = threading.Thread(target=speak_text, daemon=True)
            tts_thread.start()
            
            self.update_last_sent(message_type)
            safe_print(f"🔊 TTS 알림 재생: {text}")
            return True
            
        except Exception as e:
            logger.error(f"TTS 알림 실패: {e}")
            return False


class KakaoNotificationChannel(NotificationChannel):
    """카카오톡 봇 알림"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("kakao", config)
        self.bot_token = config.get('bot_token', '')
        self.chat_room_id = config.get('chat_room_id', '')
        
    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """카카오톡 메시지 전송"""
        try:
            if not self.bot_token or not self.enabled:
                safe_print("⚠️ 카카오톡 봇 토큰이 설정되지 않았습니다")
                return False
                
            # 쿨다운 확인
            message_type = message.get('type', 'default')
            if self.is_cooldown_active(message_type, self.config.get('cooldown', 300)):
                return False
                
            # 카카오톡 API 호출 (여기서는 시뮬레이션)
            # 실제 구현시 카카오 API 문서 참고하여 구현
            
            text = message.get('text', '새로운 알림')
            data = message.get('data', {})
            
            # 메시지 포맷팅
            if message_type == 'pair_alert':
                formatted_message = self._format_pair_message(text, data)
            else:
                formatted_message = text
                
            # 시뮬레이션 - 실제로는 HTTP 요청
            safe_print(f"📱 [카카오톡 알림] {formatted_message}")
            
            self.update_last_sent(message_type)
            return True
            
        except Exception as e:
            logger.error(f"카카오톡 알림 전송 실패: {e}")
            return False
            
    def _format_pair_message(self, text: str, data: Dict[str, Any]) -> str:
        """페어 알림 메시지 포맷팅"""
        table_name = data.get('table_name', '테이블')
        pair_type = data.get('pair_type', '페어')
        game_number = data.get('game_number', '?')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        return f"""🎯 Two Very Auto 페어 알림
        
📍 테이블: {table_name}
🎲 페어 타입: {pair_type}
🔢 게임 번호: {game_number}
⏰ 시간: {timestamp}

즉시 확인하세요! 🚀"""


class TelegramNotificationChannel(NotificationChannel):
    """텔레그램 봇 알림"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("telegram", config)
        self.bot_token = config.get('bot_token', '')
        self.chat_id = config.get('chat_id', '')
        
    async def send_notification(self, message: Dict[str, Any]) -> bool:
        """텔레그램 메시지 전송"""
        try:
            if not self.bot_token or not self.enabled:
                safe_print("⚠️ 텔레그램 봇 토큰이 설정되지 않았습니다")
                return False
                
            # 쿨다운 확인
            message_type = message.get('type', 'default')
            if self.is_cooldown_active(message_type, self.config.get('cooldown', 300)):
                return False
                
            # 텔레그램 API 호출 (여기서는 시뮬레이션)
            # 실제 구현시 telegram-bot-api 사용
            
            text = message.get('text', '새로운 알림')
            data = message.get('data', {})
            
            # 메시지 포맷팅
            if message_type == 'pair_alert':
                formatted_message = self._format_pair_message(text, data)
            else:
                formatted_message = text
                
            # 시뮬레이션 - 실제로는 HTTP 요청
            safe_print(f"💬 [텔레그램 알림] {formatted_message}")
            
            self.update_last_sent(message_type)
            return True
            
        except Exception as e:
            logger.error(f"텔레그램 알림 전송 실패: {e}")
            return False
            
    def _format_pair_message(self, text: str, data: Dict[str, Any]) -> str:
        """페어 알림 메시지 포맷팅"""
        table_name = data.get('table_name', '테이블')
        pair_type = data.get('pair_type', '페어')
        game_number = data.get('game_number', '?')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        return f"""🎯 *Two Very Auto 페어 알림*

📍 테이블: `{table_name}`
🎲 페어 타입: `{pair_type}`  
🔢 게임 번호: `{game_number}`
⏰ 시간: `{timestamp}`

[대시보드에서 확인하기](http://localhost:5000)"""


class AdvancedNotificationSystem:
    """고급 통합 알림 시스템"""
    
    def __init__(self, config_path: str = "notification_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.channels = {}
        self.message_queue = asyncio.Queue()
        self.is_running = False
        
        # 채널 초기화
        self._init_channels()
        
        logger.info("[고급 알림 시스템] 초기화 완료")
        
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 설정 생성
                default_config = {
                    "web": {
                        "enabled": True,
                        "cooldown": 5
                    },
                    "tts": {
                        "enabled": True,
                        "speech_rate": 180,
                        "volume": 0.8,
                        "cooldown": 60
                    },
                    "kakao": {
                        "enabled": False,
                        "bot_token": "",
                        "chat_room_id": "",
                        "cooldown": 300
                    },
                    "telegram": {
                        "enabled": False,
                        "bot_token": "",
                        "chat_id": "",
                        "cooldown": 300
                    },
                    "global": {
                        "max_notifications_per_hour": 20,
                        "priority_levels": ["low", "normal", "high", "urgent"]
                    }
                }
                
                self._save_config(default_config)
                return default_config
                
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return {}
            
    def _save_config(self, config: Dict[str, Any]):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            
    def _init_channels(self):
        """알림 채널 초기화"""
        try:
            # 웹 알림
            self.channels['web'] = WebNotificationChannel(self.config.get('web', {}))
            
            # TTS 알림
            self.channels['tts'] = TTSNotificationChannel(self.config.get('tts', {}))
            
            # 카카오톡 알림
            self.channels['kakao'] = KakaoNotificationChannel(self.config.get('kakao', {}))
            
            # 텔레그램 알림
            self.channels['telegram'] = TelegramNotificationChannel(self.config.get('telegram', {}))
            
            # 활성화된 채널 수 계산
            enabled_count = sum(1 for ch in self.channels.values() if ch.enabled)
            safe_print(f"✅ {enabled_count}개 알림 채널 초기화 완료")
            
        except Exception as e:
            logger.error(f"채널 초기화 실패: {e}")
            
    def set_websocket_manager(self, ws_manager):
        """WebSocket 매니저 설정"""
        if 'web' in self.channels:
            self.channels['web'].set_websocket_manager(ws_manager)
            
    async def send_pair_alert(self, pair_data: Dict[str, Any]) -> Dict[str, bool]:
        """페어 알림 전송"""
        message = {
            'type': 'pair_alert',
            'text': f"🎯 {pair_data.get('table_name', '테이블')}: {pair_data.get('pair_type', '페어')} 발생!",
            'data': pair_data,
            'priority': 'high',
            'timestamp': datetime.now().isoformat()
        }
        
        return await self.send_notification(message)
        
    async def send_notification(self, message: Dict[str, Any]) -> Dict[str, bool]:
        """알림 전송 (모든 활성화된 채널)"""
        results = {}
        
        try:
            # 모든 채널에 병렬로 알림 전송
            tasks = []
            for channel_name, channel in self.channels.items():
                if channel.enabled:
                    task = asyncio.create_task(channel.send_notification(message))
                    tasks.append((channel_name, task))
            
            # 결과 수집
            for channel_name, task in tasks:
                try:
                    result = await task
                    results[channel_name] = result
                except Exception as e:
                    logger.error(f"{channel_name} 채널 전송 실패: {e}")
                    results[channel_name] = False
                    
        except Exception as e:
            logger.error(f"알림 전송 오류: {e}")
            
        # 전송 결과 로그
        success_count = sum(1 for r in results.values() if r)
        total_count = len(results)
        safe_print(f"📤 알림 전송 결과: {success_count}/{total_count} 채널 성공")
        
        return results
        
    def update_channel_config(self, channel_name: str, config: Dict[str, Any]):
        """채널 설정 업데이트"""
        try:
            if channel_name in self.config:
                self.config[channel_name].update(config)
                self._save_config(self.config)
                
                # 채널 재초기화
                if channel_name in self.channels:
                    if channel_name == 'web':
                        self.channels[channel_name] = WebNotificationChannel(config)
                    elif channel_name == 'tts':
                        self.channels[channel_name] = TTSNotificationChannel(config)
                    elif channel_name == 'kakao':
                        self.channels[channel_name] = KakaoNotificationChannel(config)
                    elif channel_name == 'telegram':
                        self.channels[channel_name] = TelegramNotificationChannel(config)
                        
                safe_print(f"✅ {channel_name} 채널 설정 업데이트 완료")
                return True
                
        except Exception as e:
            logger.error(f"채널 설정 업데이트 실패: {e}")
            return False
            
    def get_notification_stats(self) -> Dict[str, Any]:
        """알림 통계 정보"""
        stats = {
            'channels': {},
            'total_sent_today': 0,
            'last_notification': None
        }
        
        for name, channel in self.channels.items():
            stats['channels'][name] = {
                'enabled': channel.enabled,
                'last_sent_count': len(channel.last_sent),
                'config': channel.config
            }
            
        return stats


# 전역 알림 시스템 인스턴스
notification_system = None

def get_notification_system() -> AdvancedNotificationSystem:
    """전역 알림 시스템 인스턴스 반환"""
    global notification_system
    if notification_system is None:
        notification_system = AdvancedNotificationSystem()
    return notification_system


if __name__ == "__main__":
    # 테스트 코드
    async def test_notification_system():
        """알림 시스템 테스트"""
        safe_print("=== 고급 알림 시스템 테스트 ===")
        
        # 알림 시스템 초기화
        notif_system = get_notification_system()
        
        # 테스트 페어 데이터
        test_pair = {
            'table_name': '메인테이블_A',
            'pair_type': 'PP',
            'game_number': 42,
            'timestamp': datetime.now().isoformat()
        }
        
        # 페어 알림 전송 테스트
        safe_print("\n📤 페어 알림 전송 테스트...")
        results = await notif_system.send_pair_alert(test_pair)
        
        for channel, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            safe_print(f"  {channel}: {status}")
        
        # 통계 정보 출력
        stats = notif_system.get_notification_stats()
        safe_print(f"\n📊 활성 채널: {sum(1 for ch in stats['channels'].values() if ch['enabled'])}개")
        
        safe_print("\n🎯 고급 알림 시스템 테스트 완료!")
    
    # asyncio 실행
    asyncio.run(test_notification_system())