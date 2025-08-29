#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카드 정보 추출 테스트 스크립트
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

def test_card_extraction():
    """카드 정보 추출 테스트"""
    extractor = PacketDataExtractor()
    file_path = Path("F:/two very auto 25.08.23/packet/20250809/바카라 A_08.txt")
    
    if not file_path.exists():
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return
    
    print(f"📄 파일: {file_path.name}")
    
    try:
        file_data = extractor.parse_packet_file(file_path)
        print(f"✅ 추출된 게임 수: {len(file_data)}")
        
        if file_data:
            print(f"\n🎰 처음 5개 게임의 카드 정보:")
            for i, game in enumerate(file_data[:5]):
                print(f"\n  게임 {i+1}:")
                print(f"    방명: {game['방명']}")
                print(f"    승패: {game['승패']}")
                print(f"    Player점수: {game['Player점수']}")
                print(f"    Banker점수: {game['Banker점수']}")
                print(f"    Player페어: {game['Player페어']}")
                print(f"    Banker페어: {game['Banker페어']}")
                print(f"    내추럴: {game['내추럴']}")
                print(f"    카드정보: {game['카드정보']}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    print("🃏 카드 정보 추출 테스트 시작")
    print("=" * 50)
    
    test_card_extraction()
    
    print("\n" + "=" * 50)
    print("✅ 테스트 완료!")