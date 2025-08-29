#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pair Notification System Test Client
실시간 페어 알림 시스템 테스트 클라이언트
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import aiohttp
import sys
from utils.smart_output import info, success, warning, error

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PairNotificationTestClient:
    """페어 알림 시스템 테스트 클라이언트"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8004", ws_url: str = "ws://127.0.0.1:8004"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.session = None
        self.websocket = None
        
        # 테스트 데이터
        self.test_tables = ["바카라 A", "바카라 B", "스피드 바카라 1", "VIP 바카라"]
        self.test_cards = {
            "player_pair": (["A♠", "A♥"], ["K♦", "Q♣"]),
            "banker_pair": (["K♦", "Q♣"], ["J♠", "J♥"]),
            "both_pairs": (["A♠", "A♥"], ["K♦", "K♣"]),
            "no_pair": (["A♠", "2♥"], ["K♦", "Q♣"])
        }
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()
    
    async def test_api_health(self):
        """API 상태 확인 테스트"""
        info("API 상태 확인 테스트 시작")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    success("API 상태 정상", 상태=data.get('status', 'unknown'))
                    return True
                else:
                    error("API 상태 비정상", HTTP코드=response.status)
                    return False
                    
        except Exception as e:
            error("API 상태 확인 실패", 오류=str(e))
            return False
    
    async def test_pair_notification_service_health(self):
        """페어 알림 서비스 상태 확인"""
        info("페어 알림 서비스 상태 확인 테스트 시작")
        
        try:
            async with self.session.get(f"{self.base_url}/api/pair-notifications/service/health") as response:
                if response.status == 200:
                    data = await response.json()
                    service_data = data.get('pair_notification_service', {})
                    success("페어 알림 서비스 상태 정상",
                            실행상태=service_data.get('running', False),
                            감지된페어수=service_data.get('total_pairs_detected', 0),
                            전송된알림수=service_data.get('total_notifications_sent', 0))
                    return True
                else:
                    error("페어 알림 서비스 상태 확인 실패", HTTP코드=response.status)
                    return False
                    
        except Exception as e:
            error("페어 알림 서비스 상태 확인 실패", 오류=str(e))
            return False
    
    async def test_websocket_connection(self):
        """WebSocket 연결 테스트"""
        info("WebSocket 연결 테스트 시작")
        
        try:
            uri = f"{self.ws_url}/ws/realtime?client_id=test_client"
            self.websocket = await websockets.connect(uri)
            
            # 환영 메시지 수신
            welcome_message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            welcome_data = json.loads(welcome_message)
            
            success("WebSocket 연결 성공", 환영메시지=welcome_data.get('data', {}).get('message', '없음'))
            
            # 페어 알림 구독
            subscribe_message = {
                "command": "subscribe",
                "data": {"type": "pairs"}
            }
            await self.websocket.send(json.dumps(subscribe_message))
            
            # 구독 확인 메시지 수신
            confirmation = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            confirmation_data = json.loads(confirmation)
            
            success("페어 알림 구독 완료", 타입=confirmation_data.get('type', 'unknown'))
            
            return True
            
        except Exception as e:
            error("WebSocket 연결 실패", 오류=str(e))
            return False
    
    async def test_pair_detection(self):
        """페어 감지 테스트"""
        info("페어 감지 테스트 시작")
        
        results = []
        
        for pair_type, (player_cards, banker_cards) in self.test_cards.items():
            try:
                info(f"페어 타입 테스트 중", 타입=pair_type)
                
                test_data = {
                    "table_name": "테스트 테이블",
                    "game_number": 1001,
                    "player_cards": player_cards,
                    "banker_cards": banker_cards,
                    "additional_data": {
                        "test_type": pair_type,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                async with self.session.post(
                    f"{self.base_url}/api/pair-notifications/detect",
                    json=test_data
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        success = data.get('success', False)
                        notification_sent = data.get('notification_sent', False)
                        
                        if success:
                            if notification_sent:
                                pair_event = data.get('pair_event', {})
                                success("페어 감지 성공", 테스트타입=pair_type, 감지된페어=pair_event.get('pair_type', 'unknown'))
                            else:
                                info("페어 감지되지 않음", 테스트타입=pair_type, 상태="알림 조건 불충족")
                            
                            results.append({
                                'test_type': pair_type,
                                'success': True,
                                'notification_sent': notification_sent,
                                'data': data
                            })
                        else:
                            error("페어 감지 실패", 테스트타입=pair_type)
                            results.append({
                                'test_type': pair_type,
                                'success': False,
                                'error': data
                            })
                    else:
                        error("페어 감지 HTTP 오류", 테스트타입=pair_type, HTTP코드=response.status)
                        results.append({
                            'test_type': pair_type,
                            'success': False,
                            'error': f"HTTP {response.status}"
                        })
                
                # 간격 두기
                await asyncio.sleep(1)
                
            except Exception as e:
                error("페어 감지 예외 발생", 테스트타입=pair_type, 예외=str(e))
                results.append({
                    'test_type': pair_type,
                    'success': False,
                    'error': str(e)
                })
        
        successful_tests = sum(1 for r in results if r['success'])
        success("페어 감지 테스트 완료", 성공=f"{successful_tests}/{len(results)}")
        
        return results
    
    async def test_settings_management(self):
        """설정 관리 테스트"""
        info("설정 관리 테스트 시작")
        
        try:
            # 현재 설정 조회
            async with self.session.get(f"{self.base_url}/api/pair-notifications/settings") as response:
                if response.status == 200:
                    current_settings = await response.json()
                    success("현재 설정 조회 성공",
                            알림활성화=current_settings.get('enabled', False),
                            최소신뢰도=current_settings.get('min_confidence', 0))
                else:
                    error("현재 설정 조회 실패", HTTP코드=response.status)
                    return False
            
            # 설정 업데이트 테스트
            new_settings = {
                "enabled": True,
                "min_confidence": 0.75,
                "notification_cooldown_seconds": 10,
                "max_notifications_per_minute": 5
            }
            
            async with self.session.put(
                f"{self.base_url}/api/pair-notifications/settings",
                json=new_settings
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    success("설정 업데이트 성공", 업데이트된필드=data.get('updated_fields', []))
                else:
                    error("설정 업데이트 실패", HTTP코드=response.status)
                    return False
            
            return True
            
        except Exception as e:
            error("설정 관리 테스트 실패", 오류=str(e))
            return False
    
    async def test_statistics_and_history(self):
        """통계 및 이력 조회 테스트"""
        info("통계 및 이력 조회 테스트 시작")
        
        try:
            # 통계 조회
            async with self.session.get(f"{self.base_url}/api/pair-notifications/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    stats_data = stats.get('stats', {})
                    success("통계 조회 성공",
                            총감지된페어=stats_data.get('total_pairs_detected', 0),
                            총전송된알림=stats_data.get('total_notifications_sent', 0))
                else:
                    error("통계 조회 실패", HTTP코드=response.status)
                    return False
            
            # 이력 조회
            async with self.session.get(f"{self.base_url}/api/pair-notifications/history?limit=10") as response:
                if response.status == 200:
                    history = await response.json()
                    pairs = history.get('pairs', [])
                    success("이력 조회 성공", 항목수=len(pairs))
                else:
                    error("이력 조회 실패", HTTP코드=response.status)
                    return False
            
            # 테이블별 통계 조회
            async with self.session.get(f"{self.base_url}/api/pair-notifications/tables/stats") as response:
                if response.status == 200:
                    table_stats = await response.json()
                    tables = table_stats.get('tables', {})
                    success("테이블별 통계 조회 성공", 테이블수=len(tables))
                else:
                    error("테이블별 통계 조회 실패", HTTP코드=response.status)
                    return False
            
            return True
            
        except Exception as e:
            error("통계 및 이력 조회 테스트 실패", 오류=str(e))
            return False
    
    async def test_websocket_notifications(self, duration: int = 30):
        """WebSocket 알림 수신 테스트"""
        info("WebSocket 알림 수신 테스트 시작", 지속시간=f"{duration}초")
        
        if not self.websocket:
            error("WebSocket 연결이 필요합니다")
            return False
        
        try:
            notifications_received = []
            
            # 백그라운드에서 알림 수신
            async def receive_notifications():
                try:
                    while True:
                        message = await self.websocket.recv()
                        data = json.loads(message)
                        
                        if data.get('type') == 'pair_notification':
                            notifications_received.append(data)
                            pair_data = data.get('data', {}).get('pair_event', {})
                            success("페어 알림 수신", 테이블=pair_data.get('table_name', 'unknown'), 타입=pair_data.get('pair_type', 'unknown'))
                        
                except websockets.exceptions.ConnectionClosed:
                    info("WebSocket 연결이 종료되었습니다")
                except Exception as e:
                    error("알림 수신 중 오류", 오류=str(e))
            
            # 테스트 알림 전송
            async def send_test_notifications():
                await asyncio.sleep(2)  # 초기 대기
                
                for i, table_name in enumerate(self.test_tables):
                    try:
                        async with self.session.post(
                            f"{self.base_url}/api/pair-notifications/test",
                            params={
                                "table_name": table_name,
                                "pair_type": "player_pair"
                            }
                        ) as response:
                            if response.status == 200:
                                info("테스트 알림 전송", 테이블=table_name)
                            else:
                                error("테스트 알림 전송 실패", 테이블=table_name)
                        
                        await asyncio.sleep(3)  # 간격
                        
                    except Exception as e:
                        error("테스트 알림 전송 중 오류", 테이블=table_name, 오류=str(e))
            
            # 동시 실행
            await asyncio.wait([
                asyncio.create_task(receive_notifications()),
                asyncio.create_task(send_test_notifications())
            ], timeout=duration)
            
            success("WebSocket 알림 테스트 완료", 수신된알림수=len(notifications_received))
            return len(notifications_received) > 0
            
        except Exception as e:
            error("WebSocket 알림 테스트 실패", 오류=str(e))
            return False
    
    async def run_comprehensive_test(self):
        """종합 테스트 실행"""
        info("실시간 페어 알림 시스템 종합 테스트 시작")
        
        test_results = {}
        
        # 1. API 상태 확인
        test_results['api_health'] = await self.test_api_health()
        
        # 2. 페어 알림 서비스 상태 확인
        test_results['service_health'] = await self.test_pair_notification_service_health()
        
        # 3. WebSocket 연결 테스트
        test_results['websocket_connection'] = await self.test_websocket_connection()
        
        # 4. 페어 감지 테스트
        test_results['pair_detection'] = await self.test_pair_detection()
        
        # 5. 설정 관리 테스트
        test_results['settings_management'] = await self.test_settings_management()
        
        # 6. 통계 및 이력 테스트
        test_results['statistics_and_history'] = await self.test_statistics_and_history()
        
        # 7. WebSocket 알림 수신 테스트
        test_results['websocket_notifications'] = await self.test_websocket_notifications(30)
        
        # 결과 요약
        info("테스트 결과 요약")
        successful_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            if result:
                success(f"{test_name} 통과")
            else:
                error(f"{test_name} 실패")
            if result:
                successful_tests += 1
        
        success_rate = successful_tests/total_tests*100
        success("전체 테스트 결과", 통과=f"{successful_tests}/{total_tests}", 성공률=f"{success_rate:.1f}%")
        
        return test_results

async def main():
    """메인 함수"""
    info("=" * 80)
    info("실시간 페어 알림 시스템 테스트 클라이언트")
    info("=" * 80)
    
    async with PairNotificationTestClient() as client:
        try:
            results = await client.run_comprehensive_test()
            
            # 최종 결과
            success_rate = sum(1 for r in results.values() if r) / len(results)
            if success_rate >= 0.8:
                success("테스트 성공: 시스템이 정상적으로 작동합니다!")
                sys.exit(0)
            else:
                warning("테스트 부분 실패: 일부 기능에 문제가 있을 수 있습니다")
                sys.exit(1)
                
        except KeyboardInterrupt:
            info("사용자에 의해 테스트가 중단되었습니다")
            sys.exit(1)
        except Exception as e:
            error("테스트 실행 중 오류 발생", 오류=str(e))
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())