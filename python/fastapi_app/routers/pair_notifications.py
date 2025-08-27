#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pair Notifications Router - FastAPI
실시간 페어 알림 시스템 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from models.pair_notification import (
    PairEventRequest, PairEventResponse, 
    PairNotificationSettingsRequest, PairNotificationSettingsResponse,
    PairNotificationStatsResponse, PairHistoryRequest, PairHistoryResponse,
    PairTypeEnum, PairPatternEnum
)
from services.pair_notification_service import get_pair_notification_service, PairNotificationService
from services.notification_service import get_notification_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/detect", 
             response_model=Dict[str, Any],
             summary="페어 감지 및 알림",
             description="게임 데이터에서 페어를 감지하고 실시간 알림을 전송합니다.")
async def detect_pair(
    request: PairEventRequest,
    background_tasks: BackgroundTasks,
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """
    페어 감지 및 알림 API
    
    - **table_name**: 테이블 이름
    - **game_number**: 게임 번호  
    - **player_cards**: 플레이어 카드 배열
    - **banker_cards**: 뱅커 카드 배열
    - **additional_data**: 추가 데이터 (선택사항)
    
    실시간으로 페어를 감지하고 WebSocket을 통해 알림을 전송합니다.
    """
    try:
        logger.info(f"📥 페어 감지 요청: {request.table_name} 게임 {request.game_number}")
        
        # 백그라운드에서 페어 감지 처리
        pair_event = await service.process_game_data(
            table_name=request.table_name,
            game_number=request.game_number,
            player_cards=request.player_cards,
            banker_cards=request.banker_cards,
            additional_data=request.additional_data
        )
        
        if pair_event:
            logger.info(f"✅ 페어 감지 성공: {pair_event.pair_type.value}")
            return {
                "success": True,
                "message": f"페어 감지 완료: {pair_event.pair_type.value}",
                "pair_event": {
                    "id": pair_event.id,
                    "table_name": pair_event.table_name,
                    "game_number": pair_event.game_number,
                    "pair_type": pair_event.pair_type.value,
                    "confidence": pair_event.confidence,
                    "pattern": pair_event.pattern.value if pair_event.pattern else None,
                    "timestamp": pair_event.timestamp.isoformat()
                },
                "notification_sent": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.info("ℹ️ 페어 감지되지 않음 또는 알림 조건 불충족")
            return {
                "success": True,
                "message": "페어가 감지되지 않았거나 알림 조건을 충족하지 않습니다",
                "pair_event": None,
                "notification_sent": False,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ 페어 감지 처리 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"페어 감지 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/settings", 
            response_model=PairNotificationSettingsResponse,
            summary="알림 설정 조회",
            description="현재 페어 알림 설정을 조회합니다.")
async def get_notification_settings(
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """현재 페어 알림 설정 조회"""
    try:
        settings = service.settings
        
        return PairNotificationSettingsResponse(
            enabled=settings.enabled,
            notification_types=[t for t in settings.notification_types],
            min_confidence=settings.min_confidence,
            pattern_detection_enabled=settings.pattern_detection_enabled,
            consecutive_pair_threshold=settings.consecutive_pair_threshold,
            notification_cooldown_seconds=settings.notification_cooldown_seconds,
            max_notifications_per_minute=settings.max_notifications_per_minute
        )
        
    except Exception as e:
        logger.error(f"❌ 알림 설정 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"알림 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.put("/settings", 
            response_model=Dict[str, Any],
            summary="알림 설정 업데이트",
            description="페어 알림 설정을 업데이트합니다.")
async def update_notification_settings(
    request: PairNotificationSettingsRequest,
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """페어 알림 설정 업데이트"""
    try:
        # 요청 데이터를 딕셔너리로 변환 (None 값 제외)
        settings_data = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not settings_data:
            raise HTTPException(
                status_code=400,
                detail="업데이트할 설정이 없습니다"
            )
        
        # 설정 업데이트
        service.update_settings(settings_data)
        
        logger.info(f"✅ 알림 설정 업데이트: {list(settings_data.keys())}")
        
        return {
            "success": True,
            "message": "알림 설정이 성공적으로 업데이트되었습니다",
            "updated_fields": list(settings_data.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 알림 설정 업데이트 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"알림 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/stats", 
            response_model=PairNotificationStatsResponse,
            summary="알림 통계 조회",
            description="페어 알림 시스템의 통계 정보를 조회합니다.")
async def get_notification_stats(
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """페어 알림 시스템 통계 조회"""
    try:
        stats = service.get_stats()
        
        return PairNotificationStatsResponse(
            service_status=stats['service_status'],
            settings=stats['settings'],
            stats=stats['stats'],
            recent_activity=stats['recent_activity']
        )
        
    except Exception as e:
        logger.error(f"❌ 알림 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"알림 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/history", 
            response_model=PairHistoryResponse,
            summary="페어 이력 조회",
            description="최근 페어 감지 이력을 조회합니다.")
async def get_pair_history(
    limit: int = Query(20, ge=1, le=100, description="조회할 개수"),
    table_name: Optional[str] = Query(None, description="테이블 이름 필터"),
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """페어 감지 이력 조회"""
    try:
        pairs_data = service.get_recent_pairs(limit=limit, table_name=table_name)
        
        # PairEventResponse 모델로 변환
        pairs = []
        for pair_data in pairs_data:
            pairs.append(PairEventResponse(
                id=pair_data['id'],
                table_name=pair_data['table_name'],
                game_number=pair_data['game_number'],
                pair_type=PairTypeEnum(pair_data['pair_type']),
                timestamp=datetime.fromisoformat(pair_data['timestamp']),
                player_cards=pair_data['player_cards'],
                banker_cards=pair_data['banker_cards'],
                pattern=PairPatternEnum(pair_data['pattern']) if pair_data.get('pattern') else None,
                confidence=pair_data['confidence'],
                metadata=pair_data.get('metadata', {})
            ))
        
        return PairHistoryResponse(
            pairs=pairs,
            total_count=len(service.recent_pairs),
            filters={
                "limit": limit,
                "table_name": table_name
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 페어 이력 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"페어 이력 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/service/start", 
             response_model=Dict[str, Any],
             summary="알림 서비스 시작",
             description="페어 알림 서비스를 시작합니다.")
async def start_notification_service(
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """페어 알림 서비스 시작"""
    try:
        await service.start()
        
        return {
            "success": True,
            "message": "페어 알림 서비스가 시작되었습니다",
            "service_status": {
                "running": service.running,
                "recent_pairs_count": len(service.recent_pairs)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 서비스 시작 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"알림 서비스 시작 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/service/stop", 
             response_model=Dict[str, Any],
             summary="알림 서비스 중지",
             description="페어 알림 서비스를 중지합니다.")
async def stop_notification_service(
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """페어 알림 서비스 중지"""
    try:
        await service.stop()
        
        return {
            "success": True,
            "message": "페어 알림 서비스가 중지되었습니다",
            "service_status": {
                "running": service.running,
                "recent_pairs_count": len(service.recent_pairs)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 서비스 중지 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"알림 서비스 중지 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/service/health", 
            response_model=Dict[str, Any],
            summary="알림 서비스 상태 확인",
            description="페어 알림 서비스의 상태를 확인합니다.")
async def check_service_health(
    service: PairNotificationService = Depends(get_pair_notification_service),
    notification_service = Depends(get_notification_service)
):
    """페어 알림 서비스 상태 확인"""
    try:
        # 페어 알림 서비스 통계
        pair_stats = service.get_stats()
        
        # 일반 알림 서비스 상태
        notification_health = await notification_service.health_check()
        
        return {
            "success": True,
            "message": "서비스 상태 확인 완료",
            "pair_notification_service": {
                "running": service.running,
                "recent_pairs": len(service.recent_pairs),
                "settings_enabled": service.settings.enabled,
                "total_pairs_detected": pair_stats['stats']['total_pairs_detected'],
                "total_notifications_sent": pair_stats['stats']['total_notifications_sent']
            },
            "notification_service": {
                "running": notification_health['service_running'],
                "worker_active": notification_health['worker_active'],
                "queue_size": notification_health['queue_size'],
                "channels": notification_health['channels']
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 서비스 상태 확인 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"서비스 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/test", 
             response_model=Dict[str, Any],
             summary="테스트 페어 알림 전송",
             description="테스트용 페어 알림을 전송합니다.")
async def send_test_notification(
    table_name: str = Query("테스트 테이블", description="테스트 테이블 이름"),
    pair_type: PairTypeEnum = Query(PairTypeEnum.PLAYER_PAIR, description="테스트 페어 타입"),
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """테스트 페어 알림 전송"""
    try:
        # 테스트 게임 데이터 생성
        test_cards = {
            PairTypeEnum.PLAYER_PAIR: (["A♠", "A♥"], ["K♦", "Q♣"]),
            PairTypeEnum.BANKER_PAIR: (["K♦", "Q♣"], ["J♠", "J♥"]),
            PairTypeEnum.BOTH_PAIRS: (["A♠", "A♥"], ["K♦", "K♣"])
        }
        
        player_cards, banker_cards = test_cards.get(pair_type, (["A♠", "A♥"], ["K♦", "Q♣"]))
        
        # 테스트 페어 이벤트 처리
        pair_event = await service.process_game_data(
            table_name=table_name,
            game_number=9999,  # 테스트 게임 번호
            player_cards=player_cards,
            banker_cards=banker_cards,
            additional_data={
                "test_mode": True,
                "description": "API 테스트용 페어 알림"
            }
        )
        
        if pair_event:
            return {
                "success": True,
                "message": f"테스트 알림 전송 완료: {pair_type.value}",
                "test_data": {
                    "table_name": table_name,
                    "pair_type": pair_type.value,
                    "player_cards": player_cards,
                    "banker_cards": banker_cards,
                    "pair_event_id": pair_event.id,
                    "confidence": pair_event.confidence
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "테스트 알림 전송 실패 (서비스 비활성화 또는 설정 문제)",
                "test_data": {
                    "table_name": table_name,
                    "pair_type": pair_type.value,
                    "service_enabled": service.settings.enabled
                },
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ 테스트 알림 전송 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"테스트 알림 전송 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/tables/stats", 
            response_model=Dict[str, Any],
            summary="테이블별 페어 통계",
            description="테이블별 페어 감지 통계를 조회합니다.")
async def get_table_pair_stats(
    service: PairNotificationService = Depends(get_pair_notification_service)
):
    """테이블별 페어 통계 조회"""
    try:
        stats = service.get_stats()
        table_stats = stats['stats']['tables']
        
        return {
            "success": True,
            "message": "테이블별 통계 조회 완료",
            "tables": table_stats,
            "summary": {
                "total_tables": len(table_stats),
                "most_active_table": max(table_stats.keys(), key=lambda k: table_stats[k]['total_pairs']) if table_stats else None,
                "total_pairs_all_tables": sum(t['total_pairs'] for t in table_stats.values())
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 테이블별 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"테이블별 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )