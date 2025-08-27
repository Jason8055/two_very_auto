#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 이벤트 스트리밍 시스템
실시간 게임 이벤트 및 AI 예측 스트리밍
"""

import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import deque

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class EventType(Enum):
    """이벤트 타입"""
    GAME_RESULT = "game_result"
    CARD_DEALT = "card_dealt"
    BET_PLACED = "bet_placed"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    AI_PREDICTION = "ai_prediction"
    PATTERN_DETECTED = "pattern_detected"
    BANKROLL_UPDATE = "bankroll_update"
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_METRIC = "performance_metric"


@dataclass
class StreamEvent:
    """스트림 이벤트 클래스"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str
    payload: Dict[str, Any]
    priority: int = 1  # 1(낮음) ~ 5(높음)
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "payload": self.payload,
            "priority": self.priority,
            "tags": self.tags
        }


@dataclass
class StreamFilter:
    """스트림 필터"""
    event_types: Optional[List[EventType]] = None
    sources: Optional[List[str]] = None
    min_priority: int = 1
    tags: Optional[List[str]] = None
    time_window_minutes: Optional[int] = None


class EventStreamer:
    """이벤트 스트리밍 시스템"""
    
    def __init__(self, buffer_size: int = 10000):
        self.buffer_size = buffer_size
        
        # 이벤트 버퍼
        self.event_buffer: deque = deque(maxlen=buffer_size)
        self.event_index: Dict[str, StreamEvent] = {}
        
        # 구독자 및 필터
        self.subscribers: Dict[str, Callable] = {}
        self.subscriber_filters: Dict[str, StreamFilter] = {}
        
        # 통계
        self.events_processed = 0
        self.events_filtered = 0
        self.subscribers_count = 0
        
        # 스트림 처리
        self.processing_enabled = True
        self.processing_thread = None
        
        # 외부 통합
        self._message_broker = None
        self._websocket_server = None
        
        self.start_processing()
        safe_print("🌊 이벤트 스트리밍 시스템 초기화 완료")
    
    def generate_event_id(self) -> str:
        """이벤트 ID 생성"""
        return f"evt_{int(time.time() * 1000)}_{id(self) % 10000}"
    
    def add_event(self, event_type: EventType, source: str, payload: Dict[str, Any],
                  priority: int = 1, tags: List[str] = None) -> str:
        """이벤트 추가"""
        event_id = self.generate_event_id()
        
        event = StreamEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            source=source,
            payload=payload,
            priority=priority,
            tags=tags or []
        )
        
        # 버퍼에 추가
        self.event_buffer.append(event)
        self.event_index[event_id] = event
        
        self.events_processed += 1
        
        # 버퍼 크기 관리
        if len(self.event_index) > self.buffer_size:
            # 가장 오래된 이벤트 제거
            oldest_event = self.event_buffer[0]
            self.event_index.pop(oldest_event.event_id, None)
        
        # 구독자에게 이벤트 전파
        self._notify_subscribers(event)
        
        return event_id
    
    def subscribe(self, subscriber_id: str, callback: Callable,
                 event_filter: Optional[StreamFilter] = None):
        """이벤트 구독"""
        self.subscribers[subscriber_id] = callback
        
        if event_filter:
            self.subscriber_filters[subscriber_id] = event_filter
        
        self.subscribers_count += 1
        safe_print(f"📡 구독자 등록: {subscriber_id}")
    
    def unsubscribe(self, subscriber_id: str):
        """구독 해제"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            self.subscriber_filters.pop(subscriber_id, None)
            self.subscribers_count -= 1
            safe_print(f"📡 구독자 해제: {subscriber_id}")
    
    def _apply_filter(self, event: StreamEvent, event_filter: StreamFilter) -> bool:
        """필터 적용"""
        # 이벤트 타입 필터
        if event_filter.event_types and event.event_type not in event_filter.event_types:
            return False
        
        # 소스 필터
        if event_filter.sources and event.source not in event_filter.sources:
            return False
        
        # 우선순위 필터
        if event.priority < event_filter.min_priority:
            return False
        
        # 태그 필터
        if event_filter.tags:
            if not any(tag in event.tags for tag in event_filter.tags):
                return False
        
        # 시간 윈도우 필터
        if event_filter.time_window_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=event_filter.time_window_minutes)
            if event.timestamp < cutoff_time:
                return False
        
        return True
    
    def _notify_subscribers(self, event: StreamEvent):
        """구독자에게 이벤트 알림"""
        for subscriber_id, callback in self.subscribers.items():
            try:
                # 필터 적용
                event_filter = self.subscriber_filters.get(subscriber_id)
                if event_filter and not self._apply_filter(event, event_filter):
                    self.events_filtered += 1
                    continue
                
                # 콜백 실행
                callback(event)
                
            except Exception as e:
                logger.error(f"구독자 알림 실패 ({subscriber_id}): {e}")
    
    def get_events(self, event_filter: Optional[StreamFilter] = None,
                   limit: int = 100) -> List[StreamEvent]:
        """필터링된 이벤트 목록 조회"""
        events = list(self.event_buffer)
        
        if event_filter:
            events = [e for e in events if self._apply_filter(e, event_filter)]
        
        # 최신순 정렬 후 제한
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
    
    def get_event_by_id(self, event_id: str) -> Optional[StreamEvent]:
        """ID로 이벤트 조회"""
        return self.event_index.get(event_id)
    
    def start_processing(self):
        """이벤트 처리 시작"""
        if self.processing_thread and self.processing_thread.is_alive():
            return
        
        def processing_worker():
            safe_print("🔄 이벤트 처리 워커 시작")
            
            while self.processing_enabled:
                try:
                    # 주기적인 정리 작업
                    self._cleanup_old_events()
                    
                    # 메시지 브로커 통합
                    self._sync_with_message_broker()
                    
                    # 성능 메트릭 이벤트 생성
                    self._generate_performance_metrics()
                    
                    time.sleep(10)  # 10초마다 실행
                    
                except Exception as e:
                    logger.error(f"이벤트 처리 워커 오류: {e}")
                    time.sleep(5)
        
        self.processing_thread = threading.Thread(target=processing_worker, daemon=True)
        self.processing_thread.start()
    
    def _cleanup_old_events(self, max_age_hours: int = 24):
        """오래된 이벤트 정리"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # 버퍼에서 오래된 이벤트 제거
        while self.event_buffer and self.event_buffer[0].timestamp < cutoff_time:
            old_event = self.event_buffer.popleft()
            self.event_index.pop(old_event.event_id, None)
    
    def _sync_with_message_broker(self):
        """메시지 브로커와 동기화"""
        if not self.message_broker:
            return
        
        try:
            from message_broker import MessageType
            
            # 최근 이벤트를 메시지 브로커로 전송
            recent_events = self.get_events(
                StreamFilter(time_window_minutes=1),
                limit=10
            )
            
            for event in recent_events:
                # 이벤트 타입에 따른 메시지 타입 매핑
                message_type_map = {
                    EventType.GAME_RESULT: MessageType.BACCARAT_UPDATE,
                    EventType.AI_PREDICTION: MessageType.AI_PREDICTION,
                    EventType.SYSTEM_STATUS: MessageType.SYSTEM_ALERT,
                    EventType.PERFORMANCE_METRIC: MessageType.PERFORMANCE_METRIC
                }
                
                message_type = message_type_map.get(event.event_type)
                if message_type:
                    self.message_broker.produce_message(
                        "event_stream",
                        message_type,
                        event.to_dict(),
                        event.source,
                        event.priority
                    )
                    
        except Exception as e:
            logger.error(f"메시지 브로커 동기화 실패: {e}")
    
    def _generate_performance_metrics(self):
        """성능 메트릭 이벤트 생성"""
        try:
            metrics = {
                "events_processed": self.events_processed,
                "events_filtered": self.events_filtered,
                "subscribers_count": self.subscribers_count,
                "buffer_usage": len(self.event_buffer) / self.buffer_size,
                "events_per_minute": self._calculate_events_per_minute(),
                "memory_usage_mb": self._estimate_memory_usage()
            }
            
            self.add_event(
                EventType.PERFORMANCE_METRIC,
                "event_streamer",
                metrics,
                priority=2,
                tags=["performance", "metrics"]
            )
            
        except Exception as e:
            logger.error(f"성능 메트릭 생성 실패: {e}")
    
    def _calculate_events_per_minute(self) -> float:
        """분당 이벤트 수 계산"""
        recent_events = [
            e for e in self.event_buffer
            if e.timestamp > datetime.now() - timedelta(minutes=1)
        ]
        return len(recent_events)
    
    def _estimate_memory_usage(self) -> float:
        """메모리 사용량 추정 (MB)"""
        try:
            import sys
            total_size = sum(sys.getsizeof(event) for event in self.event_buffer)
            return total_size / (1024 * 1024)
        except:
            return 0.0
    
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
    
    def integrate_with_game_system(self):
        """게임 시스템과 통합"""
        try:
            # 바카라 게임 이벤트 핸들러
            def handle_game_event(event_type: str, data: Dict[str, Any]):
                event_type_map = {
                    "game_result": EventType.GAME_RESULT,
                    "card_dealt": EventType.CARD_DEALT,
                    "round_start": EventType.ROUND_START,
                    "round_end": EventType.ROUND_END,
                    "bet_placed": EventType.BET_PLACED
                }
                
                mapped_type = event_type_map.get(event_type)
                if mapped_type:
                    self.add_event(
                        mapped_type,
                        "baccarat_game",
                        data,
                        priority=3,
                        tags=["game", "baccarat"]
                    )
            
            # AI 예측 이벤트 핸들러
            def handle_ai_prediction(prediction_data: Dict[str, Any]):
                self.add_event(
                    EventType.AI_PREDICTION,
                    "ai_engine",
                    prediction_data,
                    priority=4,
                    tags=["ai", "prediction"]
                )
            
            # WebSocket을 통한 실시간 스트리밍
            if self.websocket_server:
                self.subscribe("websocket_streamer", self._stream_to_websocket)
            
            safe_print("🎮 게임 시스템 통합 완료")
            
        except Exception as e:
            logger.error(f"게임 시스템 통합 실패: {e}")
    
    def _stream_to_websocket(self, event: StreamEvent):
        """WebSocket으로 이벤트 스트리밍"""
        if not self.websocket_server:
            return
        
        try:
            # 이벤트 타입에 따른 룸 매핑
            room_map = {
                EventType.GAME_RESULT: "baccarat_live",
                EventType.AI_PREDICTION: "ai_predictions",
                EventType.SYSTEM_STATUS: "system_alerts",
                EventType.PERFORMANCE_METRIC: "admin_room"
            }
            
            room_id = room_map.get(event.event_type, "baccarat_live")
            
            # WebSocket으로 브로드캐스트
            self.websocket_server.broadcast_to_room(
                room_id,
                "stream_event",
                event.to_dict()
            )
            
        except Exception as e:
            logger.error(f"WebSocket 스트리밍 실패: {e}")
    
    def get_stream_statistics(self) -> Dict[str, Any]:
        """스트림 통계 정보"""
        event_type_counts = {}
        source_counts = {}
        
        for event in self.event_buffer:
            event_type_counts[event.event_type.value] = event_type_counts.get(event.event_type.value, 0) + 1
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
        
        return {
            "total_events": len(self.event_buffer),
            "events_processed": self.events_processed,
            "events_filtered": self.events_filtered,
            "active_subscribers": self.subscribers_count,
            "buffer_utilization": len(self.event_buffer) / self.buffer_size,
            "events_per_minute": self._calculate_events_per_minute(),
            "memory_usage_mb": self._estimate_memory_usage(),
            "event_type_distribution": event_type_counts,
            "source_distribution": source_counts
        }
    
    def stop(self):
        """스트리머 중지"""
        self.processing_enabled = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        safe_print("🛑 이벤트 스트리밍 시스템 중지")


