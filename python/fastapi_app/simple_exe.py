#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 BAT 파일 실행 EXE
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🎯 Two Very Auto 서버 시작 중...")
    
    # EXE 파일 위치 기준으로 BAT 파일 찾기
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent.parent
    
    bat_file = exe_dir / '🚀 서버 시작.bat'
    
    if bat_file.exists():
        print(f"✅ BAT 파일 발견: {bat_file}")
        print("🚀 서버 시작...")
        subprocess.run([str(bat_file)], shell=True)
    else:
        print(f"❌ BAT 파일을 찾을 수 없습니다: {bat_file}")
        print("")
        print("💡 해결 방법:")
        print("1. EXE 파일을 Two Very Auto 메인 폴더에 위치시키세요")
        print("2. '🚀 서버 시작.bat' 파일이 같은 폴더에 있는지 확인하세요")
        print("")
        input("계속하려면 Enter를 누르세요...")

if __name__ == "__main__":
    main()