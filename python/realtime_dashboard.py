#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실시간 대시보드 시스템 v2.0
실시간 데이터 처리, WebSocket 통신, 대시보드 백엔드
"""

import json
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeDashboard:
    """실시간 대시보드 시스템"""
    
    def __init__(self):
        self.active_connections: Set = set()
        self.data_buffer = {
            'live_games': deque(maxlen=100),
            'pair_alerts': deque(maxlen=50),
            'table_status': {},
            'system_metrics': {},
            'alert_history': deque(maxlen=200)
        }
        
        # 실시간 통계
        self.live_stats = {
            'games_per_minute': deque(maxlen=60),  # 1분간 게임 수
            'pairs_per_hour': deque(maxlen=60),    # 1시간간 페어 수
            'active_tables': set(),
            'peak_activity': {
                'games': 0,
                'pairs': 0,
                'timestamp': None
            }
        }
        
        # 알림 규칙
        self.alert_rules = {
            'consecutive_pairs': {'limit': 3, 'enabled': True},
            'no_pairs_timeout': {'limit': 100, 'enabled': True},  # 게임 수
            'high_activity': {'games_per_minute': 10, 'enabled': True},
            'table_inactive': {'minutes': 5, 'enabled': True}
        }
        
        self.is_running = False
        self.background_task = None
        
        safe_print("🎛️ 실시간 대시보드 시스템 초기화 완료")
    
    async def add_connection(self, websocket):
        """WebSocket 연결 추가"""
        self.active_connections.add(websocket)
        logger.info(f"대시보드 클라이언트 연결. 총 연결: {len(self.active_connections)}")
        
        # 초기 데이터 전송
        await self.send_initial_dashboard_data(websocket)
    
    async def remove_connection(self, websocket):
        """WebSocket 연결 제거"""
        self.active_connections.discard(websocket)
        logger.info(f"대시보드 클라이언트 연결 해제. 총 연결: {len(self.active_connections)}")
    
    async def send_initial_dashboard_data(self, websocket):
        """초기 대시보드 데이터 전송"""
        try:
            initial_data = {
                'type': 'dashboard_init',
                'data': {
                    'live_stats': self.get_live_statistics(),
                    'table_overview': self.get_table_overview(),
                    'recent_alerts': list(self.data_buffer['pair_alerts'])[-10:],
                    'system_status': self.get_system_status(),
                    'alert_rules': self.alert_rules
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(initial_data, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"초기 대시보드 데이터 전송 실패: {e}")
    
    def process_game_event(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """게임 이벤트 처리"""
        table_name = game_data.get('table_name', 'Unknown')
        timestamp = datetime.now()
        
        # 라이브 게임 데이터 버퍼에 추가
        live_game = {
            'table_name': table_name,
            'game_id': game_data.get('game_id', 0),
            'has_pair': game_data.get('has_pair', False),
            'pair_type': game_data.get('pair_type'),
            'timestamp': timestamp.isoformat(),
            'player_cards': game_data.get('player_cards', []),
            'banker_cards': game_data.get('banker_cards', [])
        }
        
        self.data_buffer['live_games'].append(live_game)
        
        # 테이블 상태 업데이트
        self._update_table_status(table_name, live_game)
        
        # 실시간 통계 업데이트
        self._update_live_stats(live_game)
        
        # 알림 규칙 검사
        alerts = self._check_alert_rules(table_name, live_game)
        
        # 페어 발생 시 특별 처리
        if game_data.get('has_pair', False):
            pair_alert = {
                'id': f"pair_{timestamp.timestamp()}",
                'table_name': table_name,
                'pair_type': game_data.get('pair_type'),
                'game_id': game_data.get('game_id'),
                'timestamp': timestamp.isoformat(),
                'severity': 'high',
                'message': f"{table_name}에서 {game_data.get('pair_type', '페어')} 발생!",
                'auto_generated': True
            }
            
            self.data_buffer['pair_alerts'].append(pair_alert)
            alerts.append(pair_alert)
        
        # 🚫 실시간 브로드캐스트 비활성화 (AsyncIO 충돌 방지)
        logger.debug("🚫 실시간 브로드캐스트 비활성화됨 - AsyncIO 충돌 방지")
        # asyncio.create_task() 호출 완전 비활성화
        
        return {
            'processed': True,
            'alerts_generated': len(alerts),
            'live_connections': len(self.active_connections)
        }
    
    def _update_table_status(self, table_name: str, game_data: Dict[str, Any]):
        """테이블 상태 업데이트"""
        if table_name not in self.data_buffer['table_status']:
            self.data_buffer['table_status'][table_name] = {
                'total_games': 0,
                'total_pairs': 0,
                'last_game': None,
                'last_pair': None,
                'games_since_last_pair': 0,
                'pair_streak': 0,
                'is_active': True
            }
        
        status = self.data_buffer['table_status'][table_name]
        status['total_games'] += 1
        status['last_game'] = game_data['timestamp']
        status['is_active'] = True
        
        if game_data.get('has_pair', False):
            status['total_pairs'] += 1
            status['last_pair'] = game_data['timestamp']
            status['games_since_last_pair'] = 0
            status['pair_streak'] += 1
        else:
            status['games_since_last_pair'] += 1
            status['pair_streak'] = 0
    
    def _update_live_stats(self, game_data: Dict[str, Any]):
        """실시간 통계 업데이트"""
        current_minute = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 분당 게임 수 업데이트
        if not self.live_stats['games_per_minute'] or \
           self.live_stats['games_per_minute'][-1]['minute'] != current_minute:
            self.live_stats['games_per_minute'].append({
                'minute': current_minute,
                'count': 1
            })
        else:
            self.live_stats['games_per_minute'][-1]['count'] += 1
        
        # 활성 테이블 업데이트
        self.live_stats['active_tables'].add(game_data['table_name'])
        
        # 최고 활동량 기록
        current_games = self.live_stats['games_per_minute'][-1]['count'] if self.live_stats['games_per_minute'] else 0
        if current_games > self.live_stats['peak_activity']['games']:
            self.live_stats['peak_activity'].update({
                'games': current_games,
                'timestamp': datetime.now().isoformat()
            })
        
        # 페어 발생 시 시간당 통계 업데이트
        if game_data.get('has_pair', False):
            current_hour = datetime.now().strftime('%Y-%m-%d %H:00')
            if not self.live_stats['pairs_per_hour'] or \
               self.live_stats['pairs_per_hour'][-1]['hour'] != current_hour:
                self.live_stats['pairs_per_hour'].append({
                    'hour': current_hour,
                    'count': 1
                })
            else:
                self.live_stats['pairs_per_hour'][-1]['count'] += 1
    
    def _check_alert_rules(self, table_name: str, game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """알림 규칙 검사"""
        alerts = []
        table_status = self.data_buffer['table_status'].get(table_name, {})
        
        # 연속 페어 알림
        if self.alert_rules['consecutive_pairs']['enabled']:
            pair_streak = table_status.get('pair_streak', 0)
            if pair_streak >= self.alert_rules['consecutive_pairs']['limit']:
                alerts.append({
                    'id': f"consecutive_{table_name}_{datetime.now().timestamp()}",
                    'type': 'consecutive_pairs',
                    'table_name': table_name,
                    'severity': 'warning',
                    'message': f"{table_name}: {pair_streak}연속 페어 발생!",
                    'data': {'streak': pair_streak},
                    'timestamp': datetime.now().isoformat(),
                    'rule': 'consecutive_pairs'
                })
        
        # 장기간 페어 없음 알림
        if self.alert_rules['no_pairs_timeout']['enabled']:
            games_since = table_status.get('games_since_last_pair', 0)
            if games_since >= self.alert_rules['no_pairs_timeout']['limit']:
                alerts.append({
                    'id': f"timeout_{table_name}_{datetime.now().timestamp()}",
                    'type': 'no_pairs_timeout',
                    'table_name': table_name,
                    'severity': 'info',
                    'message': f"{table_name}: {games_since}게임째 페어 없음",
                    'data': {'games_without_pair': games_since},
                    'timestamp': datetime.now().isoformat(),
                    'rule': 'no_pairs_timeout'
                })
        
        # 고활동 알림
        if self.alert_rules['high_activity']['enabled'] and self.live_stats['games_per_minute']:
            current_rate = self.live_stats['games_per_minute'][-1]['count']
            threshold = self.alert_rules['high_activity']['games_per_minute']
            if current_rate >= threshold:
                alerts.append({
                    'id': f"activity_{datetime.now().timestamp()}",
                    'type': 'high_activity',
                    'severity': 'info',
                    'message': f"높은 활동량 감지: 분당 {current_rate}게임",
                    'data': {'games_per_minute': current_rate},
                    'timestamp': datetime.now().isoformat(),
                    'rule': 'high_activity'
                })
        
        # 알림을 히스토리에 저장
        for alert in alerts:
            self.data_buffer['alert_history'].append(alert)
        
        return alerts
    
    async def _broadcast_live_update(self, data: Dict[str, Any]):
        """라이브 업데이트 브로드캐스트"""
        if not self.active_connections:
            return
        
        message = json.dumps(data, ensure_ascii=False)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send(message)
            except:
                disconnected.add(connection)
        
        # 연결이 끊어진 클라이언트 정리
        for connection in disconnected:
            self.active_connections.discard(connection)
    
    def get_live_statistics(self) -> Dict[str, Any]:
        """실시간 통계 반환"""
        now = datetime.now()
        
        # 현재 분 게임 수
        current_games = 0
        if self.live_stats['games_per_minute']:
            current_minute = now.strftime('%Y-%m-%d %H:%M')
            if self.live_stats['games_per_minute'][-1]['minute'] == current_minute:
                current_games = self.live_stats['games_per_minute'][-1]['count']
        
        # 현재 시간 페어 수
        current_pairs = 0
        if self.live_stats['pairs_per_hour']:
            current_hour = now.strftime('%Y-%m-%d %H:00')
            if self.live_stats['pairs_per_hour'][-1]['hour'] == current_hour:
                current_pairs = self.live_stats['pairs_per_hour'][-1]['count']
        
        # 전체 통계
        total_games = sum(status['total_games'] for status in self.data_buffer['table_status'].values())
        total_pairs = sum(status['total_pairs'] for status in self.data_buffer['table_status'].values())
        
        return {
            'current_minute': {
                'games': current_games,
                'timestamp': now.strftime('%H:%M')
            },
            'current_hour': {
                'pairs': current_pairs,
                'timestamp': now.strftime('%H:00')
            },
            'total': {
                'games': total_games,
                'pairs': total_pairs,
                'pair_rate': round((total_pairs / total_games * 100) if total_games > 0 else 0, 2)
            },
            'active_tables': len(self.live_stats['active_tables']),
            'peak_activity': self.live_stats['peak_activity'],
            'last_update': now.isoformat()
        }
    
    def get_table_overview(self) -> Dict[str, Any]:
        """테이블 개요 반환"""
        overview = {}
        current_time = datetime.now()
        
        for table_name, status in self.data_buffer['table_status'].items():
            # 마지막 활동 시간 계산
            last_activity = None
            minutes_inactive = 0
            
            if status['last_game']:
                try:
                    last_game_time = datetime.fromisoformat(status['last_game'])
                    minutes_inactive = int((current_time - last_game_time).total_seconds() / 60)
                    last_activity = last_game_time.strftime('%H:%M:%S')
                except:
                    pass
            
            # 활성 상태 판정
            is_active = minutes_inactive < self.alert_rules['table_inactive']['minutes']
            
            overview[table_name] = {
                'total_games': status['total_games'],
                'total_pairs': status['total_pairs'],
                'games_since_last_pair': status['games_since_last_pair'],
                'pair_streak': status['pair_streak'],
                'pair_rate': round((status['total_pairs'] / status['total_games'] * 100) 
                                 if status['total_games'] > 0 else 0, 2),
                'last_activity': last_activity,
                'minutes_inactive': minutes_inactive,
                'is_active': is_active,
                'status': 'active' if is_active else 'inactive'
            }
        
        return overview
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            'uptime': self._get_uptime(),
            'active_connections': len(self.active_connections),
            'data_buffer_size': {
                'live_games': len(self.data_buffer['live_games']),
                'pair_alerts': len(self.data_buffer['pair_alerts']),
                'alert_history': len(self.data_buffer['alert_history'])
            },
            'memory_usage': self._get_memory_usage(),
            'last_activity': datetime.now().isoformat()
        }
    
    def _get_uptime(self) -> str:
        """시스템 가동 시간"""
        # 간단한 구현 - 실제로는 시스템 시작 시간을 저장해야 함
        return "시스템 실행 중"
    
    def _get_memory_usage(self) -> Dict[str, int]:
        """메모리 사용량 (간단한 구현)"""
        import sys
        return {
            'total_objects': len(gc.get_objects()) if 'gc' in sys.modules else 0,
            'buffer_size': sum(len(str(buf)) for buf in self.data_buffer.values() if hasattr(buf, '__len__'))
        }
    
    def update_alert_rules(self, rules: Dict[str, Any]) -> bool:
        """알림 규칙 업데이트"""
        try:
            for rule_name, rule_config in rules.items():
                if rule_name in self.alert_rules:
                    self.alert_rules[rule_name].update(rule_config)
            
            safe_print(f"✅ 알림 규칙 업데이트 완료: {len(rules)}개 규칙")
            return True
            
        except Exception as e:
            logger.error(f"알림 규칙 업데이트 실패: {e}")
            return False
    
    async def start_background_monitoring(self):
        """백그라운드 모니터링 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self.background_task = asyncio.create_task(self._background_monitor())
        safe_print("🔄 백그라운드 모니터링 시작")
    
    async def stop_background_monitoring(self):
        """백그라운드 모니터링 중지"""
        self.is_running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        safe_print("⏹️ 백그라운드 모니터링 중지")
    
    async def _background_monitor(self):
        """백그라운드 모니터링 작업"""
        try:
            while self.is_running:
                await asyncio.sleep(30)  # 30초마다 실행
                
                # 비활성 테이블 검사
                await self._check_inactive_tables()
                
                # 시스템 상태 브로드캐스트
                if self.active_connections:
                    system_update = {
                        'type': 'system_update',
                        'live_stats': self.get_live_statistics(),
                        'table_overview': self.get_table_overview(),
                        'system_status': self.get_system_status(),
                        'timestamp': datetime.now().isoformat()
                    }
                    await self._broadcast_live_update(system_update)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"백그라운드 모니터링 오류: {e}")
    
    async def _check_inactive_tables(self):
        """비활성 테이블 검사"""
        if not self.alert_rules['table_inactive']['enabled']:
            return
        
        current_time = datetime.now()
        threshold_minutes = self.alert_rules['table_inactive']['minutes']
        
        for table_name, status in self.data_buffer['table_status'].items():
            if not status.get('last_game'):
                continue
            
            try:
                last_game_time = datetime.fromisoformat(status['last_game'])
                minutes_inactive = (current_time - last_game_time).total_seconds() / 60
                
                if minutes_inactive >= threshold_minutes and status['is_active']:
                    # 비활성 상태로 변경
                    status['is_active'] = False
                    
                    # 비활성 알림 생성
                    alert = {
                        'id': f"inactive_{table_name}_{current_time.timestamp()}",
                        'type': 'table_inactive',
                        'table_name': table_name,
                        'severity': 'warning',
                        'message': f"{table_name} 테이블이 {int(minutes_inactive)}분간 비활성 상태",
                        'data': {'minutes_inactive': int(minutes_inactive)},
                        'timestamp': current_time.isoformat(),
                        'rule': 'table_inactive'
                    }
                    
                    self.data_buffer['alert_history'].append(alert)
                    
                    # 브로드캐스트
                    await self._broadcast_live_update({
                        'type': 'alert',
                        'alert': alert,
                        'timestamp': current_time.isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"테이블 비활성 검사 오류 ({table_name}): {e}")


# 전역 인스턴스
realtime_dashboard = RealTimeDashboard()

def get_realtime_dashboard() -> RealTimeDashboard:
    """전역 실시간 대시보드 인스턴스 반환"""
    return realtime_dashboard


if __name__ == "__main__":
    # 테스트 코드
    import random
    import gc
    
    async def test_dashboard():
        safe_print("=== 실시간 대시보드 테스트 ===")
        
        dashboard = RealTimeDashboard()
        
        # 백그라운드 모니터링 시작
        await dashboard.start_background_monitoring()
        
        # 테스트 데이터 생성
        tables = ['메인테이블_A', '메인테이블_B', 'VIP테이블_1']
        pair_types = ['PLAYER_PAIR', 'BANKER_PAIR', 'BOTH_PAIR']
        
        safe_print("\n📊 테스트 게임 데이터 생성 중...")
        
        for i in range(50):
            test_game = {
                'table_name': random.choice(tables),
                'game_id': i + 1,
                'has_pair': random.random() < 0.15,  # 15% 페어 확률
                'pair_type': random.choice(pair_types) if random.random() < 0.15 else None,
                'player_cards': ['A♠', 'K♦'],
                'banker_cards': ['Q♣', 'J♥']
            }
            
            result = dashboard.process_game_event(test_game)
            
            # 페어 발생 시 출력
            if test_game.get('has_pair'):
                safe_print(f"  🎯 페어 발생: {test_game['table_name']} - {test_game['pair_type']}")
            
            await asyncio.sleep(0.1)  # 0.1초 간격
        
        # 통계 출력
        stats = dashboard.get_live_statistics()
        safe_print(f"\n📈 실시간 통계:")
        safe_print(f"  총 게임: {stats['total']['games']}")
        safe_print(f"  총 페어: {stats['total']['pairs']}")
        safe_print(f"  페어율: {stats['total']['pair_rate']}%")
        safe_print(f"  활성 테이블: {stats['active_tables']}")
        
        # 테이블 개요
        overview = dashboard.get_table_overview()
        safe_print(f"\n🎲 테이블 개요:")
        for table, info in overview.items():
            safe_print(f"  {table}: {info['total_games']}게임, {info['total_pairs']}페어 ({info['pair_rate']}%)")
        
        # 알림 히스토리
        alerts = len(dashboard.data_buffer['alert_history'])
        safe_print(f"\n🚨 생성된 알림: {alerts}개")
        
        # 백그라운드 모니터링 중지
        await dashboard.stop_background_monitoring()
        
        safe_print("\n🎯 실시간 대시보드 테스트 완료!")
    
    # 테스트 실행
    asyncio.run(test_dashboard())