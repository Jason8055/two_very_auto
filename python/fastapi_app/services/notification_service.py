#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time Notification Service - FastAPI
고급 알림 시스템 with 멀티채널 지원
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """알림 타입"""
    PAIR_ALERT = "pair_alert"
    SYSTEM_WARNING = "system_warning" 
    PERFORMANCE_ALERT = "performance_alert"
    CONNECTION_STATUS = "connection_status"
    GAME_UPDATE = "game_update"
    AI_PREDICTION = "ai_prediction"
    BATCH_COMPLETE = "batch_complete"
    ERROR_ALERT = "error_alert"

class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class NotificationData:
    """알림 데이터 모델"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    expires_at: Optional[datetime] = None
    channels: Set[str] = None
    recipient_ids: Set[str] = None
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = {"websocket"}
        if self.recipient_ids is None:
            self.recipient_ids = {"all"}
        if self.expires_at is None:
            # 기본 24시간 만료
            self.expires_at = self.timestamp + timedelta(hours=24)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'channels': list(self.channels),
            'recipient_ids': list(self.recipient_ids)
        }

class NotificationChannel:
    """알림 채널 추상 클래스"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.last_error = None
    
    async def send(self, notification: NotificationData) -> bool:
        """알림 전송 (구현 필요)"""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """채널 상태 확인"""
        return True

class WebSocketNotificationChannel(NotificationChannel):
    """WebSocket 알림 채널"""
    
    def __init__(self, websocket_manager):
        super().__init__("websocket")
        self.websocket_manager = websocket_manager
    
    async def send(self, notification: NotificationData) -> bool:
        """WebSocket으로 알림 전송"""
        try:
            message = {
                'type': 'notification',
                'data': notification.to_dict()
            }
            
            if "all" in notification.recipient_ids:
                # 모든 클라이언트에게 브로드캐스트
                await self.websocket_manager.broadcast(message)
            else:
                # 특정 클라이언트들에게만 전송 (향후 구현)
                await self.websocket_manager.broadcast(message)
            
            logger.info(f"📡 WebSocket 알림 전송: {notification.type.value} - {notification.title}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ WebSocket 알림 전송 실패: {e}")
            return False
    
    async def health_check(self) -> bool:
        """WebSocket 채널 상태 확인"""
        return self.websocket_manager.get_connection_count() > 0

class LogNotificationChannel(NotificationChannel):
    """로그 파일 알림 채널"""
    
    def __init__(self, log_file: str = None):
        super().__init__("log")
        self.log_file = log_file
        self.logger = logging.getLogger("notifications")
    
    async def send(self, notification: NotificationData) -> bool:
        """로그로 알림 기록"""
        try:
            log_message = f"[{notification.priority.value.upper()}] {notification.title}: {notification.message}"
            
            if notification.priority in [NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY]:
                self.logger.error(log_message)
            elif notification.priority == NotificationPriority.HIGH:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ 로그 알림 기록 실패: {e}")
            return False

