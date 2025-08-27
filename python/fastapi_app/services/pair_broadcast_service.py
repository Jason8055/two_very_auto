#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pair Broadcast Service - FastAPI
페어 알림 브로드캐스트 서비스
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from services.pair_notification_service import PairEvent, PairType, PairPattern

logger = logging.getLogger(__name__)

class BroadcastChannelType(Enum):
    """브로드캐스트 채널 타입"""
    WEBSOCKET = "websocket"
    PUSH_NOTIFICATION = "push_notification"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"

class BroadcastPriority(Enum):
    """브로드캐스트 우선순위"""
    REAL_TIME = "real_time"  # 즉시 전송
    HIGH = "high"           # 1초 이내
    NORMAL = "normal"       # 5초 이내
    LOW = "low"             # 30초 이내

class PairBroadcastMessage:
    """페어 브로드캐스트 메시지"""
    
    def __init__(self, pair_event: PairEvent, priority: BroadcastPriority = BroadcastPriority.NORMAL):
        self.pair_event = pair_event
        self.priority = priority
        self.created_at = datetime.now()
        self.channels = self._determine_channels()
        self.message_data = self._build_message_data()
    
    def _determine_channels(self) -> Set[BroadcastChannelType]:
        """브로드캐스트할 채널 결정"""
        channels = {BroadcastChannelType.WEBSOCKET}  # 기본적으로 WebSocket
        
        # 페어 타입에 따른 채널 추가
        if self.pair_event.pair_type == PairType.BOTH_PAIRS:
            channels.add(BroadcastChannelType.PUSH_NOTIFICATION)
            self.priority = BroadcastPriority.REAL_TIME
        
        # 패턴에 따른 채널 추가
        if self.pair_event.pattern in [PairPattern.CONSECUTIVE_PAIRS, PairPattern.RARE_PATTERN]:
            channels.add(BroadcastChannelType.PUSH_NOTIFICATION)
            if self.priority == BroadcastPriority.NORMAL:
                self.priority = BroadcastPriority.HIGH
        
        return channels
    
    def _build_message_data(self) -> Dict[str, Any]:
        """메시지 데이터 생성"""
        # 기본 메시지 데이터
        base_data = {
            "type": "pair_alert",
            "pair_event": self.pair_event.to_dict(),
            "priority": self.priority.value,
            "timestamp": self.created_at.isoformat(),
            "channels": [c.value for c in self.channels]
        }
        
        # 시각적 표시를 위한 추가 정보
        visual_data = self._get_visual_data()
        base_data.update(visual_data)
        
        return base_data
    
    def _get_visual_data(self) -> Dict[str, Any]:
        """시각적 표시를 위한 데이터"""
        pair_emojis = {
            PairType.PLAYER_PAIR: "🎰",
            PairType.BANKER_PAIR: "🏦", 
            PairType.BOTH_PAIRS: "💰"
        }
        
        pattern_emojis = {
            PairPattern.SINGLE_PAIR: "🎯",
            PairPattern.CONSECUTIVE_PAIRS: "🔥",
            PairPattern.ALTERNATING_PAIRS: "⚡",
            PairPattern.RARE_PATTERN: "💎"
        }
        
        # 우선순위별 색상
        priority_colors = {
            BroadcastPriority.REAL_TIME: "#ff0000",  # 빨간색
            BroadcastPriority.HIGH: "#ff8c00",       # 주황색
            BroadcastPriority.NORMAL: "#32cd32",     # 초록색
            BroadcastPriority.LOW: "#87ceeb"         # 하늘색
        }
        
        emoji = pair_emojis.get(self.pair_event.pair_type, "🎲")
        pattern_emoji = pattern_emojis.get(self.pair_event.pattern, "") if self.pair_event.pattern else ""
        
        return {
            "display": {
                "emoji": emoji,
                "pattern_emoji": pattern_emoji,
                "color": priority_colors.get(self.priority, "#32cd32"),
                "title": f"{emoji} {self.pair_event.pair_type.value.replace('_', ' ').title()}",
                "subtitle": f"{self.pair_event.table_name} 게임 #{self.pair_event.game_number}",
                "confidence_text": f"신뢰도: {self.pair_event.confidence:.1%}",
                "pattern_text": f"패턴: {self.pair_event.pattern.value.replace('_', ' ').title()}" if self.pair_event.pattern else None
            },
            "cards": {
                "player": self.pair_event.player_cards,
                "banker": self.pair_event.banker_cards,
                "player_display": " ".join(self.pair_event.player_cards),
                "banker_display": " ".join(self.pair_event.banker_cards)
            },
            "analytics": {
                "betting_recommendation": self._get_betting_recommendation(),
                "risk_level": self._get_risk_level(),
                "follow_up_action": self._get_follow_up_action()
            }
        }
    
    def _get_betting_recommendation(self) -> str:
        """베팅 권장사항"""
        recommendations = {
            PairType.PLAYER_PAIR: "플레이어 페어 베팅 고려",
            PairType.BANKER_PAIR: "뱅커 페어 베팅 고려",
            PairType.BOTH_PAIRS: "양쪽 페어 베팅 기회"
        }
        
        base_rec = recommendations.get(self.pair_event.pair_type, "관찰 권장")
        
        if self.pair_event.pattern == PairPattern.CONSECUTIVE_PAIRS:
            base_rec += " (연속 패턴 - 트렌드 지속 가능성)"
        elif self.pair_event.pattern == PairPattern.RARE_PATTERN:
            base_rec += " (희귀 패턴 - 신중한 베팅)"
        
        return base_rec
    
    def _get_risk_level(self) -> str:
        """위험 수준 평가"""
        if self.pair_event.confidence >= 0.95:
            return "매우 낮음"
        elif self.pair_event.confidence >= 0.85:
            return "낮음"
        elif self.pair_event.confidence >= 0.75:
            return "보통"
        else:
            return "높음"
    
    def _get_follow_up_action(self) -> str:
        """후속 조치 권장"""
        if self.pair_event.pattern == PairPattern.CONSECUTIVE_PAIRS:
            return "다음 게임 주의깊게 관찰"
        elif self.pair_event.pattern == PairPattern.RARE_PATTERN:
            return "패턴 지속성 모니터링"
        elif self.pair_event.pair_type == PairType.BOTH_PAIRS:
            return "테이블 상태 집중 모니터링"
        else:
            return "일반적인 관찰 지속"

