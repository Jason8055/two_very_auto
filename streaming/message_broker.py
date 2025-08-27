#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 메시지 브로커
Redis Streams 기반 실시간 메시징 시스템
"""

import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
from enum import Enum

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
    safe_print("✅ Redis 클라이언트 라이브러리 사용 가능")
except ImportError:
    REDIS_AVAILABLE = False
    safe_print("⚠️ Redis 라이브러리 미설치. pip install redis 실행 필요")


class MessageType(Enum):
    """메시지 타입"""
    BACCARAT_UPDATE = "baccarat_update"
    AI_PREDICTION = "ai_prediction"
    SYSTEM_ALERT = "system_alert"
    USER_ACTION = "user_action"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_LOG = "error_log"


@dataclass
class StreamMessage:
    """스트림 메시지 클래스"""
    message_id: str
    stream_name: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    producer: str
    priority: int = 1  # 1(낮음) ~ 5(높음)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "message_id": self.message_id,
            "stream_name": self.stream_name,
            "message_type": self.message_type.value,
            "payload": json.dumps(self.payload),
            "timestamp": self.timestamp.isoformat(),
            "producer": self.producer,
            "priority": self.priority
        }


@dataclass
class ConsumerGroup:
    """컨슈머 그룹 정보"""
    group_name: str
    stream_name: str
    consumers: List[str]
    last_id: str
    pending_count: int


class RedisMessageBroker:
    """Redis Streams 기반 메시지 브로커"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379,
                 redis_db: int = 0, redis_password: Optional[str] = None):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        
        # 동기/비동기 클라이언트
        self.redis_client = None
        self.async_redis_client = None
        
        # 컨슈머 및 스트림 관리
        self.streams: Dict[str, Dict] = {}
        self.consumer_groups: Dict[str, ConsumerGroup] = {}
        self.message_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.consumer_threads: Dict[str, threading.Thread] = {}
        
        # 메트릭
        self.messages_produced = 0
        self.messages_consumed = 0
        self.error_count = 0
        
        if REDIS_AVAILABLE:
            self.initialize_redis()
        
        safe_print("📨 Redis 메시지 브로커 초기화 완료")
    
    def initialize_redis(self) -> bool:
        """Redis 클라이언트 초기화"""
        try:
            # 동기 클라이언트
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # 연결 테스트
            self.redis_client.ping()
            
            # 비동기 클라이언트
            self.async_redis_client = aioredis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True
            )
            
            safe_print("✅ Redis 연결 완료")
            return True
            
        except Exception as e:
            logger.error(f"Redis 초기화 실패: {e}")
            return False
    
    def create_stream(self, stream_name: str, max_length: int = 10000) -> bool:
        """스트림 생성"""
        if not self.redis_client:
            return False
        
        try:
            # 스트림이 존재하지 않으면 생성
            if not self.redis_client.exists(stream_name):
                # 더미 메시지로 스트림 생성
                self.redis_client.xadd(
                    stream_name, 
                    {"type": "init", "timestamp": datetime.now().isoformat()},
                    maxlen=max_length,
                    approximate=True
                )
                
                # 더미 메시지 삭제
                messages = self.redis_client.xread({stream_name: "0"}, count=1)
                if messages and messages[0][1]:
                    self.redis_client.xdel(stream_name, messages[0][1][0][0])
            
            self.streams[stream_name] = {
                "max_length": max_length,
                "created_at": datetime.now()
            }
            
            safe_print(f"📋 스트림 생성: {stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"스트림 생성 실패: {e}")
            return False
    
    def create_consumer_group(self, stream_name: str, group_name: str,
                            start_id: str = "$") -> bool:
        """컨슈머 그룹 생성"""
        if not self.redis_client:
            return False
        
        try:
            # 스트림이 없으면 생성
            self.create_stream(stream_name)
            
            # 컨슈머 그룹 생성 (이미 존재하면 무시)
            try:
                self.redis_client.xgroup_create(
                    stream_name, group_name, start_id, mkstream=True
                )
                safe_print(f"👥 컨슈머 그룹 생성: {group_name} @ {stream_name}")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    safe_print(f"👥 컨슈머 그룹 존재: {group_name}")
                else:
                    raise e
            
            self.consumer_groups[f"{stream_name}:{group_name}"] = ConsumerGroup(
                group_name=group_name,
                stream_name=stream_name,
                consumers=[],
                last_id=start_id,
                pending_count=0
            )
            
            return True
            
        except Exception as e:
            logger.error(f"컨슈머 그룹 생성 실패: {e}")
            return False
    
    def produce_message(self, stream_name: str, message_type: MessageType,
                       payload: Dict[str, Any], producer: str = "system",
                       priority: int = 1) -> Optional[str]:
        """메시지 생성"""
        if not self.redis_client:
            return None
        
        try:
            # 스트림 생성 (없으면)
            self.create_stream(stream_name)
            
            # 메시지 생성
            message = StreamMessage(
                message_id="",  # Redis가 자동 생성
                stream_name=stream_name,
                message_type=message_type,
                payload=payload,
                timestamp=datetime.now(),
                producer=producer,
                priority=priority
            )
            
            # Redis Streams에 추가
            message_id = self.redis_client.xadd(
                stream_name,
                message.to_dict(),
                maxlen=self.streams.get(stream_name, {}).get("max_length", 10000),
                approximate=True
            )
            
            self.messages_produced += 1
            
            safe_print(f"📤 메시지 생성: {message_type.value} -> {stream_name} ({message_id})")
            return message_id
            
        except Exception as e:
            logger.error(f"메시지 생성 실패: {e}")
            self.error_count += 1
            return None
    
    def consume_messages(self, stream_name: str, group_name: str,
                        consumer_name: str, count: int = 10,
                        block: int = 1000) -> List[StreamMessage]:
        """메시지 소비"""
        if not self.redis_client:
            return []
        
        try:
            # 컨슈머 그룹 확인/생성
            if not self.create_consumer_group(stream_name, group_name):
                return []
            
            # 미처리 메시지 먼저 확인
            pending_messages = self.redis_client.xreadgroup(
                group_name,
                consumer_name,
                {stream_name: "0"},
                count=count
            )
            
            if not pending_messages or not pending_messages[0][1]:
                # 새 메시지 읽기
                messages = self.redis_client.xreadgroup(
                    group_name,
                    consumer_name,
                    {stream_name: ">"},
                    count=count,
                    block=block
                )
            else:
                messages = pending_messages
            
            result_messages = []
            
            if messages and messages[0][1]:
                for message_id, fields in messages[0][1]:
                    try:
                        # 메시지 파싱
                        message = StreamMessage(
                            message_id=message_id,
                            stream_name=stream_name,
                            message_type=MessageType(fields.get("message_type", "")),
                            payload=json.loads(fields.get("payload", "{}")),
                            timestamp=datetime.fromisoformat(fields.get("timestamp", "")),
                            producer=fields.get("producer", "unknown"),
                            priority=int(fields.get("priority", 1))
                        )
                        
                        result_messages.append(message)
                        self.messages_consumed += 1
                        
                    except Exception as e:
                        logger.error(f"메시지 파싱 실패: {e}")
                        self.error_count += 1
            
            return result_messages
            
        except Exception as e:
            logger.error(f"메시지 소비 실패: {e}")
            self.error_count += 1
            return []
    
    def acknowledge_message(self, stream_name: str, group_name: str,
                          message_id: str) -> bool:
        """메시지 확인 응답"""
        if not self.redis_client:
            return False
        
        try:
            result = self.redis_client.xack(stream_name, group_name, message_id)
            return result > 0
            
        except Exception as e:
            logger.error(f"메시지 ACK 실패: {e}")
            return False
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """메시지 핸들러 등록"""
        self.message_handlers[message_type.value].append(handler)
        safe_print(f"🔧 핸들러 등록: {message_type.value}")
    
    def start_consumer(self, stream_name: str, group_name: str,
                      consumer_name: str, auto_ack: bool = True):
        """컨슈머 시작"""
        def consumer_worker():
            safe_print(f"🔄 컨슈머 시작: {consumer_name} @ {group_name}")
            
            while True:
                try:
                    # 메시지 소비
                    messages = self.consume_messages(
                        stream_name, group_name, consumer_name, count=5
                    )
                    
                    for message in messages:
                        # 핸들러 실행
                        handlers = self.message_handlers.get(message.message_type.value, [])
                        
                        for handler in handlers:
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"핸들러 실행 실패: {e}")
                                self.error_count += 1
                        
                        # 자동 ACK
                        if auto_ack:
                            self.acknowledge_message(
                                stream_name, group_name, message.message_id
                            )
                    
                    # 메시지가 없으면 잠깐 대기
                    if not messages:
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"컨슈머 오류: {e}")
                    time.sleep(1)
        
        # 백그라운드 스레드로 실행
        thread = threading.Thread(target=consumer_worker, daemon=True)
        thread.start()
        self.consumer_threads[consumer_name] = thread
    
    def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """스트림 정보 조회"""
        if not self.redis_client:
            return {}
        
        try:
            info = self.redis_client.xinfo_stream(stream_name)
            
            return {
                "name": stream_name,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
                "radix_tree_keys": info.get("radix-tree-keys", 0),
                "radix_tree_nodes": info.get("radix-tree-nodes", 0)
            }
            
        except Exception as e:
            logger.error(f"스트림 정보 조회 실패: {e}")
            return {}
    
    def get_consumer_group_info(self, stream_name: str) -> List[Dict[str, Any]]:
        """컨슈머 그룹 정보 조회"""
        if not self.redis_client:
            return []
        
        try:
            groups_info = self.redis_client.xinfo_groups(stream_name)
            
            result = []
            for group in groups_info:
                result.append({
                    "name": group.get("name"),
                    "consumers": group.get("consumers", 0),
                    "pending": group.get("pending", 0),
                    "last_delivered_id": group.get("last-delivered-id")
                })
            
            return result
            
        except Exception as e:
            logger.error(f"컨슈머 그룹 정보 조회 실패: {e}")
            return []
    
    def cleanup_old_messages(self, stream_name: str, max_age_hours: int = 24) -> int:
        """오래된 메시지 정리"""
        if not self.redis_client:
            return 0
        
        try:
            # 현재 시간 - max_age_hours
            cutoff_timestamp = int((datetime.now() - timedelta(hours=max_age_hours)).timestamp() * 1000)
            
            # 해당 시간보다 오래된 메시지 삭제
            deleted = self.redis_client.xtrim(stream_name, minid=cutoff_timestamp)
            
            safe_print(f"🧹 {stream_name}: {deleted}개 오래된 메시지 삭제")
            return deleted
            
        except Exception as e:
            logger.error(f"메시지 정리 실패: {e}")
            return 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """브로커 메트릭 조회"""
        stream_metrics = {}
        
        for stream_name in self.streams:
            stream_info = self.get_stream_info(stream_name)
            stream_metrics[stream_name] = stream_info
        
        return {
            "messages_produced": self.messages_produced,
            "messages_consumed": self.messages_consumed,
            "error_count": self.error_count,
            "active_streams": len(self.streams),
            "active_consumers": len(self.consumer_threads),
            "stream_details": stream_metrics
        }


