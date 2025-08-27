#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket 실시간 통신 라우트
페어 데이터 실시간 업데이트 및 시스템 모니터링
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import logging
import asyncio
from datetime import datetime

# 로컬 모듈
from ..services.packet_monitor_service import get_packet_monitor_service
from ..services.deep_learning_analysis_service import get_deep_learning_analysis_service
from ..services.optimized_database import get_database_service

logger = logging.getLogger(__name__)
router = APIRouter()


class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: dict = {}
    
    async def connect(self, websocket: WebSocket, client_type: str = "client"):
        """새 연결 추가"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            'type': client_type,
            'connected_at': datetime.now().isoformat(),
            'last_ping': datetime.now().isoformat()
        }
        logger.info(f"WebSocket 연결 추가: {client_type} (총 {len(self.active_connections)}개)")
    
    def disconnect(self, websocket: WebSocket):
        """연결 제거"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_info:
            del self.connection_info[websocket]
        logger.info(f"WebSocket 연결 제거 (총 {len(self.active_connections)}개)")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """개별 연결에 메시지 전송"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"개별 메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """모든 연결에 메시지 브로드캐스트"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message, ensure_ascii=False, default=str)
        disconnected_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.warning(f"브로드캐스트 실패: {e}")
                disconnected_connections.append(connection)
        
        # 실패한 연결들 정리
        for connection in disconnected_connections:
            self.disconnect(connection)
    
    def get_connection_stats(self) -> dict:
        """연결 통계 반환"""
        return {
            'total_connections': len(self.active_connections),
            'connection_types': {},
            'connections_info': [
                {
                    'type': info['type'],
                    'connected_at': info['connected_at'],
                    'last_ping': info['last_ping']
                }
                for info in self.connection_info.values()
            ]
        }


# 전역 WebSocket 매니저
websocket_manager = WebSocketManager()


@router.websocket("/ws/pair-updates")
async def pair_updates_websocket(websocket: WebSocket):
    """
    페어 업데이트 실시간 WebSocket 엔드포인트
    
    클라이언트는 다음 메시지를 받을 수 있습니다:
    - new_pair: 새로운 페어 발생
    - stats_update: 통계 업데이트
    - prediction_update: AI 예측 업데이트
    """
    await websocket_manager.connect(websocket, "pair_client")
    
    try:
        # 초기 상태 전송
        await _send_initial_state(websocket)
        
        while True:
            # 클라이언트 메시지 수신 및 처리
            message = await websocket.receive_text()
            await _handle_client_message(websocket, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("페어 업데이트 클라이언트 연결 해제")
    except Exception as e:
        logger.error(f"페어 업데이트 WebSocket 오류: {e}")
        websocket_manager.disconnect(websocket)


@router.websocket("/ws/system-monitor")
async def system_monitor_websocket(websocket: WebSocket):
    """
    시스템 모니터링 실시간 WebSocket 엔드포인트
    
    시스템 상태, 성능 메트릭, 서비스 상태 등을 실시간으로 전송
    """
    await websocket_manager.connect(websocket, "monitor_client")
    
    try:
        # 시스템 상태 실시간 전송 시작
        await _start_system_monitoring(websocket)
        
        while True:
            message = await websocket.receive_text()
            
            if message == "get_status":
                await _send_system_status(websocket)
            elif message == "get_performance":
                await _send_performance_metrics(websocket)
            elif message.startswith("subscribe:"):
                # 특정 메트릭 구독
                metric = message.split(":", 1)[1]
                await _subscribe_to_metric(websocket, metric)
            else:
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                    websocket
                )
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("시스템 모니터링 클라이언트 연결 해제")
    except Exception as e:
        logger.error(f"시스템 모니터링 WebSocket 오류: {e}")
        websocket_manager.disconnect(websocket)


