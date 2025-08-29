#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 FastAPI 서버 시작 스크립트
Two Very Auto - 페어 정보 시스템
"""

import uvicorn
import sys
import os
import socket
import time
from pathlib import Path

def find_available_port():
    """사용 가능한 포트 찾기"""
    preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000]
    
    for port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                print(f"SUCCESS: 포트 {port} 사용 가능")
                return port
        except OSError:
            print(f"WARNING: 포트 {port} 사용 중")
            continue
    
    return None

def main():
    print("Two Very Auto - FastAPI 서버 시작")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    current_dir = Path.cwd()
    print(f"현재 디렉토리: {current_dir}")
    
    # main.py 파일 확인
    main_py = current_dir / "main.py"
    if not main_py.exists():
        print("ERROR: main.py 파일을 찾을 수 없습니다.")
        print("   fastapi_app 폴더에서 실행해주세요.")
        return False
    
    # 포트 찾기
    port = find_available_port()
    if not port:
        print("ERROR: 사용 가능한 포트를 찾을 수 없습니다.")
        return False
    
    print(f"서버 시작 중... 포트: {port}")
    print(f"접속 URL: http://127.0.0.1:{port}")
    print(f"페어 대시보드: http://127.0.0.1:{port}/pair-dashboard")
    print(f"API 문서: http://127.0.0.1:{port}/docs")
    print("=" * 50)
    print("서버를 중지하려면 Ctrl+C를 누르세요.")
    print("=" * 50)
    
    try:
        # uvicorn으로 서버 시작 - 최소 설정
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=port,
            reload=False,
            access_log=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n서버가 사용자에 의해 중단되었습니다.")
        return True
    except Exception as e:
        print(f"ERROR: 서버 시작 실패: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("SUCCESS: 서버가 정상적으로 종료되었습니다.")
    else:
        print("ERROR: 서버 시작에 실패했습니다.")
        sys.exit(1)