class NotificationService:
    """실시간 알림 서비스"""
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        self.notification_history: List[NotificationData] = []
        self.max_history_size = 1000
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
        
        # 통계
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'by_type': {},
            'by_priority': {},
            'by_channel': {}
        }
    
    def register_channel(self, channel: NotificationChannel):
        """알림 채널 등록"""
        self.channels[channel.name] = channel
        self.stats['by_channel'][channel.name] = {'sent': 0, 'failed': 0}
        logger.info(f"📢 알림 채널 등록: {channel.name}")
    
    def unregister_channel(self, channel_name: str):
        """알림 채널 해제"""
        if channel_name in self.channels:
            del self.channels[channel_name]
            logger.info(f"📢 알림 채널 해제: {channel_name}")
    
    async def start(self):
        """알림 서비스 시작"""
        if self.running:
            return
        
        self.running = True
        self.worker_task = asyncio.create_task(self._notification_worker())
        logger.info("🚀 실시간 알림 서비스 시작")
    
    async def stop(self):
        """알림 서비스 중지"""
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ 실시간 알림 서비스 중지")
    
    async def send_notification(self, notification: NotificationData):
        """알림 전송 (큐에 추가)"""
        try:
            await self.notification_queue.put(notification)
            logger.info(f"📨 알림 큐에 추가: {notification.type.value} - {notification.title}")
        except Exception as e:
            logger.error(f"❌ 알림 큐 추가 실패: {e}")
    
    async def send_pair_alert(self, table_name: str, pair_type: str, game_number: int, data: Dict[str, Any] = None):
        """페어 알림 전송"""
        notification = NotificationData(
            id=f"pair_{table_name}_{game_number}",
            type=NotificationType.PAIR_ALERT,
            priority=NotificationPriority.HIGH,
            title=f"🎰 {pair_type} 페어 발견!",
            message=f"{table_name} 테이블 {game_number}게임에서 {pair_type} 페어가 발견되었습니다.",
            data={
                'table_name': table_name,
                'pair_type': pair_type,
                'game_number': game_number,
                'additional_data': data or {}
            },
            timestamp=datetime.now(),
            channels={"websocket", "log"}
        )
        
        await self.send_notification(notification)
    
    async def send_system_warning(self, title: str, message: str, data: Dict[str, Any] = None):
        """시스템 경고 전송"""
        notification = NotificationData(
            id=f"system_warning_{datetime.now().timestamp()}",
            type=NotificationType.SYSTEM_WARNING,
            priority=NotificationPriority.HIGH,
            title=f"⚠️ {title}",
            message=message,
            data=data or {},
            timestamp=datetime.now(),
            channels={"websocket", "log"}
        )
        
        await self.send_notification(notification)
    
    async def send_performance_alert(self, metric_name: str, current_value: float, threshold: float, data: Dict[str, Any] = None):
        """성능 알림 전송"""
        priority = NotificationPriority.CRITICAL if current_value > threshold * 1.5 else NotificationPriority.HIGH
        
        notification = NotificationData(
            id=f"perf_{metric_name}_{datetime.now().timestamp()}",
            type=NotificationType.PERFORMANCE_ALERT,
            priority=priority,
            title=f"📊 성능 알림: {metric_name}",
            message=f"{metric_name}: {current_value:.2f} (임계값: {threshold:.2f})",
            data={
                'metric_name': metric_name,
                'current_value': current_value,
                'threshold': threshold,
                'additional_data': data or {}
            },
            timestamp=datetime.now(),
            channels={"websocket", "log"}
        )
        
        await self.send_notification(notification)
    
    async def send_ai_prediction(self, table_name: str, prediction: Dict[str, Any]):
        """AI 예측 결과 알림"""
        confidence = prediction.get('confidence', 0)
        priority = NotificationPriority.HIGH if confidence > 0.8 else NotificationPriority.NORMAL
        
        notification = NotificationData(
            id=f"ai_pred_{table_name}_{datetime.now().timestamp()}",
            type=NotificationType.AI_PREDICTION,
            priority=priority,
            title=f"🤖 AI 예측: {table_name}",
            message=f"다음 게임 예측 완료 (신뢰도: {confidence:.1%})",
            data={
                'table_name': table_name,
                'prediction': prediction
            },
            timestamp=datetime.now(),
            channels={"websocket"}  # AI 예측은 WebSocket만
        )
        
        await self.send_notification(notification)
    
    async def _notification_worker(self):
        """알림 처리 워커"""
        logger.info("🔄 알림 처리 워커 시작")
        
        while self.running:
            try:
                # 0.1초 타임아웃으로 큐에서 알림 가져오기
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=0.1
                )
                
                # 만료된 알림 확인
                if notification.expires_at and datetime.now() > notification.expires_at:
                    logger.info(f"⏰ 만료된 알림 무시: {notification.id}")
                    continue
                
                # 모든 활성화된 채널로 전송
                sent_count = 0
                failed_count = 0
                
                for channel_name in notification.channels:
                    if channel_name not in self.channels:
                        continue
                    
                    channel = self.channels[channel_name]
                    if not channel.enabled:
                        continue
                    
                    try:
                        success = await channel.send(notification)
                        if success:
                            sent_count += 1
                            self.stats['by_channel'][channel_name]['sent'] += 1
                        else:
                            failed_count += 1
                            self.stats['by_channel'][channel_name]['failed'] += 1
                    except Exception as e:
                        logger.error(f"❌ 채널 {channel_name} 전송 실패: {e}")
                        failed_count += 1
                        self.stats['by_channel'][channel_name]['failed'] += 1
                
                # 통계 업데이트
                self.stats['total_sent'] += sent_count
                self.stats['total_failed'] += failed_count
                
                type_key = notification.type.value
                priority_key = notification.priority.value
                
                self.stats['by_type'][type_key] = self.stats['by_type'].get(type_key, 0) + 1
                self.stats['by_priority'][priority_key] = self.stats['by_priority'].get(priority_key, 0) + 1
                
                # 이력 저장
                self.notification_history.append(notification)
                if len(self.notification_history) > self.max_history_size:
                    self.notification_history.pop(0)
                
                logger.info(f"✅ 알림 처리 완료: {notification.id} (성공:{sent_count}, 실패:{failed_count})")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ 알림 처리 워커 오류: {e}")
                await asyncio.sleep(1)
    
    def get_stats(self) -> Dict[str, Any]:
        """알림 서비스 통계 반환"""
        return {
            'running': self.running,
            'queue_size': self.notification_queue.qsize(),
            'history_size': len(self.notification_history),
            'registered_channels': list(self.channels.keys()),
            'stats': self.stats
        }
    
    def get_recent_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """최근 알림 이력 반환"""
        recent = self.notification_history[-limit:] if limit else self.notification_history
        return [notif.to_dict() for notif in recent]
    
    async def health_check(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        channel_status = {}
        
        for name, channel in self.channels.items():
            try:
                healthy = await channel.health_check()
                channel_status[name] = {
                    'healthy': healthy,
                    'enabled': channel.enabled,
                    'last_error': channel.last_error
                }
            except Exception as e:
                channel_status[name] = {
                    'healthy': False,
                    'enabled': channel.enabled,
                    'last_error': str(e)
                }
        
        return {
            'service_running': self.running,
            'worker_active': self.worker_task is not None and not self.worker_task.done(),
            'queue_size': self.notification_queue.qsize(),
            'channels': channel_status,
            'stats': self.get_stats()
        }

# 전역 알림 서비스 인스턴스
notification_service = NotificationService()

async def get_notification_service() -> NotificationService:
    """알림 서비스 의존성"""
    return notification_service