#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two Very Auto - EXE 빌드 스크립트
PyInstaller를 사용하여 EXE 파일 생성
"""

import os
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """필요한 패키지 설치"""
    print("📦 필요한 패키지 설치 중...")
    
    packages = ['pyinstaller', 'fastapi', 'uvicorn']
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} 설치 완료")
        except subprocess.CalledProcessError:
            print(f"❌ {package} 설치 실패")
            return False
    
    return True

def create_icon():
    """간단한 아이콘 생성 (선택사항)"""
    # 실제 프로젝트에서는 .ico 파일을 준비하는 것이 좋습니다
    pass

def build_exe():
    """EXE 파일 빌드"""
    print("\n🔨 EXE 파일 빌드 시작...")
    
    script_path = Path(__file__).parent / "exe_launcher.py"
    output_dir = Path(__file__).parent.parent / "dist"
    
    # PyInstaller 명령어 구성
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',  # 단일 실행 파일
        '--windowed',  # 콘솔 창 숨기기 (GUI만)
        '--name', 'TwoVeryAuto_서버런처',  # EXE 파일 이름
        '--distpath', str(output_dir),  # 출력 디렉토리
        '--workpath', str(Path(__file__).parent / 'build'),  # 임시 디렉토리
        '--specpath', str(Path(__file__).parent),  # spec 파일 위치
        str(script_path)
    ]
    
    # 아이콘이 있는 경우 추가
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        cmd.extend(['--icon', str(icon_path)])
    
    # 추가 데이터 파일들 (필요한 경우)
    # cmd.extend(['--add-data', 'templates;templates'])
    
    try:
        subprocess.check_call(cmd)
        print("✅ EXE 파일 빌드 완료!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ EXE 파일 빌드 실패: {e}")
        return False

def create_simple_exe_wrapper():
    """더 간단한 BAT → EXE 변환 방법"""
    print("\n🔧 간단한 EXE 래퍼 생성 중...")
    
    wrapper_script = Path(__file__).parent / "simple_wrapper.py"
    
    with open(wrapper_script, 'w', encoding='utf-8') as f:
        f.write('''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""간단한 BAT 파일 실행 래퍼"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # EXE 파일 위치 기준으로 BAT 파일 찾기
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent.parent
    
    bat_file = exe_dir / '🚀 서버 시작.bat'
    
    if bat_file.exists():
        subprocess.run([str(bat_file)], shell=True)
    else:
        print(f"BAT 파일을 찾을 수 없습니다: {bat_file}")
        input("계속하려면 Enter를 누르세요...")

if __name__ == "__main__":
    main()
''')
    
    # 간단한 버전 빌드
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--console',  # 콘솔 버전
        '--name', 'TwoVeryAuto_Simple',
        '--distpath', str(Path(__file__).parent.parent / "dist"),
        str(wrapper_script)
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✅ 간단한 EXE 래퍼 생성 완료!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 간단한 EXE 래퍼 생성 실패: {e}")
        return False

def main():
    """메인 빌드 프로세스"""
    print("🎯 Two Very Auto EXE 빌드 스크립트")
    print("=" * 50)
    
    # 1. 패키지 설치
    if not install_requirements():
        print("❌ 패키지 설치에 실패했습니다.")
        return
    
    # 2. 사용자 선택
    print("\n📋 빌드 옵션을 선택하세요:")
    print("1. GUI 버전 EXE (권장)")
    print("2. 간단한 BAT 래퍼 EXE")
    print("3. 둘 다 생성")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    success = False
    
    if choice in ['1', '3']:
        success = build_exe() or success
    
    if choice in ['2', '3']:
        success = create_simple_exe_wrapper() or success
    
    if success:
        dist_dir = Path(__file__).parent.parent / "dist"
        print(f"\n🎉 빌드 완료! EXE 파일 위치: {dist_dir}")
        print("\n📋 생성된 파일:")
        if dist_dir.exists():
            for exe_file in dist_dir.glob("*.exe"):
                print(f"  - {exe_file.name}")
        
        print("\n💡 사용법:")
        print("1. 생성된 EXE 파일을 원하는 위치에 복사")
        print("2. EXE 파일을 더블클릭하여 실행")
        print("3. 필요시 바탕화면에 바로가기 생성")
    else:
        print("\n❌ 빌드에 실패했습니다.")

if __name__ == "__main__":
    main()