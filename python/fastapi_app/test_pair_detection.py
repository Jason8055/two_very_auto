#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
페어 감지 시스템 테스트 스크립트
실제 패킷 데이터로 페어 감지 기능을 검증
"""

import sys
import os
import json
from pathlib import Path
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(__file__))

from enhanced_pair_detector import enhanced_pair_detector
from utils.smart_output import info, success, warning, error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_real_packet_data():
    """실제 패킷 데이터로 페어 감지 테스트"""
    
    info("Two Very Auto - 페어 감지 시스템 테스트")
    info("=" * 60)
    
    # 패킷 폴더 경로
    packet_folder = Path("F:/two very auto 25.08.23/packet")
    
    if not packet_folder.exists():
        error("패킷 폴더를 찾을 수 없습니다", 경로=str(packet_folder))
        return False
    
    total_files = 0
    total_pairs = 0
    
    # 모든 날짜 폴더 검사
    for date_folder in sorted(packet_folder.iterdir()):
        if not date_folder.is_dir():
            continue
        
        info(f"날짜 폴더 검사 시작", 폴더=date_folder.name)
        info("-" * 40)
        
        folder_pairs = 0
        
        # 패킷 파일들 검사
        for packet_file in date_folder.glob("*.txt"):
            if packet_file.name in ['Main.txt', 'Rejected.txt']:
                continue
            
            total_files += 1
            
            # 페어 감지 실행
            pairs_found = enhanced_pair_detector.process_packet_file(packet_file)
            
            if pairs_found:
                folder_pairs += len(pairs_found)
                total_pairs += len(pairs_found)
                
                success("페어 감지 성공", 
                        파일=packet_file.name,
                        페어수=len(pairs_found))
                
                # 첫 번째 페어 상세 정보 표시
                first_pair = pairs_found[0]
                pair_types = first_pair.get('pair_type', [])
                info("페어 상세정보", 
                     타입=', '.join(pair_types),
                     게임번호=first_pair.get('game_number', 'N/A'),
                     승부=first_pair.get('winner', 'N/A'),
                     점수=f"P{first_pair.get('player_score', 0)} vs B{first_pair.get('banker_score', 0)}")
            
        if folder_pairs > 0:
            success("폴더 통계", 폴더=date_folder.name, 총페어수=folder_pairs)
    
    # 전체 결과 요약
    info("\n" + "=" * 60)
    info("테스트 결과 요약")
    info("=" * 60)
    success("검사 완료", 총파일수=total_files, 총페어수=total_pairs)
    
    if total_pairs > 0:
        pair_rate = (total_pairs/max(1, total_files)*100)
        success("페어 감지 시스템 정상 작동", 페어발생률=f"{pair_rate:.1f}%")
        
        # 통계 정보
        info("페어 분석 통계")
        info("페어 타입별 예상 빈도", 
             플레이어페어="예상됨",
             뱅커페어="예상됨",
             양쪽페어="매우 희귀")
        
        return True
    else:
        warning("페어가 감지되지 않았습니다", 권장사항="패킷 데이터를 확인해보세요")
        return False

def test_json_parsing():
    """JSON 파싱 기능 테스트"""
    
    info("JSON 파싱 테스트 시작")
    info("-" * 30)
    
    # 테스트용 JSON 데이터 (실제 패킷에서 추출)
    test_json = '''
    {"id":"1754696775387-7007","type":"baccarat.encodedShoeState","args":{"stats":{"gameCount":1,"playerWins":0,"bankerWins":1,"ties":0,"playerPairs":1,"bankerPairs":0},"history":"-O","history_v2":[{"winner":"Banker","playerPair":true,"playerScore":6,"bankerScore":7}],"tableId":"test_table"},"time":1754696775387}
    '''
    
    try:
        packet_data = json.loads(test_json)
        pairs = enhanced_pair_detector.extract_pair_info_from_json(packet_data)
        
        if pairs:
            success("JSON 파싱 성공")
            success("페어 감지 성공", 페어수=len(pairs))
            
            for pair in pairs:
                info("감지된 페어 정보",
                     타입=pair.get('pair_type', []),
                     게임번호=pair.get('game_number', 'N/A'),
                     테이블=pair.get('table_id', 'N/A'))
            
            return True
        else:
            error("페어 감지 실패")
            return False
            
    except Exception as e:
        error("JSON 파싱 오류", 오류내용=str(e))
        return False

def main():
    """메인 테스트 함수"""
    
    info("Two Very Auto - 페어 감지 시스템 종합 테스트")
    info("=" * 70)
    
    # JSON 파싱 테스트
    json_test_passed = test_json_parsing()
    
    # 실제 패킷 데이터 테스트
    packet_test_passed = test_real_packet_data()
    
    # 최종 결과
    info("\n" + "=" * 70)
    info("최종 테스트 결과")
    info("=" * 70)
    
    if json_test_passed and packet_test_passed:
        success("모든 테스트 통과")
        success("페어 감지 시스템이 완벽하게 작동합니다")
        info("실시간 페어 정보 확인 URL",
             대시보드="http://localhost:8080/pair-dashboard",
             API="http://localhost:8080/api/packet-data/pairs")
        return True
    else:
        error("일부 테스트 실패", 권장사항="시스템을 점검해보세요")
        return False

if __name__ == "__main__":
    main()