@router.websocket("/ws/analysis-updates")
async def analysis_updates_websocket(websocket: WebSocket):
    """
    딥러닝 분석 업데이트 실시간 WebSocket 엔드포인트
    
    AI 분석 결과, 모델 훈련 상태, 예측 업데이트 등을 전송
    """
    await websocket_manager.connect(websocket, "analysis_client")
    
    try:
        # 분석 상태 전송
        await _send_analysis_status(websocket)
        
        while True:
            message = await websocket.receive_text()
            
            if message == "get_analysis_status":
                await _send_analysis_status(websocket)
            elif message.startswith("analyze:"):
                # 실시간 분석 요청
                table_name = message.split(":", 1)[1]
                await _trigger_realtime_analysis(websocket, table_name)
            elif message == "get_predictions":
                await _send_latest_predictions(websocket)
            else:
                # 기본 응답
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                    websocket
                )
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("분석 업데이트 클라이언트 연결 해제")
    except Exception as e:
        logger.error(f"분석 업데이트 WebSocket 오류: {e}")
        websocket_manager.disconnect(websocket)


# 유틸리티 함수들

async def _send_initial_state(websocket: WebSocket):
    """초기 상태 정보 전송"""
    try:
        db_service = get_database_service()
        
        # 최근 페어 데이터
        recent_pairs = await db_service.get_recent_pairs(limit=10)
        
        # 기본 통계
        stats = await db_service.get_pair_statistics()
        
        initial_data = {
            "type": "initial_state",
            "data": {
                "recent_pairs": recent_pairs,
                "statistics": stats,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(initial_data, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"초기 상태 전송 실패: {e}")


async def _handle_client_message(websocket: WebSocket, message: str):
    """클라이언트 메시지 처리"""
    try:
        if message == "ping":
            await websocket_manager.send_personal_message("pong", websocket)
            
        elif message == "get_stats":
            db_service = get_database_service()
            stats = await db_service.get_pair_statistics()
            
            response = {
                "type": "stats_update",
                "data": stats,
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket_manager.send_personal_message(
                json.dumps(response, ensure_ascii=False, default=str),
                websocket
            )
            
        elif message.startswith("filter:"):
            # 필터 설정
            filter_params = message.split(":", 1)[1]
            await _apply_client_filter(websocket, filter_params)
            
        elif message == "get_tables":
            # 테이블 목록 전송
            await _send_table_list(websocket)
        
        # 클라이언트 활성 상태 업데이트
        if websocket in websocket_manager.connection_info:
            websocket_manager.connection_info[websocket]['last_ping'] = datetime.now().isoformat()
            
    except Exception as e:
        logger.error(f"클라이언트 메시지 처리 실패: {e}")


async def _start_system_monitoring(websocket: WebSocket):
    """시스템 모니터링 시작"""
    try:
        # 백그라운드에서 주기적으로 시스템 상태 전송
        asyncio.create_task(_periodic_system_updates(websocket))
        
    except Exception as e:
        logger.error(f"시스템 모니터링 시작 실패: {e}")


async def _periodic_system_updates(websocket: WebSocket):
    """주기적 시스템 상태 업데이트"""
    try:
        while websocket in websocket_manager.active_connections:
            await _send_system_status(websocket)
            await asyncio.sleep(10)  # 10초마다 업데이트
            
    except Exception as e:
        logger.error(f"주기적 시스템 업데이트 실패: {e}")


async def _send_system_status(websocket: WebSocket):
    """시스템 상태 전송"""
    try:
        packet_monitor = get_packet_monitor_service()
        
        system_status = {
            "type": "system_status",
            "data": {
                "packet_monitor": packet_monitor.get_monitoring_stats(),
                "websocket_connections": websocket_manager.get_connection_stats(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(system_status, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"시스템 상태 전송 실패: {e}")


async def _send_performance_metrics(websocket: WebSocket):
    """성능 메트릭 전송"""
    try:
        db_service = get_database_service()
        
        performance_data = {
            "type": "performance_metrics",
            "data": {
                "database_performance": await db_service.get_performance_metrics(),
                "websocket_stats": websocket_manager.get_connection_stats(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(performance_data, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"성능 메트릭 전송 실패: {e}")


async def _subscribe_to_metric(websocket: WebSocket, metric: str):
    """특정 메트릭 구독"""
    try:
        # 메트릭별 구독 로직 구현
        subscription_response = {
            "type": "subscription_confirmed",
            "data": {
                "metric": metric,
                "subscribed": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(subscription_response, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"메트릭 구독 실패: {e}")


async def _send_analysis_status(websocket: WebSocket):
    """분석 상태 전송"""
    try:
        dl_service = get_deep_learning_analysis_service()
        
        analysis_status = {
            "type": "analysis_status",
            "data": {
                "service_stats": dl_service.get_analysis_stats(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(analysis_status, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"분석 상태 전송 실패: {e}")


async def _trigger_realtime_analysis(websocket: WebSocket, table_name: str):
    """실시간 분석 실행"""
    try:
        dl_service = get_deep_learning_analysis_service()
        
        # 백그라운드에서 분석 실행
        asyncio.create_task(_background_analysis(websocket, table_name, dl_service))
        
        # 분석 시작 알림
        start_notification = {
            "type": "analysis_started",
            "data": {
                "table_name": table_name,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(start_notification, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"실시간 분석 실행 실패: {e}")


async def _background_analysis(websocket: WebSocket, table_name: str, dl_service):
    """백그라운드 분석 실행 및 결과 전송"""
    try:
        # 분석 실행
        analysis_result = await dl_service.analyze_pair_patterns(
            table_name=table_name,
            days=7,
            include_prediction=True
        )
        
        # 결과 전송
        result_message = {
            "type": "analysis_complete",
            "data": {
                "table_name": table_name,
                "result": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if websocket in websocket_manager.active_connections:
            await websocket_manager.send_personal_message(
                json.dumps(result_message, ensure_ascii=False, default=str),
                websocket
            )
        
    except Exception as e:
        logger.error(f"백그라운드 분석 실패: {e}")
        
        # 오류 메시지 전송
        error_message = {
            "type": "analysis_error",
            "data": {
                "table_name": table_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if websocket in websocket_manager.active_connections:
            await websocket_manager.send_personal_message(
                json.dumps(error_message, ensure_ascii=False, default=str),
                websocket
            )


async def _send_latest_predictions(websocket: WebSocket):
    """최신 예측 전송"""
    try:
        db_service = get_database_service()
        
        # 최근 예측 데이터 조회 (실제 구현 필요)
        predictions_data = {
            "type": "predictions_update",
            "data": {
                "predictions": [],  # 실제 예측 데이터
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(predictions_data, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"최신 예측 전송 실패: {e}")


async def _apply_client_filter(websocket: WebSocket, filter_params: str):
    """클라이언트 필터 적용"""
    try:
        # 필터 파라미터 파싱 (예: "table:스피드바카라A,type:PLAYER_PAIR")
        filters = {}
        for param in filter_params.split(","):
            if ":" in param:
                key, value = param.split(":", 1)
                filters[key.strip()] = value.strip()
        
        # 필터 확인 응답
        filter_response = {
            "type": "filter_applied",
            "data": {
                "filters": filters,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(filter_response, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"클라이언트 필터 적용 실패: {e}")


async def _send_table_list(websocket: WebSocket):
    """테이블 목록 전송"""
    try:
        db_service = get_database_service()
        tables = await db_service.get_tables_with_pairs()
        
        table_list = {
            "type": "table_list",
            "data": {
                "tables": tables,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(
            json.dumps(table_list, ensure_ascii=False, default=str),
            websocket
        )
        
    except Exception as e:
        logger.error(f"테이블 목록 전송 실패: {e}")


# 브로드캐스트 함수들 (외부에서 사용)

async def broadcast_new_pair(pair_data: dict):
    """새로운 페어 발생 브로드캐스트"""
    await websocket_manager.broadcast({
        "type": "new_pair",
        "data": pair_data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_stats_update(stats_data: dict):
    """통계 업데이트 브로드캐스트"""
    await websocket_manager.broadcast({
        "type": "stats_update",
        "data": stats_data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_prediction_update(prediction_data: dict):
    """예측 업데이트 브로드캐스트"""
    await websocket_manager.broadcast({
        "type": "prediction_update",
        "data": prediction_data,
        "timestamp": datetime.now().isoformat()
    })


def get_websocket_manager():
    """WebSocket 매니저 반환"""
    return websocket_manager