#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
방명별 패킷 데이터 분석 스크립트
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

def analyze_room_structure():
    """방명별 패킷 데이터 구조 분석"""
    extractor = PacketDataExtractor()
    packet_folder = Path('F:/two very auto 25.08.23/packet')
    
    rooms = {}
    total_games = {}
    
    for file_path in packet_folder.rglob('*.txt'):
        if file_path.is_file():
            room_name = extractor.extract_room_name(file_path.name)
            date = extractor.extract_date_from_path(file_path)
            
            if room_name not in rooms:
                rooms[room_name] = []
                total_games[room_name] = 0
            
            # 간단한 게임 수 카운트 (파일 크기로 추정)
            try:
                file_data = extractor.parse_packet_file(file_path)
                game_count = len(file_data)
                total_games[room_name] += game_count
                
                rooms[room_name].append({
                    '파일': file_path.name,
                    '날짜': date,
                    '게임수': game_count,
                    '경로': str(file_path)
                })
            except Exception as e:
                print(f"오류 {file_path.name}: {e}")
    
    print('📍 발견된 방명별 데이터 현황:')
    print('=' * 80)
    
    for room_name in sorted(rooms.keys()):
        files = rooms[room_name]
        total = total_games[room_name]
        
        print(f'\n🎰 {room_name}')
        print(f'   📊 총 {len(files)}개 파일, {total:,}개 게임')
        
        # 날짜별로 정렬
        files.sort(key=lambda x: x['날짜'], reverse=True)
        
        for file_info in files[:5]:  # 최근 5개만 표시
            print(f'   📄 {file_info["파일"]} ({file_info["날짜"]}) - {file_info["게임수"]:,}게임')
        
        if len(files) > 5:
            print(f'   ... 외 {len(files)-5}개 파일 더')
    
    print('\n' + '=' * 80)
    print(f'📈 전체 통계:')
    print(f'   - 총 방명: {len(rooms)}개')
    print(f'   - 총 파일: {sum(len(files) for files in rooms.values())}개')
    print(f'   - 총 게임: {sum(total_games.values()):,}개')
    
    return rooms, total_games

if __name__ == "__main__":
    analyze_room_structure()