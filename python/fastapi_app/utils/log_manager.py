#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Log Management System
고급 로그 관리 시스템 - 로테이션, 분석, 자동 정리
"""

import logging
import logging.config
import os
import gzip
import shutil
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import threading
import time

class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"  
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogStats:
    """로그 통계"""
    total_lines: int
    by_level: Dict[str, int]
    by_hour: Dict[int, int]
    error_patterns: List[Tuple[str, int]]
    performance_stats: Dict[str, float]
    file_size_mb: float
    date_range: Tuple[datetime, datetime]

class LogManager:
    """로그 매니저"""
    
    def __init__(self, log_dir: str = "../logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 로그 설정 로드
        self._setup_logging()
        
        # 정리 설정
        self.max_age_days = 30
        self.max_size_mb = 1000
        self.compression_age_days = 7
        
        # 분석 패턴
        self.error_patterns = [
            r"Error|ERROR|Exception|EXCEPTION",
            r"Failed|FAILED|Fail|FAIL", 
            r"Timeout|TIMEOUT|timeout",
            r"Connection.*refused|refused.*connection",
            r"Memory.*error|Out of memory",
            r"Database.*error|SQL.*error"
        ]
        
    def _setup_logging(self):
        """로깅 설정"""
        config_file = Path(__file__).parent.parent / "logging.conf"
        
        if config_file.exists():
            logging.config.fileConfig(config_file)
        else:
            # 기본 설정
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(self.log_dir / "app.log")
                ]
            )
    
    def get_log_files(self) -> List[Path]:
        """로그 파일 목록 조회"""
        log_files = []
        for pattern in ["*.log", "*.log.gz"]:
            log_files.extend(self.log_dir.glob(pattern))
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def rotate_logs(self):
        """로그 로테이션"""
        from utils.smart_output import info, success, warning, error
        
        info("로그 로테이션 시작")
        rotated_count = 0
        compressed_count = 0
        
        for log_file in self.get_log_files():
            if log_file.suffix == ".gz":
                continue
                
            # 파일 크기 확인
            size_mb = log_file.stat().st_size / (1024 * 1024)
            age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
            
            # 크기가 크거나 오래된 파일 로테이션
            if size_mb > self.max_size_mb or age_days > self.compression_age_days:
                try:
                    # 압축
                    compressed_file = log_file.with_suffix(f".log.{datetime.now().strftime('%Y%m%d')}.gz")
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # 원본 파일 삭제
                    log_file.unlink()
                    
                    compressed_count += 1
                    info(f"로그 압축 완료", 파일=log_file.name, 크기=f"{size_mb:.1f}MB")
                    
                except Exception as e:
                    error(f"로그 압축 실패", 파일=log_file.name, 오류=str(e))
            
            rotated_count += 1
        
        success("로그 로테이션 완료", 처리파일수=rotated_count, 압축파일수=compressed_count)
    
    def cleanup_old_logs(self):
        """오래된 로그 정리"""
        from utils.smart_output import info, success, warning
        
        info("오래된 로그 정리 시작")
        deleted_count = 0
        freed_mb = 0.0
        
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        
        for log_file in self.get_log_files():
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_time < cutoff_date:
                try:
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    log_file.unlink()
                    
                    deleted_count += 1
                    freed_mb += size_mb
                    
                    info(f"오래된 로그 삭제", 파일=log_file.name, 나이=f"{(datetime.now() - file_time).days}일")
                    
                except Exception as e:
                    warning(f"로그 삭제 실패", 파일=log_file.name, 오류=str(e))
        
        success("로그 정리 완료", 삭제파일수=deleted_count, 확보용량=f"{freed_mb:.1f}MB")
    
    def analyze_log_file(self, log_file: Path) -> LogStats:
        """로그 파일 분석"""
        stats = LogStats(
            total_lines=0,
            by_level={},
            by_hour={},
            error_patterns=[],
            performance_stats={},
            file_size_mb=0.0,
            date_range=(datetime.now(), datetime.now())
        )
        
        if not log_file.exists():
            return stats
        
        stats.file_size_mb = log_file.stat().st_size / (1024 * 1024)
        
        # 파일 읽기 (압축 파일 지원)
        if log_file.suffix == '.gz':
            file_opener = gzip.open
            mode = 'rt'
        else:
            file_opener = open
            mode = 'r'
        
        try:
            with file_opener(log_file, mode, encoding='utf-8') as f:
                first_date = None
                last_date = None
                
                for line_num, line in enumerate(f, 1):
                    stats.total_lines += 1
                    
                    # 날짜 추출
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if date_match:
                        try:
                            line_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M:%S')
                            if first_date is None:
                                first_date = line_date
                            last_date = line_date
                            
                            # 시간대별 통계
                            hour = line_date.hour
                            stats.by_hour[hour] = stats.by_hour.get(hour, 0) + 1
                            
                        except ValueError:
                            pass
                    
                    # 레벨별 통계
                    for level in LogLevel:
                        if level.value in line:
                            stats.by_level[level.value] = stats.by_level.get(level.value, 0) + 1
                            break
                    
                    # 에러 패턴 분석
                    for pattern in self.error_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            found = False
                            for i, (existing_pattern, count) in enumerate(stats.error_patterns):
                                if existing_pattern == pattern:
                                    stats.error_patterns[i] = (pattern, count + 1)
                                    found = True
                                    break
                            if not found:
                                stats.error_patterns.append((pattern, 1))
                
                # 날짜 범위 설정
                if first_date and last_date:
                    stats.date_range = (first_date, last_date)
                
        except Exception as e:
            print(f"로그 분석 오류: {e}")
        
        # 에러 패턴 정렬 (빈도순)
        stats.error_patterns.sort(key=lambda x: x[1], reverse=True)
        
        return stats
    
    def generate_daily_report(self, date: datetime = None) -> Dict[str, Any]:
        """일별 로그 리포트 생성"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        report = {
            "date": date_str,
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": [],
            "summary": {
                "total_lines": 0,
                "total_errors": 0,
                "total_warnings": 0,
                "performance_issues": 0
            },
            "top_errors": [],
            "hourly_activity": {}
        }
        
        # 해당 날짜의 로그 파일들 분석
        for log_file in self.get_log_files():
            if date_str in log_file.name or log_file.stat().st_mtime >= date.timestamp():
                stats = self.analyze_log_file(log_file)
                
                report["files_analyzed"].append({
                    "file": log_file.name,
                    "size_mb": stats.file_size_mb,
                    "lines": stats.total_lines,
                    "errors": stats.by_level.get("ERROR", 0),
                    "warnings": stats.by_level.get("WARNING", 0)
                })
                
                # 요약 통계 업데이트
                report["summary"]["total_lines"] += stats.total_lines
                report["summary"]["total_errors"] += stats.by_level.get("ERROR", 0)
                report["summary"]["total_warnings"] += stats.by_level.get("WARNING", 0)
                
                # 에러 패턴 통합
                for pattern, count in stats.error_patterns:
                    found = False
                    for existing in report["top_errors"]:
                        if existing["pattern"] == pattern:
                            existing["count"] += count
                            found = True
                            break
                    if not found:
                        report["top_errors"].append({"pattern": pattern, "count": count})
                
                # 시간대별 활동 통합
                for hour, count in stats.by_hour.items():
                    report["hourly_activity"][hour] = report["hourly_activity"].get(hour, 0) + count
        
        # 에러 패턴 정렬
        report["top_errors"].sort(key=lambda x: x["count"], reverse=True)
        report["top_errors"] = report["top_errors"][:10]  # 상위 10개만
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """리포트 저장"""
        if filename is None:
            filename = f"daily_report_{report['date']}.json"
        
        report_file = self.log_dir / "reports" / filename
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_file

