#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
완전한 백업 시스템 설정 도구
모든 구성 요소를 통합하여 원클릭 설정 제공
"""

import os
import json
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

class CompleteBackupSystemSetup:
    """완전한 백업 시스템 설정"""
    
    def __init__(self):
        self.setup_status = {
            "cloud_auth": False,
            "windows_scheduler": False,
            "notifications": False,
            "monitoring": False,
            "ssl_check": False
        }
        
        self.project_dir = Path(__file__).parent
        
        safe_print("🚀 Two Very Auto 완전한 백업 시스템 설정")
    
    def run_complete_setup(self):
        """완전한 설정 실행"""
        safe_print("=" * 60)
        safe_print("🎯 Two Very Auto - 완전한 백업 시스템 설정")
        safe_print("=" * 60)
        safe_print("")
        
        # 1. 환영 메시지 및 개요
        self.show_setup_overview()
        
        # 2. 사전 점검
        self.pre_setup_checks()
        
        # 3. 단계별 설정
        self.setup_cloud_authentication()
        self.setup_notification_system()
        self.setup_windows_scheduler()
        self.setup_monitoring_system()
        self.setup_ssl_monitoring()
        
        # 4. 최종 테스트
        self.run_final_tests()
        
        # 5. 설정 완료 보고서
        self.generate_completion_report()
    
    def show_setup_overview(self):
        """설정 개요 표시"""
        safe_print("📋 설정 단계:")
        safe_print("  1. ☁️ 클라우드 인증 정보 설정 (AWS, GCP, Azure)")
        safe_print("  2. 📢 알림 시스템 설정 (이메일, Slack, Discord)")
        safe_print("  3. ⏰ Windows 작업 스케줄러 통합")
        safe_print("  4. 🔍 통합 모니터링 시스템 활성화")
        safe_print("  5. 🔐 SSL 인증서 모니터링")
        safe_print("  6. ✅ 최종 테스트 및 검증")
        safe_print("")
        
        proceed = input("설정을 시작하시겠습니까? (Y/n): ").strip().lower()
        if proceed == 'n':
            safe_print("설정이 취소되었습니다.")
            return False
        
        return True
    
    def pre_setup_checks(self):
        """사전 점검"""
        safe_print("🔍 사전 점검 실행...")
        
        # Python 버전 확인
        python_version = sys.version_info
        safe_print(f"  🐍 Python 버전: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 필수 라이브러리 확인
        required_packages = ['boto3', 'google-cloud-storage', 'azure-storage-blob', 'schedule', 'aiohttp']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                safe_print(f"  ✅ {package} 설치됨")
            except ImportError:
                safe_print(f"  ❌ {package} 미설치")
                missing_packages.append(package)
        
        if missing_packages:
            safe_print(f"\\n⚠️ 누락된 패키지: {', '.join(missing_packages)}")
            install = input("자동으로 설치하시겠습니까? (Y/n): ").strip().lower()
            if install != 'n':
                self.install_missing_packages(missing_packages)
        
        # 관리자 권한 확인
        admin_check = self.check_admin_privileges()
        if admin_check:
            safe_print("  ✅ 관리자 권한 확인됨")
        else:
            safe_print("  ⚠️ 관리자 권한 없음 (Windows 스케줄러 설정 제한)")
        
        safe_print("✅ 사전 점검 완료\\n")
    
    def check_admin_privileges(self) -> bool:
        """관리자 권한 확인"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def install_missing_packages(self, packages: List[str]):
        """누락된 패키지 설치"""
        safe_print(f"📦 패키지 설치 중: {', '.join(packages)}")
        
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install"
            ] + packages, check=True)
            
            safe_print("✅ 패키지 설치 완료")
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ 패키지 설치 실패: {e}")
    
    def setup_cloud_authentication(self):
        """클라우드 인증 설정"""
        safe_print("=" * 40)
        safe_print("☁️ 1단계: 클라우드 인증 설정")
        safe_print("=" * 40)
        
        try:
            # 클라우드 인증 설정 스크립트 실행
            from cloud_auth_setup import CloudAuthSetup
            
            auth_setup = CloudAuthSetup()
            auth_setup.interactive_setup()
            
            self.setup_status["cloud_auth"] = True
            safe_print("✅ 클라우드 인증 설정 완료\\n")
            
        except Exception as e:
            safe_print(f"❌ 클라우드 인증 설정 실패: {e}")
            safe_print("   수동으로 .env 파일을 설정해주세요.\\n")
    
    def setup_notification_system(self):
        """알림 시스템 설정"""
        safe_print("=" * 40)
        safe_print("📢 2단계: 알림 시스템 설정")
        safe_print("=" * 40)
        
        try:
            from notification_system import NotificationSystem
            
            notification = NotificationSystem()
            notification.create_setup_wizard()
            
            self.setup_status["notifications"] = True
            safe_print("✅ 알림 시스템 설정 완료\\n")
            
        except Exception as e:
            safe_print(f"❌ 알림 시스템 설정 실패: {e}")
            safe_print("   notification_config.json 파일을 수동으로 설정해주세요.\\n")
    
    def setup_windows_scheduler(self):
        """Windows 스케줄러 설정"""
        safe_print("=" * 40)
        safe_print("⏰ 3단계: Windows 작업 스케줄러 설정")
        safe_print("=" * 40)
        
        if not self.check_admin_privileges():
            safe_print("⚠️ 관리자 권한이 없어 자동 설정을 건너뜁니다.")
            safe_print("   setup_windows_scheduler.bat을 관리자 권한으로 실행해주세요.")
            return
        
        try:
            from windows_task_scheduler import WindowsTaskScheduler
            
            scheduler = WindowsTaskScheduler()
            results = scheduler.register_backup_tasks()
            
            success_count = sum(results.values()) if results else 0
            total_count = len(results) if results else 0
            
            if success_count > 0:
                self.setup_status["windows_scheduler"] = True
                safe_print(f"✅ Windows 스케줄러 설정 완료: {success_count}/{total_count} 작업\\n")
            else:
                safe_print("⚠️ Windows 스케줄러 작업 등록 실패")
                safe_print("   수동으로 작업을 등록해주세요.\\n")
                
        except Exception as e:
            safe_print(f"❌ Windows 스케줄러 설정 실패: {e}")
            safe_print("   수동 설정 가이드를 참조해주세요.\\n")
    
    def setup_monitoring_system(self):
        """모니터링 시스템 설정"""
        safe_print("=" * 40)
        safe_print("🔍 4단계: 통합 모니터링 시스템 설정")
        safe_print("=" * 40)
        
        try:
            # 모니터링 설정 파일 생성
            monitoring_config = {
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
            
            with open("monitoring_config.json", 'w', encoding='utf-8') as f:
                json.dump(monitoring_config, f, ensure_ascii=False, indent=2)
            
            safe_print("✅ 모니터링 설정 파일 생성됨")
            
            # 백업 건전성 점검 설정 생성
            health_config = {
                "enabled": True,
                "test_interval_days": 7,
                "max_test_duration_minutes": 30,
                "tests": {
                    "file_integrity": True,
                    "database_structure": True,
                    "data_completeness": True,
                    "restore_functionality": True,
                    "performance_benchmark": True
                },
                "thresholds": {
                    "max_restore_time_minutes": 5,
                    "min_data_records": 100,
                    "max_file_size_diff_percent": 5
                },
                "notifications": {
                    "success": False,
                    "warning": True,
                    "failure": True,
                    "report_email": None
                }
            }
            
            with open("backup_health_config.json", 'w', encoding='utf-8') as f:
                json.dump(health_config, f, ensure_ascii=False, indent=2)
            
            safe_print("✅ 백업 건전성 점검 설정 파일 생성됨")
            
            self.setup_status["monitoring"] = True
            safe_print("✅ 통합 모니터링 시스템 설정 완료\\n")
            
        except Exception as e:
            safe_print(f"❌ 모니터링 시스템 설정 실패: {e}\\n")
    
    def setup_ssl_monitoring(self):
        """SSL 모니터링 설정"""
        safe_print("=" * 40)
        safe_print("🔐 5단계: SSL 인증서 모니터링 설정")
        safe_print("=" * 40)
        
        try:
            from ssl_cert_manager import SSLCertificateManager
            
            ssl_manager = SSLCertificateManager()
            
            # SSL 상태 리포트 생성
            report = ssl_manager.get_certificate_report()
            cert_status = report["certificate_status"]
            
            # 인증서 상태 표시
            files_status = cert_status.get("files_status", {})
            
            safe_print("📋 SSL 인증서 상태:")
            for file_type, status in files_status.items():
                if status["exists"]:
                    safe_print(f"  ✅ {file_type.upper()}: {status['size_kb']}KB")
                else:
                    safe_print(f"  ❌ {file_type.upper()}: 없음")
            
            # 경고 사항 표시
            warnings = cert_status.get("warnings", [])
            if warnings:
                safe_print("\\n⚠️ 경고 사항:")
                for warning in warnings:
                    safe_print(f"  - {warning}")
            
            # SSL 모니터링 설정 생성
            ssl_manager.create_monitoring_config()
            
            self.setup_status["ssl_check"] = True
            safe_print("\\n✅ SSL 인증서 모니터링 설정 완료\\n")
            
        except Exception as e:
            safe_print(f"❌ SSL 모니터링 설정 실패: {e}\\n")
    
    def run_final_tests(self):
        """최종 테스트"""
        safe_print("=" * 40)
        safe_print("🧪 최종 테스트 실행")
        safe_print("=" * 40)
        
        test_results = {}
        
        # 1. 로컬 백업 테스트
        safe_print("1️⃣ 로컬 백업 테스트...")
        try:
            from cloud.backup_manager import get_backup_manager
            
            backup_manager = get_backup_manager()
            result = backup_manager.backup_database("local_backup")
            
            if result.success:
                safe_print(f"   ✅ 성공: {result.size_mb:.1f}MB")
                test_results["local_backup"] = True
            else:
                safe_print(f"   ❌ 실패: {result.error_message}")
                test_results["local_backup"] = False
                
        except Exception as e:
            safe_print(f"   ❌ 오류: {e}")
            test_results["local_backup"] = False
        
        # 2. 복원 시스템 테스트
        safe_print("\\n2️⃣ 복원 시스템 테스트...")
        try:
            from cloud.restore_system import get_restore_system
            
            restore_system = get_restore_system()
            restore_points = restore_system.discover_restore_points()
            
            if restore_points:
                safe_print(f"   ✅ {len(restore_points)}개 복원 지점 발견")
                test_results["restore_system"] = True
            else:
                safe_print("   ⚠️ 복원 가능한 백업 없음")
                test_results["restore_system"] = False
                
        except Exception as e:
            safe_print(f"   ❌ 오류: {e}")
            test_results["restore_system"] = False
        
        # 3. 알림 시스템 테스트
        safe_print("\\n3️⃣ 알림 시스템 테스트...")
        try:
            from notification_system import get_notification_system
            
            notification = get_notification_system()
            
            # 간단한 테스트 알림 (실제 전송하지 않음)
            config = notification.config
            enabled_channels = []
            
            if config.get("email", {}).get("enabled"):
                enabled_channels.append("이메일")
            if config.get("slack", {}).get("enabled"):
                enabled_channels.append("Slack")
            if config.get("discord", {}).get("enabled"):
                enabled_channels.append("Discord")
            
            if enabled_channels:
                safe_print(f"   ✅ 활성화된 채널: {', '.join(enabled_channels)}")
                test_results["notification"] = True
            else:
                safe_print("   ⚠️ 활성화된 알림 채널 없음")
                test_results["notification"] = False
                
        except Exception as e:
            safe_print(f"   ❌ 오류: {e}")
            test_results["notification"] = False
        
        # 4. 스케줄러 테스트
        safe_print("\\n4️⃣ 스케줄러 테스트...")
        try:
            # 백업 스케줄 설정 확인
            if Path("backup_schedule_config.json").exists():
                with open("backup_schedule_config.json", 'r', encoding='utf-8') as f:
                    schedule_config = json.load(f)
                
                enabled_schedules = [
                    name for name, config in schedule_config.get("schedules", {}).items()
                    if config.get("enabled", True)
                ]
                
                if enabled_schedules:
                    safe_print(f"   ✅ 활성화된 스케줄: {', '.join(enabled_schedules)}")
                    test_results["scheduler"] = True
                else:
                    safe_print("   ⚠️ 활성화된 스케줄 없음")
                    test_results["scheduler"] = False
            else:
                safe_print("   ❌ 스케줄 설정 파일 없음")
                test_results["scheduler"] = False
                
        except Exception as e:
            safe_print(f"   ❌ 오류: {e}")
            test_results["scheduler"] = False
        
        self.test_results = test_results
        safe_print("\\n✅ 최종 테스트 완료\\n")
    
    def generate_completion_report(self):
        """설정 완료 보고서 생성"""
        safe_print("=" * 60)
        safe_print("📊 Two Very Auto 백업 시스템 설정 완료 보고서")
        safe_print("=" * 60)
        
        # 설정 상태 요약
        safe_print("\\n🔧 설정 상태:")
        for component, status in self.setup_status.items():
            status_icon = "✅" if status else "❌"
            component_name = {
                "cloud_auth": "클라우드 인증",
                "windows_scheduler": "Windows 스케줄러",
                "notifications": "알림 시스템",
                "monitoring": "모니터링",
                "ssl_check": "SSL 점검"
            }.get(component, component)
            
            safe_print(f"  {status_icon} {component_name}")
        
        # 테스트 결과 요약
        if hasattr(self, 'test_results'):
            safe_print("\\n🧪 테스트 결과:")
            for test, result in self.test_results.items():
                status_icon = "✅" if result else "❌"
                test_name = {
                    "local_backup": "로컬 백업",
                    "restore_system": "복원 시스템",
                    "notification": "알림 시스템",
                    "scheduler": "스케줄러"
                }.get(test, test)
                
                safe_print(f"  {status_icon} {test_name}")
        
        # 다음 단계 안내
        safe_print("\\n📋 다음 단계:")
        safe_print("  1. 클라우드 인증 정보 입력 (.env 파일)")
        safe_print("  2. 알림 채널 설정 (notification_config.json)")
        safe_print("  3. 통합 모니터링 시작:")
        safe_print("     python integrated_monitoring.py --start")
        safe_print("  4. 백업 건전성 점검:")
        safe_print("     python backup_health_checker.py")
        safe_print("  5. 수동 백업 테스트:")
        safe_print("     python test_cloud_backups.py")
        
        # 주요 파일 목록
        safe_print("\\n📁 생성된 주요 파일:")
        important_files = [
            ".env.example",
            "cloud_config.json",
            "backup_schedule_config.json", 
            "notification_config.json",
            "monitoring_config.json",
            "backup_health_config.json",
            "ssl_monitoring_config.json"
        ]
        
        for file_path in important_files:
            if Path(file_path).exists():
                safe_print(f"  ✅ {file_path}")
            else:
                safe_print(f"  ❌ {file_path}")
        
        # 완료 메시지
        setup_success_count = sum(self.setup_status.values())
        setup_total_count = len(self.setup_status)
        
        safe_print("\\n" + "=" * 60)
        if setup_success_count == setup_total_count:
            safe_print("🎉 Two Very Auto 백업 시스템 설정이 완료되었습니다!")
        else:
            safe_print(f"⚠️ 설정이 부분적으로 완료되었습니다: {setup_success_count}/{setup_total_count}")
            safe_print("   누락된 부분을 수동으로 설정해주세요.")
        
        safe_print("=" * 60)
        
        # 설정 보고서 파일 저장
        self.save_setup_report()
    
    def save_setup_report(self):
        """설정 보고서 파일 저장"""
        report = {
            "setup_completed": datetime.now().isoformat(),
            "setup_status": self.setup_status,
            "test_results": getattr(self, 'test_results', {}),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "admin_privileges": self.check_admin_privileges()
        }
        
        with open("setup_completion_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        safe_print("\\n📄 설정 보고서 저장: setup_completion_report.json")

if __name__ == "__main__":
    setup = CompleteBackupSystemSetup()
    
    try:
        if setup.show_setup_overview():
            setup.run_complete_setup()
    except KeyboardInterrupt:
        safe_print("\\n⏹️ 사용자에 의한 설정 중단")
    except Exception as e:
        safe_print(f"\\n❌ 설정 중 오류: {e}")
        import traceback
        traceback.print_exc()