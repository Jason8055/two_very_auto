#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto - 원클릭 설정 스크립트
전체 시스템을 자동으로 설정하는 마법사
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 로컬 모듈
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

class OneClickSetup:
    """원클릭 설정 마법사"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.absolute()
        self.setup_log = []
        self.failed_steps = []
        
        safe_print("🚀 Two Very Auto 원클릭 설정 시작")
        safe_print(f"📁 프로젝트 경로: {self.project_dir}")
    
    def log_step(self, step: str, success: bool, message: str = ""):
        """설정 단계 로그"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "step": step,
            "success": success,
            "message": message
        }
        self.setup_log.append(log_entry)
        
        if not success:
            self.failed_steps.append(step)
        
        status = "✅" if success else "❌"
        safe_print(f"{status} [{timestamp}] {step}: {message}")
    
    def check_python_version(self) -> bool:
        """Python 버전 확인"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            self.log_step("Python 버전 확인", True, f"Python {version.major}.{version.minor} 사용 중")
            return True
        else:
            self.log_step("Python 버전 확인", False, f"Python 3.8 이상 필요 (현재: {version.major}.{version.minor})")
            return False
    
    def install_dependencies(self) -> bool:
        """의존성 패키지 설치"""
        safe_print("📦 의존성 패키지 설치 중...")
        
        # requirements.txt가 있는지 확인
        requirements_file = self.project_dir / "requirements.txt"
        if not requirements_file.exists():
            # 기본 requirements.txt 생성
            requirements = [
                "fastapi>=0.68.0",
                "uvicorn[standard]>=0.15.0",
                "aiohttp>=3.8.0",
                "schedule>=1.1.0",
                "psutil>=5.8.0",
                "requests>=2.25.0",
                "boto3>=1.20.0",
                "google-cloud-storage>=2.0.0",
                "azure-storage-blob>=12.8.0",
                "cryptography>=3.4.8"
            ]
            
            with open(requirements_file, 'w') as f:
                f.write('\n'.join(requirements))
            
            safe_print(f"📝 requirements.txt 생성: {len(requirements)}개 패키지")
        
        try:
            # pip 업그레이드
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         check=True, capture_output=True)
            
            # requirements 설치
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_step("의존성 패키지 설치", True, "모든 패키지 설치 완료")
                return True
            else:
                self.log_step("의존성 패키지 설치", False, f"설치 오류: {result.stderr[:200]}")
                return False
                
        except Exception as e:
            self.log_step("의존성 패키지 설치", False, f"예외 발생: {str(e)}")
            return False
    
    def setup_environment_variables(self) -> bool:
        """환경변수 설정"""
        safe_print("⚙️ 환경변수 설정 중...")
        
        try:
            # .env.example을 .env로 복사 (존재하지 않는 경우)
            env_example = self.project_dir / ".env.example"
            env_file = self.project_dir / ".env"
            
            if env_example.exists() and not env_file.exists():
                import shutil
                shutil.copy(env_example, env_file)
                safe_print("📋 .env.example을 .env로 복사")
            
            # 기본 환경변수 설정
            default_env = {
                "FASTAPI_HOST": "127.0.0.1",
                "FASTAPI_PORT": "8000",
                "LOG_LEVEL": "INFO",
                "BACKUP_ENABLED": "true",
                "SSL_CERT_EXPIRY_ALERT_DAYS": "30"
            }
            
            if env_file.exists():
                # 기존 .env 파일 업데이트
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                
                updated = False
                for key, value in default_env.items():
                    if f"{key}=" not in env_content:
                        env_content += f"\n{key}={value}"
                        updated = True
                
                if updated:
                    with open(env_file, 'w', encoding='utf-8') as f:
                        f.write(env_content)
            else:
                # .env 파일 새로 생성
                with open(env_file, 'w', encoding='utf-8') as f:
                    for key, value in default_env.items():
                        f.write(f"{key}={value}\n")
            
            self.log_step("환경변수 설정", True, f".env 파일 설정 완료")
            return True
            
        except Exception as e:
            self.log_step("환경변수 설정", False, f"설정 오류: {str(e)}")
            return False
    
    def setup_directories(self) -> bool:
        """필요한 디렉토리 생성"""
        safe_print("📁 디렉토리 구조 생성 중...")
        
        directories = [
            "temp_backups",
            "backup_health_reports", 
            "logs",
            "ssl_certificates",
            "webroot",
            "static",
            "templates"
        ]
        
        try:
            for dir_name in directories:
                dir_path = self.project_dir / dir_name
                dir_path.mkdir(exist_ok=True)
            
            self.log_step("디렉토리 구조 생성", True, f"{len(directories)}개 디렉토리 생성")
            return True
            
        except Exception as e:
            self.log_step("디렉토리 구조 생성", False, f"생성 오류: {str(e)}")
            return False
    
    def setup_cloud_auth(self) -> bool:
        """클라우드 인증 설정"""
        safe_print("☁️ 클라우드 인증 자동 설정 중...")
        
        try:
            # cloud_auth_setup.py 자동 모드로 실행
            script_path = self.project_dir / "cloud_auth_setup.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path), "--auto"],
                    capture_output=True, text=True, cwd=str(self.project_dir)
                )
                
                if result.returncode == 0:
                    self.log_step("클라우드 인증 설정", True, "자동 설정 완료")
                    return True
                else:
                    self.log_step("클라우드 인증 설정", False, f"설정 오류: {result.stderr[:200]}")
                    return False
            else:
                self.log_step("클라우드 인증 설정", False, "cloud_auth_setup.py 파일 없음")
                return False
                
        except Exception as e:
            self.log_step("클라우드 인증 설정", False, f"예외 발생: {str(e)}")
            return False
    
    def setup_ssl_certificate(self) -> bool:
        """SSL 인증서 설정"""
        safe_print("🔐 SSL 인증서 자동 설정 중...")
        
        try:
            # 자체 서명 인증서 생성 (개발용)
            script_path = self.project_dir / "ssl_auto_setup.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path), "--generate-self", "localhost"],
                    capture_output=True, text=True, cwd=str(self.project_dir)
                )
                
                if result.returncode == 0:
                    self.log_step("SSL 인증서 설정", True, "localhost 자체 서명 인증서 생성")
                    return True
                else:
                    self.log_step("SSL 인증서 설정", False, f"생성 오류: {result.stderr[:200]}")
                    return False
            else:
                self.log_step("SSL 인증서 설정", False, "ssl_auto_setup.py 파일 없음")
                return False
                
        except Exception as e:
            self.log_step("SSL 인증서 설정", False, f"예외 발생: {str(e)}")
            return False
    
    def setup_backup_scheduler(self) -> bool:
        """백업 스케줄러 설정"""
        safe_print("📅 백업 스케줄러 설정 중...")
        
        try:
            # backup_schedule_config.json 확인 및 생성
            config_file = self.project_dir / "backup_schedule_config.json"
            if not config_file.exists():
                # 기본 스케줄 설정
                default_schedule = {
                    "enabled": True,
                    "schedules": {
                        "daily_backup": {
                            "enabled": True,
                            "time": "02:00",
                            "configs": ["local_backup"],
                            "description": "일일 로컬 백업"
                        }
                    },
                    "notifications": {
                        "success": True,
                        "failure": True,
                        "log_file": "backup_scheduler.log"
                    }
                }
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_schedule, f, ensure_ascii=False, indent=2)
            
            self.log_step("백업 스케줄러 설정", True, "스케줄 설정 파일 생성")
            return True
            
        except Exception as e:
            self.log_step("백업 스케줄러 설정", False, f"설정 오류: {str(e)}")
            return False
    
    def setup_notification_system(self) -> bool:
        """알림 시스템 설정"""
        safe_print("📢 알림 시스템 설정 중...")
        
        try:
            # notification_config.json 확인 및 생성
            config_file = self.project_dir / "notification_config.json"
            if not config_file.exists():
                # 기본 알림 설정
                default_notification = {
                    "enabled": True,
                    "email": {
                        "enabled": False,
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "sender_email": "",
                        "sender_password": "",
                        "recipients": [],
                        "use_tls": True
                    },
                    "slack": {
                        "enabled": False,
                        "webhook_url": "",
                        "channel": "#backups",
                        "username": "Two Very Auto",
                        "icon_emoji": "🎰"
                    },
                    "notification_levels": {
                        "success": ["slack"],
                        "warning": ["email", "slack"],
                        "error": ["email", "slack"],
                        "critical": ["email", "slack"]
                    }
                }
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_notification, f, ensure_ascii=False, indent=2)
            
            self.log_step("알림 시스템 설정", True, "알림 설정 파일 생성")
            return True
            
        except Exception as e:
            self.log_step("알림 시스템 설정", False, f"설정 오류: {str(e)}")
            return False
    
    def test_system_components(self) -> bool:
        """시스템 구성요소 테스트"""
        safe_print("🧪 시스템 구성요소 테스트 중...")
        
        test_results = []
        
        # 1. 백업 시스템 테스트
        try:
            script_path = self.project_dir / "backup_scheduler.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path), "--status"],
                    capture_output=True, text=True, cwd=str(self.project_dir), timeout=30
                )
                test_results.append(("백업 스케줄러", result.returncode == 0))
            else:
                test_results.append(("백업 스케줄러", False))
        except Exception:
            test_results.append(("백업 스케줄러", False))
        
        # 2. 알림 시스템 테스트
        try:
            script_path = self.project_dir / "notification_system.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path), "--validate"],
                    capture_output=True, text=True, cwd=str(self.project_dir), timeout=30
                )
                test_results.append(("알림 시스템", result.returncode == 0))
            else:
                test_results.append(("알림 시스템", False))
        except Exception:
            test_results.append(("알림 시스템", False))
        
        # 3. SSL 인증서 테스트
        try:
            script_path = self.project_dir / "ssl_auto_setup.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path), "--status"],
                    capture_output=True, text=True, cwd=str(self.project_dir), timeout=30
                )
                test_results.append(("SSL 인증서", result.returncode == 0))
            else:
                test_results.append(("SSL 인증서", False))
        except Exception:
            test_results.append(("SSL 인증서", False))
        
        # 결과 평가
        successful_tests = sum(1 for _, success in test_results if success)
        total_tests = len(test_results)
        
        for test_name, success in test_results:
            status = "✅" if success else "❌"
            safe_print(f"  {status} {test_name}")
        
        if successful_tests >= total_tests * 0.7:  # 70% 이상 성공
            self.log_step("시스템 구성요소 테스트", True, f"{successful_tests}/{total_tests} 테스트 통과")
            return True
        else:
            self.log_step("시스템 구성요소 테스트", False, f"너무 많은 테스트 실패: {successful_tests}/{total_tests}")
            return False
    
    def create_startup_scripts(self) -> bool:
        """시작 스크립트 생성"""
        safe_print("🚀 시작 스크립트 생성 중...")
        
        try:
            # Windows 배치 파일
            batch_script = f'''@echo off
title Two Very Auto - Backup System
echo 🎰 Two Very Auto 백업 시스템 시작
echo.

cd /d "{self.project_dir}"

echo 📊 대시보드 서버 시작...
start "Dashboard" cmd /c "python dashboard_server.py"

timeout /t 3

echo 📅 백업 스케줄러 시작...
start "Scheduler" cmd /c "python backup_scheduler.py --start"

timeout /t 2

echo ✅ 모든 서비스가 시작되었습니다!
echo.
echo 📊 대시보드: http://localhost:8888
echo 📋 모니터링: python backup_monitoring.py
echo.
pause
'''
            
            batch_file = self.project_dir / "start_system.bat"
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_script)
            
            # Python 시작 스크립트
            python_script = f'''#!/usr/bin/env python3
"""
Two Very Auto 시스템 시작 스크립트
"""
import subprocess
import sys
import time
from pathlib import Path

def start_system():
    project_dir = Path(__file__).parent
    
    print("🎰 Two Very Auto 백업 시스템 시작")
    print(f"📁 프로젝트 경로: {{project_dir}}")
    print()
    
    # 대시보드 서버 시작
    print("📊 대시보드 서버 시작...")
    dashboard_process = subprocess.Popen(
        [sys.executable, "dashboard_server.py"],
        cwd=str(project_dir)
    )
    
    time.sleep(3)
    
    # 모니터링 시작
    print("🔍 모니터링 시스템 시작...")
    monitoring_process = subprocess.Popen(
        [sys.executable, "integrated_monitoring.py", "--start"],
        cwd=str(project_dir)
    )
    
    print("✅ 시스템 시작 완료!")
    print()
    print("📊 대시보드: http://localhost:8888")
    print("📋 상태 확인: python backup_monitoring.py")
    print()
    print("서비스를 중지하려면 Ctrl+C를 누르세요.")
    
    try:
        dashboard_process.wait()
    except KeyboardInterrupt:
        print("\\n⏹️ 시스템 종료 중...")
        dashboard_process.terminate()
        monitoring_process.terminate()

if __name__ == "__main__":
    start_system()
'''
            
            python_file = self.project_dir / "start_system.py"
            with open(python_file, 'w', encoding='utf-8') as f:
                f.write(python_script)
            
            self.log_step("시작 스크립트 생성", True, "start_system.bat, start_system.py 생성")
            return True
            
        except Exception as e:
            self.log_step("시작 스크립트 생성", False, f"생성 오류: {str(e)}")
            return False
    
    def create_setup_summary(self) -> str:
        """설정 요약 보고서 생성"""
        safe_print("📋 설정 요약 보고서 생성 중...")
        
        successful_steps = len([log for log in self.setup_log if log["success"]])
        total_steps = len(self.setup_log)
        success_rate = (successful_steps / total_steps * 100) if total_steps > 0 else 0
        
        summary = f"""# Two Very Auto - 원클릭 설정 완료 보고서

