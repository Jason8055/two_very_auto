#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패킷 데이터 조회 라우터 - 핵심 목적 구현
직접적인 패킷 JSON 디코딩 및 실제 페어 정보 표시
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

# 절대 경로 import 사용 (패키지 구조 문제로 인해)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from card_display_system import HybridCardDisplaySystem
from enhanced_pair_detector import enhanced_pair_detector
from improved_pair_detector import improved_pair_detector

router = APIRouter()
logger = logging.getLogger(__name__)

# 패킷 폴더 경로 (프로젝트 루트 기준)
PACKET_FOLDER = Path(__file__).parent.parent.parent.parent / "packet"

class PacketDataExtractor:
    """패킷 데이터 추출기 - 핵심 목적에 특화"""
    
    def __init__(self):
        """초기화"""
        self.card_display = HybridCardDisplaySystem()
    
    @staticmethod
    def extract_room_name(filename: str) -> str:
        """파일명에서 방명 추출"""
        # 예: "바카라 A_08.txt" → "바카라 A"
        # 예: "스피드 바카라 1_08.txt" → "스피드 바카라 1"
        match = re.match(r'(.+?)_\d+\.txt$', filename)
        return match.group(1) if match else filename.replace('.txt', '')
    
    @staticmethod
    def extract_date_from_path(file_path: Path) -> str:
        """경로에서 날짜 추출"""
        # 예: "/packet/20250809/파일.txt" → "2025-08-09"
        date_match = re.search(r'(\d{8})', str(file_path))
        if date_match:
            date_str = date_match.group(1)
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return "Unknown"
    
    @staticmethod
    def parse_packet_file(file_path: Path) -> List[Dict[str, Any]]:
        """패킷 파일에서 실제 게임 데이터 추출"""
        results = []
        
        try:
            room_name = PacketDataExtractor.extract_room_name(file_path.name)
            date = PacketDataExtractor.extract_date_from_path(file_path)
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                
                # 타임스태프가 있는 JSON 라인 처리
                # 예: [08:46:12] {"id":"..."}
                json_part = None
                if line.startswith('{'):
                    json_part = line
                elif '] {' in line:
                    # 타임스태프 뒤의 JSON 부분 추출
                    json_start = line.find('] {') + 2
                    json_part = line[json_start:]
                
                if not json_part:
                    continue
                    
                try:
                    data = json.loads(json_part)
                    if data.get('type') != 'baccarat.encodedShoeState':
                        continue
                        
                    args = data.get('args', {})
                    history_v2 = args.get('history_v2', [])
                    history = args.get('history', '')
                    table_id = args.get('tableId', 'Unknown')
                    
                    # 이전 카드 디코딩 시스템 사용
                    decoded_cards = []
                    try:
                        # 이전 개발된 카드 디코딩 시스템 임포트 시도
                        import sys
                        import os
                        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                        from card_decoding_integration import CardDecodingIntegration
                        
                        decoder = CardDecodingIntegration()
                        decode_result = decoder.decode_history_string(history, history_v2)
                        
                        if decode_result.get('best_match') and decode_result.get('confidence_score', 0) > 0.5:
                            decoded_cards = decode_result.get('decoded_cards', [])
                        
                    except Exception as e:
                        logger.warning(f"카드 디코딩 실패, 기존 방식 사용: {e}")
                    
                    # 하이브리드 카드 표시 시스템 초기화 
                    card_display = HybridCardDisplaySystem()
                    
                    for game_idx, game in enumerate(history_v2):
                        # 하이브리드 카드 표시 시스템 사용
                        card_info = card_display.generate_card_info(game, game_idx, 'hybrid')
                        
                        results.append({
                            '방명': room_name,
                            '테이블ID': table_id,
                            '날짜': date,
                            '게임번호': game_idx + 1,
                            '승패': game.get('winner', 'Unknown'),
                            'Player점수': game.get('playerScore', 0),
                            'Banker점수': game.get('bankerScore', 0),
                            'Player페어': game.get('playerPair', False),
                            'Banker페어': game.get('bankerPair', False),
                            '내추럴': game.get('natural', False),
                            '카드정보': card_info,
                            '파일명': file_path.name,
                            '라인번호': line_num
                        })
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"파일 파싱 오류 {file_path}: {e}")
            
        return results

extractor = PacketDataExtractor()

