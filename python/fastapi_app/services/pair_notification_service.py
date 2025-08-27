#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time Pair Notification Service - FastAPI
실시간 페어 알림 시스템
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
import json

from services.notification_service import notification_service, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

class PairType(Enum):
    """페어 타입"""
    PLAYER_PAIR = "player_pair"
    BANKER_PAIR = "banker_pair"
    BOTH_PAIRS = "both_pairs"
    NO_PAIR = "no_pair"

class PairPattern(Enum):
    """페어 패턴"""
    SINGLE_PAIR = "single_pair"
    CONSECUTIVE_PAIRS = "consecutive_pairs"
    ALTERNATING_PAIRS = "alternating_pairs"
    RARE_PATTERN = "rare_pattern"

@dataclass
class PairEvent:
    """페어 이벤트"""
    id: str
    table_name: str
    game_number: int
    pair_type: PairType
    timestamp: datetime
    player_cards: List[str] = field(default_factory=list)
    banker_cards: List[str] = field(default_factory=list)
    pattern: Optional[PairPattern] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'id': self.id,
            'table_name': self.table_name,
            'game_number': self.game_number,
            'pair_type': self.pair_type.value,
            'timestamp': self.timestamp.isoformat(),
            'player_cards': self.player_cards,
            'banker_cards': self.banker_cards,
            'pattern': self.pattern.value if self.pattern else None,
            'confidence': self.confidence,
            'metadata': self.metadata
        }

@dataclass
class PairNotificationSettings:
    """페어 알림 설정"""
    enabled: bool = True
    notification_types: Set[PairType] = field(default_factory=lambda: {PairType.PLAYER_PAIR, PairType.BANKER_PAIR, PairType.BOTH_PAIRS})
    min_confidence: float = 0.8
    pattern_detection_enabled: bool = True
    consecutive_pair_threshold: int = 2
    notification_cooldown_seconds: int = 5
    max_notifications_per_minute: int = 10

class PairDetector:
    """페어 감지기"""
    
    def __init__(self):
        self.card_values = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13
        }
    
    def detect_pair(self, cards: List[str]) -> Tuple[bool, float]:
        """
        카드에서 페어 감지
        
        Args:
            cards: 카드 리스트 (예: ['A♠', 'A♥'])
            
        Returns:
            Tuple[bool, float]: (페어 여부, 신뢰도)
        """
        if len(cards) < 2:
            return False, 0.0
        
        try:
            # 카드 값 추출 (숫자/문자 부분만)
            card_values = []
            for card in cards:
                # 카드 표기에서 숫자/문자 부분 추출
                value = card.rstrip('♠♥♦♣').rstrip('SHDC')
                card_values.append(value)
            
            # 페어 확인 (같은 값이 2개 이상)
            unique_values = set(card_values)
            if len(unique_values) < len(card_values):
                # 페어 존재
                confidence = 1.0 - (len(unique_values) / len(card_values))
                return True, confidence
            
            return False, 0.0
            
        except Exception as e:
            logger.error(f"❌ 페어 감지 오류: {e}")
            return False, 0.0
    
    def analyze_pair_pattern(self, recent_pairs: List[PairEvent], table_name: str) -> Optional[PairPattern]:
        """
        최근 페어 이벤트에서 패턴 분석
        
        Args:
            recent_pairs: 최근 페어 이벤트 리스트
            table_name: 테이블 이름
            
        Returns:
            Optional[PairPattern]: 감지된 패턴
        """
        if len(recent_pairs) < 2:
            return None
        
        try:
            # 테이블별로 필터링
            table_pairs = [pair for pair in recent_pairs if pair.table_name == table_name]
            if len(table_pairs) < 2:
                return None
            
            # 시간순 정렬
            table_pairs.sort(key=lambda x: x.timestamp)
            
            # 연속 페어 패턴 확인
            consecutive_count = 0
            for i in range(1, len(table_pairs)):
                if table_pairs[i].game_number == table_pairs[i-1].game_number + 1:
                    consecutive_count += 1
                else:
                    break
            
            if consecutive_count >= 2:
                return PairPattern.CONSECUTIVE_PAIRS
            
            # 교대 패턴 확인 (플레이어-뱅커-플레이어-뱅커...)
            if len(table_pairs) >= 3:
                alternating = True
                for i in range(2, len(table_pairs)):
                    if table_pairs[i].pair_type == table_pairs[i-2].pair_type:
                        continue
                    else:
                        alternating = False
                        break
                
                if alternating:
                    return PairPattern.ALTERNATING_PAIRS
            
            # 희귀 패턴 (짧은 시간 내 많은 페어)
            recent_time = datetime.now() - timedelta(minutes=5)
            recent_count = sum(1 for pair in table_pairs if pair.timestamp >= recent_time)
            
            if recent_count >= 5:
                return PairPattern.RARE_PATTERN
            
            return PairPattern.SINGLE_PAIR
            
        except Exception as e:
            logger.error(f"❌ 패턴 분석 오류: {e}")
            return None

