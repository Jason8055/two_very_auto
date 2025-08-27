#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Baccarat Pair Tracking System v2.0
SQLite 기반 고성능 페어 추적 시스템
"""

# 표준 라이브러리
import json
import logging
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 로컬 모듈
# from advanced_notification_system import get_notification_system  # 🚫 AsyncIO 충돌 방지
from database_manager import DatabaseManager
from pair_tracker_helper_methods import (
    detect_pair_from_cards, 
    get_pair_type, 
    get_pair_cards
)

# 한국어 인코딩 설정
try:
    from korean_encoding_fix import setup_korean_encoding
    setup_korean_encoding()
except ImportError:
    pass

# 로깅 설정 (한국어 지원)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout if hasattr(sys, 'stdout') else None)
    ]
)
logger = logging.getLogger(__name__)


class PairTrackerV2:
    """SQLite 기반 바카라 페어 추적 시스템 v2.0"""
    
    def __init__(self, db_path: str = "baccarat_monitor.db"):
        """
        페어 추적기 v2.0 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db = DatabaseManager(db_path)
        
        # 메모리 캐시 (성능 향상)
        self.memory_cache = {
            'tables': {},
            'recent_games': defaultdict(lambda: deque(maxlen=50)),
            'last_cache_update': {},
            'cache_timeout': 30  # 30초 캐시
        }
        
        logger.info(f"[Pair Tracker v2.0] Initialized with database: {db_path}")
        
        # 기존 데이터 마이그레이션 확인
        self._check_migration()
    
    def _check_migration(self) -> None:
        """기존 JSON 데이터 마이그레이션 확인"""
        try:
            from pathlib import Path
            old_file = Path("pair_tracking_data.json")
            
            if old_file.exists():
                logger.info("Found legacy JSON data file, starting migration...")
                self._migrate_from_json(old_file)
                
                # 백업 후 삭제
                backup_name = f"pair_tracking_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                old_file.rename(backup_name)
                logger.info(f"Legacy data migrated and backed up to: {backup_name}")
                
        except Exception as e:
            logger.warning(f"Migration check failed: {e}")
    
    def _migrate_from_json(self, json_file: Path) -> None:
        """JSON 데이터를 SQLite로 마이그레이션"""
        try:
            import json
            
            with open(json_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            migrated_count = 0
            
            # 테이블 통계 마이그레이션
            for table_name, table_data in old_data.get('tables', {}).items():
                self.db.update_table_stats(table_name, table_data)
                
                # 최근 페어 데이터를 게임으로 변환
                for pair in table_data.get('recent_pairs', []):
                    game_data = {
                        'table_name': table_name,
                        'game_id': pair.get('game_id', 0),
                        'game_time': pair.get('game_time', datetime.now().isoformat()),
                        'result': pair.get('result', 'UNKNOWN'),
                        'player_cards': pair.get('player_cards', []),
                        'banker_cards': pair.get('banker_cards', []),
                        'pair_info': {
                            'has_any_pair': True,
                            'pair_type': pair.get('pair_type'),
                            'pair_cards': pair.get('pair_cards', [])
                        }
                    }
                    
                    self.db.save_game(game_data)
                    migrated_count += 1
            
            logger.info(f"Migration completed: {migrated_count} records migrated")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
    
    def track_game(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        게임 데이터를 추적하여 페어 정보 업데이트 (v2.0)
        
        Args:
            game_data: 패킷 디코더에서 생성한 게임 데이터
            
        Returns:
            업데이트된 페어 정보
        """
        table_name = game_data['table_name']
        
        # 1. 게임 데이터를 데이터베이스 형식으로 변환
        db_game_data = {
            'table_name': table_name,
            'game_id': game_data.get('game_number', 1),  # game_number를 game_id로 매핑
            'game_time': game_data.get('timestamp', datetime.now()),
            'result': game_data.get('result', 'UNKNOWN'),
            'player_cards': ', '.join(game_data.get('player_cards', [])),
            'banker_cards': ', '.join(game_data.get('banker_cards', [])),
            'has_pair': detect_pair_from_cards(game_data),
            'pair_type': get_pair_type(game_data),
            'pair_cards': get_pair_cards(game_data),
            'pair_info': game_data.get('pair_info', {})
        }
        
        # 2. 데이터베이스에 게임 저장
        game_id = self.db.save_game(db_game_data)
        
        # 2. 메모리 캐시 업데이트
        self.memory_cache['recent_games'][table_name].append(game_data)
        
        # 3. 페어 정보 처리 (실제 감지된 페어 정보 사용)
        actual_pair_info = {
            'has_any_pair': db_game_data['has_pair'],
            'pair_type': db_game_data['pair_type'],
            'pair_cards': db_game_data['pair_cards'].split(', ') if db_game_data['pair_cards'] else []
        }
        tracking_result = self._process_pair_info_v2(table_name, db_game_data, actual_pair_info)
        
        # 4. 통계 업데이트 (비동기적으로 처리)
        self._update_table_stats_async(table_name)
        
        # 5. 캐시 무효화
        self._invalidate_cache(table_name)
        
        tracking_result['database_id'] = game_id
        return tracking_result
    
    def _process_pair_info_v2(self, table_name: str, game_data: Dict[str, Any], 
                             pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """페어 정보 처리 및 추적 v2.0"""
        
        tracking_result = {
            'table_name': table_name,
            'game_id': game_data.get('game_id'),
            'has_pair': pair_info.get('has_any_pair', False),
            'pair_type': pair_info.get('pair_type'),
            'pair_cards': pair_info.get('pair_cards', []),
            'games_since_last_pair': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # 페어가 발생한 경우
        if pair_info.get('has_any_pair', False):
            tracking_result['alert'] = True
            tracking_result['message'] = f"{pair_info.get('pair_type')} detected at {table_name}!"
            
            # 실시간 알림 데이터 준비
            tracking_result['notification_data'] = {
                'rule': 'pair_detection',
                'message': tracking_result['message'],
                'priority': 'high',
                'channels': ['websocket', 'browser'],
                'table_name': table_name,
                'game_id': game_data.get('game_id'),
                'pair_details': {
                    'type': pair_info.get('pair_type'),
                    'cards': pair_info.get('pair_cards', []),
                    'player_cards': game_data.get('player_cards', []),
                    'banker_cards': game_data.get('banker_cards', [])
                }
            }
            
            # 알림 히스토리 저장
            self.db.save_notification(tracking_result['notification_data'])
            
            # 🚫 고급 알림 시스템 완전 비활성화 (AsyncIO 충돌 방지)
            logger.debug("🚫 페어 알림 시스템 비활성화됨 - AsyncIO 충돌 방지")
            # 모든 비동기 알림 관련 코드 완전 비활성화
            
        else:
            tracking_result['alert'] = False
        
        # 마지막 페어 이후 게임 수 계산 (메모리 캐시 사용)
        tracking_result['games_since_last_pair'] = self._calculate_games_since_last_pair_simple(table_name)
        
        return tracking_result
    
    def _calculate_games_since_last_pair_simple(self, table_name: str) -> int:
        """마지막 페어 이후 게임 수 계산 (단순 버전, 재귀 없음)"""
        try:
            # 메모리 캐시에서만 확인 (데이터베이스 호출 없음)
            recent_games = list(self.memory_cache['recent_games'][table_name])
            
            # 뒤에서부터 페어 찾기
            for i, game in enumerate(reversed(recent_games)):
                # pair_info가 있는지 확인 후 페어 여부 체크
                pair_info = game.get('pair_info', {})
                if pair_info.get('has_any_pair', False):
                    return i
            
            # 메모리에서 페어를 찾지 못한 경우 기본값 반환
            return len(recent_games)
            
        except Exception as e:
            logger.error(f"Failed to calculate games since last pair: {e}")
            return 0
    
    def _update_table_stats_async(self, table_name: str) -> None:
        """테이블 통계 비동기 업데이트"""
        try:
            # 데이터베이스에서 실시간 통계 계산
            games = self.db.get_games(table_name=table_name, limit=1000)
            
            if not games:
                return
            
            total_games = len(games)
            pair_games = [g for g in games if g.get('has_pair', False)]
            
            # 페어 타입별 계산
            player_pairs = len([g for g in pair_games if g.get('pair_type') == 'PLAYER_PAIR'])
            banker_pairs = len([g for g in pair_games if g.get('pair_type') == 'BANKER_PAIR'])
            both_pairs = len([g for g in pair_games if g.get('pair_type') == 'BOTH_PAIR'])
            
            stats = {
                'total_games': total_games,
                'pair_count': len(pair_games),
                'player_pairs': player_pairs,
                'banker_pairs': banker_pairs,
                'both_pairs': both_pairs,
                'last_game_time': games[0]['game_time'] if games else None,
                'statistics': {
                    'pair_rate': len(pair_games) / total_games if total_games > 0 else 0.0,
                    'player_pair_rate': player_pairs / total_games if total_games > 0 else 0.0,
                    'banker_pair_rate': banker_pairs / total_games if total_games > 0 else 0.0,
                    'avg_games_between_pairs': total_games / len(pair_games) if pair_games else 0.0
                }
            }
            
            # 데이터베이스 업데이트
            self.db.update_table_stats(table_name, stats)
            
            # 메모리 캐시 업데이트
            self.memory_cache['tables'][table_name] = stats
            self.memory_cache['last_cache_update'][table_name] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to update table stats for {table_name}: {e}")
    
    def _invalidate_cache(self, table_name: str = None) -> None:
        """캐시 무효화"""
        if table_name:
            self.memory_cache['last_cache_update'].pop(table_name, None)
            self.memory_cache['tables'].pop(table_name, None)
        else:
            self.memory_cache['last_cache_update'].clear()
            self.memory_cache['tables'].clear()
    
    def _is_cache_valid(self, table_name: str) -> bool:
        """캐시 유효성 확인"""
        if table_name not in self.memory_cache['last_cache_update']:
            return False
        
        last_update = self.memory_cache['last_cache_update'][table_name]
        return (datetime.now() - last_update).seconds < self.memory_cache['cache_timeout']
    
    def _is_cache_valid_simple(self, table_name: str) -> bool:
        """단순 캐시 유효성 검사 (재귀 호출 없음)"""
        if table_name not in self.memory_cache['last_cache_update']:
            return False
        last_update = self.memory_cache['last_cache_update'][table_name]
        return (datetime.now() - last_update).seconds < 30
    
    def get_table_summary(self, table_name: str) -> Optional[Dict[str, Any]]:
        """특정 테이블의 요약 정보 반환 v2.0 (재귀 호출 완전 제거)"""
        try:
            # 캐시된 데이터가 있고 유효한 경우 즉시 반환 (재귀 호출 없음)
            cached_data = self.memory_cache['tables'].get(table_name)
            if cached_data and self._is_cache_valid_simple(table_name):
                cached_data['recent_games_cached'] = len(self.memory_cache['recent_games'][table_name])
                return cached_data
            
            # 데이터베이스에서 직접 조회 (중간 호출 제거)
            stats = self.db.get_table_statistics(table_name)
            if not stats:
                return None
            
            # 최근 페어 정보 추가
            recent_pairs = self.db.get_games(table_name=table_name, limit=10)
            recent_pair = next((g for g in recent_pairs if g.get('has_pair', False)), None)
            
            result = {
                'table_name': table_name,
                'total_games': stats.get('total_games', 0),
                'pair_count': stats.get('total_pairs', 0),
                'player_pairs': stats.get('player_pairs', 0),
                'banker_pairs': stats.get('banker_pairs', 0),
                'both_pairs': stats.get('both_pairs', 0),
                'games_since_last_pair': self._calculate_games_since_last_pair_simple(table_name),
                'recent_games_cached': len(self.memory_cache['recent_games'][table_name]),
                'statistics': {
                    'pair_rate': stats.get('pair_rate', 0.0),
                    'avg_games_between_pairs': stats.get('avg_games_between_pairs', 0.0)
                },
                'last_game_time': stats.get('last_game_time'),
                'latest_pair_info': {
                    'game_id': recent_pair.get('game_id'),
                    'game_time': recent_pair.get('game_time'),
                    'pair_type': recent_pair.get('pair_type'),
                    'pair_cards': recent_pair.get('pair_cards')
                } if recent_pair else None
            }
            
            # 캐시 업데이트
            self.memory_cache['tables'][table_name] = result
            self.memory_cache['last_cache_update'][table_name] = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get table summary for {table_name}: {e}")
            return None
    
    def get_all_tables_summary(self) -> Dict[str, Any]:
        """모든 테이블의 요약 정보 반환 v2.0"""
        try:
            # 전역 통계
            global_stats = self.db.get_table_statistics()
            
            # 모든 테이블 목록 조회
            all_games = self.db.get_games(limit=1000)
            table_names = list(set(game['table_name'] for game in all_games))
            
            summary = {
                'global_stats': global_stats.get('global_stats', {}),
                'tables': {},
                'active_tables': 0,
                'total_tables': len(table_names),
                'database_info': self.db.get_database_info()
            }
            
            # 각 테이블 정보
            for table_name in table_names:
                table_summary = self.get_table_summary(table_name)
                if table_summary:
                    summary['tables'][table_name] = table_summary
                    
                    # 활성 테이블 확인 (최근 10분 내 활동)
                    if table_summary['last_game_time']:
                        try:
                            last_game = datetime.fromisoformat(table_summary['last_game_time'].replace('Z', '+00:00'))
                            if datetime.now() - last_game < timedelta(minutes=10):
                                summary['active_tables'] += 1
                        except:
                            pass
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get all tables summary: {e}")
            return {'tables': {}, 'global_stats': {}}
    
    def get_recent_pairs(self, table_name: str = None, limit: int = 10, 
                        include_details: bool = True) -> List[Dict[str, Any]]:
        """최근 페어 발생 기록 조회 v2.0"""
        try:
            # 데이터베이스에서 페어 게임만 조회
            all_games = self.db.get_games(table_name=table_name, limit=limit * 5)  # 여유있게 조회
            pair_games = [g for g in all_games if g.get('has_pair', False)][:limit]
            
            results = []
            for game in pair_games:
                pair_data = {
                    'table_name': game['table_name'],
                    'game_id': game['game_id'],
                    'game_time': game['game_time'],
                    'pair_type': game['pair_type'],
                    'pair_cards': game.get('pair_cards', [])
                }
                
                if include_details:
                    pair_data.update({
                        'player_cards': game.get('player_cards', []),
                        'banker_cards': game.get('banker_cards', []),
                        'result': game.get('result', 'UNKNOWN')
                    })
                
                results.append(pair_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get recent pairs: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """시스템 성능 메트릭 조회"""
        try:
            db_info = self.db.get_database_info()
            
            return {
                'database': {
                    'file_size_mb': round(db_info.get('file_size', 0) / (1024 * 1024), 2),
                    'games_count': db_info.get('games_count', 0),
                    'tables_count': db_info.get('table_stats_count', 0),
                    'notifications_count': db_info.get('notification_history_count', 0)
                },
                'memory_cache': {
                    'cached_tables': len(self.memory_cache['tables']),
                    'cached_games': sum(len(games) for games in self.memory_cache['recent_games'].values()),
                    'cache_timeout': self.memory_cache['cache_timeout']
                },
                'system': {
                    'version': db_info.get('version', '2.0.0'),
                    'initialized_at': db_info.get('initialized_at'),
                    'last_cleanup': self.db.get_config('system.last_cleanup')
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 7) -> int:
        """오래된 데이터 정리 v2.0"""
        try:
            deleted_count = self.db.cleanup_old_data(days)
            
            # 설정 업데이트
            self.db.set_config('system.last_cleanup', datetime.now().isoformat())
            
            # 캐시 무효화
            self._invalidate_cache()
            
            logger.info(f"Cleanup completed: {deleted_count} records deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def backup_data(self, backup_path: str = None) -> bool:
        """데이터 백업"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"backup_baccarat_{timestamp}.db"
            
            success = self.db.backup_database(backup_path)
            
            if success:
                self.db.set_config('system.last_backup', datetime.now().isoformat())
                self.db.set_config('system.last_backup_path', backup_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False


if __name__ == '__main__':
    # 테스트 실행
    from packet_decoder import BaccaratPacketDecoder, DemoDataGenerator
    
    print("Testing Pair Tracker v2.0...")
    
    # 초기화
    tracker = PairTrackerV2("test_baccarat_v2.db")
    decoder = BaccaratPacketDecoder()
    demo_gen = DemoDataGenerator()
    
    # 테스트 데이터 생성 및 추적
    demo_data = demo_gen.generate_demo_packet(20)
    games = decoder._parse_packet_content(demo_data)
    
    print(f"\nTracking {len(games)} demo games with v2.0...")
    
    for game in games:
        result = tracker.track_game(game)
        if result.get('alert'):
            print(f"PAIR ALERT: {result['message']}")
            print(f"   Database ID: {result.get('database_id')}")
            print(f"   Since Last Pair: {result['games_since_last_pair']} games")
    
    # 요약 정보 출력
    print("\n" + "="*60)
    print("TRACKING SUMMARY v2.0")
    print("="*60)
    
    summary = tracker.get_all_tables_summary()
    print(f"Global Stats: {summary['global_stats']}")
    print(f"Active Tables: {summary['active_tables']}/{summary['total_tables']}")
    
    # 성능 메트릭
    metrics = tracker.get_performance_metrics()
    print(f"\nPerformance Metrics:")
    print(f"  Database Size: {metrics['database']['file_size_mb']} MB")
    print(f"  Games Stored: {metrics['database']['games_count']}")
    print(f"  Memory Cache: {metrics['memory_cache']['cached_games']} games")
    
    # 최근 페어
    recent_pairs = tracker.get_recent_pairs(limit=5)
    print(f"\nRecent Pairs ({len(recent_pairs)}):")
    for pair in recent_pairs:
        print(f"  {pair['table_name']}: {pair['pair_type']} at {pair['game_time']}")
    
    # 백업 테스트
    if tracker.backup_data("test_backup.db"):
        print("\nBackup created successfully")
    
    # 정리
    from pathlib import Path
    Path("test_baccarat_v2.db").unlink(missing_ok=True)
    Path("test_backup.db").unlink(missing_ok=True)
    print("\nTest completed successfully!")