@router.get("/packet-data/pairs", response_model=Dict[str, Any])
async def get_pair_data(
    limit: int = Query(20, ge=1, le=100, description="결과 제한수"),
    room_filter: Optional[str] = Query(None, description="방명 필터"),
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD)")
):
    """
    패킷 데이터에서 페어 정보만 추출 - 성능 최적화 버전
    핵심 목적: 첫 두장 같은 무늬 같은 숫자 감지 및 표시
    """
    try:
        from datetime import datetime, timedelta
        import time
        
        start_time = time.time()
        all_pairs = []
        max_files_total = 20    # 전체 최대 파일 처리 제한 (더 감소)
        processed_files = 0
        
        # 현재 날짜만 처리 (더 제한적)
        current_date = datetime.now()
        today_str = current_date.strftime("%Y%m%d")
        
        # 오늘 날짜 폴더만 확인
        today_folder = PACKET_FOLDER / today_str
        if not today_folder.exists():
            # 오늘 폴더가 없으면 가장 최근 폴더 사용
            date_folders = [f for f in PACKET_FOLDER.iterdir() if f.is_dir()]
            if date_folders:
                today_folder = max(date_folders, key=lambda x: x.name)
            else:
                return {
                    "success": True,
                    "message": "패킷 폴더에 데이터가 없습니다",
                    "statistics": {"total_pairs": 0, "player_pairs": 0, "banker_pairs": 0, "both_pairs": 0},
                    "pairs": [],
                    "total_files_scanned": 0,
                    "timestamp": datetime.now().isoformat()
                }
        
        # 파일 처리 (최신 5개만)
        packet_files = list(today_folder.glob("*.txt"))
        packet_files = [f for f in packet_files if f.name not in ['Main.txt', 'Rejected.txt']]
        
        # 최신 파일 순으로 정렬하고 제한
        packet_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        packet_files = packet_files[:max_files_total]
        
        for packet_file in packet_files:
            # 방명 필터 적용
            if room_filter and room_filter not in packet_file.name:
                continue
            
            try:
                # 타임아웃 방지를 위해 간단한 처리
                pairs_found = enhanced_pair_detector.process_packet_file(packet_file)
                
                for pair in pairs_found:
                    pair['room_name'] = extractor.extract_room_name(packet_file.name)
                    pair['date'] = extractor.extract_date_from_path(packet_file)
                    
                all_pairs.extend(pairs_found)
                processed_files += 1
                
                # 처리 시간 체크 (5초 제한)
                if time.time() - start_time > 5:
                    logger.warning("API 처리 시간 제한 도달, 조기 종료")
                    break
                    
            except Exception as file_error:
                logger.warning(f"파일 처리 오류 {packet_file}: {file_error}")
                continue
        
        # 시간순 정렬 및 제한
        all_pairs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        limited_pairs = all_pairs[:limit]
        
        # 기본 통계
        stats = {
            "total_pairs": len(limited_pairs),
            "player_pairs": len([p for p in limited_pairs if p.get('pair_details', {}).get('player_pair')]),
            "banker_pairs": len([p for p in limited_pairs if p.get('pair_details', {}).get('banker_pair')]),
            "both_pairs": len([p for p in limited_pairs if p.get('pair_details', {}).get('both_pairs')])
        }
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "message": f"총 {len(limited_pairs)}개의 페어 발견 (파일 {processed_files}개 처리)",
            "statistics": stats,
            "pairs": limited_pairs,
            "total_files_scanned": processed_files,
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "processing_time_seconds": round(processing_time, 2),
                "limited_processing": True,
                "max_files_total": max_files_total,
                "folder_processed": today_folder.name
            }
        }
        
    except Exception as e:
        logger.error(f"페어 데이터 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 안전한 기본 응답 반환
        return {
            "success": False,
            "message": "패킷 데이터 처리 중 오류 발생",
            "error": str(e),
            "statistics": {"total_pairs": 0, "player_pairs": 0, "banker_pairs": 0, "both_pairs": 0},
            "pairs": [],
            "total_files_scanned": 0,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/rooms/statistics", response_model=Dict[str, Any])
async def get_rooms_statistics(
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD)")
):
    """모든 방의 페어 통계 정보 조회"""
    try:
        from datetime import datetime, timedelta
        import time
        from collections import defaultdict
        
        start_time = time.time()
        room_stats = defaultdict(lambda: {
            "room_name": "",
            "total_pairs": 0,
            "player_pairs": 0,
            "banker_pairs": 0,
            "both_pairs": 0,
            "last_activity": "",
            "games_processed": 0,
            "sample_pairs": []
        })
        
        # 현재 날짜만 처리 (성능 최적화)
        current_date = datetime.now()
        today_str = current_date.strftime("%Y%m%d")
        
        # 날짜 폴더 확인
        if date_filter:
            target_date = date_filter.replace('-', '')
            target_folder = PACKET_FOLDER / target_date
        else:
            target_folder = PACKET_FOLDER / today_str
            if not target_folder.exists():
                date_folders = [f for f in PACKET_FOLDER.iterdir() if f.is_dir()]
                if date_folders:
                    target_folder = max(date_folders, key=lambda x: x.name)
        
        if not target_folder.exists():
            return {
                "success": True,
                "message": "해당 날짜의 데이터가 없습니다",
                "rooms": [],
                "total_rooms": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # 방별로 파일 그룹화
        room_files = defaultdict(list)
        packet_files = list(target_folder.glob("*.txt"))
        packet_files = [f for f in packet_files if f.name not in ['Main.txt', 'Rejected.txt']]
        
        for packet_file in packet_files[:100]:  # 최대 100개 파일만 처리
            room_name = extractor.extract_room_name(packet_file.name)
            room_files[room_name].append(packet_file)
        
        # 각 방별로 통계 계산
        for room_name, files in room_files.items():
            # 방별로 최대 5개 파일만 처리 (성능 최적화)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            files = files[:5]
            
            for packet_file in files:
                try:
                    pairs_found = enhanced_pair_detector.process_packet_file(packet_file)
                    
                    for pair in pairs_found:
                        pair['room_name'] = room_name
                        pair['date'] = extractor.extract_date_from_path(packet_file)
                        
                        # 통계 업데이트
                        room_stats[room_name]["total_pairs"] += 1
                        
                        if pair.get('pair_details', {}).get('player_pair'):
                            room_stats[room_name]["player_pairs"] += 1
                        if pair.get('pair_details', {}).get('banker_pair'):
                            room_stats[room_name]["banker_pairs"] += 1
                        if pair.get('pair_details', {}).get('both_pairs'):
                            room_stats[room_name]["both_pairs"] += 1
                        
                        # 샘플 페어 저장 (최대 3개)
                        if len(room_stats[room_name]["sample_pairs"]) < 3:
                            room_stats[room_name]["sample_pairs"].append(pair)
                        
                        # 최근 활동 시간 업데이트
                        if not room_stats[room_name]["last_activity"] or pair.get('timestamp', '') > room_stats[room_name]["last_activity"]:
                            room_stats[room_name]["last_activity"] = pair.get('timestamp', '')
                    
                    room_stats[room_name]["games_processed"] += 1
                    room_stats[room_name]["room_name"] = room_name
                    
                except Exception as file_error:
                    logger.warning(f"파일 처리 오류 {packet_file}: {file_error}")
                    continue
            
            # 처리 시간 체크 (10초 제한)
            if time.time() - start_time > 10:
                logger.warning("방별 통계 처리 시간 제한 도달")
                break
        
        # 결과 정리
        rooms_list = []
        for room_name, stats in room_stats.items():
            if stats["total_pairs"] > 0:  # 페어가 있는 방만 포함
                rooms_list.append(stats)
        
        # 페어 수 기준으로 정렬
        rooms_list.sort(key=lambda x: x["total_pairs"], reverse=True)
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "message": f"총 {len(rooms_list)}개 방의 통계 분석 완료",
            "rooms": rooms_list,
            "total_rooms": len(rooms_list),
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "processing_time_seconds": round(processing_time, 2),
                "folder_processed": target_folder.name,
                "total_files_available": len(packet_files)
            }
        }
        
    except Exception as e:
        logger.error(f"방별 통계 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "방별 통계 처리 중 오류 발생",
            "error": str(e),
            "rooms": [],
            "total_rooms": 0,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/rooms/{room_name}/pairs", response_model=Dict[str, Any])
async def get_room_pairs(
    room_name: str,
    limit: int = Query(20, ge=1, le=100, description="결과 제한수"),
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD)")
):
    """특정 방의 페어 상세 목록 조회"""
    try:
        from datetime import datetime, timedelta
        import time
        
        start_time = time.time()
        all_pairs = []
        
        # 현재 날짜만 처리
        current_date = datetime.now()
        today_str = current_date.strftime("%Y%m%d")
        
        if date_filter:
            target_date = date_filter.replace('-', '')
            target_folder = PACKET_FOLDER / target_date
        else:
            target_folder = PACKET_FOLDER / today_str
            if not target_folder.exists():
                date_folders = [f for f in PACKET_FOLDER.iterdir() if f.is_dir()]
                if date_folders:
                    target_folder = max(date_folders, key=lambda x: x.name)
        
        if not target_folder.exists():
            return {
                "success": True,
                "message": f"방 '{room_name}'의 데이터가 없습니다",
                "room_name": room_name,
                "pairs": [],
                "total_pairs": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # 해당 방의 파일들만 필터링
        packet_files = []
        for file_path in target_folder.glob("*.txt"):
            if file_path.name in ['Main.txt', 'Rejected.txt']:
                continue
            
            file_room_name = extractor.extract_room_name(file_path.name)
            if file_room_name == room_name:
                packet_files.append(file_path)
        
        # 최신 순으로 정렬하고 제한
        packet_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        packet_files = packet_files[:20]  # 최대 20개 파일
        
        for packet_file in packet_files:
            try:
                pairs_found = enhanced_pair_detector.process_packet_file(packet_file)
                
                for pair in pairs_found:
                    pair['room_name'] = room_name
                    pair['date'] = extractor.extract_date_from_path(packet_file)
                    
                all_pairs.extend(pairs_found)
                
                # 처리 시간 체크 (5초 제한)
                if time.time() - start_time > 5:
                    logger.warning(f"방 '{room_name}' 처리 시간 제한 도달")
                    break
                    
            except Exception as file_error:
                logger.warning(f"파일 처리 오류 {packet_file}: {file_error}")
                continue
        
        # 시간순 정렬 및 제한
        all_pairs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        limited_pairs = all_pairs[:limit]
        
        # 통계
        stats = {
            "total_pairs": len(limited_pairs),
            "player_pairs": len([p for p in limited_pairs if p.get('pair_details', {}).get('player_pair')]),
            "banker_pairs": len([p for p in limited_pairs if p.get('pair_details', {}).get('banker_pair')]),
            "both_pairs": len([p for p in limited_pairs if p.get('pair_details', {}).get('both_pairs')])
        }
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "message": f"방 '{room_name}'에서 {len(limited_pairs)}개 페어 발견",
            "room_name": room_name,
            "statistics": stats,
            "pairs": limited_pairs,
            "total_pairs": len(all_pairs),
            "files_processed": len(packet_files),
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "processing_time_seconds": round(processing_time, 2),
                "folder_processed": target_folder.name
            }
        }
        
    except Exception as e:
        logger.error(f"방 '{room_name}' 페어 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"방 '{room_name}' 데이터 처리 중 오류 발생",
            "error": str(e),
            "room_name": room_name,
            "pairs": [],
            "total_pairs": 0,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/packet-data/live-pairs", response_model=Dict[str, Any])
async def get_live_pairs():
    """
    실시간 페어 정보 - 최신 데이터에서 페어 감지
    """
    try:
        # 가장 최근 날짜 폴더 찾기
        latest_date_folder = None
        for date_folder in sorted(PACKET_FOLDER.iterdir(), reverse=True):
            if date_folder.is_dir():
                latest_date_folder = date_folder
                break
        
        if not latest_date_folder:
            raise HTTPException(status_code=404, detail="패킷 데이터 폴더를 찾을 수 없습니다")
        
        live_pairs = []
        
        # 최신 폴더의 모든 파일 검사
        for packet_file in latest_date_folder.glob("*.txt"):
            if packet_file.name in ['Main.txt', 'Rejected.txt']:
                continue
            
            pairs_found = enhanced_pair_detector.process_packet_file(packet_file)
            
            for pair in pairs_found:
                pair['room_name'] = extractor.extract_room_name(packet_file.name)
                pair['date'] = extractor.extract_date_from_path(packet_file)
                pair['is_live'] = True
            
            live_pairs.extend(pairs_found)
        
        # 최신 순으로 정렬
        live_pairs.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_pairs = live_pairs[:20]  # 최근 20개만
        
        return {
            "success": True,
            "message": f"실시간 페어 데이터 {len(recent_pairs)}개",
            "live_pairs": recent_pairs,
            "scan_date": latest_date_folder.name,
            "active_tables": list(set(pair['table_id'] for pair in recent_pairs)),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"실시간 페어 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"실시간 페어 조회 실패: {str(e)}")

@router.get("/packet-data/all", response_model=List[Dict[str, Any]])
async def get_all_packet_data(
    limit: int = Query(100, ge=1, le=1000, description="결과 제한수"),
    room_filter: Optional[str] = Query(None, description="방명 필터"),
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD)")
):
    """
    모든 패킷 데이터 조회 - 핵심 기능
    
    실제 JSON에서 승패, 점수, 페어 정보 등을 직접 추출
    """
    try:
        if not PACKET_FOLDER.exists():
            raise HTTPException(status_code=404, detail=f"패킷 폴더를 찾을 수 없습니다: {PACKET_FOLDER}")
            
        all_data = []
        processed_files = 0
        
        # 모든 .txt 파일 스캔
        for file_path in PACKET_FOLDER.rglob("*.txt"):
            if file_path.is_file():
                file_data = extractor.parse_packet_file(file_path)
                
                # 필터 적용
                if room_filter:
                    file_data = [d for d in file_data if room_filter.lower() in d['방명'].lower()]
                    
                if date_filter:
                    file_data = [d for d in file_data if d['날짜'] == date_filter]
                    
                all_data.extend(file_data)
                processed_files += 1
                
        # 최신 데이터부터 정렬
        all_data.sort(key=lambda x: (x['날짜'], x['파일명'], x['라인번호']), reverse=True)
        
        # 제한 적용
        limited_data = all_data[:limit]
        
        logger.info(f"패킷 데이터 조회 완료: {processed_files}개 파일, {len(all_data)}개 게임, {len(limited_data)}개 반환")
        
        return limited_data
        
    except Exception as e:
        logger.error(f"패킷 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/packet-data/rooms")
async def get_available_rooms():
    """사용 가능한 방명 목록 조회"""
    try:
        rooms = set()
        
        for file_path in PACKET_FOLDER.rglob("*.txt"):
            if file_path.is_file():
                room_name = extractor.extract_room_name(file_path.name)
                rooms.add(room_name)
                
        return {"rooms": sorted(list(rooms))}
        
    except Exception as e:
        logger.error(f"방명 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/packet-data/dates")
async def get_available_dates():
    """사용 가능한 날짜 목록 조회"""
    try:
        dates = set()
        
        for file_path in PACKET_FOLDER.rglob("*.txt"):
            if file_path.is_file():
                date = extractor.extract_date_from_path(file_path)
                dates.add(date)
                
        return {"dates": sorted(list(dates), reverse=True)}
        
    except Exception as e:
        logger.error(f"날짜 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/packet-data/by-rooms")
async def get_data_by_rooms(
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD)"),
    limit_per_room: int = Query(50, ge=1, le=500, description="방별 최대 게임 수")
):
    """
    방별로 그룹화된 패킷 데이터 조회
    
    각 방명별로 최신 게임 데이터를 그룹화하여 반환
    """
    try:
        if not PACKET_FOLDER.exists():
            raise HTTPException(status_code=404, detail=f"패킷 폴더를 찾을 수 없습니다: {PACKET_FOLDER}")
            
        rooms_data = {}
        processed_files = 0
        
        # 모든 .txt 파일 스캔
        for file_path in PACKET_FOLDER.rglob("*.txt"):
            if file_path.is_file():
                file_data = extractor.parse_packet_file(file_path)
                
                if file_data:
                    room_name = file_data[0]['방명']
                    
                    # 날짜 필터 적용
                    if date_filter:
                        file_data = [d for d in file_data if d['날짜'] == date_filter]
                        
                    if file_data:
                        if room_name not in rooms_data:
                            rooms_data[room_name] = []
                        
                        rooms_data[room_name].extend(file_data)
                        
                processed_files += 1
                
        # 각 방별로 최신 데이터 정렬 및 제한
        for room_name in rooms_data:
            rooms_data[room_name].sort(
                key=lambda x: (x['날짜'], x['파일명'], x['라인번호']), 
                reverse=True
            )
            rooms_data[room_name] = rooms_data[room_name][:limit_per_room]
        
        # 통계 계산
        total_rooms = len(rooms_data)
        total_games = sum(len(games) for games in rooms_data.values())
        
        result = {
            "rooms": rooms_data,
            "statistics": {
                "총방명수": total_rooms,
                "총게임수": total_games,
                "처리파일수": processed_files,
                "방별최대게임수": limit_per_room
            }
        }
        
        logger.info(f"방별 패킷 데이터 조회 완료: {total_rooms}개 방, {total_games}개 게임")
        
        return result
        
    except Exception as e:
        logger.error(f"방별 패킷 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/packet-data/room-summary")