class PairNotificationService:
    """실시간 페어 알림 서비스"""
    
    def __init__(self):
        self.detector = PairDetector()
        self.settings = PairNotificationSettings()
        self.recent_pairs: List[PairEvent] = []
        self.notification_history: Dict[str, datetime] = {}
        self.notification_count_minute: Dict[str, int] = {}
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # 통계
        self.stats = {
            'total_pairs_detected': 0,
            'total_notifications_sent': 0,
            'pair_types': {pair_type.value: 0 for pair_type in PairType},
            'patterns': {pattern.value: 0 for pattern in PairPattern},
            'tables': {}
        }
    
    async def start(self):
        """서비스 시작"""
        if self.running:
            return
        
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        logger.info("🚀 실시간 페어 알림 서비스 시작")
    
    async def stop(self):
        """서비스 중지"""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ 실시간 페어 알림 서비스 중지")
    
    async def process_game_data(self, table_name: str, game_number: int, 
                               player_cards: List[str], banker_cards: List[str],
                               additional_data: Dict[str, Any] = None) -> Optional[PairEvent]:
        """
        게임 데이터에서 페어 감지 및 알림 처리
        
        Args:
            table_name: 테이블 이름
            game_number: 게임 번호
            player_cards: 플레이어 카드
            banker_cards: 뱅커 카드
            additional_data: 추가 데이터
            
        Returns:
            Optional[PairEvent]: 감지된 페어 이벤트
        """
        try:
            if not self.settings.enabled:
                return None
            
            # 페어 감지
            player_has_pair, player_confidence = self.detector.detect_pair(player_cards)
            banker_has_pair, banker_confidence = self.detector.detect_pair(banker_cards)
            
            # 페어 타입 결정
            pair_type = PairType.NO_PAIR
            confidence = 0.0
            
            if player_has_pair and banker_has_pair:
                pair_type = PairType.BOTH_PAIRS
                confidence = min(player_confidence, banker_confidence)
            elif player_has_pair:
                pair_type = PairType.PLAYER_PAIR
                confidence = player_confidence
            elif banker_has_pair:
                pair_type = PairType.BANKER_PAIR
                confidence = banker_confidence
            
            # 페어가 없거나 신뢰도가 낮으면 무시
            if pair_type == PairType.NO_PAIR or confidence < self.settings.min_confidence:
                return None
            
            # 알림 설정 확인
            if pair_type not in self.settings.notification_types:
                return None
            
            # 페어 이벤트 생성
            event_id = f"{table_name}_{game_number}_{datetime.now().strftime('%H%M%S')}"
            pair_event = PairEvent(
                id=event_id,
                table_name=table_name,
                game_number=game_number,
                pair_type=pair_type,
                timestamp=datetime.now(),
                player_cards=player_cards,
                banker_cards=banker_cards,
                confidence=confidence,
                metadata=additional_data or {}
            )
            
            # 패턴 분석
            if self.settings.pattern_detection_enabled:
                pattern = self.detector.analyze_pair_pattern(self.recent_pairs, table_name)
                pair_event.pattern = pattern
            
            # 쿨다운 확인
            if not await self._check_notification_cooldown(table_name):
                logger.info(f"🔕 페어 알림 쿨다운 중: {table_name}")
                return pair_event
            
            # 분당 알림 제한 확인
            if not await self._check_rate_limit(table_name):
                logger.info(f"🔕 페어 알림 속도 제한: {table_name}")
                return pair_event
            
            # 알림 전송
            await self._send_pair_notification(pair_event)
            
            # 이력에 추가
            self.recent_pairs.append(pair_event)
            
            # 통계 업데이트
            self._update_stats(pair_event)
            
            logger.info(f"✅ 페어 감지 및 알림: {table_name} - {pair_type.value} (신뢰도: {confidence:.2f})")
            
            return pair_event
            
        except Exception as e:
            logger.error(f"❌ 게임 데이터 처리 오류: {e}")
            return None
    
    async def _send_pair_notification(self, pair_event: PairEvent):
        """페어 알림 전송"""
        try:
            # 알림 제목 생성
            pair_emoji = {
                PairType.PLAYER_PAIR: "🎰",
                PairType.BANKER_PAIR: "🏦",
                PairType.BOTH_PAIRS: "💰",
            }
            
            emoji = pair_emoji.get(pair_event.pair_type, "🎯")
            title = f"{emoji} {pair_event.pair_type.value.replace('_', ' ').title()} 감지!"
            
            # 메시지 생성
            message = f"{pair_event.table_name} 테이블 게임 {pair_event.game_number}에서 페어가 감지되었습니다."
            
            if pair_event.pattern:
                message += f" 패턴: {pair_event.pattern.value.replace('_', ' ').title()}"
            
            # 우선순위 결정
            priority = NotificationPriority.HIGH
            if pair_event.pair_type == PairType.BOTH_PAIRS:
                priority = NotificationPriority.CRITICAL
            elif pair_event.pattern in [PairPattern.CONSECUTIVE_PAIRS, PairPattern.RARE_PATTERN]:
                priority = NotificationPriority.HIGH
            else:
                priority = NotificationPriority.NORMAL
            
            # 추가 데이터
            notification_data = {
                'pair_event': pair_event.to_dict(),
                'cards_info': {
                    'player_cards': pair_event.player_cards,
                    'banker_cards': pair_event.banker_cards
                },
                'analysis': {
                    'confidence': pair_event.confidence,
                    'pattern': pair_event.pattern.value if pair_event.pattern else None,
                    'recommendation': self._get_betting_recommendation(pair_event)
                }
            }
            
            # 알림 서비스로 전송
            from services.notification_service import NotificationData
            
            notification = NotificationData(
                id=f"pair_notif_{pair_event.id}",
                type=NotificationType.PAIR_ALERT,
                priority=priority,
                title=title,
                message=message,
                data=notification_data,
                timestamp=pair_event.timestamp,
                channels={"websocket", "log"}
            )
            
            await notification_service.send_notification(notification)
            
            # 알림 이력 업데이트
            self.notification_history[pair_event.table_name] = datetime.now()
            
            # 분당 카운터 업데이트
            minute_key = f"{pair_event.table_name}_{datetime.now().strftime('%H%M')}"
            self.notification_count_minute[minute_key] = self.notification_count_minute.get(minute_key, 0) + 1
            
            self.stats['total_notifications_sent'] += 1
            
        except Exception as e:
            logger.error(f"❌ 페어 알림 전송 실패: {e}")
    
    def _get_betting_recommendation(self, pair_event: PairEvent) -> str:
        """베팅 권장사항 생성"""
        recommendations = {
            PairType.PLAYER_PAIR: "플레이어 페어 베팅 고려",
            PairType.BANKER_PAIR: "뱅커 페어 베팅 고려", 
            PairType.BOTH_PAIRS: "양쪽 페어 베팅 기회"
        }
        
        base_rec = recommendations.get(pair_event.pair_type, "관찰 권장")
        
        if pair_event.pattern == PairPattern.CONSECUTIVE_PAIRS:
            base_rec += " (연속 패턴 - 주의깊게 관찰)"
        elif pair_event.pattern == PairPattern.RARE_PATTERN:
            base_rec += " (희귀 패턴 - 신중한 베팅)"
        
        return base_rec
    
    async def _check_notification_cooldown(self, table_name: str) -> bool:
        """알림 쿨다운 확인"""
        if table_name not in self.notification_history:
            return True
        
        last_notification = self.notification_history[table_name]
        cooldown_end = last_notification + timedelta(seconds=self.settings.notification_cooldown_seconds)
        
        return datetime.now() >= cooldown_end
    
    async def _check_rate_limit(self, table_name: str) -> bool:
        """분당 알림 제한 확인"""
        minute_key = f"{table_name}_{datetime.now().strftime('%H%M')}"
        current_count = self.notification_count_minute.get(minute_key, 0)
        
        return current_count < self.settings.max_notifications_per_minute
    
    def _update_stats(self, pair_event: PairEvent):
        """통계 업데이트"""
        self.stats['total_pairs_detected'] += 1
        self.stats['pair_types'][pair_event.pair_type.value] += 1
        
        if pair_event.pattern:
            self.stats['patterns'][pair_event.pattern.value] += 1
        
        if pair_event.table_name not in self.stats['tables']:
            self.stats['tables'][pair_event.table_name] = {
                'total_pairs': 0,
                'pair_types': {pair_type.value: 0 for pair_type in PairType}
            }
        
        table_stats = self.stats['tables'][pair_event.table_name]
        table_stats['total_pairs'] += 1
        table_stats['pair_types'][pair_event.pair_type.value] += 1
    
    async def _cleanup_worker(self):
        """정리 작업 워커"""
        while self.running:
            try:
                # 1시간마다 실행
                await asyncio.sleep(3600)
                
                # 오래된 페어 이벤트 제거 (24시간 이상)
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.recent_pairs = [pair for pair in self.recent_pairs if pair.timestamp >= cutoff_time]
                
                # 오래된 알림 이력 제거 (1시간 이상)
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.notification_history = {
                    table: timestamp for table, timestamp in self.notification_history.items()
                    if timestamp >= cutoff_time
                }
                
                # 오래된 분당 카운터 제거
                current_hour_minute = datetime.now().strftime('%H%M')
                self.notification_count_minute = {
                    key: count for key, count in self.notification_count_minute.items()
                    if key.endswith(current_hour_minute)
                }
                
                logger.info("🧹 페어 알림 서비스 정리 작업 완료")
                
            except Exception as e:
                logger.error(f"❌ 정리 작업 오류: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return {
            'service_status': {
                'running': self.running,
                'recent_pairs_count': len(self.recent_pairs),
                'notification_cooldown_active': len(self.notification_history)
            },
            'settings': {
                'enabled': self.settings.enabled,
                'min_confidence': self.settings.min_confidence,
                'cooldown_seconds': self.settings.notification_cooldown_seconds,
                'max_per_minute': self.settings.max_notifications_per_minute
            },
            'stats': self.stats,
            'recent_activity': {
                'last_5_pairs': [pair.to_dict() for pair in self.recent_pairs[-5:]]
            }
        }
    
    def get_recent_pairs(self, limit: int = 20, table_name: str = None) -> List[Dict[str, Any]]:
        """최근 페어 이벤트 반환"""
        pairs = self.recent_pairs
        
        if table_name:
            pairs = [pair for pair in pairs if pair.table_name == table_name]
        
        # 최신순으로 정렬하고 제한
        pairs = sorted(pairs, key=lambda x: x.timestamp, reverse=True)
        return [pair.to_dict() for pair in pairs[:limit]]
    
    def update_settings(self, settings: Dict[str, Any]):
        """설정 업데이트"""
        try:
            if 'enabled' in settings:
                self.settings.enabled = settings['enabled']
            
            if 'min_confidence' in settings:
                self.settings.min_confidence = max(0.0, min(1.0, settings['min_confidence']))
            
            if 'notification_cooldown_seconds' in settings:
                self.settings.notification_cooldown_seconds = max(1, settings['notification_cooldown_seconds'])
            
            if 'max_notifications_per_minute' in settings:
                self.settings.max_notifications_per_minute = max(1, settings['max_notifications_per_minute'])
            
            if 'pattern_detection_enabled' in settings:
                self.settings.pattern_detection_enabled = settings['pattern_detection_enabled']
            
            if 'notification_types' in settings:
                try:
                    types = [PairType(t) for t in settings['notification_types'] if t in [pt.value for pt in PairType]]
                    self.settings.notification_types = set(types)
                except ValueError:
                    logger.warning("잘못된 알림 타입 설정 무시")
            
            logger.info("✅ 페어 알림 설정 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 설정 업데이트 오류: {e}")

# 전역 페어 알림 서비스 인스턴스
pair_notification_service = PairNotificationService()

async def get_pair_notification_service() -> PairNotificationService:
    """페어 알림 서비스 의존성"""
    return pair_notification_service