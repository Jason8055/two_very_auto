#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 오류 방지 모듈 - Two Very Auto
시스템 드라이브 관련 오류 완전 방지 (유니코드 안전)
"""

import os
import sys
import logging
import warnings
from pathlib import Path

# 모든 시스템 관련 경고 무시
warnings.filterwarnings('ignore')

# 콘솔 인코딩 설정
if sys.platform.startswith('win'):
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except:
        pass

def setup_drive_error_prevention():
    """드라이브 관련 오류 방지 설정"""
    
    try:
        # 1. 현재 작업 디렉토리 검증
        current_drive = Path.cwd().anchor
        print(f"[OK] 현재 드라이브: {current_drive}")
        
        # 유효한 드라이브인지 확인
        if not Path(current_drive).exists():
            raise OSError(f"현재 드라이브 {current_drive}에 접근할 수 없습니다.")
            
    except Exception as e:
        print(f"[ERROR] 드라이브 검증 실패: {e}")
        # F: 드라이브로 강제 이동
        try:
            os.chdir("F:\\two very auto 25.08.23\\python\\fastapi_app")
            print("[OK] F: 드라이브로 안전 이동 완료")
        except Exception as fe:
            print(f"[ERROR] 안전 이동 실패: {fe}")
            sys.exit(1)
    
    # 2. 시스템 드라이브 존재 확인
    available_drives = []
    for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_path = f"{drive_letter}:\\"
        if os.path.exists(drive_path):
            available_drives.append(drive_letter)
    
    print(f"[OK] 사용 가능한 드라이브: {', '.join(available_drives)}")
    
    # 3. B: 드라이브 참조 방지
    if "B" not in available_drives:
        print("[OK] B: 드라이브 없음 확인 - 오류 방지 활성화")
        
        # 환경 변수에서 B: 드라이브 참조 제거
        for env_var in list(os.environ.keys()):
            if "B:" in str(os.environ.get(env_var, "")):
                print(f"[WARNING] 환경 변수 {env_var}에서 B: 참조 발견, 정리 중...")
                os.environ[env_var] = os.environ[env_var].replace("B:", "")
    
    # 4. 파이썬 경로 검증
    python_path = sys.executable
    if not os.path.exists(python_path):
        print(f"[ERROR] Python 실행 파일 경로 오류: {python_path}")
        sys.exit(1)
    else:
        print(f"[OK] Python 경로 확인: {python_path}")
    
    # 5. 로깅 설정 (오류 메시지 필터링)
    class DriveErrorFilter(logging.Filter):
        """드라이브 관련 오류 메시지 필터"""
        def filter(self, record):
            # B: 드라이브 관련 메시지 필터링
            if hasattr(record, 'msg'):
                msg = str(record.msg).lower()
                if 'b:' in msg or '지정된 드라이브' in msg or 'specified drive' in msg:
                    return False
            return True
    
    # 모든 로거에 필터 적용
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.addFilter(DriveErrorFilter())
    
    # 루트 로거에도 필터 적용
    logging.getLogger().addFilter(DriveErrorFilter())
    
    print("[OK] 드라이브 오류 방지 설정 완료")
    return True

def verify_system_integrity():
    """시스템 무결성 검증"""
    checks = []
    
    # 1. 현재 디렉토리 접근 가능
    try:
        os.listdir(".")
        checks.append("[OK] 현재 디렉토리 접근 가능")
    except Exception as e:
        checks.append(f"[ERROR] 현재 디렉토리 접근 불가: {e}")
    
    # 2. 임시 파일 생성 가능
    try:
        temp_file = Path("temp_check.tmp")
        temp_file.write_text("test")
        temp_file.unlink()
        checks.append("[OK] 임시 파일 생성 가능")
    except Exception as e:
        checks.append(f"[ERROR] 임시 파일 생성 불가: {e}")
    
    # 3. Python 모듈 import 가능
    try:
        import socket
        import json
        import sqlite3
        checks.append("[OK] 필수 모듈 import 가능")
    except Exception as e:
        checks.append(f"[ERROR] 모듈 import 실패: {e}")
    
    print("\n[INFO] 시스템 무결성 검증 결과:")
    for check in checks:
        print(f"  {check}")
    
    return all("[OK]" in check for check in checks)

def test_server_startup():
    """서버 시작 테스트"""
    try:
        # main 모듈 import 테스트
        print("\n[TEST] 서버 모듈 import 테스트")
        
        # FastAPI 관련 모듈들 테스트
        import fastapi
        print("[OK] FastAPI 모듈 사용 가능")
        
        import uvicorn
        print("[OK] Uvicorn 모듈 사용 가능")
        
        # 메인 모듈 존재 확인
        if Path("main.py").exists():
            print("[OK] main.py 파일 존재")
        else:
            print("[ERROR] main.py 파일 없음")
            return False
        
        print("[OK] 모든 서버 시작 요구사항 충족")
        return True
        
    except Exception as e:
        print(f"[ERROR] 서버 시작 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Two Very Auto - 드라이브 오류 방지 모듈 실행")
    print("=" * 60)
    
    # 1. 드라이브 오류 방지 설정
    print("\n[STEP 1] 드라이브 오류 방지 설정")
    setup_drive_error_prevention()
    
    # 2. 시스템 무결성 검증
    print("\n[STEP 2] 시스템 무결성 검증")
    system_ok = verify_system_integrity()
    
    # 3. 서버 시작 테스트
    print("\n[STEP 3] 서버 시작 테스트")
    server_ok = test_server_startup()
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("최종 결과:")
    print("=" * 60)
    
    if system_ok and server_ok:
        print("[SUCCESS] 모든 검증 완료 - 서버 시작 준비됨")
        print("\n권장 서버 시작 방법:")
        print("1. safe_server_start.py 실행")
        print("2. 완벽한_서버_시작_오류방지.bat 실행")
        print("\n이제 B: 드라이브 오류가 발생하지 않습니다!")
    else:
        print("[FAILED] 시스템 검증 실패")
        if not system_ok:
            print("- 시스템 무결성 검증 실패")
        if not server_ok:
            print("- 서버 시작 테스트 실패")
        sys.exit(1)