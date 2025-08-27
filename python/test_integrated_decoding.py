#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합된 카드 디코딩 시스템 테스트
실제 패킷 파일을 사용하여 카드 디코딩 통합 테스트
"""

import json
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print
from packet_decoder import BaccaratPacketDecoder

# 한국어 인코딩 설정
setup_korean_encoding()

def test_integrated_decoding():
    """통합된 카드 디코딩 시스템 테스트"""
    safe_print("🧪 통합 카드 디코딩 시스템 테스트")
    
    # 패킷 디코더 생성
    decoder = BaccaratPacketDecoder()
    
    # 실제 패킷 파일 읽기
    packet_file = Path("F:/two very auto 25.08.23/packet/20250809/바카라 A_08.txt")
    
    if not packet_file.exists():
        safe_print("❌ 패킷 파일을 찾을 수 없습니다.")
        return False
    
    safe_print(f"📁 패킷 파일 읽기: {packet_file.name}")
    
    # 파일에서 JSON 패킷 추출
    with open(packet_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    json_packets = []
    
    for line in lines:
        line = line.strip()
        # 타임스탬프 로그 라인에서 JSON 부분 추출
        if '"type":"baccarat.encodedShoeState"' in line:
            # 타임스탬프 부분을 제거하고 JSON만 추출
            json_start = line.find('{"id":')
            if json_start != -1:
                json_part = line[json_start:]
                try:
                    packet_data = json.loads(json_part)
                    json_packets.append(packet_data)
                except json.JSONDecodeError as e:
                    safe_print(f"⚠️ JSON 파싱 실패: {e}")
                    continue
    
    safe_print(f"📊 JSON 패킷 발견: {len(json_packets)}개")
    
    if not json_packets:
        safe_print("❌ JSON 패킷을 찾을 수 없습니다.")
        return False
    
    # 첫 번째 패킷으로 테스트
    test_packet = json_packets[0]
    
    safe_print(f"🔍 테스트 패킷 정보:")
    args = test_packet.get('args', {})
    safe_print(f"  - 게임 수: {len(args.get('history_v2', []))}")
    safe_print(f"  - 인코딩 길이: {len(args.get('history', ''))}")
    safe_print(f"  - 테이블 ID: {args.get('tableId', 'Unknown')}")
    
    # 패킷 디코딩 수행
    safe_print("⚙️ 패킷 디코딩 수행...")
    games = decoder.parse_json_packet(test_packet)
    
    safe_print(f"✅ 디코딩 완료: {len(games)}개 게임")
    
    # 첫 3개 게임 결과 표시
    for i, game in enumerate(games[:3]):
        safe_print(f"\n🎮 게임 #{i+1}:")
        safe_print(f"  - 결과: {game['result']}")
        safe_print(f"  - 플레이어: {game['player_score']}점 ({', '.join(game['player_cards'])})")
        safe_print(f"  - 뱅커: {game['banker_score']}점 ({', '.join(game['banker_cards'])})")
        safe_print(f"  - 페어: {game['pair_info']['pair_type']}")
        safe_print(f"  - 소스: {game['source']}")
    
    # 페어 통계
    pair_games = [g for g in games if g['pair_info']['has_any_pair']]
    safe_print(f"\n📈 페어 통계: {len(pair_games)}/{len(games)} ({len(pair_games)/len(games)*100:.1f}%)")
    
    return True

if __name__ == '__main__':
    test_integrated_decoding()