#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database Manager
SQLite 기반 데이터베이스 관리자
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite 데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "baccarat_monitor.db"):
        """
        데이터베이스 매니저 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self.connection = None
        
        # 데이터베이스 초기화
        self._initialize_database()
        logger.info(f"[Database Manager] Initialized with {self.db_path}")
    
    def _initialize_database(self) -> None:
        """데이터베이스 및 테이블 초기화"""
        try:
            with self.get_connection() as conn:
                # 테이블 생성 강제 실행
                self._create_tables(conn)
                
                # 초기 데이터 확인
                self._check_initial_data(conn)
                
                # 테이블 생성 확인
                result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [r[0] for r in result]
                logger.info(f"Created tables: {table_names}")
                
                if len(table_names) < 5:
                    raise Exception(f"테이블 생성 실패: {len(table_names)} 개만 생성됨")
                
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """테이블 생성"""
        
        # 1. 게임 테이블
        conn.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                game_id INTEGER NOT NULL,
                game_time TIMESTAMP NOT NULL,
                result TEXT NOT NULL,
                player_cards TEXT NOT NULL,
                banker_cards TEXT NOT NULL,
                has_pair BOOLEAN NOT NULL,
                pair_type TEXT,
                pair_cards TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(table_name, game_id)
            )
        ''')
        
        # 2. 테이블 통계
        conn.execute('''
            CREATE TABLE IF NOT EXISTS table_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT UNIQUE NOT NULL,
                total_games INTEGER DEFAULT 0,
                total_pairs INTEGER DEFAULT 0,
                player_pairs INTEGER DEFAULT 0,
                banker_pairs INTEGER DEFAULT 0,
                both_pairs INTEGER DEFAULT 0,
                last_game_time TIMESTAMP,
                pair_rate REAL DEFAULT 0.0,
                avg_games_between_pairs REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. 알림 히스토리
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL,
                channels TEXT NOT NULL,
                table_name TEXT,
                game_id INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 4. 패턴 분석 결과
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pattern_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                result_data TEXT NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5. 시스템 설정
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 인덱스 생성
        conn.execute('CREATE INDEX IF NOT EXISTS idx_games_table_time ON games(table_name, game_time)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_games_pair ON games(has_pair, game_time)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_sent ON notification_history(sent_at)')
        
        conn.commit()
    
    def _check_initial_data(self, conn: sqlite3.Connection) -> None:
        """초기 데이터 확인 및 생성"""
        # 기본 시스템 설정
        default_configs = [
            ('system.version', '3.1.0'),
            ('system.initialized_at', datetime.now().isoformat()),
            ('notifications.enabled', 'true'),
            ('patterns.auto_analysis', 'true')
        ]
        
        for key, value in default_configs:
            conn.execute('''
                INSERT OR IGNORE INTO system_config (config_key, config_value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
    
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Row 객체로 결과 반환
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def save_game(self, game_data: Dict[str, Any]) -> int:
        """게임 데이터 저장"""
        try:
            with self.get_connection() as conn:
                pair_info = game_data.get('pair_info', {})
                
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO games 
                    (table_name, game_id, game_time, result, player_cards, banker_cards,
                     has_pair, pair_type, pair_cards)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_data['table_name'],
                    game_data['game_id'],
                    game_data['game_time'],
                    game_data['result'],
                    json.dumps(game_data.get('player_cards', [])),
                    json.dumps(game_data.get('banker_cards', [])),
                    pair_info.get('has_any_pair', False),
                    pair_info.get('pair_type'),
                    json.dumps(pair_info.get('pair_cards', []))
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to save game: {e}")
            return -1
    
    def update_table_stats(self, table_name: str, stats: Dict[str, Any]) -> None:
        """테이블 통계 업데이트"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO table_stats 
                    (table_name, total_games, total_pairs, player_pairs, banker_pairs,
                     both_pairs, last_game_time, pair_rate, avg_games_between_pairs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    table_name,
                    stats.get('total_games', 0),
                    stats.get('pair_count', 0),
                    stats.get('player_pairs', 0),
                    stats.get('banker_pairs', 0),
                    stats.get('both_pairs', 0),
                    stats.get('last_game_time'),
                    stats.get('statistics', {}).get('pair_rate', 0.0),
                    stats.get('statistics', {}).get('avg_games_between_pairs', 0.0)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update table stats: {e}")
    
    def get_games(self, table_name: str = None, limit: int = 100, 
                  since: datetime = None) -> List[Dict[str, Any]]:
        """게임 데이터 조회"""
        try:
            with self.get_connection() as conn:
                query = 'SELECT * FROM games'
                params = []
                
                conditions = []
                if table_name:
                    conditions.append('table_name = ?')
                    params.append(table_name)
                
                if since:
                    conditions.append('game_time >= ?')
                    params.append(since.isoformat())
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY game_time DESC LIMIT ?'
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                games = []
                for row in cursor.fetchall():
                    game = dict(row)
                    # JSON 필드 파싱
                    game['player_cards'] = json.loads(game['player_cards'])
                    game['banker_cards'] = json.loads(game['banker_cards'])
                    if game['pair_cards']:
                        game['pair_cards'] = json.loads(game['pair_cards'])
                    games.append(game)
                
                return games
                
        except Exception as e:
            logger.error(f"Failed to get games: {e}")
            return []
    
    def get_table_statistics(self, table_name: str = None) -> Dict[str, Any]:
        """테이블 통계 조회"""
        try:
            with self.get_connection() as conn:
                if table_name:
                    # 특정 테이블 통계
                    cursor = conn.execute('''
                        SELECT * FROM table_stats WHERE table_name = ?
                    ''', (table_name,))
                    
                    row = cursor.fetchone()
                    return dict(row) if row else {}
                    
                else:
                    # 전체 통계
                    cursor = conn.execute('''
                        SELECT 
                            COUNT(*) as total_tables,
                            SUM(total_games) as total_games,
                            SUM(total_pairs) as total_pairs,
                            AVG(pair_rate) as avg_pair_rate
                        FROM table_stats
                    ''')
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'global_stats': {
                                'total_games': row['total_games'] or 0,
                                'total_pairs': row['total_pairs'] or 0,
                                'avg_pair_rate': row['avg_pair_rate'] or 0.0,
                                'total_tables': row['total_tables'] or 0
                            }
                        }
                    
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
            return {}
    
    def save_notification(self, notification_data: Dict[str, Any]) -> int:
        """알림 히스토리 저장"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO notification_history
                    (rule_name, message, priority, channels, table_name, game_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    notification_data.get('rule', ''),
                    notification_data.get('message', ''),
                    notification_data.get('priority', ''),
                    json.dumps(notification_data.get('channels', [])),
                    notification_data.get('table_name'),
                    notification_data.get('game_id')
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to save notification: {e}")
            return -1
    
    def get_notifications(self, limit: int = 50, since: datetime = None) -> List[Dict[str, Any]]:
        """알림 히스토리 조회"""
        try:
            with self.get_connection() as conn:
                query = 'SELECT * FROM notification_history'
                params = []
                
                if since:
                    query += ' WHERE sent_at >= ?'
                    params.append(since.isoformat())
                
                query += ' ORDER BY sent_at DESC LIMIT ?'
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                notifications = []
                for row in cursor.fetchall():
                    notification = dict(row)
                    notification['channels'] = json.loads(notification['channels'])
                    notifications.append(notification)
                
                return notifications
                
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return []
    
    def save_pattern_analysis(self, table_name: str, analysis_type: str, 
                            result_data: Dict[str, Any]) -> int:
        """패턴 분석 결과 저장"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO pattern_analysis
                    (table_name, analysis_type, result_data)
                    VALUES (?, ?, ?)
                ''', (
                    table_name,
                    analysis_type,
                    json.dumps(result_data, ensure_ascii=False)
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to save pattern analysis: {e}")
            return -1
    
    def get_pattern_analysis(self, table_name: str = None, 
                           analysis_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """패턴 분석 결과 조회"""
        try:
            with self.get_connection() as conn:
                query = 'SELECT * FROM pattern_analysis'
                params = []
                conditions = []
                
                if table_name:
                    conditions.append('table_name = ?')
                    params.append(table_name)
                
                if analysis_type:
                    conditions.append('analysis_type = ?')
                    params.append(analysis_type)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY analyzed_at DESC LIMIT ?'
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                analyses = []
                for row in cursor.fetchall():
                    analysis = dict(row)
                    analysis['result_data'] = json.loads(analysis['result_data'])
                    analyses.append(analysis)
                
                return analyses
                
        except Exception as e:
            logger.error(f"Failed to get pattern analysis: {e}")
            return []
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """시스템 설정 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT config_value FROM system_config WHERE config_key = ?
                ''', (key,))
                
                row = cursor.fetchone()
                if row:
                    value = row['config_value']
                    # JSON 파싱 시도
                    try:
                        return json.loads(value)
                    except:
                        return value
                
                return default
                
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return default
    
    def set_config(self, key: str, value: Any) -> None:
        """시스템 설정 저장"""
        try:
            with self.get_connection() as conn:
                # JSON으로 변환 시도
                try:
                    value_str = json.dumps(value, ensure_ascii=False)
                except:
                    value_str = str(value)
                
                conn.execute('''
                    INSERT OR REPLACE INTO system_config (config_key, config_value)
                    VALUES (?, ?)
                ''', (key, value_str))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to set config: {e}")
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """오래된 데이터 정리"""
        try:
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            with self.get_connection() as conn:
                # 오래된 게임 데이터 삭제
                cursor = conn.execute('''
                    DELETE FROM games WHERE game_time < datetime(?, 'unixepoch')
                ''', (cutoff_date,))
                games_deleted = cursor.rowcount
                
                # 오래된 알림 히스토리 삭제
                cursor = conn.execute('''
                    DELETE FROM notification_history WHERE sent_at < datetime(?, 'unixepoch')
                ''', (cutoff_date,))
                notifications_deleted = cursor.rowcount
                
                # 오래된 패턴 분석 결과 삭제
                cursor = conn.execute('''
                    DELETE FROM pattern_analysis WHERE analyzed_at < datetime(?, 'unixepoch')
                ''', (cutoff_date,))
                patterns_deleted = cursor.rowcount
                
                conn.commit()
                
                total_deleted = games_deleted + notifications_deleted + patterns_deleted
                logger.info(f"Cleanup completed: {total_deleted} records deleted")
                
                return total_deleted
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def get_database_info(self) -> Dict[str, Any]:
        """데이터베이스 정보 조회"""
        try:
            with self.get_connection() as conn:
                info = {}
                
                # 테이블별 레코드 수
                tables = ['games', 'table_stats', 'notification_history', 
                         'pattern_analysis', 'system_config']
                
                for table in tables:
                    cursor = conn.execute(f'SELECT COUNT(*) as count FROM {table}')
                    row = cursor.fetchone()
                    info[f'{table}_count'] = row['count']
                
                # 데이터베이스 파일 크기
                info['file_size'] = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                # 버전 정보
                info['version'] = self.get_config('system.version', '3.1.0')
                info['initialized_at'] = self.get_config('system.initialized_at')
                
                return info
                
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """데이터베이스 백업"""
        try:
            import shutil
            
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Database backed up to: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False


