#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완벽한 서버 런처 - 모든 연결 문제 해결
Two Very Auto - 페어 정보 시스템
"""

import uvicorn
import sys
import os
import socket
import time
import subprocess
import webbrowser
import threading
import requests
from pathlib import Path
import psutil
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class PerfectServerLauncher:
    def __init__(self):
        self.selected_port = None
        self.server_process = None
        self.monitoring = False
        
    def print_banner(self):
        """배너 출력"""
        print("\n" + "="*60)
        print("🎯 Two Very Auto - 완벽한 페어 시스템 런처")
        print("   모든 연결 문제를 해결하는 스마트 솔루션")
        print("="*60)
    
    def check_admin_rights(self):
        """관리자 권한 확인"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def request_admin_rights(self):
        """관리자 권한 요청"""
        if not self.check_admin_rights():
            print("⚠️  관리자 권한이 필요합니다. 관리자 모드로 재시작합니다...")
            try:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
                sys.exit(0)
            except Exception as e:
                print(f"❌ 관리자 권한 요청 실패: {e}")
                return False
        return True
    
    def kill_existing_processes(self):
        """기존 프로세스 완전 정리"""
        print("\n🔄 1단계: 기존 서버 프로세스 완전 정리")
        print("-" * 40)
        
        killed_count = 0
        
        # Python 프로세스 중 서버로 추정되는 것들 종료
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe':
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(keyword in cmdline.lower() for keyword in 
                          ['uvicorn', 'fastapi', 'main:app', 'two very auto']):
                        print(f"🔍 서버 프로세스 종료: PID {proc.info['pid']}")
                        proc.kill()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 포트 점유 프로세스 확인 및 종료
        for port in [8080, 8000, 3000, 9999]:
            try:
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == 'LISTEN':
                        try:
                            proc = psutil.Process(conn.pid)
                            print(f"🔍 포트 {port} 점유 프로세스 종료: PID {conn.pid}")
                            proc.kill()
                            killed_count += 1
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            except:
                pass
        
        if killed_count > 0:
            print(f"✅ {killed_count}개 프로세스 정리 완료")
            time.sleep(2)  # 프로세스 완전 종료 대기
        else:
            print("✅ 정리할 프로세스 없음")
    
    def setup_firewall(self):
        """방화벽 자동 설정"""
        print("\n🛡️  2단계: 방화벽 자동 설정")
        print("-" * 40)
        
        try:
            # Windows 방화벽 규칙 추가
            commands = [
                'netsh advfirewall firewall delete rule name="Two Very Auto" >nul 2>&1',
                'netsh advfirewall firewall add rule name="Two Very Auto" dir=in action=allow protocol=TCP localport=8080',
                'netsh advfirewall firewall add rule name="Two Very Auto 8000" dir=in action=allow protocol=TCP localport=8000',
                f'netsh advfirewall firewall add rule name="Two Very Auto Python" dir=in action=allow program="{sys.executable}"'
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, capture_output=True)
            
            print("✅ 방화벽 설정 완료")
        except Exception as e:
            print(f"⚠️  방화벽 설정 실패 (계속 진행): {e}")
    
    def find_available_port(self):
        """사용 가능한 포트 찾기"""
        print("\n🔧 3단계: 스마트 포트 선택")
        print("-" * 40)
        
        preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000, 8888, 7000]
        
        for port in preferred_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('0.0.0.0', port))
                    print(f"✅ 포트 {port} 선택됨")
                    self.selected_port = port
                    return port
            except OSError:
                print(f"⚠️  포트 {port} 사용 중")
                continue
        
        print("❌ 사용 가능한 포트를 찾을 수 없습니다")
        return None
    
    def verify_environment(self):
        """환경 검증"""
        print("\n📋 4단계: 환경 검증")
        print("-" * 40)
        
        # 현재 디렉토리 확인
        if not Path("main.py").exists():
            print("❌ main.py를 찾을 수 없습니다.")
            return False
        
        # 필수 패키지 확인
        try:
            import fastapi
            import uvicorn
            print("✅ 필수 패키지 확인 완료")
        except ImportError as e:
            print(f"❌ 필수 패키지 누락: {e}")
            print("  설치 명령: pip install fastapi uvicorn")
            return False
        
        return True
    
    def start_server(self):
        """서버 시작"""
        print(f"\n🚀 5단계: 서버 시작 (포트 {self.selected_port})")
        print("-" * 40)
        
        try:
            # 서버를 별도 스레드에서 시작
            def run_server():
                from main import app
                uvicorn.run(
                    app,
                    host="0.0.0.0",
                    port=self.selected_port,
                    access_log=False,
                    log_level="warning"
                )
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # 서버 시작 대기
            print("서버 시작 대기 중...")
            max_wait = 30
            for i in range(max_wait):
                try:
                    response = requests.get(
                        f"http://127.0.0.1:{self.selected_port}/health",
                        timeout=2
                    )
                    if response.status_code == 200:
                        print("✅ 서버 시작 성공!")
                        return True
                except:
                    pass
                
                print(f"⏳ 대기 중... ({i+1}/{max_wait})")
                time.sleep(1)
            
            print("❌ 서버 시작 실패")
            return False
            
        except Exception as e:
            print(f"❌ 서버 시작 오류: {e}")
            return False
    
    def open_browser(self):
        """브라우저 자동 열기"""
        print("\n🌐 6단계: 브라우저 자동 연결")
        print("-" * 40)
        
        urls = {
            "메인 페이지": f"http://127.0.0.1:{self.selected_port}",
            "페어 대시보드": f"http://127.0.0.1:{self.selected_port}/pair-dashboard",
            "API 문서": f"http://127.0.0.1:{self.selected_port}/docs"
        }
        
        try:
            # 메인 페이지 먼저 열기
            webbrowser.open(urls["메인 페이지"])
            time.sleep(2)
            
            # 페어 대시보드 열기
            webbrowser.open(urls["페어 대시보드"])
            
            print("✅ 브라우저 자동 열기 완료")
            
            # URL 정보 출력
            print("\n" + "="*60)
            print("🎉 시작 완료! 다음 URL에서 확인하세요:")
            for name, url in urls.items():
                print(f"  📱 {name}: {url}")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"⚠️  브라우저 열기 실패: {e}")
            print("수동으로 브라우저에서 다음 주소로 접속하세요:")
            for name, url in urls.items():
                print(f"  {name}: {url}")
            return False
    
    def monitor_server(self):
        """서버 상태 모니터링"""
        print("\n🔄 7단계: 서버 모니터링 시작")
        print("-" * 40)
        print("  - 10초마다 서버 상태 확인")
        print("  - 서버 중단 시 자동 알림")
        print("  - 종료하려면 Ctrl+C 누르기")
        print("-" * 40)
        
        self.monitoring = True
        consecutive_failures = 0
        
        while self.monitoring:
            try:
                time.sleep(10)
                
                # 서버 상태 확인
                response = requests.get(
                    f"http://127.0.0.1:{self.selected_port}/health",
                    timeout=5
                )
                
                if response.status_code == 200:
                    if consecutive_failures > 0:
                        print(f"✅ [{time.strftime('%H:%M:%S')}] 서버 복구됨")
                        consecutive_failures = 0
                    else:
                        print(f"✅ [{time.strftime('%H:%M:%S')}] 서버 정상 작동 중")
                else:
                    consecutive_failures += 1
                    print(f"⚠️  [{time.strftime('%H:%M:%S')}] 서버 응답 이상 (연속 {consecutive_failures}회)")
                    
            except requests.exceptions.RequestException:
                consecutive_failures += 1
                print(f"❌ [{time.strftime('%H:%M:%S')}] 서버 응답 없음 (연속 {consecutive_failures}회)")
                
                if consecutive_failures >= 3:
                    print("🚨 서버가 중단된 것 같습니다!")
                    print("   브라우저를 새로고침하거나 스크립트를 다시 실행하세요.")
                    
            except KeyboardInterrupt:
                print("\n사용자에 의해 모니터링이 중단되었습니다.")
                break
            except Exception as e:
                print(f"⚠️  모니터링 오류: {e}")
    
    def run(self):
        """메인 실행 함수"""
        try:
            self.print_banner()
            
            # 관리자 권한 확인
            if not self.request_admin_rights():
                return False
            
            # 1. 기존 프로세스 정리
            self.kill_existing_processes()
            
            # 2. 방화벽 설정
            self.setup_firewall()
            
            # 3. 포트 선택
            if not self.find_available_port():
                print("❌ 포트 선택 실패")
                return False
            
            # 4. 환경 검증
            if not self.verify_environment():
                print("❌ 환경 검증 실패")
                return False
            
            # 5. 서버 시작
            if not self.start_server():
                print("❌ 서버 시작 실패")
                return False
            
            # 6. 브라우저 열기
            self.open_browser()
            
            # 7. 모니터링 시작
            self.monitor_server()
            
            return True
            
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단되었습니다.")
            return True
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.monitoring = False
            print("\n정리 작업 중...")

def main():
    launcher = PerfectServerLauncher()
    
    # 현재 디렉토리를 fastapi_app으로 변경
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = launcher.run()
    
    if success:
        print("✅ 완벽한 서버 런처 실행 완료")
    else:
        print("❌ 서버 런처 실행 실패")
        input("Enter를 눌러 종료...")

if __name__ == "__main__":
    main()