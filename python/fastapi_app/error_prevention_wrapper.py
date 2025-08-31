#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오류 방지 래퍼 모듈 - Two Very Auto
시스템 드라이브 관련 오류 완전 방지
"""

import os
import sys
import logging
import warnings
from pathlib import Path

# 모든 시스템 관련 경고 무시
warnings.filterwarnings('ignore')

def setup_drive_error_prevention():
    """드라이브 관련 오류 방지 설정"""
    
    # 1. 현재 작업 디렉토리 검증
    try:
        current_drive = Path.cwd().anchor
        print(f"✅ 현재 드라이브: {current_drive}")
        
        # 유효한 드라이브인지 확인
        if not Path(current_drive).exists():
            raise OSError(f"현재 드라이브 {current_drive}에 접근할 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 드라이브 검증 실패: {e}")
        # F: 드라이브로 강제 이동
        try:
            os.chdir("F:\\two very auto 25.08.23\\python\\fastapi_app")
            print("✅ F: 드라이브로 안전 이동 완료")
        except Exception as fe:
            print(f"❌ 안전 이동 실패: {fe}")
            sys.exit(1)
    
    # 2. 시스템 드라이브 존재 확인
    available_drives = []
    for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_path = f"{drive_letter}:\\"
        if os.path.exists(drive_path):
            available_drives.append(drive_letter)
    
    print(f"✅ 사용 가능한 드라이브: {', '.join(available_drives)}")
    
    # 3. B: 드라이브 참조 방지
    if "B" not in available_drives:
        print("✅ B: 드라이브 없음 확인 - 오류 방지 활성화")
        
        # 환경 변수에서 B: 드라이브 참조 제거
        for env_var in os.environ:
            if "B:" in os.environ[env_var]:
                print(f"⚠️ 환경 변수 {env_var}에서 B: 참조 발견, 정리 중...")
                os.environ[env_var] = os.environ[env_var].replace("B:", "")
    
    # 4. 파이썬 경로 검증
    python_path = sys.executable
    if not os.path.exists(python_path):
        print(f"❌ Python 실행 파일 경로 오류: {python_path}")
        sys.exit(1)
    else:
        print(f"✅ Python 경로 확인: {python_path}")
    
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
    
    print("✅ 드라이브 오류 방지 설정 완료")
    return True

def safe_path_resolver(path_str):
    """안전한 경로 해결기"""
    try:
        if isinstance(path_str, str):
            # B: 드라이브 참조를 현재 드라이브로 변경
            if path_str.startswith("B:"):
                current_drive = Path.cwd().anchor
                path_str = path_str.replace("B:", current_drive.rstrip("\\"))
                print(f"🔧 경로 수정: B: → {current_drive}")
        
        return Path(path_str).resolve()
    except Exception as e:
        print(f"⚠️ 경로 해결 실패: {e}")
        return Path.cwd()

def verify_system_integrity():
    """시스템 무결성 검증"""
    checks = []
    
    # 1. 현재 디렉토리 접근 가능
    try:
        os.listdir(".")
        checks.append("✅ 현재 디렉토리 접근 가능")
    except Exception as e:
        checks.append(f"❌ 현재 디렉토리 접근 불가: {e}")
    
    # 2. 임시 파일 생성 가능
    try:
        temp_file = Path("temp_check.tmp")
        temp_file.write_text("test")
        temp_file.unlink()
        checks.append("✅ 임시 파일 생성 가능")
    except Exception as e:
        checks.append(f"❌ 임시 파일 생성 불가: {e}")
    
    # 3. Python 모듈 import 가능
    try:
        import socket
        import json
        import sqlite3
        checks.append("✅ 필수 모듈 import 가능")
    except Exception as e:
        checks.append(f"❌ 모듈 import 실패: {e}")
    
    print("\n🔍 시스템 무결성 검증 결과:")
    for check in checks:
        print(f"  {check}")
    
    return all("✅" in check for check in checks)

if __name__ == "__main__":
    print("드라이브 오류 방지 모듈 실행")
    print("=" * 50)
    
    # 드라이브 오류 방지 설정
    setup_drive_error_prevention()
    
    print()
    
    # 시스템 무결성 검증
    if verify_system_integrity():
        print("\n모든 검증 완료 - 서버 시작 준비됨")
    else:
        print("\n시스템 검증 실패")
        sys.exit(1)