## 설정 요약
- **설정 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **성공률**: {success_rate:.1f}% ({successful_steps}/{total_steps})
- **실패한 단계**: {len(self.failed_steps)}개

## 설정 결과

### ✅ 성공한 단계
"""
        
        for log in self.setup_log:
            if log["success"]:
                summary += f"- {log['step']}: {log['message']}\n"
        
        if self.failed_steps:
            summary += f"\n### ❌ 실패한 단계\n"
            for log in self.setup_log:
                if not log["success"]:
                    summary += f"- {log['step']}: {log['message']}\n"
        
        summary += f"""

## 다음 단계

### 시스템 시작
```bash
# Windows 배치 파일로 시작
start_system.bat

# 또는 Python 스크립트로 시작
python start_system.py
```

### 개별 구성요소 실행
```bash
# 대시보드만 실행
python dashboard_server.py

# 백업 스케줄러 실행
python backup_scheduler.py --start

# 시스템 모니터링
python backup_monitoring.py
```

### 클라우드 설정 (선택사항)
```bash
# 클라우드 인증 설정
python cloud_auth_setup.py

# 알림 채널 설정
python notification_system.py --setup

# SSL 인증서 설정
python ssl_auto_setup.py --setup
```

## 웹 인터페이스
- **메인 대시보드**: http://localhost:8888
- **백업 상태**: http://localhost:8888/backup-status
- **시스템 상태**: http://localhost:8888/system-status