if __name__ == '__main__':
    # 테스트 실행
    print("Testing Database Manager...")
    
    # 데이터베이스 매니저 초기화
    db = DatabaseManager("test_baccarat.db")
    
    # 테스트 데이터 저장
    test_game = {
        'table_name': 'test_table',
        'game_id': 12345,
        'game_time': datetime.now().isoformat(),
        'result': 'PLAYER',
        'player_cards': ['AH', 'KS'],
        'banker_cards': ['QD', 'JC'],
        'pair_info': {
            'has_any_pair': True,
            'pair_type': 'PLAYER_PAIR',
            'pair_cards': ['AH', 'AS']
        }
    }
    
    # 게임 저장
    game_id = db.save_game(test_game)
    print(f"Saved game with ID: {game_id}")
    
    # 통계 업데이트
    test_stats = {
        'total_games': 10,
        'pair_count': 2,
        'player_pairs': 1,
        'banker_pairs': 1,
        'both_pairs': 0,
        'last_game_time': datetime.now().isoformat(),
        'statistics': {
            'pair_rate': 0.2,
            'avg_games_between_pairs': 5.0
        }
    }
    
    db.update_table_stats('test_table', test_stats)
    print("Updated table statistics")
    
    # 데이터 조회
    games = db.get_games(limit=5)
    print(f"Retrieved {len(games)} games")
    
    stats = db.get_table_statistics()
    print(f"Global stats: {stats}")
    
    # 데이터베이스 정보
    info = db.get_database_info()
    print(f"Database info: {info}")
    
    # 정리
    Path("test_baccarat.db").unlink(missing_ok=True)
    print("Test completed successfully!")