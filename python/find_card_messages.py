#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
여러 파일에서 카드 정보 메시지 검색
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

def search_card_messages():
    """여러 파일에서 카드 정보 검색"""
    packet_folder = Path("F:/two very auto 25.08.23/packet")
    
    # 여러 파일 검사
    files_to_check = []
    for file_path in packet_folder.rglob("*.txt"):
        if file_path.stat().st_size > 1000:  # 1KB 이상인 파일만
            files_to_check.append(file_path)
            if len(files_to_check) >= 5:  # 5개 파일만 검사
                break
    
    print(f"🔍 검사할 파일들:")
    for f in files_to_check:
        print(f"  - {f}")
    
    card_keywords = ['card', 'suit', 'rank', 'hearts', 'diamonds', 'clubs', 'spades', 
                    'player_cards', 'banker_cards', 'deal', 'cards', 'deck']
    
    found_card_info = False
    
    for file_path in files_to_check:
        print(f"\n📄 파일: {file_path.name}")
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            message_types = set()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # 카드 키워드가 포함된 라인 찾기
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in card_keywords):
                    print(f"  🎰 라인 {line_num}에서 카드 키워드 발견!")
                    print(f"    라인: {line[:200]}...")
                    found_card_info = True
                    
                # JSON 파싱 시도
                json_part = None
                if line.startswith('{'):
                    json_part = line
                elif '] {' in line:
                    json_start = line.find('] {') + 2
                    json_part = line[json_start:]
                
                if json_part:
                    try:
                        data = json.loads(json_part)
                        msg_type = data.get('type', 'unknown')
                        message_types.add(msg_type)
                        
                        # args에서 카드 정보 검색
                        args = data.get('args', {})
                        args_str = json.dumps(args).lower()
                        
                        if any(keyword in args_str for keyword in card_keywords):
                            print(f"  🃏 라인 {line_num}에서 카드 데이터 발견!")
                            print(f"    타입: {msg_type}")
                            print(f"    Args: {json.dumps(args, indent=2, ensure_ascii=False)[:300]}...")
                            found_card_info = True
                    
                    except json.JSONDecodeError:
                        continue
            
            print(f"  📊 이 파일의 메시지 타입들: {sorted(list(message_types))}")
        
        except Exception as e:
            print(f"  ❌ 파일 읽기 오류: {e}")
    
    if not found_card_info:
        print(f"\n❌ 직접적인 카드 정보를 찾지 못했습니다.")
        print(f"🔄 history 필드 디코딩이 필요할 수 있습니다.")
        
        # 인코딩 패턴 분석
        print(f"\n🔍 인코딩 패턴 분석:")
        analyze_encoding_pattern()

def analyze_encoding_pattern():
    """인코딩 패턴 분석"""
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
                
                if history and history_v2:
                    print(f"  📊 History 길이: {len(history)}")
                    print(f"  📊 Games 수: {len(history_v2)}")
                    print(f"  📊 문자당 게임 수: {len(history_v2) / len(history):.2f}")
                    
                    # 특별한 문자들 확인
                    special_chars = set(c for c in history if not c.isalnum())
                    print(f"  🔤 특별문자들: {sorted(list(special_chars))}")
                    break
                    
    except Exception as e:
        print(f"❌ 인코딩 분석 오류: {e}")

if __name__ == "__main__":
    search_card_messages()