class LogMaintenanceScheduler:
    """로그 유지보수 스케줄러"""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
    def start_scheduler(self, rotation_interval: int = 3600, cleanup_interval: int = 86400):
        """스케줄러 시작"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(rotation_interval, cleanup_interval)
        )
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        from utils.smart_output import success
        success("로그 유지보수 스케줄러 시작", 
                로테이션간격=f"{rotation_interval//60}분",
                정리간격=f"{cleanup_interval//3600}시간")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5.0)
        
        from utils.smart_output import info
        info("로그 유지보수 스케줄러 중지")
    
    def _scheduler_loop(self, rotation_interval: int, cleanup_interval: int):
        """스케줄러 루프"""
        last_rotation = time.time()
        last_cleanup = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # 로테이션 체크
                if current_time - last_rotation >= rotation_interval:
                    self.log_manager.rotate_logs()
                    last_rotation = current_time
                
                # 정리 체크  
                if current_time - last_cleanup >= cleanup_interval:
                    self.log_manager.cleanup_old_logs()
                    
                    # 일일 리포트 생성
                    report = self.log_manager.generate_daily_report()
                    self.log_manager.save_report(report)
                    
                    last_cleanup = current_time
                
                time.sleep(60)  # 1분마다 체크
                
            except Exception as e:
                from utils.smart_output import error
                error("로그 유지보수 오류", 오류=str(e))
                time.sleep(300)  # 오류 시 5분 대기

# 전역 로그 매니저 인스턴스
_global_log_manager: Optional[LogManager] = None
_global_scheduler: Optional[LogMaintenanceScheduler] = None

def get_log_manager() -> LogManager:
    """전역 로그 매니저 가져오기"""
    global _global_log_manager
    if _global_log_manager is None:
        _global_log_manager = LogManager()
    return _global_log_manager

def start_log_maintenance():
    """로그 유지보수 시작"""
    global _global_scheduler
    if _global_scheduler is None:
        log_manager = get_log_manager()
        _global_scheduler = LogMaintenanceScheduler(log_manager)
        _global_scheduler.start_scheduler()
    return _global_scheduler

if __name__ == "__main__":
    # 테스트 코드
    print("Log Manager 테스트")
    
    log_manager = LogManager("./test_logs")
    
    # 테스트 로그 생성
    logger = logging.getLogger("test_logger")
    logger.info("테스트 정보 메시지")
    logger.warning("테스트 경고 메시지")
    logger.error("테스트 오류 메시지")
    
    # 분석 테스트
    log_files = log_manager.get_log_files()
    for log_file in log_files[:3]:  # 최근 3개 파일만
        stats = log_manager.analyze_log_file(log_file)
        print(f"\n{log_file.name} 분석 결과:")
        print(f"  총 라인: {stats.total_lines}")
        print(f"  레벨별: {stats.by_level}")
        print(f"  크기: {stats.file_size_mb:.1f}MB")
    
    # 일일 리포트 생성
    report = log_manager.generate_daily_report()
    print(f"\n일일 리포트:")
    print(f"  총 라인: {report['summary']['total_lines']}")
    print(f"  총 오류: {report['summary']['total_errors']}")
    print(f"  분석 파일: {len(report['files_analyzed'])}")
    
    print("\n테스트 완료")