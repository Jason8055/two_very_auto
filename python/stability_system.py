#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
안정성 및 자동 복구 시스템 v1.0
에러 처리, 자동 복구, 데이터 백업 및 시스템 장애 대응
"""

import sys
import json
import asyncio
import logging
import threading
import time
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from collections import defaultdict, deque
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorHandler:
    """중앙화된 에러 처리 시스템"""
    
    def __init__(self, max_error_history: int = 1000):
        self.error_history = deque(maxlen=max_error_history)
        self.error_patterns = defaultdict(int)
        self.recovery_strategies = {}
        self.error_callbacks = []
        
        # 에러 통계
        self.error_stats = {
            'total_errors': 0,
            'critical_errors': 0,
            'recovered_errors': 0,
            'unrecoverable_errors': 0,
            'last_error_time': None
        }
        
        self._register_default_strategies()
        
    def _register_default_strategies(self):
        """기본 복구 전략 등록"""
        self.recovery_strategies = {
            'database_connection_error': self._recover_database_connection,
            'websocket_connection_error': self._recover_websocket_connection,
            'ai_model_error': self._recover_ai_model,
            'memory_error': self._recover_memory_issue,
            'file_system_error': self._recover_file_system,
            'network_error': self._recover_network_issue
        }
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """에러 처리 및 복구 시도"""
        timestamp = datetime.now()
        error_type = type(error).__name__
        error_message = str(error)
        
        # 에러 기록 생성
        error_record = {
            'timestamp': timestamp.isoformat(),
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
            'stack_trace': self._get_stack_trace(),
            'severity': self._assess_severity(error, context),
            'recovery_attempted': False,
            'recovery_successful': False
        }
        
        # 통계 업데이트
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = timestamp.isoformat()
        
        if error_record['severity'] == 'critical':
            self.error_stats['critical_errors'] += 1
        
        # 에러 패턴 분석
        error_pattern = self._analyze_error_pattern(error_record)
        self.error_patterns[error_pattern] += 1
        
        # 복구 시도
        recovery_successful = False
        if error_pattern in self.recovery_strategies:
            try:
                error_record['recovery_attempted'] = True
                recovery_successful = self.recovery_strategies[error_pattern](error, context)
                error_record['recovery_successful'] = recovery_successful
                
                if recovery_successful:
                    self.error_stats['recovered_errors'] += 1
                else:
                    self.error_stats['unrecoverable_errors'] += 1
                    
            except Exception as recovery_error:
                logger.error(f"복구 전략 실행 중 오류: {recovery_error}")
                error_record['recovery_error'] = str(recovery_error)
        
        # 에러 기록 저장
        self.error_history.append(error_record)
        
        # 에러 콜백 실행
        for callback in self.error_callbacks:
            try:
                callback(error_record)
            except Exception as callback_error:
                logger.error(f"에러 콜백 실행 중 오류: {callback_error}")
        
        # 로그 기록
        log_level = logging.CRITICAL if error_record['severity'] == 'critical' else logging.ERROR
        logger.log(log_level, f"에러 처리: {error_type} - {error_message} (복구: {'성공' if recovery_successful else '실패'})")
        
        return recovery_successful
    
    def _get_stack_trace(self) -> str:
        """스택 트레이스 가져오기"""
        import traceback
        return traceback.format_exc()
    
    def _assess_severity(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """에러 심각도 평가"""
        error_type = type(error).__name__
        
        # 치명적 에러 패턴
        critical_patterns = [
            'SystemExit', 'KeyboardInterrupt', 'MemoryError',
            'DatabaseError', 'ConnectionError', 'FileNotFoundError'
        ]
        
        if any(pattern in error_type for pattern in critical_patterns):
            return 'critical'
        elif 'Warning' in error_type:
            return 'warning'
        else:
            return 'error'
    
    def _analyze_error_pattern(self, error_record: Dict[str, Any]) -> str:
        """에러 패턴 분석"""
        error_type = error_record['error_type']
        error_message = error_record['error_message'].lower()
        
        # 패턴 매칭
        if 'database' in error_message or 'sqlite' in error_message:
            return 'database_connection_error'
        elif 'websocket' in error_message or 'connection' in error_message:
            return 'websocket_connection_error'
        elif 'tensorflow' in error_message or 'model' in error_message:
            return 'ai_model_error'
        elif 'memory' in error_message:
            return 'memory_error'
        elif 'file' in error_message or 'path' in error_message:
            return 'file_system_error'
        elif 'network' in error_message or 'http' in error_message:
            return 'network_error'
        else:
            return f'unknown_{error_type}'
    
    def _recover_database_connection(self, error: Exception, context: Dict[str, Any]) -> bool:
        """데이터베이스 연결 복구"""
        try:
            safe_print("🔧 데이터베이스 연결 복구 시도...")
            
            # 데이터베이스 파일 존재 확인
            db_path = context.get('db_path', 'two_very_auto.db')
            if not Path(db_path).exists():
                safe_print(f"⚠️ 데이터베이스 파일이 없음: {db_path}")
                return False
            
            # 연결 테스트
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("SELECT 1")
            conn.close()
            
            safe_print("✅ 데이터베이스 연결 복구 성공")
            return True
            
        except Exception as e:
            safe_print(f"❌ 데이터베이스 연결 복구 실패: {e}")
            return False
    
    def _recover_websocket_connection(self, error: Exception, context: Dict[str, Any]) -> bool:
        """WebSocket 연결 복구"""
        try:
            safe_print("🔧 WebSocket 연결 복구 시도...")
            
            # 짧은 대기 후 재연결 시도
            time.sleep(2)
            
            # 실제 WebSocket 복구는 각 모듈에서 처리
            safe_print("✅ WebSocket 연결 복구 준비 완료")
            return True
            
        except Exception as e:
            safe_print(f"❌ WebSocket 연결 복구 실패: {e}")
            return False
    
    def _recover_ai_model(self, error: Exception, context: Dict[str, Any]) -> bool:
        """AI 모델 복구"""
        try:
            safe_print("🔧 AI 모델 복구 시도...")
            
            # 모델 파일 존재 확인
            model_path = context.get('model_path', 'pair_prediction_model.h5')
            if Path(model_path).exists():
                safe_print("✅ AI 모델 파일 존재 확인")
                return True
            else:
                safe_print("⚠️ AI 모델 파일 없음 - 통계 모델로 대체")
                return True  # 통계 모델로 대체 가능
            
        except Exception as e:
            safe_print(f"❌ AI 모델 복구 실패: {e}")
            return False
    
    def _recover_memory_issue(self, error: Exception, context: Dict[str, Any]) -> bool:
        """메모리 문제 복구"""
        try:
            safe_print("🔧 메모리 정리 시도...")
            
            # 가비지 컬렉션 강제 실행
            import gc
            gc.collect()
            
            # 캐시 정리
            if hasattr(context, 'clear_cache'):
                context['clear_cache']()
            
            safe_print("✅ 메모리 정리 완료")
            return True
            
        except Exception as e:
            safe_print(f"❌ 메모리 정리 실패: {e}")
            return False
    
    def _recover_file_system(self, error: Exception, context: Dict[str, Any]) -> bool:
        """파일 시스템 문제 복구"""
        try:
            safe_print("🔧 파일 시스템 문제 복구 시도...")
            
            # 필요한 디렉토리 생성
            required_dirs = ['backup', 'logs', 'temp']
            for dir_name in required_dirs:
                Path(dir_name).mkdir(exist_ok=True)
            
            safe_print("✅ 파일 시스템 복구 완료")
            return True
            
        except Exception as e:
            safe_print(f"❌ 파일 시스템 복구 실패: {e}")
            return False
    
    def _recover_network_issue(self, error: Exception, context: Dict[str, Any]) -> bool:
        """네트워크 문제 복구"""
        try:
            safe_print("🔧 네트워크 연결 확인 중...")
            
            # 네트워크 연결 테스트 (간단한 구현)
            import socket
            socket.setdefaulttimeout(5)
            
            try:
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                safe_print("✅ 네트워크 연결 정상")
                return True
            except socket.error:
                safe_print("⚠️ 네트워크 연결 불안정")
                return False
                
        except Exception as e:
            safe_print(f"❌ 네트워크 복구 실패: {e}")
            return False
    
    def add_error_callback(self, callback: Callable):
        """에러 콜백 추가"""
        self.error_callbacks.append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """에러 통계 반환"""
        # 최근 24시간 에러
        recent_errors = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for error in self.error_history:
            error_time = datetime.fromisoformat(error['timestamp'])
            if error_time > cutoff_time:
                recent_errors.append(error)
        
        # 에러 패턴 분석
        top_error_patterns = dict(sorted(self.error_patterns.items(), 
                                       key=lambda x: x[1], reverse=True)[:5])
        
        return {
            'total_stats': self.error_stats,
            'recent_24h': {
                'total_errors': len(recent_errors),
                'critical_errors': len([e for e in recent_errors if e['severity'] == 'critical']),
                'recovery_rate': len([e for e in recent_errors if e['recovery_successful']]) / len(recent_errors) * 100 if recent_errors else 0
            },
            'top_error_patterns': top_error_patterns,
            'system_stability': self._assess_system_stability()
        }
    
    def _assess_system_stability(self) -> str:
        """시스템 안정성 평가"""
        recent_errors = []
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for error in self.error_history:
            error_time = datetime.fromisoformat(error['timestamp'])
            if error_time > cutoff_time:
                recent_errors.append(error)
        
        if len(recent_errors) == 0:
            return 'excellent'
        elif len(recent_errors) <= 2:
            return 'good'
        elif len(recent_errors) <= 5:
            return 'fair'
        else:
            return 'poor'


class BackupSystem:
    """자동 백업 시스템"""
    
    def __init__(self, backup_dir: str = "backup"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        self.backup_config = {
            'database_backup_interval': 300,  # 5분
            'config_backup_interval': 3600,   # 1시간
            'log_backup_interval': 86400,     # 24시간
            'max_backups': 10
        }
        
        self.last_backup_times = {}
        self.backup_thread = None
        self.is_backup_active = False
        
    def start_automatic_backup(self):
        """자동 백업 시작"""
        if self.is_backup_active:
            return
        
        self.is_backup_active = True
        self.backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self.backup_thread.start()
        safe_print("💾 자동 백업 시스템 시작")
    
    def stop_automatic_backup(self):
        """자동 백업 중지"""
        self.is_backup_active = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        safe_print("⏹️ 자동 백업 시스템 중지")
    
    def _backup_loop(self):
        """백업 루프"""
        while self.is_backup_active:
            try:
                current_time = time.time()
                
                # 데이터베이스 백업 확인
                if self._should_backup('database', current_time):
                    self.backup_database()
                    self.last_backup_times['database'] = current_time
                
                # 설정 파일 백업 확인
                if self._should_backup('config', current_time):
                    self.backup_config_files()
                    self.last_backup_times['config'] = current_time
                
                # 로그 파일 백업 확인
                if self._should_backup('log', current_time):
                    self.backup_log_files()
                    self.last_backup_times['log'] = current_time
                
                time.sleep(60)  # 1분마다 확인
                
            except Exception as e:
                logger.error(f"백업 루프 오류: {e}")
                time.sleep(300)  # 오류 시 5분 대기
    
    def _should_backup(self, backup_type: str, current_time: float) -> bool:
        """백업 필요 여부 확인"""
        if backup_type not in self.last_backup_times:
            return True
        
        interval_key = f'{backup_type}_backup_interval'
        interval = self.backup_config.get(interval_key, 3600)
        
        return (current_time - self.last_backup_times[backup_type]) >= interval
    
    def backup_database(self) -> bool:
        """데이터베이스 백업"""
        try:
            db_file = Path("two_very_auto.db")
            if not db_file.exists():
                return False
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"database_backup_{timestamp}.db"
            
            shutil.copy2(db_file, backup_file)
            self._cleanup_old_backups("database_backup_*.db")
            
            safe_print(f"💾 데이터베이스 백업 완료: {backup_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 백업 실패: {e}")
            return False
    
    def backup_config_files(self) -> bool:
        """설정 파일 백업"""
        try:
            config_files = [
                "*.json", "*.yaml", "*.yml", "*.ini", "*.conf"
            ]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            config_backup_dir = self.backup_dir / f"config_backup_{timestamp}"
            config_backup_dir.mkdir(exist_ok=True)
            
            backed_up = False
            for pattern in config_files:
                for file_path in Path(".").glob(pattern):
                    if file_path.is_file():
                        shutil.copy2(file_path, config_backup_dir)
                        backed_up = True
            
            if backed_up:
                self._cleanup_old_backups("config_backup_*")
                safe_print(f"💾 설정 파일 백업 완료: {config_backup_dir.name}")
            
            return backed_up
            
        except Exception as e:
            logger.error(f"설정 파일 백업 실패: {e}")
            return False
    
    def backup_log_files(self) -> bool:
        """로그 파일 백업"""
        try:
            log_files = list(Path(".").glob("*.log"))
            if not log_files:
                return False
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_backup_dir = self.backup_dir / f"log_backup_{timestamp}"
            log_backup_dir.mkdir(exist_ok=True)
            
            for log_file in log_files:
                shutil.copy2(log_file, log_backup_dir)
            
            self._cleanup_old_backups("log_backup_*")
            safe_print(f"💾 로그 파일 백업 완료: {log_backup_dir.name}")
            return True
            
        except Exception as e:
            logger.error(f"로그 파일 백업 실패: {e}")
            return False
    
    def _cleanup_old_backups(self, pattern: str):
        """오래된 백업 정리"""
        try:
            backups = sorted(self.backup_dir.glob(pattern), 
                           key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 최대 백업 수를 초과하는 백업 삭제
            for old_backup in backups[self.backup_config['max_backups']:]:
                if old_backup.is_dir():
                    shutil.rmtree(old_backup)
                else:
                    old_backup.unlink()
                    
        except Exception as e:
            logger.error(f"백업 정리 실패: {e}")
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """백업에서 복원"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return False
            
            if "database" in backup_file.name:
                # 데이터베이스 복원
                target_file = Path("two_very_auto.db")
                shutil.copy2(backup_file, target_file)
                safe_print(f"🔄 데이터베이스 복원 완료: {backup_file.name}")
                
            return True
            
        except Exception as e:
            logger.error(f"백업 복원 실패: {e}")
            return False
    
    def get_backup_status(self) -> Dict[str, Any]:
        """백업 상태 반환"""
        backups = {
            'database': len(list(self.backup_dir.glob("database_backup_*.db"))),
            'config': len(list(self.backup_dir.glob("config_backup_*"))),
            'log': len(list(self.backup_dir.glob("log_backup_*")))
        }
        
        total_size = sum(
            f.stat().st_size for f in self.backup_dir.rglob("*") if f.is_file()
        )
        
        return {
            'backup_counts': backups,
            'total_backup_size': total_size,
            'backup_directory': str(self.backup_dir),
            'is_active': self.is_backup_active,
            'last_backup_times': self.last_backup_times.copy()
        }


