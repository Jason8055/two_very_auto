#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
페어 전용 알림 채널 시스템
별도 WebSocket 채널로 페어 발생 시 실시간 알림 전송
"""

import json
import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from collections import deque
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PairAlertChannel:
    """페어 전용 알림 채널"""
    
    def __init__(self, port: int = 8765):
        """
        페어 알림 채널 초기화
        
        Args:
            port: WebSocket 서버 포트 (기본: 8765)
        """
        self.port = port
        self.connected_clients: Set = set()
        self.alert_queue = deque(maxlen=1000)
        self.server = None
        self.running = False
        
        # 페어 필터링 설정
        self.pair_filters = {
            'enable_player_pair': True,
            'enable_banker_pair': True, 
            'enable_both_pair': True,
            'minimum_confidence': 0.95,  # 페어 확신도 최소값
            'cooldown_seconds': 5  # 같은 테이블 연속 알림 방지 쿨다운
        }
        
        # 쿨다운 관리
        self.last_alert_time = {}  # table_id -> timestamp
        
        logger.info(f"[Pair Alert Channel] Initialized on port {port}")
    
    async def start_server(self):
        """WebSocket 서버 시작"""
        try:
            import websockets
            
            async def handle_client(websocket, path):
                """클라이언트 연결 처리"""
                client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
                self.connected_clients.add(websocket)
                logger.info(f"[Pair Alert] Client connected: {client_id}")
                
                try:
                    # 환영 메시지 전송
                    welcome_msg = {
                        'type': 'connection_established',
                        'message': '페어 알림 채널에 연결되었습니다',
                        'timestamp': datetime.now().isoformat(),
                        'settings': self.pair_filters
                    }
                    await websocket.send(json.dumps(welcome_msg, ensure_ascii=False))
                    
                    # 클라이언트 메시지 수신 대기
                    async for message in websocket:
                        await self._handle_client_message(websocket, message)
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"[Pair Alert] Client disconnected: {client_id}")
                except Exception as e:
                    logger.error(f"[Pair Alert] Client error: {e}")
                finally:
                    self.connected_clients.discard(websocket)
            
            self.server = await websockets.serve(handle_client, "localhost", self.port)
            self.running = True
            logger.info(f"[Pair Alert] Server started on ws://localhost:{self.port}")
            
            # 서버 실행 유지
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"[Pair Alert] Server start failed: {e}")
            raise
    
    async def _handle_client_message(self, websocket, message: str):
        """클라이언트 메시지 처리"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            if msg_type == 'update_filters':
                # 필터 설정 업데이트
                new_filters = data.get('filters', {})
                self.pair_filters.update(new_filters)
                
                response = {
                    'type': 'filters_updated',
                    'filters': self.pair_filters,
                    'timestamp': datetime.now().isoformat()
                }
                await websocket.send(json.dumps(response, ensure_ascii=False))
                
            elif msg_type == 'get_recent_alerts':
                # 최근 알림 내역 요청
                recent_alerts = list(self.alert_queue)[-20:]  # 최근 20개
                response = {
                    'type': 'recent_alerts',
                    'alerts': recent_alerts,
                    'count': len(recent_alerts),
                    'timestamp': datetime.now().isoformat()
                }
                await websocket.send(json.dumps(response, ensure_ascii=False))
                
            elif msg_type == 'ping':
                # 연결 확인
                response = {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }
                await websocket.send(json.dumps(response, ensure_ascii=False))
                
        except Exception as e:
            logger.error(f"[Pair Alert] Message handling error: {e}")
    
    async def send_pair_alert(self, pair_data: Dict[str, Any]) -> bool:
        """
        페어 알림 전송
        
        Args:
            pair_data: 페어 발생 데이터
            
        Returns:
            전송 성공 여부
        """
        try:
            # 필터링 검사
            if not self._should_send_alert(pair_data):
                return False
            
            # 알림 메시지 구성
            alert_message = self._create_alert_message(pair_data)
            
            # 큐에 저장
            self.alert_queue.append(alert_message)
            
            # 연결된 모든 클라이언트에게 전송
            if self.connected_clients:
                disconnected_clients = set()
                
                for client in self.connected_clients:
                    try:
                        await client.send(json.dumps(alert_message, ensure_ascii=False))
                    except Exception as e:
                        logger.warning(f"[Pair Alert] Failed to send to client: {e}")
                        disconnected_clients.add(client)
                
                # 연결 끊어진 클라이언트 제거
                self.connected_clients -= disconnected_clients
                
                logger.info(f"[Pair Alert] Sent to {len(self.connected_clients)} clients: {pair_data.get('pair_type', 'UNKNOWN')}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[Pair Alert] Send failed: {e}")
            return False
    
    def _should_send_alert(self, pair_data: Dict[str, Any]) -> bool:
        """알림 전송 여부 판단"""
        try:
            table_id = pair_data.get('table_name', 'unknown')
            pair_type = pair_data.get('pair_info', {}).get('pair_type')
            
            # 페어 타입 필터링
            if pair_type == 'PLAYER_PAIR' and not self.pair_filters['enable_player_pair']:
                return False
            elif pair_type == 'BANKER_PAIR' and not self.pair_filters['enable_banker_pair']:
                return False
            elif pair_type == 'BOTH_PAIR' and not self.pair_filters['enable_both_pair']:
                return False
            
            # 쿨다운 검사
            current_time = datetime.now().timestamp()
            last_time = self.last_alert_time.get(table_id, 0)
            
            if current_time - last_time < self.pair_filters['cooldown_seconds']:
                return False
            
            # 쿨다운 시간 업데이트
            self.last_alert_time[table_id] = current_time
            
            return True
            
        except Exception as e:
            logger.error(f"[Pair Alert] Filter check failed: {e}")
            return False
    
    def _create_alert_message(self, pair_data: Dict[str, Any]) -> Dict[str, Any]:
        """알림 메시지 생성"""
        pair_info = pair_data.get('pair_info', {})
        
        return {
            'type': 'pair_alert',
            'table_name': pair_data.get('table_name', 'Unknown'),
            'game_id': pair_data.get('game_id', 0),
            'pair_type': pair_info.get('pair_type', 'UNKNOWN'),
            'pair_cards': pair_info.get('pair_cards', []),
            'player_cards': pair_data.get('player_cards', []),
            'banker_cards': pair_data.get('banker_cards', []),
            'result': pair_data.get('result', 'Unknown'),
            'player_score': pair_data.get('player_score', 0),
            'banker_score': pair_data.get('banker_score', 0),
            'timestamp': pair_data.get('game_time', datetime.now().isoformat()),
            'alert_time': datetime.now().isoformat(),
            'confidence': 1.0,  # 현재는 고정값, 향후 AI 분석 결과로 대체 가능
            'priority': self._calculate_priority(pair_info.get('pair_type'))
        }
    
    def _calculate_priority(self, pair_type: Optional[str]) -> str:
        """페어 타입에 따른 우선순위 계산"""
        if pair_type == 'BOTH_PAIR':
            return 'HIGH'
        elif pair_type in ['PLAYER_PAIR', 'BANKER_PAIR']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계 정보 반환"""
        return {
            'connected_clients': len(self.connected_clients),
            'total_alerts_sent': len(self.alert_queue),
            'server_running': self.running,
            'port': self.port,
            'filters': self.pair_filters
        }
    
    def start_async_server(self):
        """비동기 서버를 별도 스레드에서 시작"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self.start_server())
            except Exception as e:
                logger.error(f"[Pair Alert] Async server error: {e}")
            finally:
                loop.close()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info("[Pair Alert] Async server started in background thread")


