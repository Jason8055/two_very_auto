#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Real-time Notification System
실시간 알림 시스템 - 웹, 이메일, 텔레그램 지원
"""

import json
import logging
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import threading
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationRule:
    """알림 규칙 클래스"""
    
    def __init__(self, name: str, condition: Callable, message_template: str, 
                 channels: List[str], priority: str = 'normal', cooldown: int = 300):
        """
        알림 규칙 초기화
        
        Args:
            name: 규칙명
            condition: 조건 함수 (game_data, tracking_result) -> bool
            message_template: 메시지 템플릿
            channels: 알림 채널 리스트 ['web', 'email', 'telegram']
            priority: 우선순위 ('low', 'normal', 'high', 'critical')
            cooldown: 재알림 방지 시간 (초)
        """
        self.name = name
        self.condition = condition
        self.message_template = message_template
        self.channels = channels
        self.priority = priority
        self.cooldown = cooldown
        self.last_triggered = None


class NotificationSystem:
    """통합 알림 시스템"""
    
    def __init__(self, config_file: str = "notification_config.json"):
        """알림 시스템 초기화"""
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.rules = []
        self.pending_notifications = []
        self.notification_history = []
        
        # 알림 통계
        self.stats = {
            'total_sent': 0,
            'web_sent': 0,
            'email_sent': 0,
            'telegram_sent': 0,
            'failed': 0
        }
        
        self._setup_default_rules()
        logger.info("[Notification System] Initialized successfully")
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_email': '',
                'to_emails': []
            },
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_ids': []
            },
            'web': {
                'enabled': True,
                'sound_enabled': True,
                'desktop_notifications': True
            },
            'general': {
                'max_notifications_per_hour': 20,
                'min_interval_seconds': 30,
                'enable_cooldown': True
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 기본값과 로드된 값 병합
                    for key, value in loaded_config.items():
                        if key in default_config:
                            default_config[key].update(value)
                return default_config
            else:
                # 기본 설정 파일 생성
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Failed to load notification config: {e}")
            return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save notification config: {e}")
    
    def _setup_default_rules(self) -> None:
        """기본 알림 규칙 설정"""
        
        # 1. 페어 발생 알림
        def pair_detected(game_data, tracking_result):
            return tracking_result.get('has_pair', False)
        
        self.add_rule(
            name="pair_detected",
            condition=pair_detected,
            message_template="🎯 PAIR DETECTED! {pair_type} at {table_name} - Cards: {pair_cards}",
            channels=['web'],
            priority='normal',
            cooldown=60
        )
        
        # 2. 긴 스트릭 알림
        def long_streak(game_data, tracking_result):
            return tracking_result.get('games_since_last_pair', 0) >= 15
        
        self.add_rule(
            name="long_streak",
            condition=long_streak,
            message_template="⚡ LONG STREAK ALERT! {games_since_last_pair} games without pairs at {table_name}",
            channels=['web', 'email'],
            priority='high',
            cooldown=300
        )
        
        # 3. 연속 페어 알림
        def multiple_pairs(game_data, tracking_result):
            # 이 로직은 pair_tracker에서 연속 페어 정보를 제공해야 구현 가능
            return False  # 일단 비활성화
        
        self.add_rule(
            name="multiple_pairs",
            condition=multiple_pairs,
            message_template="🔥 MULTIPLE PAIRS! Consecutive pairs detected at {table_name}",
            channels=['web', 'telegram'],
            priority='high',
            cooldown=180
        )
        
        # 4. 시간 기반 알림
        def hourly_summary(game_data, tracking_result):
            # 이는 주기적 알림이므로 별도 처리 필요
            return False
        
        self.add_rule(
            name="hourly_summary",
            condition=hourly_summary,
            message_template="📊 Hourly Summary: {total_games} games, {total_pairs} pairs",
            channels=['telegram'],
            priority='low',
            cooldown=3600
        )
    
    def add_rule(self, name: str, condition: Callable, message_template: str,
                channels: List[str], priority: str = 'normal', cooldown: int = 300) -> None:
        """알림 규칙 추가"""
        rule = NotificationRule(name, condition, message_template, channels, priority, cooldown)
        self.rules.append(rule)
        logger.info(f"Added notification rule: {name}")
    
    def process_game_event(self, game_data: Dict[str, Any], tracking_result: Dict[str, Any]) -> None:
        """게임 이벤트 처리 및 알림 규칙 체크"""
        for rule in self.rules:
            try:
                # 쿨다운 체크
                if rule.last_triggered:
                    time_since_last = (datetime.now() - rule.last_triggered).total_seconds()
                    if time_since_last < rule.cooldown:
                        continue
                
                # 조건 체크
                if rule.condition(game_data, tracking_result):
                    message = self._format_message(rule.message_template, game_data, tracking_result)
                    
                    # 알림 전송
                    self._send_notification(message, rule.channels, rule.priority)
                    rule.last_triggered = datetime.now()
                    
                    # 히스토리 기록
                    self.notification_history.append({
                        'rule': rule.name,
                        'message': message,
                        'channels': rule.channels,
                        'priority': rule.priority,
                        'timestamp': datetime.now().isoformat(),
                        'table_name': tracking_result.get('table_name', ''),
                        'game_id': tracking_result.get('game_id', '')
                    })
                    
            except Exception as e:
                logger.error(f"Error processing rule {rule.name}: {e}")
    
    def _format_message(self, template: str, game_data: Dict[str, Any], 
                       tracking_result: Dict[str, Any]) -> str:
        """메시지 템플릿 포매팅"""
        try:
            format_data = {
                **tracking_result,
                **game_data,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 안전한 포맷팅 (키가 없으면 빈 문자열)
            formatted = template
            for key, value in format_data.items():
                placeholder = f"{{{key}}}"
                if placeholder in formatted:
                    formatted = formatted.replace(placeholder, str(value))
            
            return formatted
            
        except Exception as e:
            logger.error(f"Message formatting error: {e}")
            return template
    
    def _send_notification(self, message: str, channels: List[str], priority: str) -> None:
        """알림 전송"""
        notification_data = {
            'message': message,
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'channels': channels
        }
        
        # 웹 알림
        if 'web' in channels and self.config['web']['enabled']:
            self._send_web_notification(notification_data)
        
        # 이메일 알림
        if 'email' in channels and self.config['email']['enabled']:
            threading.Thread(
                target=self._send_email_notification,
                args=(notification_data,),
                daemon=True
            ).start()
        
        # 텔레그램 알림
        if 'telegram' in channels and self.config['telegram']['enabled']:
            threading.Thread(
                target=self._send_telegram_notification,
                args=(notification_data,),
                daemon=True
            ).start()
        
        self.stats['total_sent'] += 1
    
    def _send_web_notification(self, notification_data: Dict[str, Any]) -> None:
        """웹 알림 전송 (메모리에 저장, 웹에서 폴링으로 조회)"""
        try:
            self.pending_notifications.append(notification_data)
            
            # 최대 100개 유지
            if len(self.pending_notifications) > 100:
                self.pending_notifications = self.pending_notifications[-100:]
            
            self.stats['web_sent'] += 1
            logger.info(f"Web notification queued: {notification_data['message']}")
            
        except Exception as e:
            logger.error(f"Web notification error: {e}")
            self.stats['failed'] += 1
    
    def _send_email_notification(self, notification_data: Dict[str, Any]) -> None:
        """이메일 알림 전송"""
        try:
            if not self.config['email']['to_emails']:
                return
            
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['from_email']
            msg['To'] = ', '.join(self.config['email']['to_emails'])
            msg['Subject'] = f"Baccarat Alert - {notification_data['priority'].upper()}"
            
            body = f"""
