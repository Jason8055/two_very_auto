#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
페어 데이터 관련 API 라우트
페어 발생 정보 조회, 통계, 상세 정보 제공
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import asyncio

# 로컬 모듈
from ..models.game import GameData, PairType, TableStats, SystemStats
from ..services.optimized_database import OptimizedDatabase, get_database_service
from ..services.async_ai_engine import AsyncAIEngine, get_async_ai_engine
from ..services.packet_monitor_service import PacketMonitorService, get_packet_monitor_service
from ..services.notification_service import NotificationService, get_notification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pairs", tags=["페어 데이터"])

# WebSocket 연결 관리
class PairWebSocketManager:
    """페어 데이터 WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """새 연결 추가"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"페어 WebSocket 연결 추가: {len(self.active_connections)}개 활성")
    
    def disconnect(self, websocket: WebSocket):
        """연결 제거"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"페어 WebSocket 연결 제거: {len(self.active_connections)}개 활성")
    
    async def broadcast(self, message: dict):
        """모든 연결에 메시지 브로드캐스트"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message, ensure_ascii=False, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.warning(f"WebSocket 메시지 전송 실패: {e}")
                disconnected.append(connection)
        
        # 실패한 연결들 제거
        for conn in disconnected:
            self.disconnect(conn)

# 전역 WebSocket 매니저
websocket_manager = PairWebSocketManager()


