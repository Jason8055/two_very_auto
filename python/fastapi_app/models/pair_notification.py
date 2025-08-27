#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pair Notification Models - FastAPI
페어 알림 시스템 모델
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Pydantic 모델들
class PairTypeEnum(str, Enum):
    """페어 타입 열거형"""
    PLAYER_PAIR = "player_pair"
    BANKER_PAIR = "banker_pair"
    BOTH_PAIRS = "both_pairs"
    NO_PAIR = "no_pair"

class PairPatternEnum(str, Enum):
    """페어 패턴 열거형"""
    SINGLE_PAIR = "single_pair"
    CONSECUTIVE_PAIRS = "consecutive_pairs"
    ALTERNATING_PAIRS = "alternating_pairs"
    RARE_PATTERN = "rare_pattern"

class NotificationStatusEnum(str, Enum):
    """알림 상태 열거형"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PairEventRequest(BaseModel):
    """페어 이벤트 요청 모델"""
    table_name: str = Field(..., description="테이블 이름")
    game_number: int = Field(..., description="게임 번호", ge=1)
    player_cards: List[str] = Field(..., description="플레이어 카드 목록")
    banker_cards: List[str] = Field(..., description="뱅커 카드 목록")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터")
    
    @validator('player_cards', 'banker_cards')
    def validate_cards(cls, v):
        if not v or len(v) < 2:
            raise ValueError('카드는 최소 2장이 필요합니다')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "바카라 A",
                "game_number": 123,
                "player_cards": ["A♠", "A♥"],
                "banker_cards": ["K♦", "Q♣"],
                "additional_data": {"dealer": "김딜러", "room": "VIP"}
            }
        }

class PairEventResponse(BaseModel):
    """페어 이벤트 응답 모델"""
    id: str = Field(..., description="이벤트 ID")
    table_name: str = Field(..., description="테이블 이름")
    game_number: int = Field(..., description="게임 번호")
    pair_type: PairTypeEnum = Field(..., description="페어 타입")
    timestamp: datetime = Field(..., description="이벤트 시간")
    player_cards: List[str] = Field(..., description="플레이어 카드")
    banker_cards: List[str] = Field(..., description="뱅커 카드")
    pattern: Optional[PairPatternEnum] = Field(None, description="감지된 패턴")
    confidence: float = Field(..., description="감지 신뢰도", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "바카라A_123_143052",
                "table_name": "바카라 A",
                "game_number": 123,
                "pair_type": "player_pair",
                "timestamp": "2024-01-01T14:30:52",
                "player_cards": ["A♠", "A♥"],
                "banker_cards": ["K♦", "Q♣"],
                "pattern": "single_pair",
                "confidence": 1.0,
                "metadata": {"dealer": "김딜러"}
            }
        }

class PairNotificationSettingsRequest(BaseModel):
    """페어 알림 설정 요청 모델"""
    enabled: Optional[bool] = Field(None, description="알림 활성화")
    notification_types: Optional[List[PairTypeEnum]] = Field(None, description="알림 타입 목록")
    min_confidence: Optional[float] = Field(None, description="최소 신뢰도", ge=0.0, le=1.0)
    pattern_detection_enabled: Optional[bool] = Field(None, description="패턴 감지 활성화")
    notification_cooldown_seconds: Optional[int] = Field(None, description="알림 쿨다운 시간(초)", ge=1)
    max_notifications_per_minute: Optional[int] = Field(None, description="분당 최대 알림 수", ge=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "notification_types": ["player_pair", "banker_pair"],
                "min_confidence": 0.8,
                "pattern_detection_enabled": True,
                "notification_cooldown_seconds": 10,
                "max_notifications_per_minute": 5
            }
        }

class PairNotificationSettingsResponse(BaseModel):
    """페어 알림 설정 응답 모델"""
    enabled: bool = Field(..., description="알림 활성화")
    notification_types: List[PairTypeEnum] = Field(..., description="알림 타입 목록")
    min_confidence: float = Field(..., description="최소 신뢰도")
    pattern_detection_enabled: bool = Field(..., description="패턴 감지 활성화")
    consecutive_pair_threshold: int = Field(..., description="연속 페어 임계값")
    notification_cooldown_seconds: int = Field(..., description="알림 쿨다운 시간(초)")
    max_notifications_per_minute: int = Field(..., description="분당 최대 알림 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "notification_types": ["player_pair", "banker_pair", "both_pairs"],
                "min_confidence": 0.8,
                "pattern_detection_enabled": True,
                "consecutive_pair_threshold": 2,
                "notification_cooldown_seconds": 5,
                "max_notifications_per_minute": 10
            }
        }

class PairNotificationStatsResponse(BaseModel):
    """페어 알림 통계 응답 모델"""
    service_status: Dict[str, Any] = Field(..., description="서비스 상태")
    settings: Dict[str, Any] = Field(..., description="현재 설정")
    stats: Dict[str, Any] = Field(..., description="통계 정보")
    recent_activity: Dict[str, Any] = Field(..., description="최근 활동")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_status": {
                    "running": True,
                    "recent_pairs_count": 15,
                    "notification_cooldown_active": 3
                },
                "settings": {
                    "enabled": True,
                    "min_confidence": 0.8,
                    "cooldown_seconds": 5
                },
                "stats": {
                    "total_pairs_detected": 150,
                    "total_notifications_sent": 120,
                    "pair_types": {
                        "player_pair": 60,
                        "banker_pair": 55,
                        "both_pairs": 35
                    }
                },
                "recent_activity": {
                    "last_5_pairs": []
                }
            }
        }

class PairHistoryRequest(BaseModel):
    """페어 이력 요청 모델"""
    limit: Optional[int] = Field(20, description="조회 개수", ge=1, le=100)
    table_name: Optional[str] = Field(None, description="테이블 이름 필터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "limit": 50,
                "table_name": "바카라 A"
            }
        }

class PairHistoryResponse(BaseModel):
    """페어 이력 응답 모델"""
    pairs: List[PairEventResponse] = Field(..., description="페어 이벤트 목록")
    total_count: int = Field(..., description="전체 개수")
    filters: Dict[str, Any] = Field(..., description="적용된 필터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pairs": [],
                "total_count": 150,
                "filters": {
                    "limit": 20,
                    "table_name": "바카라 A"
                }
            }
        }

# SQLAlchemy 모델들
class PairEventDB(Base):
    """페어 이벤트 데이터베이스 모델"""
    __tablename__ = "pair_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    table_name = Column(String(50), nullable=False, index=True)
    game_number = Column(Integer, nullable=False, index=True)
    pair_type = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    player_cards = Column(JSON, nullable=False)
    banker_cards = Column(JSON, nullable=False)
    pattern = Column(String(30), nullable=True)
    confidence = Column(Float, nullable=False)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'id': self.event_id,
            'table_name': self.table_name,
            'game_number': self.game_number,
            'pair_type': self.pair_type,
            'timestamp': self.timestamp.isoformat(),
            'player_cards': self.player_cards,
            'banker_cards': self.banker_cards,
            'pattern': self.pattern,
            'confidence': self.confidence,
            'metadata': self.extra_data or {}
        }

class PairNotificationDB(Base):
    """페어 알림 데이터베이스 모델"""
    __tablename__ = "pair_notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String(100), unique=True, nullable=False, index=True)
    event_id = Column(String(100), nullable=False, index=True)
    table_name = Column(String(50), nullable=False, index=True)
    pair_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_data = Column(JSON, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'id': self.notification_id,
            'event_id': self.event_id,
            'table_name': self.table_name,
            'pair_type': self.pair_type,
            'status': self.status,
            'title': self.title,
            'message': self.message,
            'notification_data': self.notification_data or {},
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }

class PairStatisticsDB(Base):
    """페어 통계 데이터베이스 모델"""
    __tablename__ = "pair_statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    hour = Column(Integer, nullable=False, index=True)  # 0-23
    total_pairs = Column(Integer, default=0)
    player_pairs = Column(Integer, default=0)
    banker_pairs = Column(Integer, default=0)
    both_pairs = Column(Integer, default=0)
    total_games = Column(Integer, default=0)
    pair_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'table_name': self.table_name,
            'date': self.date,
            'hour': self.hour,
            'total_pairs': self.total_pairs,
            'player_pairs': self.player_pairs,
            'banker_pairs': self.banker_pairs,
            'both_pairs': self.both_pairs,
            'total_games': self.total_games,
            'pair_rate': self.pair_rate,
            'updated_at': self.updated_at.isoformat()
        }