#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
멀티 카지노 관리 시스템 v1.0
여러 카지노의 동시 모니터링과 데이터 통합 관리
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print
from database_manager import DatabaseManager
from pair_tracker_v2 import PairTrackerV2
from pattern_analyzer_v2 import PatternAnalyzerV2

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class CasinoConnection:
    """개별 카지노 연결 및 데이터 관리"""
    
    def __init__(self, casino_id: str, config: Dict[str, Any]):
        self.casino_id = casino_id
        self.config = config
        self.is_active = False
        self.last_update = None
        self.connection_status = "disconnected"
        self.error_count = 0
        
        # 카지노별 독립적인 데이터 관리자들
        self.db_manager = None
        self.pair_tracker = None  
        self.pattern_analyzer = None
        
        # 통계
        self.stats = {
            'games_processed': 0,
            'pairs_detected': 0,
            'uptime': timedelta(),
            'last_pair_time': None,
            'average_games_per_hour': 0.0,
            'connection_errors': 0
        }
        
        self.start_time = datetime.now()
        
    def initialize(self) -> bool:
        """카지노 연결 초기화"""
        try:
            # 카지노별 전용 데이터베이스 파일
            db_filename = f"{self.casino_id}_baccarat_data.db"
            
            self.db_manager = DatabaseManager(db_filename)
            self.pair_tracker = PairTrackerV2(db_filename)
            self.pattern_analyzer = PatternAnalyzerV2(db_filename)
            
            self.is_active = True
            self.connection_status = "connected"
            
            safe_print(f"✅ 카지노 '{self.casino_id}' 초기화 완료")
            return True
            
        except Exception as e:
            self.connection_status = "error"
            self.error_count += 1
            safe_print(f"❌ 카지노 '{self.casino_id}' 초기화 실패: {e}")
            return False
    
    def process_game_data(self, game_data: Dict[str, Any]) -> bool:
        """게임 데이터 처리"""
        try:
            if not self.is_active:
                return False
            
            # 페어 추적
            if self.pair_tracker:
                pair_result = self.pair_tracker.check_for_pairs(game_data)
                if pair_result.get('has_pair'):
                    self.stats['pairs_detected'] += 1
                    self.stats['last_pair_time'] = datetime.now()
            
            # 패턴 분석
            if self.pattern_analyzer:
                self.pattern_analyzer.analyze_patterns(game_data)
            
            # 통계 업데이트
            self.stats['games_processed'] += 1
            self.last_update = datetime.now()
            self.connection_status = "active"
            
            return True
            
        except Exception as e:
            logger.error(f"카지노 {self.casino_id} 데이터 처리 실패: {e}")
            self.error_count += 1
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """현재 카지노 상태 반환"""
        uptime = datetime.now() - self.start_time
        
        # 시간당 게임 수 계산
        hours = uptime.total_seconds() / 3600
        avg_games = self.stats['games_processed'] / hours if hours > 0 else 0
        
        return {
            'casino_id': self.casino_id,
            'is_active': self.is_active,
            'connection_status': self.connection_status,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'uptime_hours': hours,
            'games_processed': self.stats['games_processed'],
            'pairs_detected': self.stats['pairs_detected'],
            'average_games_per_hour': round(avg_games, 2),
            'error_count': self.error_count,
            'config': self.config
        }
    
    def disconnect(self):
        """카지노 연결 해제"""
        self.is_active = False
        self.connection_status = "disconnected"
        safe_print(f"🔌 카지노 '{self.casino_id}' 연결 해제됨")