async def get_room_summary():
    """
    방별 요약 정보 조회 (빠른 통계)
    """
    try:
        if not PACKET_FOLDER.exists():
            raise HTTPException(status_code=404, detail=f"패킷 폴더를 찾을 수 없습니다: {PACKET_FOLDER}")
            
        room_stats = {}
        
        for file_path in PACKET_FOLDER.rglob("*.txt"):
            if file_path.is_file():
                room_name = extractor.extract_room_name(file_path.name)
                date = extractor.extract_date_from_path(file_path)
                
                if room_name not in room_stats:
                    room_stats[room_name] = {
                        "방명": room_name,
                        "파일수": 0,
                        "총게임수": 0,
                        "최신날짜": date,
                        "최초날짜": date,
                        "날짜목록": set()
                    }
                
                # 빠른 게임 수 추정 (실제 파싱 없이 파일 크기 기반)
                try:
                    file_size = file_path.stat().st_size
                    estimated_games = max(0, (file_size // 500))  # 대략적인 추정
                    
                    room_stats[room_name]["파일수"] += 1
                    room_stats[room_name]["총게임수"] += estimated_games
                    room_stats[room_name]["날짜목록"].add(date)
                    
                    if date > room_stats[room_name]["최신날짜"]:
                        room_stats[room_name]["최신날짜"] = date
                    if date < room_stats[room_name]["최초날짜"]:
                        room_stats[room_name]["최초날짜"] = date
                        
                except Exception:
                    pass
        
        # 날짜목록을 리스트로 변환
        for room_name in room_stats:
            room_stats[room_name]["날짜수"] = len(room_stats[room_name]["날짜목록"])
            room_stats[room_name]["날짜목록"] = sorted(list(room_stats[room_name]["날짜목록"]), reverse=True)
        
        # 게임수 기준으로 정렬
        sorted_rooms = sorted(room_stats.values(), key=lambda x: x["총게임수"], reverse=True)
        
        return {
            "rooms": sorted_rooms,
            "총방명수": len(room_stats),
            "총파일수": sum(r["파일수"] for r in room_stats.values()),
            "총게임수추정": sum(r["총게임수"] for r in room_stats.values())
        }
        
    except Exception as e:
        logger.error(f"방 요약 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"요약 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/packet-data/stats")
async def get_packet_stats():
    """패킷 데이터 통계 조회"""
    try:
        total_files = len(list(PACKET_FOLDER.rglob("*.txt")))
        total_games = 0
        rooms = set()
        dates = set()
        
        for file_path in PACKET_FOLDER.rglob("*.txt"):
            if file_path.is_file():
                file_data = extractor.parse_packet_file(file_path)
                total_games += len(file_data)
                
                if file_data:
                    rooms.add(file_data[0]['방명'])
                    dates.add(file_data[0]['날짜'])
        
        return {
            "총파일수": total_files,
            "총게임수": total_games,
            "방명수": len(rooms),
            "날짜수": len(dates),
            "최신날짜": max(dates) if dates else None
        }
        
    except Exception as e:
        logger.error(f"패킷 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/packet-data/rooms-display", response_class=HTMLResponse)
async def display_rooms_data():
    """방별 패킷 데이터 웹 표시 페이지 (리스트 형식)"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎰 방별 바카라 게임 데이터</title>
        <style>
            body { 
                font-family: 'Malgun Gothic', sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                min-height: 100vh;
            }
            .container { 
                max-width: 1600px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
                overflow: hidden;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 30px; 
                text-align: center; 
            }
            .header h1 { margin: 0; font-size: 28px; }
            .header p { margin: 10px 0 0 0; opacity: 0.9; }
            
            .controls { 
                display: flex; 
                gap: 15px; 
                padding: 20px 30px; 
                background: #f8f9fa; 
                border-bottom: 1px solid #dee2e6;
                align-items: center; 
                flex-wrap: wrap;
            }
            .controls input, .controls select, .controls button { 
                padding: 10px 15px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                font-size: 14px; 
            }
            .controls button { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                cursor: pointer; 
                border: none; 
                transition: all 0.3s;
                font-weight: bold;
            }
            .controls button:hover { 
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            .search-box {
                flex: 1;
                max-width: 300px;
                position: relative;
            }
            .search-box input {
                width: 100%;
                padding-left: 40px;
            }
            .search-box::before {
                content: "🔍";
                position: absolute;
                left: 15px;
                top: 50%;
                transform: translateY(-50%);
                z-index: 1;
            }
            
            .summary-stats { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 20px; 
                padding: 30px; 
                background: #f8f9fa;
            }
            .stat-card { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 20px; 
                border-radius: 12px; 
                text-align: center; 
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }
            .stat-value { 
                font-size: 32px; 
                font-weight: bold; 
                margin-bottom: 8px; 
            }
            .stat-label { 
                font-size: 14px; 
                opacity: 0.9; 
            }
            
            .rooms-container {
                padding: 30px;
                max-height: 800px;
                overflow-y: auto;
            }
            .room-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
                gap: 20px;
            }
            .room-card {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                overflow: hidden;
                transition: all 0.3s;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .room-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                border-color: #667eea;
            }
            .room-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 20px;
                position: relative;
            }
            .room-name {
                font-size: 16px;
                font-weight: bold;
                margin: 0;
            }
            .room-stats {
                font-size: 12px;
                opacity: 0.9;
                margin-top: 5px;
            }
            .room-body {
                padding: 15px;
                max-height: 300px;
                overflow-y: auto;
            }
            .game-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #f1f3f4;
            }
            .game-item:last-child {
                border-bottom: none;
            }
            .game-result {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .winner {
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
            }
            .winner.player { background: #ff6b6b; color: white; }
            .winner.banker { background: #4ecdc4; color: white; }
            .winner.tie { background: #ffa726; color: white; }
            .scores {
                font-family: 'Courier New', monospace;
                font-weight: bold;
                color: #495057;
            }
            .pairs {
                display: flex;
                gap: 4px;
            }
            .pair-badge {
                background: #6c757d;
                color: white;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            }
            .pair-badge.player { background: #ff6b6b; }
            .pair-badge.banker { background: #4ecdc4; }
            .game-meta {
                font-size: 11px;
                color: #6c757d;
            }
            
            .loading {
                text-align: center;
                padding: 100px 50px;
                color: #666;
                font-size: 18px;
            }
            .error {
                color: #dc3545;
                text-align: center;
                padding: 50px;
                font-size: 16px;
            }
            .no-data {
                text-align: center;
                padding: 100px 50px;
                color: #6c757d;
                font-size: 16px;
            }
            
            .refresh-info {
                text-align: center;
                color: #6c757d;
                font-size: 14px;
                padding: 20px 30px;
                background: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }
            
            /* 스크롤바 스타일링 */
            .rooms-container::-webkit-scrollbar,
            .room-body::-webkit-scrollbar {
                width: 8px;
            }
            .rooms-container::-webkit-scrollbar-track,
            .room-body::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 4px;
            }
            .rooms-container::-webkit-scrollbar-thumb,
            .room-body::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎰 방별 바카라 게임 데이터</h1>
                <p>실시간 패킷 데이터 방별 리스트 조회 시스템</p>
            </div>
            
            <div class="controls">
                <div class="search-box">
                    <input type="text" id="searchRoom" placeholder="방명 검색...">
                </div>
                <select id="dateFilter">
                    <option value="">전체 날짜</option>
                </select>
                <input type="number" id="limitInput" value="20" min="5" max="100" placeholder="방별 게임 수">
                <button onclick="loadRoomsData()">🔍 조회</button>
                <button onclick="loadRoomsData(true)">🔄 새로고침</button>
                <button onclick="loadSummary()">📊 요약</button>
            </div>
            
            <div class="summary-stats" id="summaryStats" style="display: none;">
            </div>
            
            <div id="loading" class="loading">
                <div>🎰 방별 데이터 로딩 중...</div>
                <div style="margin-top: 10px; font-size: 14px;">대용량 데이터 처리 중입니다. 잠시만 기다려주세요.</div>
            </div>
            <div id="error" class="error" style="display: none;"></div>
            
            <div class="rooms-container" id="roomsContainer" style="display: none;">
                <div class="room-grid" id="roomGrid"></div>
            </div>
            
            <div class="refresh-info">
                💡 실시간 업데이트: 새로운 패킷 데이터가 추가되면 "새로고침" 버튼을 클릭하세요.<br>
                🎲 총 47개 방명에서 1,449만개 게임 데이터를 실시간으로 조회할 수 있습니다.
            </div>
        </div>

        <script>
            let allRoomsData = {};
            let currentStats = {};
            
            function formatWinner(winner) {
                const classes = {
                    'Player': 'player',
                    'Banker': 'banker', 
                    'Tie': 'tie'
                };
                return `<span class="winner ${classes[winner] || ''}">${winner}</span>`;
            }
            
            function formatPairs(playerPair, bankerPair) {
                let html = '';
                if (playerPair) html += '<span class="pair-badge player">P</span>';
                if (bankerPair) html += '<span class="pair-badge banker">B</span>';
                return html || '<span style="color: #adb5bd;">-</span>';
            }
            
            function formatGameItem(game) {
                return `
                    <div class="game-item">
                        <div class="game-result">
                            ${formatWinner(game.승패)}
                            <span class="scores">${game.Player점수} : ${game.Banker점수}</span>
                            <div class="pairs">${formatPairs(game.Player페어, game.Banker페어)}</div>
                        </div>
                        <div class="game-meta">
                            #${game.게임번호} | ${game.날짜}
                        </div>
                    </div>
                `;
            }
            
            function createRoomCard(roomName, games) {
                if (!games || games.length === 0) return '';
                
                const latestGame = games[0];
                const totalGames = games.length;
                const playerWins = games.filter(g => g.승패 === 'Player').length;
                const bankerWins = games.filter(g => g.승패 === 'Banker').length;
                const ties = games.filter(g => g.승패 === 'Tie').length;
                
                return `
                    <div class="room-card">
                        <div class="room-header">
                            <div class="room-name">${roomName}</div>
                            <div class="room-stats">
                                ${totalGames}게임 | P:${playerWins} B:${bankerWins} T:${ties} | 최신: ${latestGame.날짜}
                            </div>
                        </div>
                        <div class="room-body">
                            ${games.slice(0, 20).map(game => formatGameItem(game)).join('')}
                            ${games.length > 20 ? `<div style="text-align: center; color: #6c757d; padding: 10px; font-size: 12px;">... 외 ${games.length - 20}개 게임 더</div>` : ''}
                        </div>
                    </div>
                `;
            }
            
            async function loadDates() {
                try {
                    const response = await fetch('/api/packet-data/dates');
                    const dates = await response.json();
                    
                    const dateFilter = document.getElementById('dateFilter');
                    dateFilter.innerHTML = '<option value="">전체 날짜</option>';
                    dates.dates.forEach(date => {
                        dateFilter.innerHTML += `<option value="${date}">${date}</option>`;
                    });
                } catch (error) {
                    console.error('날짜 목록 로드 오류:', error);
                }
            }
            
            async function loadSummary() {
                const summaryStats = document.getElementById('summaryStats');
                
                try {
                    const response = await fetch('/api/packet-data/room-summary');
                    const data = await response.json();
                    
                    summaryStats.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${data.총방명수}</div>
                            <div class="stat-label">총 방명 수</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.총파일수.toLocaleString()}</div>
                            <div class="stat-label">총 파일 수</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${Math.floor(data.총게임수추정 / 10000).toLocaleString()}만</div>
                            <div class="stat-label">총 게임 수 (추정)</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.rooms.length > 0 ? data.rooms[0].최신날짜 : 'N/A'}</div>
                            <div class="stat-label">최신 날짜</div>
                        </div>
                    `;
                    
                    summaryStats.style.display = 'grid';
                    
                } catch (error) {
                    console.error('요약 정보 로드 오류:', error);
                }
            }
            
            async function loadRoomsData(refresh = false) {
                const loading = document.getElementById('loading');
                const error = document.getElementById('error');
                const roomsContainer = document.getElementById('roomsContainer');
                
                loading.style.display = 'block';
                error.style.display = 'none';
                roomsContainer.style.display = 'none';
                
                try {
                    const dateFilter = document.getElementById('dateFilter').value;
                    const limit = document.getElementById('limitInput').value;
                    
                    let url = `/api/packet-data/by-rooms?limit_per_room=${limit}`;
                    if (dateFilter) url += `&date_filter=${encodeURIComponent(dateFilter)}`;
                    
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    
                    const data = await response.json();
                    allRoomsData = data.rooms;
                    currentStats = data.statistics;
                    
                    displayRoomsData();
                    
                    if (refresh) await loadSummary();
                    
                } catch (err) {
                    error.textContent = `데이터 로드 오류: ${err.message}`;
                    error.style.display = 'block';
                } finally {
                    loading.style.display = 'none';
                }
            }
            
            function displayRoomsData() {
                const roomGrid = document.getElementById('roomGrid');
                const roomsContainer = document.getElementById('roomsContainer');
                const searchTerm = document.getElementById('searchRoom').value.toLowerCase();
                
                if (!allRoomsData || Object.keys(allRoomsData).length === 0) {
                    roomGrid.innerHTML = '<div class="no-data">조회된 데이터가 없습니다.</div>';
                } else {
                    // 검색 필터 적용
                    const filteredRooms = Object.entries(allRoomsData).filter(([roomName]) => 
                        roomName.toLowerCase().includes(searchTerm)
                    );
                    
                    // 게임 수 기준으로 정렬
                    filteredRooms.sort((a, b) => b[1].length - a[1].length);
                    
                    roomGrid.innerHTML = filteredRooms.map(([roomName, games]) => 
                        createRoomCard(roomName, games)
                    ).join('');
                }
                
                roomsContainer.style.display = 'block';
            }
            
            // 검색 기능
            document.getElementById('searchRoom').addEventListener('input', () => {
                displayRoomsData();
            });
            
            // 엔터키 지원
            document.getElementById('searchRoom').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    loadRoomsData();
                }
            });
            
            // 초기 로드
            document.addEventListener('DOMContentLoaded', async () => {
                await Promise.all([loadDates(), loadSummary()]);
                await loadRoomsData();
                
                // 5분마다 자동 새로고침
                setInterval(() => loadRoomsData(true), 5 * 60 * 1000);
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/packet-data/display", response_class=HTMLResponse)
async def display_packet_data():
    """패킷 데이터 웹 표시 페이지 (기존 테이블 형식)"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>📦 실시간 패킷 데이터 조회</title>
        <style>
            body { font-family: 'Malgun Gothic', sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .controls { display: flex; gap: 15px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
            .controls input, .controls select, .controls button { 
                padding: 8px 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; 
            }
            .controls button { 
                background: #3498db; color: white; cursor: pointer; border: none; 
                transition: background 0.3s;
            }
            .controls button:hover { background: #2980b9; }
            .stats { 
                display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                gap: 15px; margin-bottom: 20px; 
            }
            .stat-card { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 15px; border-radius: 8px; text-align: center; 
            }
            .stat-value { font-size: 24px; font-weight: bold; }
            .stat-label { font-size: 12px; opacity: 0.9; }
            .data-table { 
                width: 100%; border-collapse: collapse; margin-top: 20px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;
            }
            .data-table th, .data-table td { 
                padding: 12px; text-align: center; border-bottom: 1px solid #eee; 
            }
            .data-table th { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; font-weight: bold; font-size: 14px; 
            }
            .data-table tr:nth-child(even) { background-color: #f8f9fa; }
            .data-table tr:hover { background-color: #e3f2fd; }
            .winner-player { color: #e74c3c; font-weight: bold; }
            .winner-banker { color: #3498db; font-weight: bold; }
            .winner-tie { color: #f39c12; font-weight: bold; }
            .pair-indicator { 
                display: inline-block; padding: 2px 6px; border-radius: 3px; 
                font-size: 11px; font-weight: bold; color: white; margin: 0 2px;
            }
            .pair-player { background: #e74c3c; }
            .pair-banker { background: #3498db; }
            .loading { text-align: center; padding: 50px; color: #666; }
            .error { color: #e74c3c; text-align: center; padding: 20px; }
            .refresh-info { 
                text-align: center; color: #666; font-size: 14px; 
                margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 5px; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📦 실시간 패킷 데이터 조회 시스템</h1>
            
            <div class="controls">
                <select id="roomFilter">
                    <option value="">전체 방</option>
                </select>
                <select id="dateFilter">
                    <option value="">전체 날짜</option>
                </select>
                <input type="number" id="limitInput" value="100" min="10" max="1000" placeholder="표시 개수">
                <button onclick="loadData()">🔍 조회</button>
                <button onclick="loadData(true)">🔄 새로고침</button>
            </div>
            
            <div class="stats" id="stats"></div>
            
            <div id="loading" class="loading">📊 데이터 로딩 중...</div>
            <div id="error" class="error" style="display: none;"></div>
            
            <table class="data-table" id="dataTable" style="display: none;">
                <thead>
                    <tr>
                        <th>방명</th>
                        <th>날짜</th>
                        <th>게임#</th>
                        <th>승패</th>
                        <th>Player</th>
                        <th>Banker</th>
                        <th>페어</th>
                        <th>파일명</th>
                    </tr>
                </thead>
                <tbody id="dataBody"></tbody>
            </table>
            
            <div class="refresh-info">
                💡 실시간 업데이트: 새로운 패킷 데이터가 추가되면 "새로고침" 버튼을 클릭하세요.
            </div>
        </div>

        <script>
            let allData = [];
            
            function formatWinner(winner) {
                const classes = {
                    'Player': 'winner-player',
                    'Banker': 'winner-banker', 
                    'Tie': 'winner-tie'
                };
                return `<span class="${classes[winner] || ''}">${winner}</span>`;
            }
            
            function formatPairs(playerPair, bankerPair) {
                let html = '';
                if (playerPair) html += '<span class="pair-indicator pair-player">P</span>';
                if (bankerPair) html += '<span class="pair-indicator pair-banker">B</span>';
                return html || '-';
            }
            
            async function loadFilters() {
                try {
                    const [roomsRes, datesRes] = await Promise.all([
                        fetch('/api/packet-data/rooms'),
                        fetch('/api/packet-data/dates')
                    ]);
                    
                    const rooms = await roomsRes.json();
                    const dates = await datesRes.json();
                    
                    const roomFilter = document.getElementById('roomFilter');
                    roomFilter.innerHTML = '<option value="">전체 방</option>';
                    rooms.rooms.forEach(room => {
                        roomFilter.innerHTML += `<option value="${room}">${room}</option>`;
                    });
                    
                    const dateFilter = document.getElementById('dateFilter');
                    dateFilter.innerHTML = '<option value="">전체 날짜</option>';
                    dates.dates.forEach(date => {
                        dateFilter.innerHTML += `<option value="${date}">${date}</option>`;
                    });
                } catch (error) {
                    console.error('필터 로드 오류:', error);
                }
            }
            
            async function loadStats() {
                try {
                    const response = await fetch('/api/packet-data/stats');
                    const stats = await response.json();
                    
                    document.getElementById('stats').innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${stats.총파일수}</div>
                            <div class="stat-label">총 파일수</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.총게임수.toLocaleString()}</div>
                            <div class="stat-label">총 게임수</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.방명수}</div>
                            <div class="stat-label">방명 종류</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.최신날짜}</div>
                            <div class="stat-label">최신 날짜</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('통계 로드 오류:', error);
                }
            }
            
            async function loadData(refresh = false) {
                const loading = document.getElementById('loading');
                const error = document.getElementById('error');
                const table = document.getElementById('dataTable');
                
                loading.style.display = 'block';
                error.style.display = 'none';
                table.style.display = 'none';
                
                try {
                    const roomFilter = document.getElementById('roomFilter').value;
                    const dateFilter = document.getElementById('dateFilter').value;
                    const limit = document.getElementById('limitInput').value;
                    
                    let url = `/api/packet-data/all?limit=${limit}`;
                    if (roomFilter) url += `&room_filter=${encodeURIComponent(roomFilter)}`;
                    if (dateFilter) url += `&date_filter=${encodeURIComponent(dateFilter)}`;
                    
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    
                    allData = await response.json();
                    displayData(allData);
                    
                    if (refresh) await loadStats();
                    
                } catch (err) {
                    error.textContent = `데이터 로드 오류: ${err.message}`;
                    error.style.display = 'block';
                } finally {
                    loading.style.display = 'none';
                }
            }
            
            function displayData(data) {
                const tbody = document.getElementById('dataBody');
                const table = document.getElementById('dataTable');
                
                if (!data || data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8">데이터가 없습니다.</td></tr>';
                } else {
                    tbody.innerHTML = data.map(row => `
                        <tr>
                            <td><strong>${row.방명}</strong></td>
                            <td>${row.날짜}</td>
                            <td>${row.게임번호}</td>
                            <td>${formatWinner(row.승패)}</td>
                            <td><strong>${row.Player점수}</strong></td>
                            <td><strong>${row.Banker점수}</strong></td>
                            <td>${formatPairs(row.Player페어, row.Banker페어)}</td>
                            <td><small>${row.파일명}</small></td>
                        </tr>
                    `).join('');
                }
                
                table.style.display = 'table';
            }
            
            // 초기 로드
            document.addEventListener('DOMContentLoaded', async () => {
                await Promise.all([loadFilters(), loadStats()]);
                await loadData();
                
                // 5분마다 자동 새로고침
                setInterval(() => loadData(true), 5 * 60 * 1000);
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 카드 표시 모드 관련 엔드포인트
@router.get("/packet-data/card-modes")
async def get_card_display_modes():
    """사용 가능한 카드 표시 모드 목록"""
    extractor = PacketDataExtractor()
    return {
        "available_modes": extractor.card_display.get_available_modes(),
        "current_mode": extractor.card_display.current_mode
    }

@router.get("/packet-data/demo-cards")
async def get_demo_cards_display():
    """데모 카드 데이터 표시"""
    try:
        extractor = PacketDataExtractor()
        
        # 샘플 게임 데이터
        sample_games = [
            {"winner": "Banker", "playerScore": 3, "bankerScore": 7, "playerPair": False, "bankerPair": False, "natural": False},
            {"winner": "Banker", "playerScore": 2, "bankerScore": 8, "playerPair": False, "bankerPair": False, "natural": True}, 
            {"winner": "Player", "playerScore": 8, "bankerScore": 1, "playerPair": True, "bankerPair": False, "natural": True},
            {"winner": "Tie", "playerScore": 5, "bankerScore": 5, "playerPair": False, "bankerPair": True, "natural": False}
        ]
        
        # 각 모드별로 카드 정보 생성
        results = {}
        for mode in ['demo', 'hybrid', 'enhanced', 'raw']:
            results[mode] = []
            for idx, game in enumerate(sample_games):
                card_info = extractor.card_display.generate_card_info(game, idx, mode)
                results[mode].append({
                    "game_index": idx + 1,
                    "game_data": game,
                    "card_info": card_info
                })
        
        return {
            "title": "카드 표시 모드 비교 데모",
            "modes": results,
            "available_modes": extractor.card_display.get_available_modes()
        }
        
    except Exception as e:
        logger.error(f"데모 카드 표시 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))