# 전역 인스턴스
_message_broker = None

def get_message_broker(redis_host: str = "localhost") -> RedisMessageBroker:
    """메시지 브로커 인스턴스 반환"""
    global _message_broker
    if _message_broker is None:
        _message_broker = RedisMessageBroker(redis_host=redis_host)
    return _message_broker


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== Redis 메시지 브로커 테스트 ===")
    
    broker = get_message_broker()
    
    if REDIS_AVAILABLE and broker.redis_client:
        # 스트림 생성
        broker.create_stream("test_stream")
        broker.create_consumer_group("test_stream", "test_group")
        
        # 핸들러 등록
        def test_handler(message: StreamMessage):
            safe_print(f"🔔 메시지 수신: {message.message_type.value} - {message.payload}")
        
        broker.register_handler(MessageType.SYSTEM_ALERT, test_handler)
        
        # 컨슈머 시작
        broker.start_consumer("test_stream", "test_group", "test_consumer")
        
        # 테스트 메시지 생성
        broker.produce_message(
            "test_stream",
            MessageType.SYSTEM_ALERT,
            {"message": "테스트 알림", "level": "info"},
            "test_producer"
        )
        
        # 잠깐 대기 후 메트릭 확인
        time.sleep(2)
        metrics = broker.get_metrics()
        safe_print(f"📊 브로커 메트릭: {metrics}")
    
    else:
        safe_print("❌ Redis 기능 사용 불가")
    
    safe_print("🏁 Redis 메시지 브로커 테스트 완료")