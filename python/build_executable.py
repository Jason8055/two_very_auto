#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.2 - 실행파일 빌드 스크립트
PyInstaller를 사용하여 two_very_auto.exe 파일 생성
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_executable():
    """실행파일 빌드"""
    
    print("=" * 60)
    print("Two Very Auto v3.2 - 실행파일 빌드")
    print("=" * 60)
    
    # 현재 디렉토리 확인
    base_dir = Path(__file__).parent.absolute()
    os.chdir(base_dir)
    
    print(f"작업 디렉토리: {base_dir}")
    
    # PyInstaller 설치 확인
    try:
        import PyInstaller
        print(f"PyInstaller 버전: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller가 설치되어 있지 않습니다.")
        print("다음 명령어로 설치하세요:")
        print("pip install pyinstaller")
        return False
    
    # 빌드할 파일들
    main_script = "two_very_auto_launcher.py"
    exe_name = "two_very_auto"
    
    # 포함할 데이터 파일들
    data_files = [
        "web_server.py",
        "packet_decoder.py", 
        "pair_tracker.py",
        "pattern_analyzer.py",
        "notification_system.py",
        "chart_dashboard.py",
        "database_manager.py",
        "modern_dashboard.html",
        "modern_design_system.css",
        "modern_components.css",
        "modern_sidebar.css",
        "modern_charts.css",
        "modern_charts.js",
        "modern_notifications.js",
        "mobile_responsive.css",
        "pwa_manifest.json",
        "pwa_service_worker.js",
        "pwa_offline.html"
    ]
    
    # 존재하는 파일들만 필터링
    existing_files = []
    for file in data_files:
        if (base_dir / file).exists():
            existing_files.append(file)
            print(f"✓ {file}")
        else:
            print(f"⚠ {file} (파일 없음)")
    
    # PyInstaller 명령어 구성
    cmd = [
        "pyinstaller",
        "--onefile",                    # 단일 실행파일
        "--noconsole",                  # 콘솔 창 숨기기 (필요시 제거)
        "--name", exe_name,             # 실행파일 이름
        "--icon=icon.ico",              # 아이콘 (있는 경우)
        "--add-data", "*.py;.",         # Python 파일들 포함
        "--add-data", "*.html;.",       # HTML 파일들 포함
        "--add-data", "*.css;.",        # CSS 파일들 포함
        "--add-data", "*.js;.",         # JavaScript 파일들 포함
        "--add-data", "*.json;.",       # JSON 파일들 포함
        "--hidden-import", "flask",
        "--hidden-import", "flask_cors",
        "--hidden-import", "sqlite3",
        "--hidden-import", "json",
        "--hidden-import", "threading",
        "--hidden-import", "webbrowser",
        "--hidden-import", "http.server",
        "--hidden-import", "socketserver",
        main_script
    ]
    
    # Windows에서 경로 구분자 조정
    if sys.platform == 'win32':
        cmd = [arg.replace(';', ';') for arg in cmd]
    
    print("\n빌드 시작...")
    print(f"명령어: {' '.join(cmd)}")
    
    try:
        # PyInstaller 실행
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("빌드 성공!")
        
        # 결과 파일 확인
        dist_dir = base_dir / "dist"
        exe_file = dist_dir / f"{exe_name}.exe"
        
        if exe_file.exists():
            file_size = exe_file.stat().st_size / (1024 * 1024)  # MB
            print(f"\n생성된 파일: {exe_file}")
            print(f"파일 크기: {file_size:.1f} MB")
            
            # 실행파일을 메인 디렉토리로 복사
            target_file = base_dir / f"{exe_name}.exe"
            shutil.copy2(exe_file, target_file)
            print(f"복사 완료: {target_file}")
            
        else:
            print("⚠ 실행파일이 생성되지 않았습니다.")
            return False
        
        print("\n빌드 완료!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"빌드 실패: {e}")
        print(f"오류 출력: {e.stderr}")
        return False
    except Exception as e:
        print(f"빌드 중 오류: {e}")
        return False

def create_batch_file():
    """배치 파일 생성 (대안 실행 방법)"""
    batch_content = """@echo off
title Two Very Auto v3.2 - 통합 런처
cd /d "%~dp0"

echo ========================================
echo Two Very Auto v3.2 - 통합 런처
echo ========================================
echo.

REM Python 가상환경 활성화 (있는 경우)
if exist "venv\\Scripts\\activate.bat" (
    echo 가상환경 활성화 중...
    call venv\\Scripts\\activate.bat
)

REM Python 스크립트 실행
echo 런처 시작 중...
python two_very_auto_launcher.py

echo.
echo 런처가 종료되었습니다.
pause
"""
    
    batch_file = Path(__file__).parent / "two_very_auto.bat"
    
    try:
        with open(batch_file, 'w', encoding='cp949') as f:
            f.write(batch_content)
        print(f"배치 파일 생성 완료: {batch_file}")
        return True
    except Exception as e:
        print(f"배치 파일 생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("Two Very Auto v3.2 실행파일 빌드 도구\n")
    
    choice = input("빌드 방법을 선택하세요:\n1. PyInstaller로 EXE 파일 생성\n2. 배치 파일 생성 (간단함)\n선택 (1-2): ").strip()
    
    if choice == '1':
        success = build_executable()
        if success:
            print("\n✅ EXE 파일이 성공적으로 생성되었습니다!")
            print("📁 two_very_auto.exe 파일을 실행하세요.")
        else:
            print("\n❌ EXE 파일 생성에 실패했습니다.")
            print("🔄 배치 파일 생성을 시도해보세요.")
    
    elif choice == '2':
        success = create_batch_file()
        if success:
            print("\n✅ 배치 파일이 성공적으로 생성되었습니다!")
            print("📁 two_very_auto.bat 파일을 실행하세요.")
        else:
            print("\n❌ 배치 파일 생성에 실패했습니다.")
    
    else:
        print("잘못된 선택입니다.")
    
    input("\n엔터 키를 눌러 종료하세요...")

if __name__ == '__main__':
    main()