class PairBroadcastService:
    """페어 브로드캐스트 서비스"""
    
    def __init__(self):
        self.broadcast_queue: asyncio.Queue = asyncio.Queue()
        self.channels: Dict[BroadcastChannelType, Any] = {}
        self.running = False
        self.worker_tasks: List[asyncio.Task] = []
        
        # 통계
        self.stats = {
            'total_broadcasts': 0,
            'successful_broadcasts': 0,
            'failed_broadcasts': 0,
            'by_priority': {p.value: 0 for p in BroadcastPriority},
            'by_channel': {c.value: {'sent': 0, 'failed': 0} for c in BroadcastChannelType},
            'by_pair_type': {p.value: 0 for p in PairType}
        }
        
        # 브로드캐스트 이력
        self.broadcast_history: List[Dict[str, Any]] = []
        self.max_history_size = 500
    
    async def start(self):
        """브로드캐스트 서비스 시작"""
        if self.running:
            return
        
        self.running = True
        
        # 우선순위별 워커 시작
        self.worker_tasks = [
            asyncio.create_task(self._broadcast_worker(BroadcastPriority.REAL_TIME)),
            asyncio.create_task(self._broadcast_worker(BroadcastPriority.HIGH)),
            asyncio.create_task(self._broadcast_worker(BroadcastPriority.NORMAL)),
            asyncio.create_task(self._broadcast_worker(BroadcastPriority.LOW))
        ]
        
        logger.info("🚀 페어 브로드캐스트 서비스 시작")
    
    async def stop(self):
        """브로드캐스트 서비스 중지"""
        self.running = False
        
        # 모든 워커 태스크 취소
        for task in self.worker_tasks:
            task.cancel()
        
        # 태스크 완료 대기
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        logger.info("⏹️ 페어 브로드캐스트 서비스 중지")
    
    def register_channel(self, channel_type: BroadcastChannelType, channel_handler: Any):
        """브로드캐스트 채널 등록"""
        self.channels[channel_type] = channel_handler
        logger.info(f"📡 브로드캐스트 채널 등록: {channel_type.value}")
    
    async def broadcast_pair_event(self, pair_event: PairEvent, priority: BroadcastPriority = None):
        """페어 이벤트 브로드캐스트"""
        try:
            # 우선순위 자동 결정
            if priority is None:
                priority = self._determine_priority(pair_event)
            
            # 브로드캐스트 메시지 생성
            message = PairBroadcastMessage(pair_event, priority)
            
            # 큐에 추가
            await self.broadcast_queue.put(message)
            
            logger.info(f"📤 페어 브로드캐스트 큐 추가: {pair_event.table_name} - {pair_event.pair_type.value} (우선순위: {priority.value})")
            
        except Exception as e:
            logger.error(f"❌ 페어 브로드캐스트 큐 추가 실패: {e}")
    
    def _determine_priority(self, pair_event: PairEvent) -> BroadcastPriority:
        """우선순위 자동 결정"""
        # 양쪽 페어는 최고 우선순위
        if pair_event.pair_type == PairType.BOTH_PAIRS:
            return BroadcastPriority.REAL_TIME
        
        # 연속 패턴이나 희귀 패턴은 높은 우선순위
        if pair_event.pattern in [PairPattern.CONSECUTIVE_PAIRS, PairPattern.RARE_PATTERN]:
            return BroadcastPriority.HIGH
        
        # 높은 신뢰도는 일반 우선순위
        if pair_event.confidence >= 0.9:
            return BroadcastPriority.NORMAL
        
        # 그 외는 낮은 우선순위
        return BroadcastPriority.LOW
    
    async def _broadcast_worker(self, priority: BroadcastPriority):
        """우선순위별 브로드캐스트 워커"""
        logger.info(f"🔄 브로드캐스트 워커 시작: {priority.value}")
        
        # 우선순위별 처리 간격
        intervals = {
            BroadcastPriority.REAL_TIME: 0.1,  # 100ms
            BroadcastPriority.HIGH: 0.5,       # 500ms
            BroadcastPriority.NORMAL: 1.0,     # 1초
            BroadcastPriority.LOW: 5.0         # 5초
        }
        
        interval = intervals.get(priority, 1.0)
        
        while self.running:
            try:
                # 큐에서 메시지 가져오기 (타임아웃 적용)
                try:
                    message = await asyncio.wait_for(
                        self.broadcast_queue.get(),
                        timeout=interval
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 우선순위 확인
                if message.priority != priority:
                    # 다른 우선순위면 다시 큐에 넣기
                    await self.broadcast_queue.put(message)
                    await asyncio.sleep(0.1)
                    continue
                
                # 브로드캐스트 실행
                await self._execute_broadcast(message)
                
            except Exception as e:
                logger.error(f"❌ 브로드캐스트 워커 오류 ({priority.value}): {e}")
                await asyncio.sleep(interval)
    
    async def _execute_broadcast(self, message: PairBroadcastMessage):
        """브로드캐스트 실행"""
        try:
            broadcast_results = {}
            
            # 각 채널로 브로드캐스트
            for channel_type in message.channels:
                if channel_type not in self.channels:
                    continue
                
                try:
                    channel_handler = self.channels[channel_type]
                    success = await self._send_to_channel(channel_type, channel_handler, message)
                    
                    broadcast_results[channel_type.value] = {
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # 통계 업데이트
                    if success:
                        self.stats['by_channel'][channel_type.value]['sent'] += 1
                    else:
                        self.stats['by_channel'][channel_type.value]['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ 채널 브로드캐스트 실패 ({channel_type.value}): {e}")
                    broadcast_results[channel_type.value] = {
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    self.stats['by_channel'][channel_type.value]['failed'] += 1
            
            # 전체 통계 업데이트
            self.stats['total_broadcasts'] += 1
            self.stats['by_priority'][message.priority.value] += 1
            self.stats['by_pair_type'][message.pair_event.pair_type.value] += 1
            
            # 성공한 채널이 있는지 확인
            successful_channels = sum(1 for r in broadcast_results.values() if r.get('success', False))
            if successful_channels > 0:
                self.stats['successful_broadcasts'] += 1
            else:
                self.stats['failed_broadcasts'] += 1
            
            # 이력 저장
            history_entry = {
                'pair_event_id': message.pair_event.id,
                'table_name': message.pair_event.table_name,
                'pair_type': message.pair_event.pair_type.value,
                'priority': message.priority.value,
                'channels': list(message.channels),
                'results': broadcast_results,
                'timestamp': message.created_at.isoformat()
            }
            
            self.broadcast_history.append(history_entry)
            if len(self.broadcast_history) > self.max_history_size:
                self.broadcast_history.pop(0)
            
            logger.info(f"✅ 브로드캐스트 완료: {message.pair_event.table_name} - 성공 채널: {successful_channels}/{len(message.channels)}")
            
        except Exception as e:
            logger.error(f"❌ 브로드캐스트 실행 실패: {e}")
    
    async def _send_to_channel(self, channel_type: BroadcastChannelType, channel_handler: Any, message: PairBroadcastMessage) -> bool:
        """특정 채널로 메시지 전송"""
        try:
            if channel_type == BroadcastChannelType.WEBSOCKET:
                # WebSocket으로 브로드캐스트
                await channel_handler.broadcast({
                    'type': 'pair_notification',
                    'data': message.message_data
                })
                return True
            
            elif channel_type == BroadcastChannelType.PUSH_NOTIFICATION:
                # 푸시 알림 (향후 구현)
                logger.info(f"📱 푸시 알림 전송 (미구현): {message.pair_event.table_name}")
                return True
            
            elif channel_type == BroadcastChannelType.EMAIL:
                # 이메일 알림 (향후 구현)
                logger.info(f"📧 이메일 알림 전송 (미구현): {message.pair_event.table_name}")
                return True
            
            elif channel_type == BroadcastChannelType.SMS:
                # SMS 알림 (향후 구현)
                logger.info(f"📱 SMS 알림 전송 (미구현): {message.pair_event.table_name}")
                return True
            
            elif channel_type == BroadcastChannelType.WEBHOOK:
                # 웹훅 알림 (향후 구현)
                logger.info(f"🔗 웹훅 알림 전송 (미구현): {message.pair_event.table_name}")
                return True
            
            else:
                logger.warning(f"⚠️ 알 수 없는 채널 타입: {channel_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 채널 전송 실패 ({channel_type.value}): {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """브로드캐스트 통계 반환"""
        return {
            'service_status': {
                'running': self.running,
                'queue_size': self.broadcast_queue.qsize(),
                'active_channels': list(self.channels.keys()),
                'worker_count': len(self.worker_tasks)
            },
            'stats': self.stats,
            'recent_broadcasts': self.broadcast_history[-10:] if self.broadcast_history else []
        }
    
    def get_broadcast_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """브로드캐스트 이력 반환"""
        return self.broadcast_history[-limit:] if limit else self.broadcast_history

# 전역 브로드캐스트 서비스 인스턴스
pair_broadcast_service = PairBroadcastService()

async def get_pair_broadcast_service() -> PairBroadcastService:
    """브로드캐스트 서비스 의존성"""
    return pair_broadcast_service