# 통합 테스트 함수
async def test_pair_alert_system():
    """페어 알림 시스템 테스트"""
    alert_channel = PairAlertChannel(port=8766)  # 테스트용 포트
    
    # 서버 시작
    server_task = asyncio.create_task(alert_channel.start_server())
    
    # 잠시 대기
    await asyncio.sleep(1)
    
    # 테스트 페어 데이터
    test_pair_data = {
        'table_name': 'test_table',
        'game_id': 1,
        'pair_info': {
            'pair_type': 'PLAYER_PAIR',
            'pair_cards': ['A♠', 'A♥']
        },
        'player_cards': ['A♠', 'A♥'],
        'banker_cards': ['K♦', '5♣'],
        'result': 'Player',
        'player_score': 2,
        'banker_score': 5,
        'game_time': datetime.now().isoformat()
    }
    
    # 알림 전송 테스트
    success = await alert_channel.send_pair_alert(test_pair_data)
    safe_print(f"[Test] Pair alert sent: {success}")
    
    # 통계 출력
    stats = alert_channel.get_connection_stats()
    safe_print(f"[Test] Connection stats: {stats}")


if __name__ == '__main__':
    safe_print("=== 페어 알림 채널 시스템 테스트 ===")
    try:
        asyncio.run(test_pair_alert_system())
    except KeyboardInterrupt:
        safe_print("[Test] Test interrupted by user")
    except Exception as e:
        safe_print(f"[Test] Test failed: {e}")