Baccarat Monitoring Alert

Message: {notification_data['message']}
Priority: {notification_data['priority'].upper()}
Time: {notification_data['timestamp']}

---
Two Very Auto Baccarat Monitoring System
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['username'], self.config['email']['password'])
            
            text = msg.as_string()
            server.sendmail(msg['From'], self.config['email']['to_emails'], text)
            server.quit()
            
            self.stats['email_sent'] += 1
            logger.info(f"Email sent: {notification_data['message']}")
            
        except Exception as e:
            logger.error(f"Email notification error: {e}")
            self.stats['failed'] += 1
    
    def _send_telegram_notification(self, notification_data: Dict[str, Any]) -> None:
        """텔레그램 알림 전송"""
        try:
            bot_token = self.config['telegram']['bot_token']
            chat_ids = self.config['telegram']['chat_ids']
            
            if not bot_token or not chat_ids:
                return
            
            message = f"""
🎰 *Baccarat Alert*

{notification_data['message']}

⏰ {notification_data['timestamp']}
🔥 Priority: {notification_data['priority'].upper()}
            """.strip()
            
            for chat_id in chat_ids:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()
            
            self.stats['telegram_sent'] += 1
            logger.info(f"Telegram sent: {notification_data['message']}")
            
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            self.stats['failed'] += 1
    
    def get_pending_notifications(self, clear: bool = True) -> List[Dict[str, Any]]:
        """대기 중인 웹 알림 조회"""
        notifications = self.pending_notifications.copy()
        if clear:
            self.pending_notifications.clear()
        return notifications
    
    def get_notification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """알림 히스토리 조회"""
        return self.notification_history[-limit:] if self.notification_history else []
    
    def get_statistics(self) -> Dict[str, Any]:
        """알림 통계 조회"""
        return {
            **self.stats,
            'rules_count': len(self.rules),
            'pending_count': len(self.pending_notifications),
            'history_count': len(self.notification_history),
            'last_notification': self.notification_history[-1]['timestamp'] if self.notification_history else None
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """설정 업데이트"""
        try:
            self.config.update(new_config)
            self._save_config(self.config)
            logger.info("Notification config updated")
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
    
    def test_notification(self, channel: str = 'web') -> bool:
        """테스트 알림 전송"""
        try:
            test_notification = {
                'message': f'Test notification - {datetime.now().strftime("%H:%M:%S")}',
                'priority': 'normal',
                'timestamp': datetime.now().isoformat(),
                'channels': [channel]
            }
            
            self._send_notification(test_notification['message'], [channel], 'normal')
            return True
            
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
            return False


# 편의 함수들
def create_pair_alert_rule():
    """페어 알림 규칙 생성"""
    def condition(game_data, tracking_result):
        return tracking_result.get('has_pair', False)
    
    return NotificationRule(
        name="pair_alert",
        condition=condition,
        message_template="🎯 {pair_type} detected at {table_name}! Cards: {pair_cards}",
        channels=['web'],
        priority='normal'
    )

def create_streak_alert_rule(threshold: int = 10):
    """스트릭 알림 규칙 생성"""
    def condition(game_data, tracking_result):
        return tracking_result.get('games_since_last_pair', 0) >= threshold
    
    return NotificationRule(
        name=f"streak_alert_{threshold}",
        condition=condition,
        message_template=f"⚡ Long streak: {{games_since_last_pair}} games without pairs at {{table_name}}",
        channels=['web', 'email'],
        priority='high',
        cooldown=300
    )


if __name__ == '__main__':
    # 테스트 실행
    print("Testing Notification System...")
    
    # 시스템 초기화
    notif_system = NotificationSystem("test_notification_config.json")
    
    # 테스트 게임 데이터
    test_game_data = {
        'table_name': 'test_table',
        'game_id': 12345,
        'result': 'PLAYER',
        'pair_info': {
            'has_any_pair': True,
            'pair_type': 'PLAYER_PAIR',
            'pair_cards': ['AH', 'AS']
        }
    }
    
    test_tracking_result = {
        'table_name': 'test_table',
        'game_id': 12345,
        'has_pair': True,
        'pair_type': 'PLAYER_PAIR',
        'pair_cards': ['AH', 'AS'],
        'games_since_last_pair': 0
    }
    
    # 알림 처리 테스트
    print("Processing test game event...")
    notif_system.process_game_event(test_game_data, test_tracking_result)
    
    # 웹 알림 확인
    pending = notif_system.get_pending_notifications()
    print(f"Pending notifications: {len(pending)}")
    for notif in pending:
        print(f"- {notif['message']}")
    
    # 통계 확인
    stats = notif_system.get_statistics()
    print(f"Statistics: {stats}")
    
    # 설정 파일 정리
    Path("test_notification_config.json").unlink(missing_ok=True)
    print("Test completed successfully!")