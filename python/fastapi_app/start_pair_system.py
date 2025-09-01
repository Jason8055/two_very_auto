#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two Very Auto - 페어 정보 시스템 안정적 시작 스크립트
포트 자동 감지, 연결 문제 해결, 사용자 가이드 제공
"""

import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def print_banner():
    """시작 배너 출력"""
    print("=" * 90)
    print("🎯 Two Very Auto - 페어 정보 시스템 시작")
    print("=" * 90)
    print("🎰 실시간 바카라 페어 감지 및 알림 시스템")
    print("📊 패턴 분석 · 🔔 즉시 알림 · 📈 상세 통계")
    print("=" * 90)

def check_port_available(host, port):
    """포트 사용 가능성 확인"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except:
        return False

def find_available_port(host="127.0.0.1", preferred_ports=None):
    """사용 가능한 포트 찾기"""
    if preferred_ports is None:
        preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000, 8081, 8082, 8083, 8084]
    
    print("🔍 사용 가능한 포트 검색 중...")
    
    # 선호 포트들 확인
    for port in preferred_ports:
        if check_port_available(host, port):
            print(f"✅ 포트 {port} 사용 가능 - 선택됨")
            return port
        else:
            print(f"❌ 포트 {port} 사용 중")
    
    # 자동 포트 할당
    print("⚠️ 모든 선호 포트가 사용 중 - 자동 포트 할당")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, 0))
            auto_port = s.getsockname()[1]
            print(f"🎯 자동 할당된 포트: {auto_port}")
            return auto_port
    except Exception as e:
        print(f"❌ 포트 할당 실패: {e}")
        return None

def kill_existing_processes():
    """기존 프로세스 종료"""
    try:
        # Windows에서 포트를 사용하는 프로세스 확인 및 종료
        import psutil
        
        print("🔄 기존 프로세스 정리 중...")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    if proc.info['cmdline'] and any('main.py' in str(arg) for arg in proc.info['cmdline']):
                        print(f"🛑 기존 프로세스 종료: PID {proc.info['pid']}")
                        proc.kill()
                        time.sleep(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        print("✅ 프로세스 정리 완료")
        time.sleep(2)
        
    except ImportError:
        print("📋 psutil 모듈이 설치되지 않아 수동 프로세스 정리를 건너뜁니다.")
    except Exception as e:
        print(f"⚠️ 프로세스 정리 중 오류: {e}")

def start_server():
    """서버 시작"""
    print_banner()
    
    # 현재 디렉토리 확인
    current_dir = Path(__file__).parent
    main_py = current_dir / "main.py"
    
    if not main_py.exists():
        print(f"❌ main.py 파일을 찾을 수 없습니다: {main_py}")
        return False
    
    print(f"📂 작업 디렉토리: {current_dir}")
    print(f"🎯 서버 파일: {main_py}")
    
    # 기존 프로세스 정리
    kill_existing_processes()
    
    # 포트 찾기
    port = find_available_port()
    if port is None:
        print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
        return False
    
    host = "127.0.0.1"
    
    try:
        print("\n🚀 서버 시작 중...")
        print(f"📍 위치: {main_py}")
        print(f"🌐 주소: http://{host}:{port}")
        print("\n⏳ 서버 초기화 중... (잠시 기다려주세요)")
        
        # 서버 시작
        env = os.environ.copy()
        env['PYTHONPATH'] = str(current_dir.parent)
        
        process = subprocess.Popen(
            [sys.executable, str(main_py)],
            cwd=str(current_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 서버 시작 확인
        startup_success = False
        startup_timeout = 30  # 30초 타임아웃
        start_time = time.time()
        
        while time.time() - start_time < startup_timeout:
            # 프로세스가 종료되었는지 확인
            if process.poll() is not None:
                output, _ = process.communicate(timeout=5)
                print(f"❌ 서버 시작 실패:")
                print(output)
                return False
            
            # 포트 연결 테스트
            if check_port_connection(host, port):
                startup_success = True
                break
            
            time.sleep(1)
        
        if startup_success:
            print("\n" + "=" * 90)
            print("✅ 페어 정보 시스템이 성공적으로 시작되었습니다!")
            print("=" * 90)
            print(f"🌐 메인 페이지: http://{host}:{port}")
            print(f"🎯 페어 대시보드: http://{host}:{port}/pair-dashboard")
            print(f"📖 API 문서: http://{host}:{port}/docs")
            print(f"💚 상태 확인: http://{host}:{port}/health")
            print("=" * 90)
            print("🎮 실시간 페어 정보 확인 방법:")
            print(f"   1. 브라우저에서 http://{host}:{port} 접속")
            print(f"   2. 페어 전용 화면: http://{host}:{port}/pair-dashboard")
            print("   3. 실시간 WebSocket 알림 자동 수신")
            print("=" * 90)
            
            # 브라우저 자동 열기
            try:
                print("🌐 브라우저에서 자동으로 열기 중...")
                webbrowser.open(f"http://{host}:{port}")
            except Exception as e:
                print(f"⚠️ 브라우저 자동 열기 실패: {e}")
            
            return True, process
        else:
            print("❌ 서버 시작 타임아웃")
            process.terminate()
            return False
            
    except Exception as e:
        print(f"❌ 서버 시작 중 오류 발생: {e}")
        return False

def check_port_connection(host, port, timeout=1):
    """포트 연결 테스트"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except:
        return False

def main():
    """메인 실행 함수"""
    try:
        result = start_server()
        if isinstance(result, tuple) and result[0]:
            # 서버가 성공적으로 시작됨
            _, process = result
            print("\n🎯 서버가 실행 중입니다. 종료하려면 Ctrl+C를 누르세요.")
            
            try:
                # 서버 프로세스 대기
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 서버가 중단되었습니다.")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            except Exception as e:
                print(f"\n❌ 서버 실행 중 오류: {e}")
                process.terminate()
                
        else:
            print("\n❌ 서버 시작에 실패했습니다.")
            print("\n🔧 문제 해결 방법:")
            print("1. 다른 프로그램이 포트를 사용 중인지 확인")
            print("2. 방화벽 설정 확인")  
            print("3. Python 환경 설정 확인")
            print("4. 관리자 권한으로 실행 시도")
            
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 실행이 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()