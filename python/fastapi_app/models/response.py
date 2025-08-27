#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic 응답 모델들
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from .game import TableStats, SystemStats, PairAlert, RealtimeUpdate

class BaseResponse(BaseModel):
    """기본 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    message: Optional[str] = Field(default=None, description="메시지")

class ErrorResponse(BaseResponse):
    """오류 응답 모델"""
    success: bool = Field(default=False)
    error: str = Field(..., description="오류 내용")
    error_code: Optional[str] = Field(default=None, description="오류 코드")
    details: Optional[Dict[str, Any]] = Field(default=None, description="상세 정보")

class DemoRequest(BaseModel):
    """데모 요청 모델"""
    game_count: int = Field(default=10, ge=1, le=100, description="생성할 게임 수")
    table_name: Optional[str] = Field(default=None, description="특정 테이블명")
    force_pairs: bool = Field(default=False, description="강제 페어 생성 여부")
    pair_probability: float = Field(default=0.25, ge=0.0, le=1.0, description="페어 확률")

class DemoResponse(BaseResponse):
    """데모 응답 모델"""
    games_added: int = Field(..., ge=0, description="추가된 게임 수")
    pairs_found: int = Field(..., ge=0, description="발견된 페어 수")
    processing_time: float = Field(..., ge=0.0, description="처리 시간 (초)")
    mode: str = Field(default="fastapi_async", description="실행 모드")
    tables_affected: List[str] = Field(default_factory=list, description="영향받은 테이블 목록")
    pair_details: List[Dict[str, Any]] = Field(default_factory=list, description="페어 상세 정보")

class StatsResponse(BaseResponse):
    """통계 응답 모델"""
    stats: SystemStats = Field(..., description="시스템 통계")
    db_size_kb: float = Field(..., description="데이터베이스 크기 (KB)")
    cache_stats: Optional[Dict[str, Any]] = Field(default=None, description="캐시 통계")

class RealDataResponse(BaseResponse):
    """실제 데이터 응답 모델"""
    source: str = Field(..., description="데이터 소스")
    stats: SystemStats = Field(..., description="실제 데이터 통계")
    file_info: Dict[str, Any] = Field(..., description="파일 정보")

class HealthCheckResponse(BaseResponse):
    """상태 확인 응답 모델"""
    status: str = Field(..., description="서비스 상태")
    version: str = Field(..., description="버전")
    database_status: str = Field(..., description="데이터베이스 상태")
    services: Dict[str, str] = Field(..., description="서비스별 상태")
    uptime: Optional[str] = Field(default=None, description="가동 시간")

class WebSocketMessage(BaseModel):
    """WebSocket 메시지 모델"""
    type: str = Field(..., description="메시지 타입")
    timestamp: datetime = Field(default_factory=datetime.now, description="메시지 시간")
    data: Dict[str, Any] = Field(..., description="메시지 데이터")
    client_id: Optional[str] = Field(default=None, description="클라이언트 ID")

class PairAlertResponse(BaseResponse):
    """페어 알림 응답 모델"""
    alert: PairAlert = Field(..., description="페어 알림 정보")
    notification_sent: bool = Field(..., description="알림 전송 여부")
    channels: List[str] = Field(default_factory=list, description="전송된 채널 목록")

class RealtimeStatsResponse(BaseResponse):
    """실시간 통계 응답 모델"""
    current_stats: SystemStats = Field(..., description="현재 통계")
    updates: List[RealtimeUpdate] = Field(..., description="실시간 업데이트 목록")
    connected_clients: int = Field(..., description="연결된 클라이언트 수")

class TableResponse(BaseResponse):
    """테이블 응답 모델"""
    table_stats: TableStats = Field(..., description="테이블 통계")
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list, description="최근 활동")

class BatchResponse(BaseResponse):
    """배치 처리 응답 모델"""
    total_processed: int = Field(..., description="처리된 총 항목 수")
    successful: int = Field(..., description="성공한 항목 수")
    failed: int = Field(..., description="실패한 항목 수")
    processing_time: float = Field(..., description="처리 시간")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="처리 결과 목록")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="오류 목록")