# 전역 인스턴스
_event_streamer = None

def get_event_streamer() -> EventStreamer:
    """이벤트 스트리머 인스턴스 반환"""
    global _event_streamer
    if _event_streamer is None:
        _event_streamer = EventStreamer()
    return _event_streamer


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 이벤트 스트리밍 시스템 테스트 ===")
    
    streamer = get_event_streamer()
    
    # 테스트 구독자 등록
    def test_subscriber(event: StreamEvent):
        safe_print(f"🔔 이벤트 수신: {event.event_type.value} from {event.source}")
    
    streamer.subscribe("test_subscriber", test_subscriber)
    
    # 테스트 이벤트 생성
    test_events = [
        (EventType.ROUND_START, "baccarat_game", {"round_id": "R001", "timestamp": time.time()}),
        (EventType.CARD_DEALT, "baccarat_game", {"card": "♠A", "position": "player"}),
        (EventType.AI_PREDICTION, "ai_engine", {"prediction": "banker", "confidence": 0.85}),
        (EventType.GAME_RESULT, "baccarat_game", {"winner": "banker", "player_total": 5, "banker_total": 7}),
        (EventType.ROUND_END, "baccarat_game", {"round_id": "R001", "duration": 45})
    ]
    
    for event_type, source, payload in test_events:
        event_id = streamer.add_event(event_type, source, payload, priority=3, tags=["test"])
        safe_print(f"📤 이벤트 생성: {event_id}")
        time.sleep(0.5)
    
    # 통계 정보 출력
    time.sleep(2)
    stats = streamer.get_stream_statistics()
    safe_print(f"📊 스트림 통계: {stats}")
    
    # 게임 시스템 통합 테스트
    streamer.integrate_with_game_system()
    
    safe_print("🏁 이벤트 스트리밍 시스템 테스트 완료")