class StabilitySystem:
    """통합 안정성 시스템"""
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.backup_system = BackupSystem()
        self.health_checks = []
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # 기본 상태 확인 등록
        self._register_default_health_checks()
        
        safe_print("🛡️ 안정성 시스템 초기화 완료")
    
    def _register_default_health_checks(self):
        """기본 상태 확인 등록"""
        self.health_checks = [
            self._check_database_health,
            self._check_file_system_health,
            self._check_memory_health,
            self._check_disk_space_health
        ]
    
    def start_stability_monitoring(self):
        """안정성 모니터링 시작"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.backup_system.start_automatic_backup()
        
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        safe_print("🔄 안정성 모니터링 시작")
    
    def stop_stability_monitoring(self):
        """안정성 모니터링 중지"""
        self.is_monitoring = False
        self.backup_system.stop_automatic_backup()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        safe_print("⏹️ 안정성 모니터링 중지")
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.is_monitoring:
            try:
                # 상태 확인 실행
                health_issues = []
                for health_check in self.health_checks:
                    try:
                        result = health_check()
                        if not result['healthy']:
                            health_issues.append(result)
                    except Exception as e:
                        logger.error(f"상태 확인 실행 오류: {e}")
                
                # 심각한 문제 발견 시 알림
                for issue in health_issues:
                    if issue['severity'] == 'critical':
                        self._trigger_stability_alert(issue)
                
                time.sleep(30)  # 30초마다 확인
                
            except Exception as e:
                logger.error(f"안정성 모니터링 루프 오류: {e}")
                time.sleep(60)
    
    def _check_database_health(self) -> Dict[str, Any]:
        """데이터베이스 상태 확인"""
        try:
            db_path = Path("two_very_auto.db")
            if not db_path.exists():
                return {
                    'healthy': False,
                    'component': 'database',
                    'severity': 'critical',
                    'message': '데이터베이스 파일이 존재하지 않음'
                }
            
            # 연결 테스트
            conn = sqlite3.connect(str(db_path), timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            
            return {'healthy': True, 'component': 'database'}
            
        except Exception as e:
            return {
                'healthy': False,
                'component': 'database',
                'severity': 'critical',
                'message': f'데이터베이스 연결 실패: {str(e)}'
            }
    
    def _check_file_system_health(self) -> Dict[str, Any]:
        """파일 시스템 상태 확인"""
        try:
            # 필수 디렉토리 존재 확인
            required_dirs = ['backup', 'logs', 'temp']
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    dir_path.mkdir(exist_ok=True)
            
            # 쓰기 권한 테스트
            test_file = Path("temp/health_check.txt")
            test_file.write_text("health check")
            test_file.unlink()
            
            return {'healthy': True, 'component': 'file_system'}
            
        except Exception as e:
            return {
                'healthy': False,
                'component': 'file_system',
                'severity': 'warning',
                'message': f'파일 시스템 문제: {str(e)}'
            }
    
    def _check_memory_health(self) -> Dict[str, Any]:
        """메모리 상태 확인"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 95:
                return {
                    'healthy': False,
                    'component': 'memory',
                    'severity': 'critical',
                    'message': f'메모리 사용률이 {memory.percent:.1f}%로 매우 높음'
                }
            elif memory.percent > 85:
                return {
                    'healthy': False,
                    'component': 'memory',
                    'severity': 'warning',
                    'message': f'메모리 사용률이 {memory.percent:.1f}%로 높음'
                }
            
            return {'healthy': True, 'component': 'memory'}
            
        except Exception as e:
            return {
                'healthy': False,
                'component': 'memory',
                'severity': 'warning',
                'message': f'메모리 상태 확인 실패: {str(e)}'
            }
    
    def _check_disk_space_health(self) -> Dict[str, Any]:
        """디스크 공간 상태 확인"""
        try:
            import psutil
            disk = psutil.disk_usage('.')
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 95:
                return {
                    'healthy': False,
                    'component': 'disk_space',
                    'severity': 'critical',
                    'message': f'디스크 사용률이 {usage_percent:.1f}%로 매우 높음'
                }
            elif usage_percent > 85:
                return {
                    'healthy': False,
                    'component': 'disk_space',
                    'severity': 'warning',
                    'message': f'디스크 사용률이 {usage_percent:.1f}%로 높음'
                }
            
            return {'healthy': True, 'component': 'disk_space'}
            
        except Exception as e:
            return {
                'healthy': False,
                'component': 'disk_space',
                'severity': 'warning',
                'message': f'디스크 상태 확인 실패: {str(e)}'
            }
    
    def _trigger_stability_alert(self, issue: Dict[str, Any]):
        """안정성 알림 발송"""
        alert_message = f"🚨 시스템 안정성 경고: {issue['message']}"
        safe_print(alert_message)
        
        # 여기서 외부 알림 시스템 호출 가능
        # (이메일, 슬랙, 카카오톡 등)
    
    def handle_system_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """시스템 에러 처리"""
        return self.error_handler.handle_error(error, context)
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """시스템 상태 보고서"""
        # 상태 확인 실행
        health_results = []
        overall_health = True
        
        for health_check in self.health_checks:
            try:
                result = health_check()
                health_results.append(result)
                if not result['healthy']:
                    overall_health = False
            except Exception as e:
                health_results.append({
                    'healthy': False,
                    'component': 'unknown',
                    'severity': 'error',
                    'message': str(e)
                })
                overall_health = False
        
        # 에러 통계
        error_stats = self.error_handler.get_error_statistics()
        
        # 백업 상태
        backup_status = self.backup_system.get_backup_status()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': overall_health,
            'health_checks': health_results,
            'error_statistics': error_stats,
            'backup_status': backup_status,
            'monitoring_active': self.is_monitoring
        }


# 전역 인스턴스
stability_system = StabilitySystem()

def get_stability_system() -> StabilitySystem:
    """전역 안정성 시스템 인스턴스 반환"""
    return stability_system


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 안정성 시스템 테스트 ===")
    
    system = StabilitySystem()
    
    # 안정성 모니터링 시작
    system.start_stability_monitoring()
    
    # 테스트 에러 처리
    try:
        raise ValueError("테스트 에러입니다")
    except Exception as e:
        recovery_success = system.handle_system_error(e, {'test': True})
        safe_print(f"에러 복구 결과: {'성공' if recovery_success else '실패'}")
    
    # 상태 보고서 생성
    health_report = system.get_system_health_report()
    safe_print(f"시스템 전체 상태: {'정상' if health_report['overall_health'] else '문제 있음'}")
    
    # 5초 대기
    safe_print("5초간 모니터링 테스트...")
    time.sleep(5)
    
    # 시스템 중지
    system.stop_stability_monitoring()
    safe_print("🎯 안정성 시스템 테스트 완료!")