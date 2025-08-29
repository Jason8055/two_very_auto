#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합 모니터링 시스템
백업, SSL, 시스템 상태를 종합적으로 모니터링하고 알림 전송
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

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 모니터링 모듈들
from cloud.secure_config_manager import get_secure_config_manager
from notification_system import get_notification_system
from backup_health_checker import BackupHealthChecker

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

class IntegratedMonitoringSystem:
    """통합 모니터링 시스템"""
    
    def __init__(self):
        self.secure_config = get_secure_config_manager()
        self.notification = get_notification_system()
        self.health_checker = BackupHealthChecker()
        
        self.monitoring_config = self.load_monitoring_config()
        self.last_notifications = {}
        self.is_running = False
        
        safe_print("🔍 통합 모니터링 시스템 초기화")
    
    def load_monitoring_config(self) -> Dict[str, Any]:
        """모니터링 설정 로드"""
        config_path = Path("monitoring_config.json")
        
        default_config = {
            "enabled": True,
            "check_intervals": {
                "backup_health": "daily",
                "ssl_certificate": "daily",
                "disk_space": "hourly",
                "system_status": "hourly"
            },
            "thresholds": {
                "disk_space_warning_percent": 80,
                "disk_space_critical_percent": 90,
                "ssl_expiry_warning_days": 30,
                "ssl_expiry_critical_days": 7,
                "backup_age_warning_hours": 25,
                "backup_age_critical_hours": 48
            },
            "notification_cooldown_minutes": 60,
            "auto_actions": {
                "backup_on_warning": True,
                "cleanup_on_disk_full": True,
                "ssl_reminder": True
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값과 병합
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
            else:
                config = default_config
                self.save_monitoring_config(config)
                
            return config
        except Exception as e:
            logger.error(f"모니터링 설정 로드 오류: {e}")
            return default_config
    
    def save_monitoring_config(self, config: Dict[str, Any]):
        """모니터링 설정 저장"""
        config_path = Path("monitoring_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"모니터링 설정 저장 오류: {e}")
    
    def setup_monitoring_schedules(self):
        """모니터링 스케줄 설정"""
        intervals = self.monitoring_config.get("check_intervals", {})
        
        # 백업 건전성 점검
        if intervals.get("backup_health") == "daily":
            schedule.every().day.at("03:00").do(self.run_backup_health_check)
        elif intervals.get("backup_health") == "weekly":
            schedule.every().sunday.at("03:00").do(self.run_backup_health_check)
        
        # SSL 인증서 점검
        if intervals.get("ssl_certificate") == "daily":
            schedule.every().day.at("04:00").do(self.run_ssl_check)
        
        # 디스크 공간 점검
        if intervals.get("disk_space") == "hourly":
            schedule.every().hour.do(self.run_disk_space_check)
        
        # 시스템 상태 점검
        if intervals.get("system_status") == "hourly":
            schedule.every().hour.do(self.run_system_status_check)
        
        safe_print(f"📅 모니터링 스케줄 설정 완료: {len(schedule.get_jobs())}개 작업")
    
    def run_backup_health_check(self):
        """백업 건전성 점검 실행"""
        safe_print("🏥 백업 건전성 점검 시작")
        
        try:
            # 비동기 함수를 동기적으로 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            health_report = loop.run_until_complete(
                self.health_checker.run_comprehensive_health_check()
            )
            
            loop.close()
            
            # 결과에 따른 알림 전송
            self.process_backup_health_results(health_report)
            
        except Exception as e:
            logger.error(f"백업 건전성 점검 오류: {e}")
            
            # 오류 알림 전송
            asyncio.run(self.notification.send_notification(
                level="error",
                title="백업 건전성 점검 오류",
                message=f"백업 점검 중 오류가 발생했습니다: {str(e)}",
                details={"오류_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            ))
    
    def process_backup_health_results(self, health_report: Dict[str, Any]):
        """백업 건전성 결과 처리"""
        overall_status = health_report.get("overall_status", "unknown")
        
        # 알림 레벨 결정
        if overall_status == "critical":
            level = "critical"
            title = "🚨 백업 시스템 위험 상태"
            message = "백업 시스템에 심각한 문제가 발견되었습니다. 즉시 확인이 필요합니다."
        elif overall_status == "warning":
            level = "warning" 
            title = "⚠️ 백업 시스템 경고"
            message = "백업 시스템에 주의가 필요한 상황이 발견되었습니다."
        elif overall_status in ["healthy", "good"]:
            level = "success"
            title = "✅ 백업 시스템 정상"
            message = "백업 시스템이 정상적으로 작동하고 있습니다."
        else:
            level = "warning"
            title = "❓ 백업 상태 불명"
            message = "백업 시스템 상태를 확인할 수 없습니다."
        
        # 상세 정보 구성
        details = {
            "점검_시간": health_report.get("timestamp", "알 수 없음"),
            "테스트_수": len(health_report.get("test_results", {})),
            "경고_수": len(health_report.get("warnings", [])),
            "오류_수": len(health_report.get("errors", []))
        }
        
        # 쿨다운 체크 후 알림 전송
        if self.should_send_notification("backup_health", level):
            asyncio.run(self.notification.send_notification(
                level=level,
                title=title,
                message=message,
                details=details
            ))
            
            self.update_last_notification("backup_health", level)
    
    def run_ssl_check(self):
        """SSL 인증서 점검 실행"""
        safe_print("🔐 SSL 인증서 점검 시작")
        
        try:
            security_report = self.secure_config.get_security_report()
            ssl_status = security_report.get("ssl_certificate", {})
            
            if not ssl_status.get("exists", False):
                # SSL 인증서 없음
                asyncio.run(self.notification.send_notification(
                    level="warning",
                    title="SSL 인증서 없음",
                    message="SSL 인증서 파일이 발견되지 않았습니다.",
                    details={"확인_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                ))
                return
            
            days_until_expiry = ssl_status.get("days_until_expiry")
            if days_until_expiry is not None:
                warning_days = self.monitoring_config["thresholds"]["ssl_expiry_warning_days"]
                critical_days = self.monitoring_config["thresholds"]["ssl_expiry_critical_days"]
                
                if days_until_expiry <= critical_days:
                    level = "critical"
                    title = "🚨 SSL 인증서 만료 임박"
                    message = f"SSL 인증서가 {days_until_expiry}일 후 만료됩니다. 즉시 갱신하세요!"
                elif days_until_expiry <= warning_days:
                    level = "warning"
                    title = "⚠️ SSL 인증서 만료 예정"
                    message = f"SSL 인증서가 {days_until_expiry}일 후 만료됩니다. 갱신을 준비하세요."
                else:
                    # 정상 상태 - 알림 불필요
                    return
                
                if self.should_send_notification("ssl_certificate", level):
                    asyncio.run(self.notification.send_notification(
                        level=level,
                        title=title,
                        message=message,
                        details={
                            "남은_일수": f"{days_until_expiry}일",
                            "만료_예정일": ssl_status.get("expiry_date", "알 수 없음"),
                            "확인_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    ))
                    
                    self.update_last_notification("ssl_certificate", level)
            
        except Exception as e:
            logger.error(f"SSL 점검 오류: {e}")
    
    def run_disk_space_check(self):
        """디스크 공간 점검 실행"""
        try:
            import shutil
            
            # 현재 디스크 사용량 확인
            total, used, free = shutil.disk_usage(Path.cwd())
            
            used_percent = (used / total) * 100
            free_gb = free / (1024 ** 3)
            
            warning_percent = self.monitoring_config["thresholds"]["disk_space_warning_percent"]
            critical_percent = self.monitoring_config["thresholds"]["disk_space_critical_percent"]
            
            if used_percent >= critical_percent:
                level = "critical"
                title = "🚨 디스크 공간 부족"
                message = f"디스크 사용량이 {used_percent:.1f}%에 도달했습니다. 즉시 정리가 필요합니다."
            elif used_percent >= warning_percent:
                level = "warning"
                title = "⚠️ 디스크 공간 경고"
                message = f"디스크 사용량이 {used_percent:.1f}%입니다. 공간 정리를 권장합니다."
            else:
                return  # 정상 상태
            
            if self.should_send_notification("disk_space", level):
                asyncio.run(self.notification.send_notification(
                    level=level,
                    title=title,
                    message=message,
                    details={
                        "사용률": f"{used_percent:.1f}%",
                        "남은_공간": f"{free_gb:.1f}GB",
                        "확인_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                ))
                
                self.update_last_notification("disk_space", level)
                
                # 자동 정리 작업
                if self.monitoring_config["auto_actions"].get("cleanup_on_disk_full") and used_percent >= critical_percent:
                    self.trigger_cleanup_tasks()
        
        except Exception as e:
            logger.error(f"디스크 공간 점검 오류: {e}")
    
    def run_system_status_check(self):
        """시스템 상태 점검 실행"""
        try:
            # 백업 파일들의 최신 상태 확인
            from cloud.restore_system import get_restore_system
            restore_system = get_restore_system()
            
            restore_points = restore_system.discover_restore_points()
            
            if not restore_points:
                if self.should_send_notification("system_status", "warning"):
                    asyncio.run(self.notification.send_notification(
                        level="warning",
                        title="백업 파일 없음",
                        message="복원 가능한 백업 파일이 발견되지 않았습니다.",
                        details={"확인_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    ))
                    
                    self.update_last_notification("system_status", "warning")
                return
            
            # 최신 백업의 나이 확인
            latest_backup = restore_points[0]
            backup_age_hours = (datetime.now() - latest_backup.timestamp).total_seconds() / 3600
            
            warning_hours = self.monitoring_config["thresholds"]["backup_age_warning_hours"]
            critical_hours = self.monitoring_config["thresholds"]["backup_age_critical_hours"]
            
            if backup_age_hours >= critical_hours:
                level = "critical"
                title = "🚨 백업 파일 너무 오래됨"
                message = f"최신 백업이 {backup_age_hours:.1f}시간 전 파일입니다. 새 백업이 필요합니다."
            elif backup_age_hours >= warning_hours:
                level = "warning"
                title = "⚠️ 백업 파일 업데이트 필요"
                message = f"최신 백업이 {backup_age_hours:.1f}시간 전 파일입니다."
            else:
                return  # 정상 상태
            
            if self.should_send_notification("backup_age", level):
                asyncio.run(self.notification.send_notification(
                    level=level,
                    title=title,
                    message=message,
                    details={
                        "최신_백업": latest_backup.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "경과_시간": f"{backup_age_hours:.1f}시간",
                        "백업_개수": len(restore_points)
                    }
                ))
                
                self.update_last_notification("backup_age", level)
                
                # 자동 백업 트리거
                if self.monitoring_config["auto_actions"].get("backup_on_warning"):
                    self.trigger_backup()
        
        except Exception as e:
            logger.error(f"시스템 상태 점검 오류: {e}")
    
    def should_send_notification(self, check_type: str, level: str) -> bool:
        """알림 전송 여부 확인 (쿨다운)"""
        cooldown_minutes = self.monitoring_config.get("notification_cooldown_minutes", 60)
        
        last_notification_key = f"{check_type}_{level}"
        last_time = self.last_notifications.get(last_notification_key)
        
        if not last_time:
            return True
        
        elapsed_minutes = (datetime.now() - last_time).total_seconds() / 60
        return elapsed_minutes >= cooldown_minutes
    
    def update_last_notification(self, check_type: str, level: str):
        """마지막 알림 시간 업데이트"""
        last_notification_key = f"{check_type}_{level}"
        self.last_notifications[last_notification_key] = datetime.now()
    
    def trigger_cleanup_tasks(self):
        """정리 작업 트리거"""
        safe_print("🧹 자동 정리 작업 시작")
        
        try:
            from cloud.backup_manager import get_backup_manager
            backup_manager = get_backup_manager()
            
            # 오래된 백업 정리
            for config_name in backup_manager.backup_configs:
                deleted_count = backup_manager.cleanup_old_backups(config_name)
                safe_print(f"  {config_name}: {deleted_count}개 파일 정리")
            
        except Exception as e:
            logger.error(f"정리 작업 오류: {e}")
    
    def trigger_backup(self):
        """자동 백업 트리거"""
        safe_print("💾 자동 백업 트리거")
        
        try:
            from cloud.backup_manager import get_backup_manager
            backup_manager = get_backup_manager()
            
            # 로컬 백업만 수행 (빠른 백업)
            result = backup_manager.backup_database("local_backup")
            
            if result.success:
                safe_print(f"✅ 자동 백업 성공: {result.size_mb:.1f}MB")
            else:
                safe_print(f"❌ 자동 백업 실패: {result.error_message}")
        
        except Exception as e:
            logger.error(f"자동 백업 오류: {e}")
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_running:
            safe_print("⚠️ 모니터링이 이미 실행 중입니다")
            return
        
        if not self.monitoring_config.get("enabled", True):
            safe_print("⚠️ 모니터링이 비활성화되어 있습니다")
            return
        
        self.is_running = True
        self.setup_monitoring_schedules()
        
        safe_print("🚀 통합 모니터링 시작")
        safe_print(f"📋 등록된 점검 작업: {len(schedule.get_jobs())}개")
        
        # 시작 알림
        asyncio.run(self.notification.send_notification(
            level="success",
            title="통합 모니터링 시작",
            message="Two Very Auto 통합 모니터링 시스템이 시작되었습니다.",
            details={
                "시작_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "점검_작업": len(schedule.get_jobs())
            }
        ))
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            safe_print("⏹️ 사용자에 의한 중단")
        except Exception as e:
            logger.error(f"모니터링 실행 오류: {e}")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        schedule.clear()
        safe_print("⏹️ 통합 모니터링 중지")

def run_monitoring_daemon():
    """백그라운드 모니터링 실행"""
    monitoring = IntegratedMonitoringSystem()
    monitoring.start_monitoring()

if __name__ == "__main__":
    safe_print("=== 통합 모니터링 시스템 ===")
    
    monitoring = IntegratedMonitoringSystem()
    
    # 즉시 점검 실행 옵션
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--health-check":
            monitoring.run_backup_health_check()
        elif sys.argv[1] == "--ssl-check":
            monitoring.run_ssl_check()
        elif sys.argv[1] == "--disk-check":
            monitoring.run_disk_space_check()
        elif sys.argv[1] == "--system-check":
            monitoring.run_system_status_check()
        elif sys.argv[1] == "--start":
            monitoring.start_monitoring()
    else:
        safe_print("사용법:")
        safe_print("  python integrated_monitoring.py --health-check  # 백업 건전성 점검")
        safe_print("  python integrated_monitoring.py --ssl-check     # SSL 인증서 점검")
        safe_print("  python integrated_monitoring.py --disk-check    # 디스크 공간 점검")
        safe_print("  python integrated_monitoring.py --system-check  # 시스템 상태 점검")
        safe_print("  python integrated_monitoring.py --start         # 모니터링 시작")
        safe_print("")
        safe_print("모니터링을 시작하려면 --start 옵션을 사용하세요.")