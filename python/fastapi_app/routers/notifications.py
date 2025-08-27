#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notification API Router - FastAPI
알림 시스템 관리 API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from services.notification_service import get_notification_service, NotificationService, NotificationData, NotificationType, NotificationPriority
from models.response import BaseResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/send", response_model=BaseResponse)
async def send_custom_notification(
    title: str,
    message: str,
    notification_type: str = "system_warning",
    priority: str = "normal",
    data: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    커스텀 알림 전송
    
    - **title**: 알림 제목
    - **message**: 알림 내용
    - **notification_type**: 알림 타입 (system_warning, performance_alert 등)
    - **priority**: 우선순위 (low, normal, high, critical, emergency)
    - **data**: 추가 데이터
    - **channels**: 전송 채널 목록
    """
    try:
        # Enum 변환
        try:
            notif_type = NotificationType(notification_type)
        except ValueError:
            notif_type = NotificationType.SYSTEM_WARNING
        
        try:
            notif_priority = NotificationPriority(priority)
        except ValueError:
            notif_priority = NotificationPriority.NORMAL
        
        # 알림 데이터 생성
        notification = NotificationData(
            id=f"custom_{datetime.now().timestamp()}",
            type=notif_type,
            priority=notif_priority,
            title=title,
            message=message,
            data=data or {},
            timestamp=datetime.now(),
            channels=set(channels) if channels else {"websocket", "log"}
        )
        
        # 알림 전송
        await notification_service.send_notification(notification)
        
        return BaseResponse(
            success=True,
            message="알림이 성공적으로 전송되었습니다.",
            data={
                "notification_id": notification.id,
                "type": notification_type,
                "priority": priority,
                "channels": list(notification.channels)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 커스텀 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 전송 실패: {str(e)}")

@router.post("/pair-alert", response_model=BaseResponse)
async def send_pair_alert(
    table_name: str,
    pair_type: str,
    game_number: int,
    additional_data: Optional[Dict[str, Any]] = None,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    페어 발견 알림 전송
    
    - **table_name**: 테이블 이름
    - **pair_type**: 페어 타입 (Player Pair, Banker Pair, Both)
    - **game_number**: 게임 번호
    - **additional_data**: 추가 정보
    """
    try:
        await notification_service.send_pair_alert(
            table_name=table_name,
            pair_type=pair_type,
            game_number=game_number,
            data=additional_data
        )
        
        return BaseResponse(
            success=True,
            message=f"{table_name} 테이블의 페어 알림이 전송되었습니다.",
            data={
                "table_name": table_name,
                "pair_type": pair_type,
                "game_number": game_number
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 페어 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"페어 알림 전송 실패: {str(e)}")

@router.post("/performance-alert", response_model=BaseResponse)
async def send_performance_alert(
    metric_name: str,
    current_value: float,
    threshold: float,
    additional_data: Optional[Dict[str, Any]] = None,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    성능 알림 전송
    
    - **metric_name**: 메트릭 이름
    - **current_value**: 현재 값
    - **threshold**: 임계값
    - **additional_data**: 추가 정보
    """
    try:
        await notification_service.send_performance_alert(
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            data=additional_data
        )
        
        return BaseResponse(
            success=True,
            message=f"{metric_name} 성능 알림이 전송되었습니다.",
            data={
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold": threshold,
                "exceeded": current_value > threshold
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 성능 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"성능 알림 전송 실패: {str(e)}")

@router.get("/stats")
async def get_notification_stats(
    notification_service: NotificationService = Depends(get_notification_service)
):
    """알림 서비스 통계 조회"""
    try:
        stats = notification_service.get_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.get("/history")
async def get_notification_history(
    limit: int = 50,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    알림 이력 조회
    
    - **limit**: 조회할 최대 개수 (기본: 50)
    """
    try:
        history = notification_service.get_recent_notifications(limit)
        return {
            "success": True,
            "data": {
                "notifications": history,
                "count": len(history),
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 이력 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"이력 조회 실패: {str(e)}")

@router.get("/health")
async def notification_health_check(
    notification_service: NotificationService = Depends(get_notification_service)
):
    """알림 시스템 상태 확인"""
    try:
        health_status = await notification_service.health_check()
        
        overall_healthy = (
            health_status.get('service_running', False) and
            health_status.get('worker_active', False) and
            all(
                channel.get('healthy', False) 
                for channel in health_status.get('channels', {}).values()
            )
        )
        
        return {
            "success": True,
            "healthy": overall_healthy,
            "data": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 시스템 상태 확인 실패: {e}")
        return {
            "success": False,
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/test")
async def test_notification_system(
    notification_service: NotificationService = Depends(get_notification_service)
):
    """알림 시스템 테스트"""
    try:
        # 테스트 알림들 전송
        test_notifications = [
            {
                "title": "테스트 알림 1",
                "message": "일반 우선순위 테스트 알림입니다.",
                "type": "system_warning",
                "priority": "normal"
            },
            {
                "title": "테스트 페어 알림",
                "message": "Player Pair 테스트 알림입니다.",
                "type": "pair_alert",
                "priority": "high"
            },
            {
                "title": "테스트 성능 알림",
                "message": "CPU 사용률 테스트 알림입니다.",
                "type": "performance_alert",
                "priority": "critical"
            }
        ]
        
        sent_count = 0
        for test_notif in test_notifications:
            try:
                notification = NotificationData(
                    id=f"test_{datetime.now().timestamp()}_{sent_count}",
                    type=NotificationType(test_notif["type"]),
                    priority=NotificationPriority(test_notif["priority"]),
                    title=test_notif["title"],
                    message=test_notif["message"],
                    data={"test": True, "sequence": sent_count},
                    timestamp=datetime.now(),
                    channels={"websocket", "log"}
                )
                
                await notification_service.send_notification(notification)
                sent_count += 1
                
            except Exception as e:
                logger.error(f"❌ 테스트 알림 {sent_count} 전송 실패: {e}")
        
        return BaseResponse(
            success=True,
            message=f"테스트 알림 {sent_count}개가 전송되었습니다.",
            data={
                "sent_count": sent_count,
                "total_tests": len(test_notifications),
                "test_types": [n["type"] for n in test_notifications]
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 알림 시스템 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")

@router.get("/types")
async def get_notification_types():
    """사용 가능한 알림 타입 및 우선순위 목록"""
    return {
        "success": True,
        "data": {
            "notification_types": [t.value for t in NotificationType],
            "priorities": [p.value for p in NotificationPriority],
            "default_channels": ["websocket", "log"]
        },
        "timestamp": datetime.now().isoformat()
    }