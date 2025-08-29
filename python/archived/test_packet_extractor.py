#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패킷 데이터 추출기 테스트 스크립트
"""

import sys
import os

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi_app'))

from routers.packet_data import PacketDataExtractor
from pathlib import Path

def test_packet_extraction():
    """패킷 데이터 추출 테스트"""
    extractor = PacketDataExtractor()
    packet_folder = Path("F:/two very auto 25.08.23/packet")
    
    if not packet_folder.exists():
        print(f"❌ 패킷 폴더를 찾을 수 없습니다: {packet_folder}")
        return
    
    print(f"📂 패킷 폴더: {packet_folder}")
    
    # 처음 몇 개 파일만 테스트
    txt_files = list(packet_folder.rglob("*.txt"))[:3]
    
    print(f"🔍 테스트할 파일 수: {len(txt_files)}")
    
    total_games = 0
    
    for file_path in txt_files:
        print(f"\n📄 파일: {file_path.name}")
        
        try:
            file_data = extractor.parse_packet_file(file_path)
            print(f"  ✅ 추출된 게임 수: {len(file_data)}")
            
            if file_data:
                # 첫 번째 게임 데이터 출력
                first_game = file_data[0]
                print(f"  📊 샘플 데이터:")
                print(f"    - 방명: {first_game['방명']}")
                print(f"    - 날짜: {first_game['날짜']}")
                print(f"    - 승패: {first_game['승패']}")
                print(f"    - Player점수: {first_game['Player점수']}")
                print(f"    - Banker점수: {first_game['Banker점수']}")
                print(f"    - Player페어: {first_game['Player페어']}")
                print(f"    - Banker페어: {first_game['Banker페어']}")
            
            total_games += len(file_data)
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    
    print(f"\n🎯 총 추출된 게임 수: {total_games}")
    
    # 방명 목록 테스트
    rooms = set()
    dates = set()
    
    for file_path in txt_files:
        room_name = extractor.extract_room_name(file_path.name)
        date = extractor.extract_date_from_path(file_path)
        rooms.add(room_name)
        dates.add(date)
    
    print(f"\n📍 발견된 방명: {sorted(list(rooms))}")
    print(f"📅 발견된 날짜: {sorted(list(dates))}")

if __name__ == "__main__":
    print("🧪 패킷 데이터 추출기 테스트 시작")
    print("=" * 50)
    
    test_packet_extraction()
    
    print("\n" + "=" * 50)
    print("✅ 테스트 완료!")