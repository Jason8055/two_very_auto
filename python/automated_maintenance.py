#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동화 유지보수 시스템
일일/주간 시스템 점검, 정리, 최적화 자동 실행
"""

import os
import shutil
import sqlite3
import logging
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import psutil
from packet_archive_manager import PacketArchiveManager
from system_monitor_dashboard import SystemMonitor


class AutomatedMaintenance:
    """자동화 유지보수 관리자"""
    
    def __init__(self, project_root: str = "F:/two very auto 25.08.23"):
        self.project_root = Path(project_root)
        self.python_root = self.project_root / "python"
        self.log_file = self.python_root / "maintenance.log"
        
        # 구성요소 초기화
        self.packet_manager = PacketArchiveManager()
        self.system_monitor = SystemMonitor()
        
        # 로깅 설정
        self._setup_logging()
        
        # 유지보수 통계
        self.maintenance_stats = {
            'last_daily': None,
            'last_weekly': None,
            'total_runs': 0,
            'total_space_saved_mb': 0,
            'total_files_cleaned': 0
        }
        
        self._load_stats()
    
    def _setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_stats(self):
        """통계 로드"""
        stats_file = self.python_root / "maintenance_stats.json"
        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    self.maintenance_stats.update(json.load(f))
        except Exception as e:
            self.logger.error(f"통계 로드 실패: {e}")
    
    def _save_stats(self):
        """통계 저장"""
        stats_file = self.python_root / "maintenance_stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.maintenance_stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"통계 저장 실패: {e}")
    
    def cleanup_temp_files(self) -> Dict:
        """임시 파일 정리"""
        cleaned_files = []
        total_size = 0
        
        temp_patterns = [
            "*.tmp", "*.temp", "*~", "*.bak",
            "*.log.*", "*.old", "__pycache__"
        ]
        
        try:
            # Python 디렉토리 임시 파일
            for pattern in temp_patterns:
                for file_path in self.python_root.rglob(pattern):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_files.append(str(file_path))
                        total_size += size
            
            # 시스템 임시 디렉토리
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            for pattern in ["two_very_auto_*", "baccarat_*"]:
                for file_path in temp_dir.glob(pattern):
                    if file_path.is_file() and (datetime.now() - datetime.fromtimestamp(
                        file_path.stat().st_mtime)).days > 1:
                        try:
                            size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_files.append(str(file_path))
                            total_size += size
                        except:
                            continue
        
        except Exception as e:
            self.logger.error(f"임시 파일 정리 오류: {e}")
        
        return {
            'files_cleaned': len(cleaned_files),
            'space_freed_mb': total_size // 1024 // 1024,
            'files': cleaned_files[:10]  # 처음 10개만 기록
        }
    
    def optimize_databases(self) -> Dict:
        """데이터베이스 최적화"""
        results = {
            'databases_optimized': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        # SQLite 데이터베이스 찾기
        db_files = list(self.python_root.rglob("*.db"))
        
        for db_file in db_files:
            try:
                # 최적화 전 크기
                original_size = db_file.stat().st_size
                
                # VACUUM 실행
                with sqlite3.connect(db_file) as conn:
                    conn.execute("VACUUM")
                    conn.execute("ANALYZE")
                
                # 최적화 후 크기
                new_size = db_file.stat().st_size
                space_freed = original_size - new_size
                
                results['databases_optimized'] += 1
                results['space_freed_mb'] += space_freed // 1024 // 1024
                
                self.logger.info(
                    f"DB 최적화: {db_file.name}, "
                    f"크기 변화: {original_size//1024}KB -> {new_size//1024}KB"
                )
                
            except Exception as e:
                error_msg = f"DB 최적화 실패 {db_file.name}: {e}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        return results
    
    def check_disk_space(self) -> Dict:
        """디스크 공간 확인"""
        try:
            disk_usage = psutil.disk_usage(str(self.project_root))
            
            return {
                'total_gb': disk_usage.total // 1024**3,
                'used_gb': disk_usage.used // 1024**3,
                'free_gb': disk_usage.free // 1024**3,
                'used_percent': (disk_usage.used / disk_usage.total) * 100,
                'status': 'warning' if disk_usage.used / disk_usage.total > 0.9 else 'ok'
            }
        except Exception as e:
            self.logger.error(f"디스크 공간 확인 실패: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def rotate_logs(self, max_age_days: int = 30) -> Dict:
        """로그 파일 로테이션"""
        rotated_logs = []
        total_size = 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            # 로그 파일 찾기
            log_patterns = ["*.log", "*.log.*"]
            for pattern in log_patterns:
                for log_file in self.python_root.rglob(pattern):
                    if (log_file.is_file() and 
                        datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_date):
                        
                        size = log_file.stat().st_size
                        
                        # 압축 또는 삭제
                        if size > 1024 * 1024:  # 1MB 이상은 압축
                            import gzip
                            compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                            with open(log_file, 'rb') as f_in:
                                with gzip.open(compressed_file, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            log_file.unlink()
                            rotated_logs.append(f"압축: {log_file.name}")
                        else:
                            log_file.unlink()
                            rotated_logs.append(f"삭제: {log_file.name}")
                        
                        total_size += size
            
        except Exception as e:
            self.logger.error(f"로그 로테이션 오류: {e}")
        
        return {
            'logs_rotated': len(rotated_logs),
            'space_freed_mb': total_size // 1024 // 1024,
            'actions': rotated_logs
        }
    
    def health_check(self) -> Dict:
        """시스템 건강 상태 점검"""
        health = {
            'status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # 메모리 사용률
            memory = psutil.virtual_memory()
            health['checks']['memory_percent'] = memory.percent
            if memory.percent > 90:
                health['warnings'].append(f"높은 메모리 사용률: {memory.percent:.1f}%")
            
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            health['checks']['cpu_percent'] = cpu_percent
            if cpu_percent > 80:
                health['warnings'].append(f"높은 CPU 사용률: {cpu_percent:.1f}%")
            
            # 디스크 공간
            disk_info = self.check_disk_space()
            health['checks']['disk_usage'] = disk_info
            if disk_info.get('used_percent', 0) > 90:
                health['warnings'].append(f"디스크 공간 부족: {disk_info['used_percent']:.1f}%")
            
            # 프로세스 수
            process_count = len(psutil.pids())
            health['checks']['process_count'] = process_count
            if process_count > 300:
                health['warnings'].append(f"프로세스 수 많음: {process_count}개")
            
            # 핵심 파일 존재 확인
            critical_files = [
                self.python_root / "fastapi_app" / "main.py",
                self.python_root / "enhanced_dashboard.html"
            ]
            
            missing_files = []
            for file_path in critical_files:
                if not file_path.exists():
                    missing_files.append(str(file_path))
            
            if missing_files:
                health['errors'].extend(f"핵심 파일 없음: {f}" for f in missing_files)
            
            # 전체 상태 결정
            if health['errors']:
                health['status'] = 'error'
            elif health['warnings']:
                health['status'] = 'warning'
        
        except Exception as e:
            health['status'] = 'error'
            health['errors'].append(f"건강 점검 실패: {e}")
        
        return health
    
    def daily_maintenance(self) -> Dict:
        """일일 유지보수"""
        self.logger.info("일일 유지보수 시작")
        start_time = datetime.now()
        
        results = {
            'timestamp': start_time.isoformat(),
            'type': 'daily',
            'tasks': {}
        }
        
        # 1. 임시 파일 정리
        results['tasks']['temp_cleanup'] = self.cleanup_temp_files()
        
        # 2. 로그 로테이션 (가벼운 버전)
        results['tasks']['log_rotation'] = self.rotate_logs(max_age_days=7)
        
        # 3. 건강 상태 점검
        results['tasks']['health_check'] = self.health_check()
        
        # 4. 패킷 데이터 아카이빙 (dry-run으로 확인만)
        archivable = len(self.packet_manager.get_archivable_directories())
        results['tasks']['archivable_data'] = {
            'directories_ready': archivable,
            'action': 'scan_only'
        }
        
        # 통계 업데이트
        self.maintenance_stats['last_daily'] = start_time.isoformat()
        self.maintenance_stats['total_runs'] += 1
        self.maintenance_stats['total_space_saved_mb'] += (
            results['tasks']['temp_cleanup']['space_freed_mb'] +
            results['tasks']['log_rotation']['space_freed_mb']
        )
        self.maintenance_stats['total_files_cleaned'] += (
            results['tasks']['temp_cleanup']['files_cleaned'] +
            results['tasks']['log_rotation']['logs_rotated']
        )
        self._save_stats()
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        self.logger.info(f"일일 유지보수 완료 ({duration:.1f}초)")
        return results
    
    def weekly_maintenance(self) -> Dict:
        """주간 유지보수"""
        self.logger.info("주간 유지보수 시작")
        start_time = datetime.now()
        
        results = {
            'timestamp': start_time.isoformat(),
            'type': 'weekly',
            'tasks': {}
        }
        
        # 일일 작업 포함
        daily_results = self.daily_maintenance()
        results['tasks'].update(daily_results['tasks'])
        
        # 추가 주간 작업
        
        # 1. 데이터베이스 최적화
        results['tasks']['database_optimization'] = self.optimize_databases()
        
        # 2. 패킷 데이터 아카이빙 (실제 실행)
        results['tasks']['packet_archiving'] = self.packet_manager.archive_old_data()
        
        # 3. 시스템 메트릭 수집
        metrics = self.system_monitor.collect_metrics()
        if metrics:
            results['tasks']['system_metrics'] = {
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'disk_percent': metrics.disk_percent,
                'process_count': metrics.process_count
            }
        
        # 통계 업데이트
        self.maintenance_stats['last_weekly'] = start_time.isoformat()
        self.maintenance_stats['total_space_saved_mb'] += (
            results['tasks']['database_optimization']['space_freed_mb'] +
            results['tasks']['packet_archiving'].get('space_saved', 0) // 1024 // 1024
        )
        self._save_stats()
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        self.logger.info(f"주간 유지보수 완료 ({duration:.1f}초)")
        return results
    
    def start_scheduler(self):
        """스케줄러 시작"""
        # 일일 유지보수: 매일 새벽 3시
        schedule.every().day.at("03:00").do(self.daily_maintenance)
        
        # 주간 유지보수: 매주 일요일 새벽 2시
        schedule.every().sunday.at("02:00").do(self.weekly_maintenance)
        
        self.logger.info("자동 유지보수 스케줄러 시작")
        self.logger.info("  - 일일 유지보수: 매일 03:00")
        self.logger.info("  - 주간 유지보수: 매주 일요일 02:00")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 확인
            except KeyboardInterrupt:
                self.logger.info("스케줄러 중지")
                break
            except Exception as e:
                self.logger.error(f"스케줄러 오류: {e}")
                time.sleep(60)
    
    def get_maintenance_report(self) -> Dict:
        """유지보수 보고서 생성"""
        return {
            'stats': self.maintenance_stats,
            'next_daily': schedule.next_run() if schedule.jobs else None,
            'health_status': self.health_check(),
            'disk_usage': self.check_disk_space()
        }


def main():
    """CLI 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='자동화 유지보수 시스템')
    parser.add_argument('--action', choices=['daily', 'weekly', 'health', 'report', 'schedule'], 
                       default='health', help='실행할 작업')
    
    args = parser.parse_args()
    maintenance = AutomatedMaintenance()
    
    if args.action == 'daily':
        results = maintenance.daily_maintenance()
        print(f"\n일일 유지보수 결과:")
        print(f"  임시 파일 정리: {results['tasks']['temp_cleanup']['files_cleaned']}개")
        print(f"  로그 로테이션: {results['tasks']['log_rotation']['logs_rotated']}개")
        print(f"  건강 상태: {results['tasks']['health_check']['status']}")
        
    elif args.action == 'weekly':
        results = maintenance.weekly_maintenance()
        print(f"\n주간 유지보수 결과:")
        print(f"  데이터베이스 최적화: {results['tasks']['database_optimization']['databases_optimized']}개")
        print(f"  패킷 아카이빙: {len(results['tasks']['packet_archiving']['archived'])}개")
        
    elif args.action == 'health':
        health = maintenance.health_check()
        print(f"\n시스템 건강 상태: {health['status']}")
        if health['warnings']:
            print("경고:")
            for warning in health['warnings']:
                print(f"  - {warning}")
        if health['errors']:
            print("오류:")
            for error in health['errors']:
                print(f"  - {error}")
    
    elif args.action == 'report':
        report = maintenance.get_maintenance_report()
        print(f"\n유지보수 보고서:")
        print(f"  총 실행 횟수: {report['stats']['total_runs']}회")
        print(f"  절약한 공간: {report['stats']['total_space_saved_mb']}MB")
        print(f"  정리한 파일: {report['stats']['total_files_cleaned']}개")
        print(f"  마지막 일일: {report['stats']['last_daily'] or '없음'}")
        print(f"  마지막 주간: {report['stats']['last_weekly'] or '없음'}")
    
    elif args.action == 'schedule':
        maintenance.start_scheduler()


if __name__ == "__main__":
    main()