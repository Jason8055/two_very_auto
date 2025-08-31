#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최종 안전한 서버 시작 스크립트 - Two Very Auto
모든 드라이브 관련 오류 완전 방지 (유니코드 안전)
"""

import os
import sys
import subprocess
import socket
import time
from pathlib import Path

# 오류 방지 모듈 import
from simple_error_prevention import setup_drive_error_prevention, verify_system_integrity

def find_available_port(preferred_ports=None):
    """사용 가능한 포트 찾기"""
    if preferred_ports is None:
        preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000, 8888, 7000]
    
    for port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                print(f"[OK] 포트 {port} 사용 가능")
                return port
        except OSError:
            print(f"[INFO] 포트 {port} 사용 중")
            continue
    
    raise RuntimeError("사용 가능한 포트를 찾을 수 없습니다.")

def check_python_environment():
    """Python 환경 검증"""
    try:
        # Python 버전 확인
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"[OK] Python 버전: {python_version}")
        
        # 필수 모듈 확인
        required_modules = ['fastapi', 'uvicorn', 'sqlite3', 'asyncio']
        for module in required_modules:
            try:
                __import__(module)
                print(f"[OK] 모듈 {module} 사용 가능")
            except ImportError:
                print(f"[ERROR] 모듈 {module} 없음")
                return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Python 환경 검증 실패: {e}")
        return False

def terminate_existing_servers():
    """기존 서버 프로세스 종료"""
    try:
        # Windows에서 Python 프로세스 찾아서 종료
        if os.name == 'nt':
            subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                         capture_output=True, text=True)
        else:
            # Linux/Mac에서는 pkill 사용
            subprocess.run(['pkill', '-f', 'python.*main.py'], 
                         capture_output=True, text=True)
        
        print("[OK] 기존 서버 프로세스 정리 완료")
        time.sleep(2)  # 프로세스 종료 대기
        
    except Exception as e:
        print(f"[WARNING] 기존 서버 정리 중 오류: {e}")

def start_server_safely(port):
    """안전한 서버 시작"""
    try:
        # 서버 시작 명령어 구성
        cmd = [
            sys.executable, '-c',
            f"import uvicorn; from main import app; uvicorn.run(app, host='127.0.0.1', port={port}, access_log=False)"
        ]
        
        print(f"[INFO] 서버 시작 중... (포트: {port})")
        print(f"[INFO] 명령어: python [uvicorn 실행]")
        
        # 서버 프로세스 시작 (오류 출력 억제)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path.cwd()
        )
        
        # 서버 시작 대기 및 확인
        for attempt in range(30):  # 30초 대기
            time.sleep(1)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('127.0.0.1', port))
                    if result == 0:
                        print(f"[SUCCESS] 서버 시작 성공! (포트: {port})")
                        return process, port
            except:
                pass
            
            # 프로세스가 종료되었는지 확인
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"[ERROR] 서버 프로세스 종료됨")
                if stderr:
                    # 중요한 오류만 표시 (드라이브 관련 오류 제외)
                    error_lines = stderr.split('\n')
                    for line in error_lines:
                        if line.strip() and 'B:' not in line and '지정된 드라이브' not in line:
                            print(f"[ERROR] {line}")
                break
            
            if attempt % 5 == 0:
                print(f"[INFO] 대기 중... ({attempt + 1}/30)")
        
        # 시간 초과
        process.terminate()
        raise TimeoutError("서버 시작 시간 초과")
        
    except Exception as e:
        print(f"[ERROR] 서버 시작 실패: {e}")
        raise

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("Two Very Auto - 최종 안전한 서버 시작")
    print("=" * 60)
    
    try:
        # 1. 드라이브 오류 방지 설정
        print("\n[STEP 1] 드라이브 오류 방지 설정")
        setup_drive_error_prevention()
        
        # 2. 시스템 무결성 검증
        print("\n[STEP 2] 시스템 무결성 검증")
        if not verify_system_integrity():
            raise RuntimeError("시스템 무결성 검증 실패")
        
        # 3. Python 환경 검증
        print("\n[STEP 3] Python 환경 검증")
        if not check_python_environment():
            raise RuntimeError("Python 환경 검증 실패")
        
        # 4. 기존 서버 정리
        print("\n[STEP 4] 기존 서버 정리")
        terminate_existing_servers()
        
        # 5. 사용 가능한 포트 찾기
        print("\n[STEP 5] 포트 검색")
        port = find_available_port()
        
        # 6. 서버 시작
        print("\n[STEP 6] 서버 시작")
        process, server_port = start_server_safely(port)
        
        # 7. 성공 메시지 출력
        print(f"""
========================================
           서버 시작 완료!
========================================
메인 페이지:      http://127.0.0.1:{server_port}
페어 대시보드:    http://127.0.0.1:{server_port}/pair-dashboard
API 문서:        http://127.0.0.1:{server_port}/docs
상태 확인:       http://127.0.0.1:{server_port}/health
========================================
모든 드라이브 오류 방지 적용됨
서버 프로세스 ID: {process.pid}
========================================
""")
        
        print("서버를 중지하려면 Ctrl+C를 누르세요...")
        
        # 서버 프로세스 모니터링
        try:
            while True:
                time.sleep(10)
                # 프로세스가 여전히 실행 중인지 확인
                if process.poll() is not None:
                    print("[ERROR] 서버 프로세스가 종료되었습니다.")
                    break
                
                # 서버 응답 확인
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect(('127.0.0.1', server_port))
                        print(f"[OK] [{time.strftime('%H:%M:%S')}] 서버 정상 작동 중")
                except:
                    print(f"[WARNING] [{time.strftime('%H:%M:%S')}] 서버 응답 없음")
        
        except KeyboardInterrupt:
            print("\n\n[INFO] 서버 종료 중...")
            process.terminate()
            process.wait()
            print("[OK] 서버가 안전하게 종료되었습니다.")
    
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        print("상세한 문제 해결을 위해 시스템 관리자에게 문의하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()