@router.get("/", response_class=HTMLResponse)
async def show_pair_display_page():
    """페어 데이터 웹 인터페이스 페이지"""
    try:
        from pathlib import Path
        template_path = Path(__file__).parent.parent / "templates" / "pair_display.html"
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html><head><title>페이지를 찾을 수 없음</title></head>
            <body><h1>페어 디스플레이 페이지가 준비 중입니다.</h1></body></html>
            """)
    except Exception as e:
        logger.error(f"페어 디스플레이 페이지 로드 실패: {e}")
        raise HTTPException(status_code=500, detail="페이지 로드 실패")


@router.get("/recent")
async def get_recent_pairs(
    limit: int = Query(50, ge=1, le=200, description="조회할 페어 수"),
    table_name: Optional[str] = Query(None, description="특정 테이블 필터"),
    pair_type: Optional[PairType] = Query(None, description="페어 타입 필터"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="최근 N시간 내 데이터"),
    db: OptimizedDatabase = Depends(get_database_service)
):
    """
    최근 페어 발생 목록 조회
    
    Args:
        limit: 조회할 최대 페어 수
        table_name: 테이블명 필터
        pair_type: 페어 타입 필터
        hours: 최근 N시간 내 데이터만 조회
        db: 데이터베이스 서비스
    
    Returns:
        페어 발생 목록
    """
    try:
        # 시간 필터 설정
        since_time = None
        if hours:
            since_time = datetime.now() - timedelta(hours=hours)
        
        # 데이터베이스에서 페어 데이터 조회
        pairs = await db.get_recent_pairs(
            limit=limit,
            table_name=table_name,
            pair_type=pair_type.value if pair_type else None,
            since=since_time
        )
        
        # 페어별 발생 빈도 계산
        pair_frequency = {}
        for pair in pairs:
            key = f"{pair['table_name']}_{pair['pair_type']}"
            pair_frequency[key] = pair_frequency.get(key, 0) + 1
        
        # 빈도 정보 추가
        for pair in pairs:
            key = f"{pair['table_name']}_{pair['pair_type']}"
            pair['frequency'] = pair_frequency[key]
        
        return {
            "status": "success",
            "data": pairs,
            "total": len(pairs),
            "filters": {
                "table_name": table_name,
                "pair_type": pair_type.value if pair_type else None,
                "hours": hours
            }
        }
        
    except Exception as e:
        logger.error(f"최근 페어 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="페어 데이터 조회 실패")


@router.get("/{pair_id}/detail")
async def get_pair_detail(
    pair_id: str,
    db: OptimizedDatabase = Depends(get_database_service),
    ai_engine: AsyncAIEngine = Depends(get_async_ai_engine)
):
    """
    특정 페어의 상세 정보 조회
    
    Args:
        pair_id: 페어 ID 또는 게임 ID
        db: 데이터베이스 서비스
        ai_engine: AI 예측 엔진
    
    Returns:
        페어 상세 정보 (카드 정보, AI 예측 등)
    """
    try:
        # 페어 기본 정보 조회
        pair_detail = await db.get_pair_detail(pair_id)
        
        if not pair_detail:
            raise HTTPException(status_code=404, detail="페어 정보를 찾을 수 없습니다")
        
        # AI 예측 정보 추가 (있는 경우)
        ai_prediction = None
        try:
            # 최근 게임 데이터 조회
            recent_games = await db.get_recent_games(
                table_name=pair_detail['table_name'],
                limit=20
            )
            
            if recent_games:
                ai_prediction = await ai_engine.get_prediction_for_game(pair_detail['game_id'])
                
        except Exception as e:
            logger.warning(f"AI 예측 정보 조회 실패: {e}")
        
        # 상세 정보 구성
        detail_info = {
            **pair_detail,
            "ai_prediction": ai_prediction,
            "related_stats": await _get_related_stats(pair_detail, db)
        }
        
        return {
            "status": "success",
            "data": detail_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"페어 상세 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="상세 정보 조회 실패")


@router.get("/stats/overview")
async def get_pair_stats_overview(
    table_name: Optional[str] = Query(None, description="특정 테이블 통계"),
    db: OptimizedDatabase = Depends(get_database_service)
):
    """
    페어 발생 통계 개요
    
    Args:
        table_name: 특정 테이블 통계 (None이면 전체)
        db: 데이터베이스 서비스
    
    Returns:
        페어 통계 정보
    """
    try:
        # 전체 통계
        total_stats = await db.get_pair_statistics(table_name)
        
        # 오늘 통계
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_stats = await db.get_pair_statistics(table_name, since=today_start)
        
        # 활성 테이블 수 (최근 1시간 내 활동)
        recent_time = datetime.now() - timedelta(hours=1)
        active_tables = await db.get_active_tables_count(since=recent_time)
        
        # 페어 타입별 분포
        pair_type_distribution = await db.get_pair_type_distribution(table_name)
        
        return {
            "status": "success",
            "data": {
                "total_pairs": total_stats.get("total_pairs", 0),
                "total_games": total_stats.get("total_games", 0),
                "pair_rate": total_stats.get("pair_rate", 0.0),
                "today_pairs": today_stats.get("total_pairs", 0),
                "today_games": today_stats.get("total_games", 0),
                "today_pair_rate": today_stats.get("pair_rate", 0.0),
                "active_tables": active_tables,
                "pair_type_distribution": pair_type_distribution,
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"페어 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="통계 정보 조회 실패")


@router.get("/tables/list")
async def get_table_list(
    db: OptimizedDatabase = Depends(get_database_service)
):
    """
    페어가 발생한 테이블 목록 조회
    
    Args:
        db: 데이터베이스 서비스
    
    Returns:
        테이블 목록과 각 테이블의 기본 정보
    """
    try:
        tables = await db.get_tables_with_pairs()
        
        table_info = []
        for table in tables:
            info = {
                "name": table["table_name"],
                "total_pairs": table["total_pairs"],
                "last_pair_time": table["last_pair_time"],
                "pair_rate": table["pair_rate"]
            }
            table_info.append(info)
        
        return {
            "status": "success",
            "data": table_info
        }
        
    except Exception as e:
        logger.error(f"테이블 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="테이블 목록 조회 실패")


@router.get("/frequency/analysis")
async def get_pair_frequency_analysis(
    table_name: Optional[str] = Query(None, description="특정 테이블 분석"),
    days: int = Query(7, ge=1, le=30, description="분석 기간 (일)"),
    db: OptimizedDatabase = Depends(get_database_service)
):
    """
    페어 발생 빈도 분석
    
    Args:
        table_name: 분석할 테이블명
        days: 분석 기간
        db: 데이터베이스 서비스
    
    Returns:
        페어 발생 빈도 분석 결과
    """
    try:
        since_time = datetime.now() - timedelta(days=days)
        
        # 테이블별 페어 발생 빈도
        table_frequency = await db.get_pair_frequency_by_table(since=since_time)
        
        # 시간대별 페어 발생 패턴
        hourly_pattern = await db.get_pair_hourly_pattern(
            table_name=table_name, 
            since=since_time
        )
        
        # 페어 간격 분석
        pair_intervals = await db.get_pair_interval_analysis(
            table_name=table_name,
            since=since_time
        )
        
        return {
            "status": "success",
            "data": {
                "analysis_period": {
                    "days": days,
                    "from": since_time.isoformat(),
                    "to": datetime.now().isoformat()
                },
                "table_frequency": table_frequency,
                "hourly_pattern": hourly_pattern,
                "pair_intervals": pair_intervals,
                "summary": {
                    "avg_pairs_per_day": sum(tf["pair_count"] for tf in table_frequency) / days,
                    "most_active_hour": max(hourly_pattern.items(), key=lambda x: x[1])[0] if hourly_pattern else None,
                    "avg_interval_minutes": pair_intervals.get("avg_minutes", 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"페어 빈도 분석 실패: {e}")
        raise HTTPException(status_code=500, detail="빈도 분석 실패")


@router.post("/monitoring/start")
async def start_pair_monitoring(
    monitor_service: PacketMonitorService = Depends(get_packet_monitor_service)
):
    """
    실시간 페어 모니터링 시작
    
    Args:
        monitor_service: 패킷 모니터링 서비스
    
    Returns:
        모니터링 시작 결과
    """
    try:
        success = await monitor_service.start_monitoring()
        
        if success:
            return {
                "status": "success",
                "message": "실시간 페어 모니터링이 시작되었습니다.",
                "monitoring_stats": monitor_service.get_monitoring_stats()
            }
        else:
            raise HTTPException(status_code=500, detail="모니터링 시작 실패")
            
    except Exception as e:
        logger.error(f"페어 모니터링 시작 실패: {e}")
        raise HTTPException(status_code=500, detail="모니터링 시작 실패")


@router.post("/monitoring/stop")
async def stop_pair_monitoring(
    monitor_service: PacketMonitorService = Depends(get_packet_monitor_service)
):
    """
    실시간 페어 모니터링 중지
    
    Args:
        monitor_service: 패킷 모니터링 서비스
    
    Returns:
        모니터링 중지 결과
    """
    try:
        await monitor_service.stop_monitoring()
        
        return {
            "status": "success",
            "message": "실시간 페어 모니터링이 중지되었습니다.",
            "final_stats": monitor_service.get_monitoring_stats()
        }
        
    except Exception as e:
        logger.error(f"페어 모니터링 중지 실패: {e}")
        raise HTTPException(status_code=500, detail="모니터링 중지 실패")


@router.websocket("/ws/updates")
async def pair_websocket_endpoint(websocket: WebSocket):
    """
    페어 데이터 실시간 업데이트 WebSocket 엔드포인트
    
    Args:
        websocket: WebSocket 연결
    """
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # 클라이언트에서 메시지를 받아서 처리 (ping/pong 등)
            message = await websocket.receive_text()
            
            if message == "ping":
                await websocket.send_text("pong")
            elif message == "get_stats":
                # 실시간 통계 전송
                stats = await _get_realtime_stats()
                await websocket.send_text(json.dumps({
                    "type": "stats_update",
                    "data": stats
                }, ensure_ascii=False, default=str))
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        websocket_manager.disconnect(websocket)


async def _get_related_stats(pair_detail: dict, db: OptimizedDatabase) -> dict:
    """페어와 관련된 추가 통계 정보"""
    try:
        table_name = pair_detail['table_name']
        
        # 해당 테이블의 최근 페어 통계
        recent_stats = await db.get_pair_statistics(table_name, since=datetime.now() - timedelta(hours=24))
        
        # 같은 타입 페어의 최근 발생
        same_type_recent = await db.get_recent_pairs(
            table_name=table_name,
            pair_type=pair_detail['pair_type'],
            limit=5
        )
        
        return {
            "table_24h_pairs": recent_stats.get("total_pairs", 0),
            "table_24h_rate": recent_stats.get("pair_rate", 0.0),
            "same_type_recent_count": len(same_type_recent),
            "last_same_type": same_type_recent[0]['game_time'] if same_type_recent else None
        }
        
    except Exception as e:
        logger.warning(f"관련 통계 조회 실패: {e}")
        return {}


async def _get_realtime_stats():
    """실시간 통계 정보 수집"""
    try:
        db = get_database_service()
        
        # 기본 통계
        total_stats = await db.get_pair_statistics()
        today_stats = await db.get_pair_statistics(since=datetime.now().replace(hour=0, minute=0, second=0))
        
        return {
            "total_pairs": total_stats.get("total_pairs", 0),
            "today_pairs": today_stats.get("total_pairs", 0),
            "pair_rate": total_stats.get("pair_rate", 0.0),
            "active_tables": await db.get_active_tables_count(),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"실시간 통계 수집 실패: {e}")
        return {}


# WebSocket 매니저를 외부에서 사용할 수 있도록 export
def get_websocket_manager() -> PairWebSocketManager:
    """페어 WebSocket 매니저 반환"""
    return websocket_manager