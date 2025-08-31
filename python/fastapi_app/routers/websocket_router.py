#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 라우터 - FastAPI
실시간 통신을 위한 WebSocket 엔드포인트
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from models import WebSocketMessage, RealtimeUpdate
from services.database import DatabaseManager
from services.connection_monitor import connection_monitor, ClientType, ConnectionStatus

logger = logging.getLogger(__name__)
router = APIRouter()

class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None, client_type: ClientType = ClientType.UNKNOWN, ip_address: str = None, user_agent: str = None):
        """클라이언트 연결"""
        await websocket.accept()
        
        # 클라이언트 ID 생성
        if not client_id:
            client_id = f"client_{len(self.active_connections)}_{int(datetime.now().timestamp())}"
        
        self.active_connections.append(websocket)
        self.client_info[websocket] = {
            'client_id': client_id,
            'connected_at': datetime.now(),
            'subscriptions': set()
        }
        
        # 연결 모니터에 등록
        connection_monitor.register_client(
            client_id=client_id,
            websocket=websocket,
            client_type=client_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        client_count = len(self.active_connections)
        logger.info(f"🔌 WebSocket 클라이언트 연결: {client_id} ({client_type.value}) (총 {client_count}개 연결)")
        
        # 연결 알림 브로드캐스트
        await self.broadcast({
            'type': 'client_connected',
            'data': {
                'client_id': client_id,
                'client_type': client_type.value,
                'total_clients': client_count
            }
        }, exclude=websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            client_info = self.client_info.get(websocket, {})
            client_id = client_info.get('client_id', 'unknown')
            
            # 연결 모니터에서 해제
            connection_monitor.unregister_client(client_id)
            
            self.active_connections.remove(websocket)
            if websocket in self.client_info:
                del self.client_info[websocket]
            
            client_count = len(self.active_connections)
            logger.info(f"🔌 WebSocket 클라이언트 해제: {client_id} (총 {client_count}개 연결)")
            
            # 해제 알림 브로드캐스트
            await self.broadcast({
                'type': 'client_disconnected',
                'data': {
                    'client_id': client_id,
                    'total_clients': client_count
                }
            })
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """개인 메시지 전송"""
        try:
            formatted_message = WebSocketMessage(
                type=message.get('type', 'message'),
                data=message.get('data', {}),
                client_id=self.client_info.get(websocket, {}).get('client_id')
            )
            await websocket.send_text(json.dumps(formatted_message.dict(), default=str, ensure_ascii=False))
        except Exception as e:
            logger.error(f"❌ 개인 메시지 전송 실패: {e}")
    
    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """전체 브로드캐스트"""
        if not self.active_connections:
            return
        
        formatted_message = WebSocketMessage(
            type=message.get('type', 'broadcast'),
            data=message.get('data', {})
        )
        
        disconnected = []
        for connection in self.active_connections:
            if connection == exclude:
                continue
            
            try:
                await connection.send_text(json.dumps(formatted_message.dict(), default=str, ensure_ascii=False))
            except Exception as e:
                logger.error(f"❌ 브로드캐스트 전송 실패: {e}")
                disconnected.append(connection)
        
        # 실패한 연결들 정리
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def broadcast_to_subscribers(self, subscription_type: str, message: dict):
        """구독자에게만 브로드캐스트"""
        if not self.active_connections:
            return
        
        formatted_message = WebSocketMessage(
            type=message.get('type', subscription_type),
            data=message.get('data', {})
        )
        
        disconnected = []
        for connection in self.active_connections:
            client_info = self.client_info.get(connection, {})
            subscriptions = client_info.get('subscriptions', set())
            
            if subscription_type not in subscriptions:
                continue
            
            try:
                await connection.send_text(json.dumps(formatted_message.dict(), default=str, ensure_ascii=False))
            except Exception as e:
                logger.error(f"❌ 구독자 브로드캐스트 전송 실패: {e}")
                disconnected.append(connection)
        
        # 실패한 연결들 정리
        for connection in disconnected:
            await self.disconnect(connection)
    
    def get_connection_count(self) -> int:
        """연결 수 반환"""
        return len(self.active_connections)
    
    def get_client_info(self) -> List[Dict[str, Any]]:
        """클라이언트 정보 반환"""
        return [
            {
                'client_id': info['client_id'],
                'connected_at': info['connected_at'].isoformat(),
                'subscriptions': list(info['subscriptions'])
            }
            for info in self.client_info.values()
        ]

# 전역 WebSocket 매니저
websocket_manager = WebSocketManager()

@router.websocket("/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket, client_id: str = "anonymous"):
    """
    실시간 데이터 스트림 WebSocket
    
    - **client_id**: 클라이언트 식별자
    """
    # 헤더에서 클라이언트 정보 추출
    headers = dict(websocket.headers)
    user_agent = headers.get('user-agent', 'Unknown')
    client_host = headers.get('host', 'Unknown')
    
    await websocket_manager.connect(
        websocket, 
        client_id, 
        ClientType.API_CLIENT,
        client_host,
        user_agent
    )
    
    try:
        # 환영 메시지
        await websocket_manager.send_personal_message({
            'type': 'welcome',
            'data': {
                'message': f'환영합니다, {client_id}!',
                'server_time': datetime.now().isoformat(),
                'available_subscriptions': ['stats', 'pairs', 'alerts', 'system'],
                'commands': ['subscribe', 'unsubscribe', 'get_stats', 'ping']
            }
        }, websocket)
        
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 메시지 처리
            await handle_websocket_message(websocket, message_data)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket 오류: {e}")
        await websocket_manager.disconnect(websocket)

@router.websocket("/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """
    대시보드용 전용 WebSocket
    
    실시간 통계와 알림을 위한 대시보드 전용 연결
    """
    # 헤더에서 클라이언트 정보 추출
    headers = dict(websocket.headers)
    user_agent = headers.get('user-agent', 'Unknown')
    client_host = headers.get('host', 'Unknown')
    
    client_id = f"dashboard_{datetime.now().strftime('%H%M%S')}"
    await websocket_manager.connect(
        websocket, 
        client_id, 
        ClientType.DASHBOARD,
        client_host,
        user_agent
    )
    
    try:
        # 대시보드 초기화 데이터
        db = DatabaseManager()
        await db.initialize()
        
        try:
            stats = await db.get_system_stats()
            await websocket_manager.send_personal_message({
                'type': 'dashboard_init',
                'data': {
                    'stats': stats,
                    'client_id': client_id,
                    'features': ['실시간 통계', '페어 알림', '시스템 모니터링']
                }
            }, websocket)
        finally:
            await db.close()
        
        # 자동 구독
        client_info = websocket_manager.client_info.get(websocket, {})
        client_info['subscriptions'].update(['stats', 'pairs', 'alerts'])
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            await handle_websocket_message(websocket, message_data)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ 대시보드 WebSocket 오류: {e}")
        await websocket_manager.disconnect(websocket)

async def handle_websocket_message(websocket: WebSocket, message_data: dict):
    """WebSocket 메시지 처리"""
    try:
        command = message_data.get('command', '')
        data = message_data.get('data', {})
        
        client_info = websocket_manager.client_info.get(websocket, {})
        client_id = client_info.get('client_id', 'unknown')
        
        logger.info(f"📨 WebSocket 메시지: {client_id} - {command}")
        
        # 활동 업데이트
        connection_monitor.update_client_activity(client_id, "message_received", bytes_received=len(str(message_data)))
        
        if command == 'subscribe':
            # 구독 추가
            subscription_type = data.get('type')
            if subscription_type:
                client_info['subscriptions'].add(subscription_type)
                await websocket_manager.send_personal_message({
                    'type': 'subscription_confirmed',
                    'data': {
                        'subscription_type': subscription_type,
                        'subscriptions': list(client_info['subscriptions'])
                    }
                }, websocket)
        
        elif command == 'unsubscribe':
            # 구독 제거
            subscription_type = data.get('type')
            if subscription_type and subscription_type in client_info['subscriptions']:
                client_info['subscriptions'].remove(subscription_type)
                await websocket_manager.send_personal_message({
                    'type': 'subscription_removed',
                    'data': {
                        'subscription_type': subscription_type,
                        'subscriptions': list(client_info['subscriptions'])
                    }
                }, websocket)
        
        elif command == 'get_stats':
            # 실시간 통계 조회
            db = DatabaseManager()
            await db.initialize()
            try:
                stats = await db.get_system_stats()
                await websocket_manager.send_personal_message({
                    'type': 'current_stats',
                    'data': stats
                }, websocket)
            finally:
                await db.close()
        
        elif command == 'ping':
            # Ping/Pong 테스트
            connection_monitor.update_client_ping(client_id)
            
            await websocket_manager.send_personal_message({
                'type': 'pong',
                'data': {
                    'timestamp': datetime.now().isoformat(),
                    'client_id': client_id
                }
            }, websocket)
        
        else:
            # 알 수 없는 명령
            await websocket_manager.send_personal_message({
                'type': 'error',
                'data': {
                    'message': f'알 수 없는 명령: {command}',
                    'available_commands': ['subscribe', 'unsubscribe', 'get_stats', 'ping']
                }
            }, websocket)
    
    except Exception as e:
        logger.error(f"❌ WebSocket 메시지 처리 실패: {e}")
        await websocket_manager.send_personal_message({
            'type': 'error',
            'data': {
                'message': '메시지 처리 중 오류가 발생했습니다',
                'error': str(e)
            }
        }, websocket)

# 백그라운드에서 주기적으로 업데이트 전송
async def periodic_updates():
    """주기적 업데이트 전송"""
    while True:
        try:
            if websocket_manager.get_connection_count() > 0:
                # 시스템 통계 업데이트
                db = DatabaseManager()
                await db.initialize()
                try:
                    stats = await db.get_system_stats()
                    
                    await websocket_manager.broadcast_to_subscribers('stats', {
                        'type': 'stats_update',
                        'data': {
                            'stats': stats,
                            'update_time': datetime.now().isoformat()
                        }
                    })
                finally:
                    await db.close()
            
            # 30초마다 업데이트
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"❌ 주기적 업데이트 실패: {e}")
            await asyncio.sleep(60)  # 오류 시 1분 대기

@router.get("/connections")
async def get_websocket_connections():
    """WebSocket 연결 상태 조회"""
    stats = connection_monitor.get_connection_stats()
    clients = connection_monitor.get_detailed_client_list()
    
    return {
        'success': True,
        'connection_count': websocket_manager.get_connection_count(),
        'connection_stats': stats,
        'clients': clients,
        'legacy_clients': websocket_manager.get_client_info(),  # 호환성을 위해 유지
        'timestamp': datetime.now().isoformat()
    }

@router.get("/connections/stats")
async def get_connection_stats():
    """상세 연결 통계"""
    return {
        'success': True,
        'data': connection_monitor.get_connection_stats(),
        'timestamp': datetime.now().isoformat()
    }

@router.get("/connections/history")
async def get_connection_history(limit: int = 100):
    """연결 이력 조회"""
    return {
        'success': True,
        'data': {
            'history': connection_monitor.get_connection_history(limit),
            'limit': limit
        },
        'timestamp': datetime.now().isoformat()
    }

@router.get("/connections/{client_id}")
async def get_client_details(client_id: str):
    """특정 클라이언트 상세 정보"""
    client_info = connection_monitor.get_client_info(client_id)
    
    if not client_info:
        raise HTTPException(status_code=404, detail=f"클라이언트를 찾을 수 없습니다: {client_id}")
    
    return {
        'success': True,
        'data': client_info.to_dict(),
        'timestamp': datetime.now().isoformat()
    }

@router.post("/broadcast")
async def broadcast_message(message: dict):
    """관리자용 브로드캐스트 메시지 전송"""
    try:
        await websocket_manager.broadcast({
            'type': 'admin_message',
            'data': message
        })
        
        return {
            'success': True,
            'message': '브로드캐스트 전송 완료',
            'recipients': websocket_manager.get_connection_count(),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 브로드캐스트 실패: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.websocket("/pair-updates")
async def websocket_pair_updates_endpoint(websocket: WebSocket):
    """
    페어 업데이트 전용 WebSocket
    
    pair-display 페이지에서 실시간 페어 데이터를 받기 위한 엔드포인트
    """
    # 헤더에서 클라이언트 정보 추출
    headers = dict(websocket.headers)
    user_agent = headers.get('user-agent', 'Unknown')
    client_host = headers.get('host', 'Unknown')
    
    client_id = f"pair_updates_{datetime.now().strftime('%H%M%S')}"
    await websocket_manager.connect(
        websocket, 
        client_id, 
        ClientType.API_CLIENT,
        client_host,
        user_agent
    )
    
    try:
        # 페어 업데이트 초기화 데이터
        db = DatabaseManager()
        await db.initialize()
        
        try:
            # 최근 페어 데이터 조회
            from routers.improved_pair_api import get_recent_pairs, get_stats_overview
            recent_pairs = await get_recent_pairs(limit=10)
            stats = await get_stats_overview()
            
            await websocket_manager.send_personal_message({
                'type': 'pair_updates_init',
                'data': {
                    'recent_pairs': recent_pairs,
                    'stats': stats,
                    'client_id': client_id,
                    'features': ['실시간 페어 업데이트', '통계 정보', '테이블 상태']
                }
            }, websocket)
        finally:
            await db.close()
        
        # 페어 업데이트 구독 자동 설정
        client_info = websocket_manager.client_info.get(websocket, {})
        client_info['subscriptions'].update(['pairs', 'pair_updates', 'stats'])
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            await handle_websocket_message(websocket, message_data)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ 페어 업데이트 WebSocket 오류: {e}")
        await websocket_manager.disconnect(websocket)

# 외부에서 사용할 수 있도록 매니저 노출
def get_websocket_manager():
    """WebSocket 매니저 반환 (다른 모듈에서 사용)"""
    return websocket_manager