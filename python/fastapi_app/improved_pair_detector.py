#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 페어 감지 시스템 - Two Very Auto
요구사항: 첫 두장만 페어 검사, 회차 정보와 함께 리스트 출력
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ImprovedPairDetector:
    """개선된 페어 감지 시스템 - 첫 두장만 검사"""
    
    def __init__(self):
        """초기화"""
        self.pair_count = 0
        
    def analyze_packet_data(self, packet_content: str, room_name: str = "Unknown") -> List[Dict[str, Any]]:
        """패킷 데이터에서 페어 정보를 분석하여 리스트로 반환"""
        pair_results = []
        
        try:
            # JSON 패킷 찾기 (개선된 정규식)
            lines = packet_content.split('\n')
            json_matches = []
            
            for line in lines:
                line = line.strip()
                if '] {' in line and 'baccarat.encodedShoeState' in line:
                    # 타임스태프 뒤의 JSON 부분 추출
                    json_start = line.find('] {') + 2
                    json_part = line[json_start:]
                    json_matches.append(json_part)
                elif line.startswith('{') and 'baccarat.encodedShoeState' in line:
                    json_matches.append(line)
            
            for json_match in json_matches:
                try:
                    packet_data = json.loads(json_match)
                    pairs_found = self.extract_pairs_from_packet(packet_data, room_name)
                    if pairs_found:
                        pair_results.extend(pairs_found)
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 실패: {e}")
                    print(f"문제 JSON: {json_match[:200]}")
                    logger.warning(f"JSON 파싱 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"패킷 데이터 분석 실패: {e}")
        
        return pair_results
    
    def extract_pairs_from_packet(self, packet_data: Dict[str, Any], room_name: str) -> List[Dict[str, Any]]:
        """패킷에서 페어 정보 추출"""
        pairs_found = []
        
        try:
            args = packet_data.get('args', {})
            history_v2 = args.get('history_v2', [])
            table_id = args.get('tableId', 'unknown')
            timestamp = packet_data.get('time', 0)
            
            # 각 게임 회차별로 페어 검사
            for game_index, game_data in enumerate(history_v2):
                pair_info = self.detect_first_two_cards_pair(
                    game_data, 
                    game_index + 1,  # 회차는 1부터 시작
                    room_name, 
                    table_id, 
                    timestamp
                )
                
                if pair_info:
                    pairs_found.append(pair_info)
                    
        except Exception as e:
            logger.error(f"페어 추출 실패: {e}")
        
        return pairs_found
    
    def detect_first_two_cards_pair(self, game_data: Dict[str, Any], round_number: int, 
                                   room_name: str, table_id: str, timestamp: int) -> Optional[Dict[str, Any]]:
        """첫 두장 카드에서만 페어 감지 (3장 이상 받았을 때는 무시)"""
        
        # JSON에서 명시적으로 제공되는 페어 정보 확인
        player_pair = game_data.get('playerPair', False)
        banker_pair = game_data.get('bankerPair', False)
        
        # 페어가 없으면 None 반환
        if not (player_pair or banker_pair):
            return None
        
        # 페어 정보 구성
        pair_info = {
            'round': round_number,
            'room': room_name,
            'table_id': table_id,
            'timestamp': datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            'game_result': {
                'winner': game_data.get('winner', 'Unknown'),
                'player_score': game_data.get('playerScore', 0),
                'banker_score': game_data.get('bankerScore', 0),
                'natural': game_data.get('natural', False)
            },
            'pairs': []
        }
        
        # 플레이어 페어 처리
        if player_pair:
            pair_info['pairs'].append({
                'type': 'Player',
                'description': '플레이어 첫 두장 같은 숫자',
                'symbol': '[P]',
                'detected': True
            })
        
        # 뱅커 페어 처리
        if banker_pair:
            pair_info['pairs'].append({
                'type': 'Banker', 
                'description': '뱅커 첫 두장 같은 숫자',
                'symbol': '[B]',
                'detected': True
            })
        
        # 양쪽 페어인 경우 특별 표시
        if player_pair and banker_pair:
            pair_info['special'] = {
                'both_pairs': True,
                'rarity': 'Very Rare',
                'symbol': '[Both]'
            }
        
        return pair_info
    
    def process_packet_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """패킷 파일을 처리하여 페어 리스트 반환"""
        
        try:
            # 파일명에서 방명 추출
            room_name = self.extract_room_name(file_path.name)
            
            # 파일 내용 읽기
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # 페어 분석
            pairs_found = self.analyze_packet_data(content, room_name)
            
            # 추가 정보 보강
            for pair in pairs_found:
                pair['source_file'] = file_path.name
                pair['date'] = self.extract_date_from_path(file_path)
            
            return pairs_found
            
        except Exception as e:
            logger.error(f"파일 처리 실패 {file_path}: {e}")
            return []
    
    def extract_room_name(self, filename: str) -> str:
        """파일명에서 방명 추출"""
        # 예: "바카라 A_08.txt" → "바카라 A"
        # 예: "스피드 바카라 1_08.txt" → "스피드 바카라 1"
        match = re.match(r'(.+?)_\d+\.txt$', filename)
        return match.group(1) if match else filename.replace('.txt', '')
    
    def extract_date_from_path(self, file_path: Path) -> str:
        """경로에서 날짜 추출"""
        # 예: "/packet/20250809/파일.txt" → "2025-08-09"
        date_match = re.search(r'(\d{8})', str(file_path))
        if date_match:
            date_str = date_match.group(1)
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return "Unknown"
    
    def get_pairs_summary(self, pairs_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 리스트 요약 정보"""
        if not pairs_list:
            return {
                'total_pairs': 0,
                'player_pairs': 0,
                'banker_pairs': 0,
                'both_pairs': 0,
                'rooms': [],
                'latest_pair': None
            }
        
        # 통계 계산
        player_pairs = 0
        banker_pairs = 0  
        both_pairs = 0
        rooms = set()
        
        for pair in pairs_list:
            rooms.add(pair['room'])
            
            if pair.get('special', {}).get('both_pairs', False):
                both_pairs += 1
            else:
                for p in pair['pairs']:
                    if p['type'] == 'Player':
                        player_pairs += 1
                    elif p['type'] == 'Banker':
                        banker_pairs += 1
        
        return {
            'total_pairs': len(pairs_list),
            'player_pairs': player_pairs,
            'banker_pairs': banker_pairs, 
            'both_pairs': both_pairs,
            'rooms': list(rooms),
            'latest_pair': pairs_list[-1] if pairs_list else None,
            'date_range': {
                'start': min(p.get('date', 'Unknown') for p in pairs_list),
                'end': max(p.get('date', 'Unknown') for p in pairs_list)
            } if pairs_list and any(p.get('date') for p in pairs_list) else None
        }
    
    def format_pairs_output(self, pairs_list: List[Dict[str, Any]]) -> str:
        """페어 리스트를 보기 좋은 형식으로 포맷"""
        if not pairs_list:
            return "[페어 발견 없음]"
        
        output = [f"[페어 감지 결과] 총 {len(pairs_list)}건\n"]
        
        for i, pair in enumerate(pairs_list, 1):
            output.append(f"[#{i}] 회차: {pair['round']}회")
            output.append(f"  방명: {pair['room']}")
            output.append(f"  시간: {pair['timestamp']}")
            
            # 페어 정보
            for p in pair['pairs']:
                output.append(f"  -> {p['symbol']} {p['description']}")
            
            # 특별한 경우 (양쪽 페어)
            if pair.get('special', {}).get('both_pairs'):
                output.append(f"  -> [특별] 플레이어/뱅커 모두 페어! (매우 드문 케이스)")
            
            # 게임 결과
            result = pair['game_result']
            output.append(f"  승부: {result['winner']} (P:{result['player_score']} vs B:{result['banker_score']})")
            
            if result['natural']:
                output.append(f"  [내추럴!]")
            
            output.append("")  # 빈 줄
        
        return "\n".join(output)

# 전역 인스턴스
improved_pair_detector = ImprovedPairDetector()

# 테스트 함수
def test_improved_pair_detector():
    """개선된 페어 감지기 테스트"""
    print("=== 개선된 페어 감지기 테스트 시작 ===")
    
    # 샘플 패킷 데이터  
    sample_packet = '''[08:46:12] {"id":"test","type":"baccarat.encodedShoeState","args":{"stats":{"gameCount":3},"history":"test","history_v2":[{"winner":"Banker","playerScore":1,"bankerScore":4,"playerPair":true},{"winner":"Player","playerScore":8,"bankerScore":1,"bankerPair":true},{"winner":"Tie","playerScore":2,"bankerScore":2,"playerPair":true,"bankerPair":true}],"tableId":"test_table"},"time":1754696775387}'''
    
    pairs = improved_pair_detector.analyze_packet_data(sample_packet, "테스트 바카라 A")
    
    print(f"[OK] 감지된 페어 수: {len(pairs)}")
    print(improved_pair_detector.format_pairs_output(pairs))
    
    # 통계 출력
    summary = improved_pair_detector.get_pairs_summary(pairs)
    print(f"[통계] {summary}")

if __name__ == "__main__":
    test_improved_pair_detector()