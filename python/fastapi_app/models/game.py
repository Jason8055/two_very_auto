#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic 데이터 모델 - 게임 관련
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class PairType(str, Enum):
    """페어 타입 열거형"""
    PLAYER_PAIR = "PLAYER_PAIR"
    BANKER_PAIR = "BANKER_PAIR"
    BOTH_PAIR = "BOTH_PAIR"
    NO_PAIR = "NO_PAIR"

class TableType(str, Enum):
    """테이블 타입 열거형"""
    STANDARD = "일반"
    PREMIUM = "프리미엄"
    VIP = "VIP"

class VIPLevel(str, Enum):
    """VIP 레벨 열거형"""
    STANDARD = "Standard"
    GOLD = "Gold"
    DIAMOND = "Diamond"
    PLATINUM = "Platinum"

class GameData(BaseModel):
    """개별 게임 데이터 모델"""
    table_name: str = Field(..., description="테이블명")
    game_number: int = Field(..., ge=1, description="게임 번호")
    player_cards: List[str] = Field(..., min_items=2, max_items=3, description="플레이어 카드")
    banker_cards: List[str] = Field(..., min_items=2, max_items=3, description="뱅커 카드")
    has_pair: bool = Field(default=False, description="페어 존재 여부")
    pair_type: Optional[PairType] = Field(default=PairType.NO_PAIR, description="페어 타입")
    pair_cards: Optional[List[str]] = Field(default=None, description="페어 카드들")
    game_time: datetime = Field(default_factory=datetime.now, description="게임 시간")
    
    @validator('player_cards', 'banker_cards')
    def validate_cards(cls, cards):
        """카드 형식 검증"""
        valid_values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        valid_suits = ['♠', '♥', '♦', '♣']
        
        for card in cards:
            if not any(card.startswith(val) and card.endswith(suit) 
                      for val in valid_values for suit in valid_suits):
                raise ValueError(f"Invalid card format: {card}")
        return cards
    
    @validator('pair_type', pre=True, always=True)
    def set_pair_type(cls, pair_type, values):
        """페어 타입 자동 설정"""
        if 'has_pair' in values and not values['has_pair']:
            return PairType.NO_PAIR
        return pair_type or PairType.NO_PAIR

class TableMetadata(BaseModel):
    """테이블 메타데이터 모델"""
    name_kr: str = Field(..., description="한국어 테이블명")
    name_en: str = Field(..., description="영어 테이블명")
    table_type: TableType = Field(..., description="테이블 타입")
    vip_level: VIPLevel = Field(..., description="VIP 레벨")
    betting_limit: str = Field(..., description="배팅 한도")
    location: str = Field(..., description="위치")
    capacity: str = Field(..., description="수용 인원")
    features: str = Field(..., description="특징")

class TableStats(BaseModel):
    """테이블 통계 모델"""
    table_name: str = Field(..., description="테이블명")
    games: int = Field(ge=0, description="총 게임 수")
    pairs: int = Field(ge=0, description="총 페어 수")
    pair_rate: float = Field(ge=0.0, le=100.0, description="페어 비율 (%)")
    last_activity: Optional[datetime] = Field(default=None, description="마지막 활동 시간")
    last_game_time: Optional[datetime] = Field(default=None, description="마지막 게임 시간")
    recent_pairs: List[Dict[str, Any]] = Field(default_factory=list, description="최근 페어 목록")
    metadata: TableMetadata = Field(..., description="테이블 메타데이터")

class GameSession(BaseModel):
    """게임 세션 모델"""
    session_id: str = Field(..., description="세션 ID")
    table_name: str = Field(..., description="테이블명")
    start_time: datetime = Field(default_factory=datetime.now, description="세션 시작 시간")
    end_time: Optional[datetime] = Field(default=None, description="세션 종료 시간")
    games: List[GameData] = Field(default_factory=list, description="게임 목록")
    total_games: int = Field(default=0, ge=0, description="총 게임 수")
    total_pairs: int = Field(default=0, ge=0, description="총 페어 수")
    pair_rate: float = Field(default=0.0, ge=0.0, le=100.0, description="페어 비율")

class PairAlert(BaseModel):
    """페어 알림 모델"""
    alert_id: str = Field(..., description="알림 ID")
    table_name: str = Field(..., description="테이블명")
    pair_type: PairType = Field(..., description="페어 타입")
    pair_cards: List[str] = Field(..., description="페어 카드들")
    game_data: GameData = Field(..., description="게임 데이터")
    alert_time: datetime = Field(default_factory=datetime.now, description="알림 시간")
    severity: str = Field(default="normal", description="심각도")
    
class SystemStats(BaseModel):
    """시스템 전체 통계 모델"""
    total_games: int = Field(ge=0, description="전체 게임 수")
    total_pairs: int = Field(ge=0, description="전체 페어 수")
    global_pair_rate: float = Field(ge=0.0, le=100.0, description="전체 페어 비율")
    active_tables: int = Field(ge=0, description="활성 테이블 수")
    active_sessions: int = Field(ge=0, description="활성 세션 수")
    system_uptime: str = Field(..., description="시스템 가동 시간")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트")
    table_breakdown: Dict[str, TableStats] = Field(default_factory=dict, description="테이블별 상세 통계")

class RealtimeUpdate(BaseModel):
    """실시간 업데이트 모델"""
    update_type: str = Field(..., description="업데이트 타입")
    timestamp: datetime = Field(default_factory=datetime.now, description="업데이트 시간")
    data: Dict[str, Any] = Field(..., description="업데이트 데이터")
    table_name: Optional[str] = Field(default=None, description="관련 테이블명")