## 설정 파일
- `.env`: 환경변수 설정
- `backup_schedule_config.json`: 백업 스케줄
- `notification_config.json`: 알림 설정
- `ssl_config.json`: SSL 인증서 설정

## 문제 해결
"""
        
        if self.failed_steps:
            summary += "실패한 단계들을 수동으로 다시 실행해보세요:\n\n"
            for failed_step in self.failed_steps:
                if "의존성 패키지" in failed_step:
                    summary += "- 의존성 문제: `pip install -r requirements.txt`\n"
                elif "클라우드 인증" in failed_step:
                    summary += "- 클라우드 설정: `python cloud_auth_setup.py --setup`\n"
                elif "SSL" in failed_step:
                    summary += "- SSL 인증서: `python ssl_auto_setup.py --setup`\n"
        
        summary += """
## 지원 및 문서
- 상세 문서: `DEPLOYMENT_GUIDE.md`
- 보안 가이드: `SECURITY_OPTIMIZATION.md`
- 완성 보고서: `COMPLETION_SUMMARY.md`

---
🎰 Two Very Auto 백업 시스템 설정 완료!
"""
        
        # 보고서 파일 저장
        report_path = self.project_dir / "SETUP_SUMMARY.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        self.log_step("설정 요약 보고서", True, f"보고서 생성: {report_path}")
        return str(report_path)
    
    def run_complete_setup(self):
        """전체 설정 실행"""
        safe_print("🎰 Two Very Auto 원클릭 설정 시작!")
        safe_print("=" * 50)
        
        start_time = time.time()
        
        # 설정 단계들 실행
        setup_steps = [
            ("Python 버전 확인", self.check_python_version),
            ("디렉토리 구조 생성", self.setup_directories),
            ("환경변수 설정", self.setup_environment_variables),
            ("의존성 패키지 설치", self.install_dependencies),
            ("클라우드 인증 설정", self.setup_cloud_auth),
            ("SSL 인증서 설정", self.setup_ssl_certificate),
            ("백업 스케줄러 설정", self.setup_backup_scheduler),
            ("알림 시스템 설정", self.setup_notification_system),
            ("시스템 구성요소 테스트", self.test_system_components),
            ("시작 스크립트 생성", self.create_startup_scripts)
        ]
        
        for step_name, step_function in setup_steps:
            safe_print(f"\n🔄 {step_name}...")
            try:
                success = step_function()
                if not success and step_name in ["Python 버전 확인"]:
                    # 필수 단계 실패 시 중단
                    safe_print("❌ 필수 단계 실패로 설정을 중단합니다")
                    break
            except Exception as e:
                self.log_step(step_name, False, f"예외 발생: {str(e)}")
        
        # 설정 완료
        end_time = time.time()
        duration = end_time - start_time
        
        safe_print("\n" + "=" * 50)
        safe_print("🎉 원클릭 설정 완료!")
        safe_print(f"⏱️ 소요 시간: {duration:.1f}초")
        
        # 요약 보고서 생성
        report_path = self.create_setup_summary()
        
        successful_steps = len([log for log in self.setup_log if log["success"]])
        total_steps = len(self.setup_log)
        
        safe_print(f"📊 설정 결과: {successful_steps}/{total_steps} 단계 성공")
        safe_print(f"📋 상세 보고서: {report_path}")
        
        if successful_steps >= total_steps * 0.8:  # 80% 이상 성공
            safe_print("\n✅ 시스템이 성공적으로 설정되었습니다!")
            safe_print("다음 명령어로 시스템을 시작할 수 있습니다:")
            safe_print("  python start_system.py")
            safe_print("  또는 start_system.bat")
        else:
            safe_print("\n⚠️ 일부 설정이 실패했습니다. 보고서를 확인하고 수동 설정을 진행하세요.")
        
        return successful_steps >= total_steps * 0.8

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Two Very Auto 원클릭 설정")
    parser.add_argument("--quick", action="store_true", help="빠른 설정 (필수 구성요소만)")
    parser.add_argument("--full", action="store_true", help="전체 설정 (모든 구성요소)")
    parser.add_argument("--test-only", action="store_true", help="테스트만 실행")
    
    args = parser.parse_args()
    
    setup = OneClickSetup()
    
    if args.test_only:
        setup.test_system_components()
    elif args.quick or args.full:
        setup.run_complete_setup()
    else:
        # 대화형 모드
        safe_print("🎰 Two Very Auto 원클릭 설정")
        safe_print("설정 모드를 선택하세요:")
        safe_print("1. 빠른 설정 (필수 구성요소만)")
        safe_print("2. 전체 설정 (모든 구성요소)")
        
        choice = input("선택 (1-2): ").strip()
        
        if choice in ["1", "2"]:
            setup.run_complete_setup()
        else:
            safe_print("설정을 취소했습니다.")