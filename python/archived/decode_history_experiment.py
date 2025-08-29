#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
History 인코딩 디코딩 실험
"""

import sys
import os
import json

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path

def decode_history_experiment():
    """History 디코딩 실험"""
    file_path = Path("F:/two very auto 25.08.23/packet/20250809/바카라 A_08.txt")
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        for line in lines:
            if '] {' in line and 'baccarat.encodedShoeState' in line:
                json_start = line.find('] {') + 2
                json_part = line[json_start:]
                
                data = json.loads(json_part)
                args = data.get('args', {})
                history = args.get('history', '')
                history_v2 = args.get('history_v2', [])
                
                print(f"📊 실험 데이터:")
                print(f"  History: {history}")
                print(f"  길이: {len(history)}")
                print(f"  게임 수: {len(history_v2)}")
                
                # 각 문자의 ASCII/Unicode 값 확인
                print(f"\n🔤 문자별 분석:")
                for i, char in enumerate(history[:20]):  # 처음 20문자만
                    print(f"  {i:2d}: '{char}' (ASCII: {ord(char):3d}, hex: {hex(ord(char))})")
                
                # 게임별로 매핑 시도
                print(f"\n🎰 게임별 매핑 시도:")
                chars_per_game = len(history) // len(history_v2)
                remainder = len(history) % len(history_v2)
                print(f"  게임당 평균 문자 수: {chars_per_game}")
                print(f"  나머지: {remainder}")
                
                # 첫 5게임과 해당 문자들 매핑
                print(f"\n🎮 첫 5게임 분석:")
                for i in range(min(5, len(history_v2))):
                    game = history_v2[i]
                    start_idx = i * 2  # 게임당 2문자 가정
                    end_idx = start_idx + 2
                    
                    if end_idx <= len(history):
                        chars = history[start_idx:end_idx]
                        print(f"  게임 {i+1}: {game}")
                        print(f"    문자들: '{chars}' (ASCII: {[ord(c) for c in chars]})")
                        print(f"    점수: P={game['playerScore']}, B={game['bankerScore']}")
                
                # 바카라 카드 인코딩 추정
                print(f"\n🃏 바카라 카드 인코딩 추정:")
                print(f"  - 바카라는 각 게임당 최소 4장(P2장+B2장), 최대 6장 카드")
                print(f"  - 문자당 게임 비율이 0.5이므로 게임당 2문자")
                print(f"  - 각 문자가 특별한 의미를 가질 수 있음 (압축 인코딩)")
                
                break
                
    except Exception as e:
        print(f"❌ 디코딩 실험 오류: {e}")

def analyze_card_patterns():
    """카드 패턴 분석"""
    print(f"\n🔍 바카라 카드 시스템 분석:")
    print(f"  - 카드 값: A(1), 2-9(액면가), 10/J/Q/K(0)")
    print(f"  - 무늬: ♠(스페이드), ♥(하트), ♦(다이아), ♣(클럽)")
    print(f"  - 총 52장 카드")
    print(f"  - 인코딩 방식: 각 카드를 고유 문자로 매핑했을 가능성")

if __name__ == "__main__":
    decode_history_experiment()
    analyze_card_patterns()