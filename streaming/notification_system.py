#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 실시간 알림 시스템
다채널 알림 전송 및 관리 시스템
"""

import json
import smtplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import uuid

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    import requests
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    safe_print("⚠️ requests 라이브러리 미설치")


class NotificationChannel(Enum):
    """알림 채널 타입"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    DESKTOP = "desktop"


class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class NotificationStatus(Enum):
    """알림 상태"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"


@dataclass
class NotificationTemplate:
    """알림 템플릿"""
    template_id: str
    name: str
    title_template: str
    content_template: str
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    variables: List[str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []


@dataclass
class NotificationSubscription:
    """알림 구독"""
    user_id: str
    channels: Set[NotificationChannel]
    categories: Set[str]
    priority_threshold: NotificationPriority
    active: bool = True
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


@dataclass
class Notification:
    """알림 객체"""
    notification_id: str
    user_id: str
    title: str
    content: str
    category: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    status: NotificationStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "priority": self.priority.value,
            "channels": [ch.value for ch in self.channels],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "metadata": self.metadata
        }


class NotificationSystem:
    """실시간 알림 시스템"""
    
    def __init__(self, config_path: str = "notification_config.json"):
        self.config_path = Path(config_path)
        self.config = {}
        
        # 알림 관리
        self.notifications: Dict[str, Notification] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.subscriptions: Dict[str, NotificationSubscription] = {}
        
        # 채널 설정
        self.channel_configs = {}
        self.channel_handlers = {}
        
        # 통계
        self.notifications_sent = 0
        self.notifications_failed = 0
        self.delivery_rates = {}
        
        # 처리 큐
        self.notification_queue = []
        self.processing_enabled = True
        self.processing_thread = None
        
        # 외부 연동
        self._websocket_server = None
        self._message_broker = None
        
        self.load_config()
        self.initialize_channels()
        self.create_default_templates()
        self.start_processing()
        
        safe_print("🔔 알림 시스템 초기화 완료")
    
    def load_config(self):
        """설정 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.create_default_config()
                
        except Exception as e:
            logger.error(f"알림 설정 로드 실패: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """기본 설정 생성"""
        default_config = {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "use_tls": True
            },
            "sms": {
                "api_key": "",
                "api_url": "",
                "from_number": ""
            },
            "push": {
                "fcm_server_key": "",
                "apns_certificate": ""
            },
            "webhook": {
                "default_timeout": 30,
                "retry_attempts": 3
            },
            "rate_limits": {
                "email": {"per_minute": 60, "per_hour": 1000},
                "sms": {"per_minute": 10, "per_hour": 100},
                "websocket": {"per_minute": 1000, "per_hour": 10000}
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        self.config = default_config
        safe_print(f"📝 기본 알림 설정 생성: {self.config_path}")
    
    def initialize_channels(self):
        """알림 채널 초기화"""
        # 각 채널 핸들러 등록
        self.channel_handlers[NotificationChannel.WEBSOCKET] = self._send_websocket_notification
        self.channel_handlers[NotificationChannel.EMAIL] = self._send_email_notification
        self.channel_handlers[NotificationChannel.SMS] = self._send_sms_notification
        self.channel_handlers[NotificationChannel.PUSH] = self._send_push_notification
        self.channel_handlers[NotificationChannel.WEBHOOK] = self._send_webhook_notification
        self.channel_handlers[NotificationChannel.DESKTOP] = self._send_desktop_notification
    
    def create_default_templates(self):
        """기본 알림 템플릿 생성"""
        default_templates = [
            NotificationTemplate(
                template_id="game_result",
                name="게임 결과 알림",
                title_template="바카라 게임 결과",
                content_template="라운드 {round_id}: {winner} 승리 (Player: {player_total}, Banker: {banker_total})",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.PUSH],
                priority=NotificationPriority.NORMAL,
                variables=["round_id", "winner", "player_total", "banker_total"]
            ),
            NotificationTemplate(
                template_id="ai_prediction",
                name="AI 예측 알림",
                title_template="AI 예측 결과",
                content_template="다음 라운드 예측: {prediction} (신뢰도: {confidence}%)",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.PUSH],
                priority=NotificationPriority.HIGH,
                variables=["prediction", "confidence"]
            ),
            NotificationTemplate(
                template_id="system_alert",
                name="시스템 알림",
                title_template="시스템 알림",
                content_template="{message}",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL],
                priority=NotificationPriority.URGENT,
                variables=["message"]
            ),
            NotificationTemplate(
                template_id="bankroll_warning",
                name="자금 경고",
                title_template="자금 관리 경고",
                content_template="현재 자금: {current_amount}원, 경고 수준: {warning_level}",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.SMS],
                priority=NotificationPriority.CRITICAL,
                variables=["current_amount", "warning_level"]
            ),
            NotificationTemplate(
                template_id="pattern_detected",
                name="패턴 감지",
                title_template="패턴 감지 알림",
                content_template="패턴 '{pattern_name}' 감지됨 (신뢰도: {confidence}%)",
                channels=[NotificationChannel.WEBSOCKET],
                priority=NotificationPriority.HIGH,
                variables=["pattern_name", "confidence"]
            )
        ]
        
        for template in default_templates:
            self.templates[template.template_id] = template
        
        safe_print(f"📋 {len(default_templates)}개 기본 템플릿 생성")
    
    def subscribe_user(self, user_id: str, channels: Set[NotificationChannel],
                      categories: Set[str], priority_threshold: NotificationPriority = NotificationPriority.NORMAL,
                      settings: Dict[str, Any] = None) -> bool:
        """사용자 구독 등록"""
        try:
            subscription = NotificationSubscription(
                user_id=user_id,
                channels=channels,
                categories=categories,
                priority_threshold=priority_threshold,
                settings=settings or {}
            )
            
            self.subscriptions[user_id] = subscription
            safe_print(f"👤 사용자 구독 등록: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"구독 등록 실패: {e}")
            return False
    
    def unsubscribe_user(self, user_id: str) -> bool:
        """사용자 구독 해제"""
        if user_id in self.subscriptions:
            del self.subscriptions[user_id]
            safe_print(f"👤 사용자 구독 해제: {user_id}")
            return True
        return False
    
    def send_notification(self, user_id: str, template_id: str,
                         variables: Dict[str, Any] = None,
                         override_channels: List[NotificationChannel] = None) -> Optional[str]:
        """알림 전송"""
        try:
            # 템플릿 확인
            if template_id not in self.templates:
                logger.error(f"알림 템플릿 없음: {template_id}")
                return None
            
            template = self.templates[template_id]
            
            # 사용자 구독 확인
            subscription = self.subscriptions.get(user_id)
            if not subscription or not subscription.active:
                return None
            
            # 우선순위 확인
            if template.priority.value < subscription.priority_threshold.value:
                return None
            
            # 채널 결정
            channels = override_channels or template.channels
            subscribed_channels = subscription.channels
            final_channels = [ch for ch in channels if ch in subscribed_channels]
            
            if not final_channels:
                return None
            
            # 변수 치환
            variables = variables or {}
            title = template.title_template.format(**variables)
            content = template.content_template.format(**variables)
            
            # 알림 생성
            notification_id = str(uuid.uuid4())
            notification = Notification(
                notification_id=notification_id,
                user_id=user_id,
                title=title,
                content=content,
                category=template_id,
                priority=template.priority,
                channels=final_channels,
                status=NotificationStatus.PENDING,
                created_at=datetime.now(),
                metadata={"template_id": template_id, "variables": variables}
            )
            
            # 알림 저장 및 큐에 추가
            self.notifications[notification_id] = notification
            self.notification_queue.append(notification_id)
            
            safe_print(f"🔔 알림 생성: {title} -> {user_id}")
            return notification_id
            
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
            return None
    
    def start_processing(self):
        """알림 처리 시작"""
        if self.processing_thread and self.processing_thread.is_alive():
            return
        
        def processing_worker():
            safe_print("🔄 알림 처리 워커 시작")
            
            while self.processing_enabled:
                try:
                    if self.notification_queue:
                        notification_id = self.notification_queue.pop(0)
                        self._process_notification(notification_id)
                    
                    # 대기 시간
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"알림 처리 워커 오류: {e}")
                    time.sleep(1)
        
        self.processing_thread = threading.Thread(target=processing_worker, daemon=True)
        self.processing_thread.start()
    
    def _process_notification(self, notification_id: str):
        """개별 알림 처리"""
        if notification_id not in self.notifications:
            return
        
        notification = self.notifications[notification_id]
        
        try:
            success_channels = []
            failed_channels = []
            
            # 각 채널로 전송
            for channel in notification.channels:
                handler = self.channel_handlers.get(channel)
                if handler:
                    if handler(notification):
                        success_channels.append(channel)
                    else:
                        failed_channels.append(channel)
                else:
                    failed_channels.append(channel)
            
            # 상태 업데이트
            if success_channels:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now()
                self.notifications_sent += 1
            else:
                notification.status = NotificationStatus.FAILED
                self.notifications_failed += 1
            
            # 통계 업데이트
            for channel in success_channels:
                channel_name = channel.value
                if channel_name not in self.delivery_rates:
                    self.delivery_rates[channel_name] = {"sent": 0, "failed": 0}
                self.delivery_rates[channel_name]["sent"] += 1
            
            for channel in failed_channels:
                channel_name = channel.value
                if channel_name not in self.delivery_rates:
                    self.delivery_rates[channel_name] = {"sent": 0, "failed": 0}
                self.delivery_rates[channel_name]["failed"] += 1
            
        except Exception as e:
            logger.error(f"알림 처리 실패 ({notification_id}): {e}")
            notification.status = NotificationStatus.FAILED
            self.notifications_failed += 1
    
    def _send_websocket_notification(self, notification: Notification) -> bool:
        """WebSocket 알림 전송"""
        try:
            if not self.websocket_server:
                return False
            
            self.websocket_server.broadcast_to_user(
                notification.user_id,
                "notification",
                {
                    "id": notification.notification_id,
                    "title": notification.title,
                    "content": notification.content,
                    "category": notification.category,
                    "priority": notification.priority.value,
                    "timestamp": notification.created_at.isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket 알림 전송 실패: {e}")
            return False
    
    def _send_email_notification(self, notification: Notification) -> bool:
        """이메일 알림 전송"""
        try:
            email_config = self.config.get("email", {})
            
            if not all([email_config.get("username"), email_config.get("password"), 
                       email_config.get("from_email")]):
                return False
            
            # 사용자 이메일 주소 가져오기 (구독 설정에서)
            subscription = self.subscriptions.get(notification.user_id)
            if not subscription:
                return False
            
            to_email = subscription.settings.get("email_address")
            if not to_email:
                return False
            
            # 이메일 생성
            msg = MIMEMultipart()
            msg['From'] = email_config["from_email"]
            msg['To'] = to_email
            msg['Subject'] = notification.title
            
            msg.attach(MIMEText(notification.content, 'plain', 'utf-8'))
            
            # SMTP 서버 연결 및 전송
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            if email_config.get("use_tls", True):
                server.starttls()
            
            server.login(email_config["username"], email_config["password"])
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"이메일 알림 전송 실패: {e}")
            return False
    
    def _send_sms_notification(self, notification: Notification) -> bool:
        """SMS 알림 전송"""
        try:
            if not HTTP_AVAILABLE:
                return False
            
            sms_config = self.config.get("sms", {})
            
            # SMS API 설정 확인
            if not all([sms_config.get("api_key"), sms_config.get("api_url")]):
                return False
            
            # 사용자 전화번호 가져오기
            subscription = self.subscriptions.get(notification.user_id)
            if not subscription:
                return False
            
            phone_number = subscription.settings.get("phone_number")
            if not phone_number:
                return False
            
            # SMS API 호출 (예시)
            payload = {
                "to": phone_number,
                "from": sms_config.get("from_number", ""),
                "text": f"{notification.title}\n{notification.content}"
            }
            
            headers = {
                "Authorization": f"Bearer {sms_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                sms_config["api_url"],
                json=payload,
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"SMS 알림 전송 실패: {e}")
            return False
    
    def _send_push_notification(self, notification: Notification) -> bool:
        """푸시 알림 전송"""
        try:
            # FCM 또는 APNS 구현 (구현 생략)
            safe_print(f"📱 푸시 알림: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"푸시 알림 전송 실패: {e}")
            return False
    
    def _send_webhook_notification(self, notification: Notification) -> bool:
        """웹훅 알림 전송"""
        try:
            if not HTTP_AVAILABLE:
                return False
            
            # 사용자별 웹훅 URL 가져오기
            subscription = self.subscriptions.get(notification.user_id)
            if not subscription:
                return False
            
            webhook_url = subscription.settings.get("webhook_url")
            if not webhook_url:
                return False
            
            payload = notification.to_dict()
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.config.get("webhook", {}).get("default_timeout", 30)
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"웹훅 알림 전송 실패: {e}")
            return False
    
    def _send_desktop_notification(self, notification: Notification) -> bool:
        """데스크톱 알림 전송"""
        try:
            # 데스크톱 알림 구현 (플랫폼별)
            safe_print(f"🖥️ 데스크톱 알림: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"데스크톱 알림 전송 실패: {e}")
            return False
    
    @property
    def websocket_server(self):
        """WebSocket 서버 가져오기"""
        if self._websocket_server is None:
            try:
                from websocket_server import get_websocket_server
                self._websocket_server = get_websocket_server()
            except ImportError:
                pass
        return self._websocket_server
    
    @property
    def message_broker(self):
        """메시지 브로커 가져오기"""
        if self._message_broker is None:
            try:
                from message_broker import get_message_broker
                self._message_broker = get_message_broker()
            except ImportError:
                pass
        return self._message_broker
    
    def get_user_notifications(self, user_id: str, limit: int = 50,
                              status_filter: Optional[NotificationStatus] = None) -> List[Dict[str, Any]]:
        """사용자 알림 조회"""
        user_notifications = [
            n for n in self.notifications.values()
            if n.user_id == user_id
        ]
        
        if status_filter:
            user_notifications = [
                n for n in user_notifications
                if n.status == status_filter
            ]
        
        # 최신순 정렬
        user_notifications.sort(key=lambda x: x.created_at, reverse=True)
        
        return [n.to_dict() for n in user_notifications[:limit]]
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """알림 읽음 표시"""
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now()
            return True
        return False
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """시스템 통계 정보"""
        return {
            "total_notifications": len(self.notifications),
            "notifications_sent": self.notifications_sent,
            "notifications_failed": self.notifications_failed,
            "success_rate": self.notifications_sent / max(1, self.notifications_sent + self.notifications_failed),
            "active_subscriptions": len([s for s in self.subscriptions.values() if s.active]),
            "total_subscriptions": len(self.subscriptions),
            "delivery_rates_by_channel": self.delivery_rates,
            "templates_count": len(self.templates),
            "pending_notifications": len(self.notification_queue)
        }
    
    def cleanup_old_notifications(self, days: int = 30) -> int:
        """오래된 알림 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_notifications = [
            nid for nid, notification in self.notifications.items()
            if notification.created_at < cutoff_date
        ]
        
        for notification_id in old_notifications:
            del self.notifications[notification_id]
        
        safe_print(f"🧹 {len(old_notifications)}개 오래된 알림 삭제")
        return len(old_notifications)
    
    def stop(self):
        """알림 시스템 중지"""
        self.processing_enabled = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        safe_print("🛑 알림 시스템 중지")


# 전역 인스턴스
_notification_system = None

def get_notification_system() -> NotificationSystem:
    """알림 시스템 인스턴스 반환"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 실시간 알림 시스템 테스트 ===")
    
    notification_system = get_notification_system()
    
    # 테스트 사용자 구독
    notification_system.subscribe_user(
        "test_user",
        {NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL},
        {"game_result", "ai_prediction", "system_alert"},
        NotificationPriority.NORMAL,
        {"email_address": "test@example.com"}
    )
    
    # 테스트 알림 전송
    test_notifications = [
        ("game_result", {"round_id": "R001", "winner": "banker", "player_total": 5, "banker_total": 7}),
        ("ai_prediction", {"prediction": "player", "confidence": 78}),
        ("system_alert", {"message": "시스템 점검이 예정되어 있습니다"}),
    ]
    
    for template_id, variables in test_notifications:
        notification_id = notification_system.send_notification("test_user", template_id, variables)
        if notification_id:
            safe_print(f"✅ 알림 전송 요청: {notification_id}")
    
    # 처리 대기
    time.sleep(2)
    
    # 통계 정보 출력
    stats = notification_system.get_system_statistics()
    safe_print(f"📊 알림 시스템 통계: {stats}")
    
    # 사용자 알림 조회
    user_notifications = notification_system.get_user_notifications("test_user")
    safe_print(f"📬 사용자 알림 수: {len(user_notifications)}")
    
    safe_print("🏁 실시간 알림 시스템 테스트 완료")