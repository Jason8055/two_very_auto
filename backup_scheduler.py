#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자동 백업 스케줄러
일정에 따라 백업 작업을 실행하고 모니터링
"""

import asyncio
import schedule
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading
from concurrent.futures import ThreadPoolExecutor

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 클라우드 백업 모듈
from cloud.backup_manager import get_backup_manager
from cloud.restore_system import get_restore_system

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

class BackupScheduler:
    """자동 백업 스케줄러"""
    
    def __init__(self):
        self.backup_manager = get_backup_manager()
        self.restore_system = get_restore_system()
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 백업 기록
        self.backup_history = []
        self.schedule_config = self.load_schedule_config()
        
        safe_print("📅 백업 스케줄러 초기화 완료")
    
    def load_schedule_config(self) -> Dict[str, Any]:
        """스케줄 설정 로드"""
        config_path = Path("backup_schedule_config.json")
        
        # 기본 설정
        default_config = {
            "enabled": True,
            "schedules": {
                "daily_backup": {
                    "enabled": True,
                    "time": "02:00",
                    "configs": ["local_backup", "aws_primary"],
                    "description": "일일 백업 (로컬 + AWS)"
                },
                "weekly_full_backup": {
                    "enabled": True,
                    "day": "sunday",
                    "time": "01:00", 
                    "configs": ["local_backup", "aws_primary", "gcp_secondary"],
                    "description": "주간 전체 백업 (모든 클라우드)"
                },
                "monthly_archive": {
                    "enabled": False,
                    "day": 1,
                    "time": "00:30",
                    "configs": ["aws_primary", "gcp_secondary", "azure_tertiary"],
                    "description": "월간 아카이브 백업"
                }
            },
            "notifications": {
                "success": True,
                "failure": True,
                "log_file": "backup_scheduler.log"
            },
            "cleanup": {
                "auto_cleanup": True,
                "cleanup_interval_days": 7
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본 설정과 병합
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                safe_print(f"✅ 스케줄 설정 로드: {config_path}")
            else:
                config = default_config
                self.save_schedule_config(config)
                safe_print(f"📝 기본 스케줄 설정 생성: {config_path}")
                
            return config
            
        except Exception as e:
            logger.error(f"스케줄 설정 로드 오류: {e}")
            return default_config
    
    def save_schedule_config(self, config: Dict[str, Any]):
        """스케줄 설정 저장"""
        config_path = Path("backup_schedule_config.json")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            safe_print(f"💾 스케줄 설정 저장: {config_path}")
        except Exception as e:
            logger.error(f"스케줄 설정 저장 오류: {e}")
    
    def setup_schedules(self):
        """백업 스케줄 설정"""
        if not self.schedule_config.get("enabled", True):
            safe_print("⚠️ 백업 스케줄러가 비활성화됨")
            return
        
        schedules = self.schedule_config.get("schedules", {})
        
        # 일일 백업
        daily_config = schedules.get("daily_backup", {})
        if daily_config.get("enabled", True):
            schedule.every().day.at(daily_config.get("time", "02:00")).do(
                self.run_scheduled_backup, 
                "daily_backup", 
                daily_config.get("configs", ["local_backup"])
            )
            safe_print(f"📅 일일 백업 설정: {daily_config.get('time', '02:00')}")
        
        # 주간 전체 백업
        weekly_config = schedules.get("weekly_full_backup", {})
        if weekly_config.get("enabled", True):
            day = weekly_config.get("day", "sunday").lower()
            time_str = weekly_config.get("time", "01:00")
            
            getattr(schedule.every(), day).at(time_str).do(
                self.run_scheduled_backup,
                "weekly_full_backup",
                weekly_config.get("configs", ["local_backup", "aws_primary"])
            )
            safe_print(f"📅 주간 백업 설정: {day} {time_str}")
        
        # 월간 아카이브
        monthly_config = schedules.get("monthly_archive", {})
        if monthly_config.get("enabled", False):
            # 매월 첫 번째 일요일 (간단화)
            schedule.every().sunday.at(monthly_config.get("time", "00:30")).do(
                self.check_and_run_monthly_backup,
                "monthly_archive",
                monthly_config.get("configs", ["aws_primary"])
            )
            safe_print(f"📅 월간 아카이브 설정: 매월 첫 주 일요일 {monthly_config.get('time', '00:30')}")
        
        # 정리 스케줄
        cleanup_config = self.schedule_config.get("cleanup", {})
        if cleanup_config.get("auto_cleanup", True):
            interval = cleanup_config.get("cleanup_interval_days", 7)
            schedule.every(interval).days.do(self.run_cleanup_task)
            safe_print(f"🧹 자동 정리 설정: {interval}일마다")
    
    def run_scheduled_backup(self, backup_type: str, config_names: List[str]):
        """예약된 백업 실행"""
        safe_print(f"🚀 예약된 백업 시작: {backup_type}")
        
        backup_results = []
        start_time = datetime.now()
        
        try:
            for config_name in config_names:
                safe_print(f"📦 백업 실행: {config_name}")
                result = self.backup_manager.backup_database(config_name)
                backup_results.append(result)
                
                if result.success:
                    safe_print(f"✅ {config_name} 백업 성공")
                else:
                    safe_print(f"❌ {config_name} 백업 실패: {result.error_message}")
                
                # 백업 간 대기 (시스템 부하 완화)
                time.sleep(1)
            
            # 결과 기록
            end_time = datetime.now()
            duration = end_time - start_time
            
            backup_record = {
                "timestamp": start_time.isoformat(),
                "backup_type": backup_type,
                "configs": config_names,
                "duration_seconds": duration.total_seconds(),
                "results": [
                    {
                        "config": r.backup_id,
                        "success": r.success,
                        "size_mb": r.size_mb,
                        "error": r.error_message
                    } for r in backup_results
                ],
                "success_count": sum(1 for r in backup_results if r.success),
                "total_count": len(backup_results)
            }
            
            self.backup_history.append(backup_record)
            
            # 성공률 계산
            success_rate = backup_record["success_count"] / backup_record["total_count"] * 100
            
            safe_print(f"📊 백업 완료: {backup_record['success_count']}/{backup_record['total_count']} 성공 ({success_rate:.1f}%)")
            
            # 알림 전송
            self.send_backup_notification(backup_record)
            
            # 백업 기록 저장
            self.save_backup_history()
            
        except Exception as e:
            logger.error(f"예약된 백업 실행 오류: {e}")
            safe_print(f"❌ 백업 실행 중 오류: {e}")
    
    def check_and_run_monthly_backup(self, backup_type: str, config_names: List[str]):
        """월간 백업 확인 및 실행 (매월 첫 번째 일요일만)"""
        today = datetime.now()
        
        # 이번 달 첫 번째 일요일인지 확인
        first_day = today.replace(day=1)
        first_sunday = first_day + timedelta(days=(6 - first_day.weekday()) % 7)
        
        if today.date() == first_sunday.date():
            self.run_scheduled_backup(backup_type, config_names)
        else:
            safe_print("📅 월간 백업: 첫 번째 일요일이 아니므로 건너뜀")
    
    def run_cleanup_task(self):
        """정리 작업 실행"""
        safe_print("🧹 백업 정리 작업 시작")
        
        try:
            total_deleted = 0
            for config_name in self.backup_manager.backup_configs.keys():
                deleted_count = self.backup_manager.cleanup_old_backups(config_name)
                total_deleted += deleted_count
            
            safe_print(f"✅ 정리 완료: {total_deleted}개 오래된 백업 삭제")
            
        except Exception as e:
            logger.error(f"정리 작업 오류: {e}")
            safe_print(f"❌ 정리 작업 오류: {e}")
    
    def send_backup_notification(self, backup_record: Dict[str, Any]):
        """백업 알림 전송"""
        notifications_config = self.schedule_config.get("notifications", {})
        
        if not notifications_config.get("success", True) and backup_record["success_count"] == backup_record["total_count"]:
            return
        
        if not notifications_config.get("failure", True) and backup_record["success_count"] < backup_record["total_count"]:
            return
        
        # 로그 파일에 기록
        log_file = Path(notifications_config.get("log_file", "backup_scheduler.log"))
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "backup_notification",
                    "data": backup_record
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        except Exception as e:
            logger.error(f"알림 로그 기록 오류: {e}")
    
    def save_backup_history(self):
        """백업 기록 저장"""
        history_file = Path("backup_history.json")
        
        try:
            # 최근 100개 기록만 보관
            recent_history = self.backup_history[-100:] if len(self.backup_history) > 100 else self.backup_history
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(recent_history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"백업 기록 저장 오류: {e}")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.is_running:
            safe_print("⚠️ 스케줄러가 이미 실행 중입니다")
            return
        
        self.is_running = True
        self.setup_schedules()
        
        safe_print("🚀 백업 스케줄러 시작")
        safe_print(f"📋 등록된 작업 수: {len(schedule.get_jobs())}")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
                
        except KeyboardInterrupt:
            safe_print("⏹️ 사용자에 의한 중단")
        except Exception as e:
            logger.error(f"스케줄러 실행 오류: {e}")
        finally:
            self.stop_scheduler()
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        schedule.clear()
        safe_print("⏹️ 백업 스케줄러 중지")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """스케줄 상태 정보"""
        jobs = schedule.get_jobs()
        
        return {
            "running": self.is_running,
            "total_jobs": len(jobs),
            "next_run": str(min(jobs, key=lambda x: x.next_run).next_run) if jobs else None,
            "recent_backups": len(self.backup_history),
            "last_backup": self.backup_history[-1]["timestamp"] if self.backup_history else None,
            "config_enabled": self.schedule_config.get("enabled", True),
            "jobs_detail": [
                {
                    "job": str(job.job_func),
                    "next_run": str(job.next_run),
                    "interval": str(job.interval)
                } for job in jobs
            ]
        }

    def run_immediate_backup(self, backup_type: str = "manual", config_names: Optional[List[str]] = None):
        """즉시 백업 실행"""
        if config_names is None:
            config_names = list(self.backup_manager.backup_configs.keys())
        
        safe_print(f"🚀 즉시 백업 실행: {backup_type}")
        self.run_scheduled_backup(backup_type, config_names)
    
    def enable_schedule(self, schedule_name: str):
        """특정 스케줄 활성화"""
        if schedule_name in self.schedule_config.get("schedules", {}):
            self.schedule_config["schedules"][schedule_name]["enabled"] = True
            self.save_schedule_config(self.schedule_config)
            safe_print(f"✅ {schedule_name} 스케줄 활성화")
        else:
            safe_print(f"❌ {schedule_name} 스케줄을 찾을 수 없습니다")
    
    def disable_schedule(self, schedule_name: str):
        """특정 스케줄 비활성화"""
        if schedule_name in self.schedule_config.get("schedules", {}):
            self.schedule_config["schedules"][schedule_name]["enabled"] = False
            self.save_schedule_config(self.schedule_config)
            safe_print(f"⏸️ {schedule_name} 스케줄 비활성화")
        else:
            safe_print(f"❌ {schedule_name} 스케줄을 찾을 수 없습니다")
    
    def update_schedule_time(self, schedule_name: str, new_time: str):
        """스케줄 시간 업데이트"""
        if schedule_name in self.schedule_config.get("schedules", {}):
            self.schedule_config["schedules"][schedule_name]["time"] = new_time
            self.save_schedule_config(self.schedule_config)
            safe_print(f"⏰ {schedule_name} 스케줄 시간 변경: {new_time}")
        else:
            safe_print(f"❌ {schedule_name} 스케줄을 찾을 수 없습니다")
    
    def get_backup_report(self, days: int = 7) -> Dict[str, Any]:
        """백업 보고서 생성"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_backups = [
            backup for backup in self.backup_history 
            if datetime.fromisoformat(backup["timestamp"]) >= cutoff_date
        ]
        
        if not recent_backups:
            return {"period_days": days, "total_backups": 0, "message": "백업 기록이 없습니다."}
        
        total_backups = len(recent_backups)
        successful_backups = sum(1 for b in recent_backups if b["success_count"] == b["total_count"])
        total_size = sum(sum(r.get("size_mb", 0) for r in b["results"]) for b in recent_backups)
        
        backup_types = {}
        for backup in recent_backups:
            backup_type = backup["backup_type"]
            if backup_type not in backup_types:
                backup_types[backup_type] = 0
            backup_types[backup_type] += 1
        
        return {
            "period_days": days,
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "success_rate": (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            "total_size_mb": round(total_size, 2),
            "backup_types": backup_types,
            "average_size_mb": round(total_size / total_backups, 2) if total_backups > 0 else 0,
            "latest_backup": recent_backups[-1]["timestamp"] if recent_backups else None
        }

def run_scheduler_daemon():
    """백그라운드에서 스케줄러 실행"""
    scheduler = BackupScheduler()
    scheduler.start_scheduler()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Two Very Auto 백업 스케줄러")
    parser.add_argument("--start", action="store_true", help="스케줄러 시작")
    parser.add_argument("--status", action="store_true", help="스케줄러 상태 확인")
    parser.add_argument("--run-now", action="store_true", help="즉시 백업 실행")
    parser.add_argument("--report", type=int, metavar="DAYS", help="최근 N일간 백업 보고서")
    parser.add_argument("--enable", metavar="SCHEDULE", help="특정 스케줄 활성화")
    parser.add_argument("--disable", metavar="SCHEDULE", help="특정 스케줄 비활성화")
    parser.add_argument("--update-time", nargs=2, metavar=("SCHEDULE", "TIME"), help="스케줄 시간 업데이트 (예: daily_backup 03:00)")
    
    args = parser.parse_args()
    
    safe_print("=== 백업 스케줄러 ===")
    
    scheduler = BackupScheduler()
    
    if args.start:
        # 스케줄러 시작
        scheduler.start_scheduler()
    elif args.status:
        # 상태 확인
        status = scheduler.get_schedule_status()
        safe_print("📊 스케줄러 상태:")
        safe_print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.run_now:
        # 즉시 백업 실행
        scheduler.run_immediate_backup()
    elif args.report:
        # 백업 보고서
        report = scheduler.get_backup_report(args.report)
        safe_print(f"📊 최근 {args.report}일간 백업 보고서:")
        safe_print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.enable:
        # 스케줄 활성화
        scheduler.enable_schedule(args.enable)
    elif args.disable:
        # 스케줄 비활성화
        scheduler.disable_schedule(args.disable)
    elif args.update_time:
        # 스케줄 시간 업데이트
        schedule_name, new_time = args.update_time
        scheduler.update_schedule_time(schedule_name, new_time)
    else:
        # 기본 상태 표시
        status = scheduler.get_schedule_status()
        safe_print("📊 스케줄러 상태:")
        for key, value in status.items():
            if key != "jobs_detail":
                safe_print(f"  {key}: {value}")
        
        safe_print("\n💡 사용 가능한 명령어:")
        safe_print("  --start         : 스케줄러 시작")
        safe_print("  --status        : 상태 확인")
        safe_print("  --run-now       : 즉시 백업")
        safe_print("  --report 7      : 7일간 보고서")
        safe_print("  --enable daily  : 일일백업 활성화")
        safe_print("  --disable daily : 일일백업 비활성화")