class MultiCasinoManager:
    """멀티 카지노 통합 관리자"""
    
    def __init__(self, config_file: str = 'casino_config.json'):
        self.config_file = Path(config_file)
        self.casinos: Dict[str, CasinoConnection] = {}
        self.is_running = False
        self.monitoring_thread = None
        
        # 통합 통계
        self.global_stats = {
            'total_casinos': 0,
            'active_casinos': 0,
            'total_games': 0,
            'total_pairs': 0,
            'start_time': datetime.now()
        }
        
        self.load_casino_config()
    
    def load_casino_config(self):
        """카지노 설정 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                for casino_data in config.get('casinos', []):
                    self.add_casino(casino_data['id'], casino_data['config'])
                    
                safe_print(f"✅ {len(self.casinos)}개 카지노 설정 로드 완료")
            except Exception as e:
                safe_print(f"❌ 카지노 설정 로드 실패: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """기본 카지노 설정 생성"""
        default_casinos = [
            {
                'id': 'main_casino',
                'config': {
                    'name': '메인 카지노',
                    'server_ip': '127.0.0.1',
                    'port': 8080,
                    'protocol': 'websocket',
                    'auto_connect': True,
                    'priority': 1
                }
            },
            {
                'id': 'backup_casino',
                'config': {
                    'name': '백업 카지노',
                    'server_ip': '127.0.0.1',
                    'port': 8081,
                    'protocol': 'websocket',
                    'auto_connect': False,
                    'priority': 2
                }
            }
        ]
        
        config = {
            'casinos': default_casinos,
            'global_settings': {
                'max_concurrent_casinos': 5,
                'data_sync_interval': 30,
                'auto_failover': True,
                'cross_casino_analysis': True
            }
        }
        
        self.save_config(config)
        
        for casino_data in default_casinos:
            self.add_casino(casino_data['id'], casino_data['config'])
        
        safe_print("✅ 기본 카지노 설정 2개 생성 완료")
    
    def add_casino(self, casino_id: str, config: Dict[str, Any]) -> bool:
        """새 카지노 추가"""
        try:
            if casino_id in self.casinos:
                safe_print(f"⚠️ 카지노 '{casino_id}'가 이미 존재합니다")
                return False
            
            casino_connection = CasinoConnection(casino_id, config)
            self.casinos[casino_id] = casino_connection
            
            # 자동 연결 설정인 경우 초기화
            if config.get('auto_connect', False):
                casino_connection.initialize()
            
            self.global_stats['total_casinos'] = len(self.casinos)
            
            safe_print(f"✅ 카지노 '{casino_id}' 추가 완료")
            return True
            
        except Exception as e:
            safe_print(f"❌ 카지노 '{casino_id}' 추가 실패: {e}")
            return False
    
    def remove_casino(self, casino_id: str) -> bool:
        """카지노 제거"""
        if casino_id not in self.casinos:
            return False
        
        # 연결 해제 후 제거
        self.casinos[casino_id].disconnect()
        del self.casinos[casino_id]
        
        self.global_stats['total_casinos'] = len(self.casinos)
        
        safe_print(f"🗑️ 카지노 '{casino_id}' 제거 완료")
        return True
    
    def connect_casino(self, casino_id: str) -> bool:
        """특정 카지노 연결"""
        if casino_id not in self.casinos:
            return False
        
        return self.casinos[casino_id].initialize()
    
    def disconnect_casino(self, casino_id: str) -> bool:
        """특정 카지노 연결 해제"""
        if casino_id not in self.casinos:
            return False
        
        self.casinos[casino_id].disconnect()
        return True
    
    def process_casino_data(self, casino_id: str, game_data: Dict[str, Any]) -> bool:
        """특정 카지노의 게임 데이터 처리"""
        if casino_id not in self.casinos:
            return False
        
        result = self.casinos[casino_id].process_game_data(game_data)
        
        if result:
            # 글로벌 통계 업데이트
            self.global_stats['total_games'] += 1
            if game_data.get('has_pair'):
                self.global_stats['total_pairs'] += 1
        
        return result
    
    def get_all_casino_status(self) -> List[Dict[str, Any]]:
        """모든 카지노 상태 조회"""
        statuses = []
        active_count = 0
        
        for casino in self.casinos.values():
            status = casino.get_status()
            statuses.append(status)
            
            if status['is_active']:
                active_count += 1
        
        self.global_stats['active_casinos'] = active_count
        
        return statuses
    
    def get_casino_comparison(self) -> Dict[str, Any]:
        """카지노 간 비교 분석"""
        if not self.casinos:
            return {}
        
        comparison = {
            'performance_ranking': [],
            'pair_detection_rates': {},
            'uptime_comparison': {},
            'error_rates': {}
        }
        
        # 성능 순위 (시간당 게임 처리량 기준)
        casino_performance = []
        for casino in self.casinos.values():
            status = casino.get_status()
            casino_performance.append({
                'casino_id': casino.casino_id,
                'games_per_hour': status['average_games_per_hour'],
                'pairs_detected': status['pairs_detected'],
                'error_rate': status['error_count'] / max(status['games_processed'], 1) * 100
            })
        
        # 성능순으로 정렬
        comparison['performance_ranking'] = sorted(
            casino_performance, 
            key=lambda x: x['games_per_hour'], 
            reverse=True
        )
        
        # 페어 감지율 계산
        for perf in casino_performance:
            casino_id = perf['casino_id']
            games = self.casinos[casino_id].stats['games_processed']
            pairs = self.casinos[casino_id].stats['pairs_detected']
            
            comparison['pair_detection_rates'][casino_id] = {
                'rate': round(pairs / max(games, 1) * 100, 2),
                'total_pairs': pairs,
                'total_games': games
            }
        
        return comparison
    
    def get_recommended_casino(self) -> Optional[str]:
        """현재 최적의 카지노 추천"""
        active_casinos = [c for c in self.casinos.values() if c.is_active]
        
        if not active_casinos:
            return None
        
        # 성능 점수 계산 (게임 처리량 + 안정성)
        best_casino = None
        best_score = -1
        
        for casino in active_casinos:
            status = casino.get_status()
            
            # 점수 = 게임 처리량 - 오류율
            score = status['average_games_per_hour'] - (status['error_count'] * 10)
            
            if score > best_score:
                best_score = score
                best_casino = casino.casino_id
        
        return best_casino
    
    def save_config(self, config: Dict[str, Any] = None):
        """카지노 설정 저장"""
        try:
            if config is None:
                # 현재 카지노들의 설정을 저장
                config = {
                    'casinos': [
                        {'id': cid, 'config': casino.config}
                        for cid, casino in self.casinos.items()
                    ],
                    'global_settings': {
                        'max_concurrent_casinos': 5,
                        'data_sync_interval': 30,
                        'auto_failover': True,
                        'cross_casino_analysis': True
                    },
                    'last_updated': datetime.now().isoformat()
                }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            safe_print(f"❌ 카지노 설정 저장 실패: {e}")
    
    def start_monitoring(self):
        """카지노 모니터링 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        safe_print("🔍 멀티 카지노 모니터링 시작")
    
    def stop_monitoring(self):
        """카지노 모니터링 중지"""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        safe_print("🛑 멀티 카지노 모니터링 중지")
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        import time
        
        while self.is_running:
            try:
                # 각 카지노 상태 확인
                for casino in self.casinos.values():
                    if casino.is_active:
                        # 연결 상태 확인 및 오류 복구
                        if casino.error_count > 10:
                            safe_print(f"⚠️ 카지노 '{casino.casino_id}' 오류 과다로 재연결 시도")
                            casino.disconnect()
                            time.sleep(1)
                            casino.initialize()
                
                time.sleep(30)  # 30초마다 모니터링
                
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(5)


# 전역 인스턴스
_multi_casino_manager = None

def get_multi_casino_manager() -> MultiCasinoManager:
    """멀티 카지노 관리자 인스턴스 반환"""
    global _multi_casino_manager
    if _multi_casino_manager is None:
        _multi_casino_manager = MultiCasinoManager()
    return _multi_casino_manager


if __name__ == "__main__":
    # 테스트 코드
    manager = get_multi_casino_manager()
    
    safe_print("🎰 멀티 카지노 관리자 테스트")
    safe_print(f"등록된 카지노 수: {len(manager.casinos)}")
    
    for status in manager.get_all_casino_status():
        safe_print(f"카지노: {status['casino_id']} | 상태: {status['connection_status']} | 게임: {status['games_processed']}")
    
    recommended = manager.get_recommended_casino()
    if recommended:
        safe_print(f"추천 카지노: {recommended}")
    
    manager.start_monitoring()