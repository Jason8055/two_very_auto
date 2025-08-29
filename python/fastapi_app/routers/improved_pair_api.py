#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 페어 API 라우터 - Two Very Auto
요구사항: 첫 두장만 페어 검사, 회차 정보와 함께 리스트 출력
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os

# 개선된 페어 감지기 임포트
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from improved_pair_detector import improved_pair_detector

router = APIRouter()
logger = logging.getLogger(__name__)

# 패킷 폴더 경로
PACKET_FOLDER = Path("F:/two very auto 25.08.23/packet")

@router.get("/pairs/list", response_model=Dict[str, Any])
async def get_pairs_list(
    limit: int = Query(100, ge=1, le=1000, description="결과 제한수"),
    room_filter: Optional[str] = Query(None, description="방명 필터 (예: '바카라 A')"),
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYYMMDD)"),
    pair_type: Optional[str] = Query(None, description="페어 타입 필터 (player, banker, both)")
):
    """
    첫 두장 페어 정보를 회차와 함께 리스트로 조회
    
    - 첫 두장만 페어 검사 (3장 이상 받았을 때는 무시)
    - 회차 정보 포함
    - 리스트 형식으로 출력
    """
    try:
        all_pairs = []
        scanned_files = 0
        
        # 패킷 폴더 탐색
        for date_folder in PACKET_FOLDER.iterdir():
            if not date_folder.is_dir():
                continue
                
            # 날짜 필터 적용
            if date_filter and date_filter not in date_folder.name:
                continue
            
            for packet_file in date_folder.glob("*.txt"):
                # 메인/거부 파일 제외
                if packet_file.name in ['Main.txt', 'Rejected.txt']:
                    continue
                
                # 방명 필터 적용
                if room_filter and room_filter not in packet_file.name:
                    continue
                
                scanned_files += 1
                
                # 개선된 페어 감지기로 분석
                pairs_found = improved_pair_detector.process_packet_file(packet_file)
                
                # 페어 타입 필터 적용
                if pair_type:
                    filtered_pairs = []
                    for pair in pairs_found:
                        if pair_type.lower() == 'player':
                            if any(p['type'] == 'Player' for p in pair['pairs']):
                                filtered_pairs.append(pair)
                        elif pair_type.lower() == 'banker':
                            if any(p['type'] == 'Banker' for p in pair['pairs']):
                                filtered_pairs.append(pair)
                        elif pair_type.lower() == 'both':
                            if pair.get('special', {}).get('both_pairs', False):
                                filtered_pairs.append(pair)
                    pairs_found = filtered_pairs
                
                all_pairs.extend(pairs_found)
        
        # 회차 순으로 정렬 (최신순)
        all_pairs.sort(key=lambda x: (x['date'], x['room'], x['round']), reverse=True)
        
        # 제한 적용
        limited_pairs = all_pairs[:limit]
        
        # 통계 생성
        summary = improved_pair_detector.get_pairs_summary(limited_pairs)
        
        return {
            "success": True,
            "message": f"첫 두장 페어 {len(limited_pairs)}건 발견",
            "data": {
                "pairs_list": limited_pairs,
                "summary": summary,
                "filters_applied": {
                    "limit": limit,
                    "room_filter": room_filter,
                    "date_filter": date_filter,
                    "pair_type": pair_type
                },
                "scan_info": {
                    "files_scanned": scanned_files,
                    "total_pairs_found": len(all_pairs),
                    "pairs_returned": len(limited_pairs)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"페어 리스트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"페어 조회 중 오류 발생: {str(e)}")

@router.get("/pairs/formatted", response_class=HTMLResponse)
async def get_pairs_formatted(
    limit: int = Query(50, ge=1, le=500, description="결과 제한수"),
    room_filter: Optional[str] = Query(None, description="방명 필터")
):
    """
    페어 정보를 보기 좋은 HTML 형식으로 출력
    """
    try:
        # 페어 데이터 조회
        pairs_response = await get_pairs_list(limit=limit, room_filter=room_filter)
        pairs_list = pairs_response["data"]["pairs_list"]
        summary = pairs_response["data"]["summary"]
        
        # HTML 생성
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>바카라 페어 정보 - Two Very Auto</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }}
                .summary {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .pair-item {{ background: white; margin: 10px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #3498db; }}
                .pair-special {{ border-left-color: #f39c12; }}
                .pair-info {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
                .pair-badge {{ padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; margin: 2px; }}
                .badge-player {{ background: #e74c3c; }}
                .badge-banker {{ background: #3498db; }}
                .badge-both {{ background: #f39c12; }}
                .game-result {{ color: #7f8c8d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎰 바카라 페어 감지 결과</h1>
                <p>첫 두장 카드 페어만 감지 • 회차 정보 포함</p>
            </div>
            
            <div class="summary">
                <h3>📊 요약 정보</h3>
                <p><strong>총 페어:</strong> {summary['total_pairs']}건</p>
                <p><strong>플레이어 페어:</strong> {summary['player_pairs']}건</p>
                <p><strong>뱅커 페어:</strong> {summary['banker_pairs']}건</p>
                <p><strong>양쪽 페어:</strong> {summary['both_pairs']}건</p>
                <p><strong>발견된 방:</strong> {', '.join(summary['rooms'])}</p>
                {f"<p><strong>기간:</strong> {summary['date_range']['start']} ~ {summary['date_range']['end']}</p>" if summary.get('date_range') else ""}
            </div>
        """
        
        # 페어 목록 추가
        for i, pair in enumerate(pairs_list, 1):
            special_class = "pair-special" if pair.get('special', {}).get('both_pairs') else ""
            
            html_content += f"""
            <div class="pair-item {special_class}">
                <div class="pair-info">
                    <div>
                        <strong>#{i} • {pair['round']}회차</strong> • {pair['room']}
                    </div>
                    <div>
                        {pair['timestamp']}
                    </div>
                </div>
                
                <div>
            """
            
            # 페어 배지 추가
            for p in pair['pairs']:
                badge_class = f"badge-{p['type'].lower()}"
                html_content += f'<span class="pair-badge {badge_class}">{p["symbol"]} {p["description"]}</span>'
            
            # 특별한 경우 (양쪽 페어)
            if pair.get('special', {}).get('both_pairs'):
                html_content += f'<span class="pair-badge badge-both">{pair["special"]["symbol"]} 매우 드문 케이스!</span>'
            
            # 게임 결과
            result = pair['game_result']
            natural_text = "⭐ 내추럴" if result['natural'] else ""
            
            html_content += f"""
                </div>
                
                <div class="game-result">
                    🏆 {result['winner']} 승 • Player: {result['player_score']} vs Banker: {result['banker_score']} {natural_text}
                </div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"포맷된 페어 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"페어 조회 중 오류 발생: {str(e)}")

@router.get("/pairs/text", response_class=JSONResponse)
async def get_pairs_text(
    limit: int = Query(20, ge=1, le=100, description="결과 제한수"),
    room_filter: Optional[str] = Query(None, description="방명 필터")
):
    """
    페어 정보를 텍스트 형식으로 출력 (콘솔 출력용)
    """
    try:
        # 페어 데이터 조회
        pairs_response = await get_pairs_list(limit=limit, room_filter=room_filter)
        pairs_list = pairs_response["data"]["pairs_list"]
        
        # 텍스트 형식으로 포맷
        formatted_text = improved_pair_detector.format_pairs_output(pairs_list)
        
        return {
            "success": True,
            "formatted_output": formatted_text,
            "pairs_count": len(pairs_list),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"텍스트 페어 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"페어 조회 중 오류 발생: {str(e)}")

@router.get("/pairs/live/{room_name}")
async def get_live_pairs(room_name: str):
    """
    특정 방의 최신 페어 정보 실시간 조회
    """
    try:
        # 오늘 날짜로 필터링
        today = datetime.now().strftime('%Y%m%d')
        
        pairs_response = await get_pairs_list(
            limit=10, 
            room_filter=room_name,
            date_filter=today
        )
        
        pairs_list = pairs_response["data"]["pairs_list"]
        
        if not pairs_list:
            return {
                "success": True,
                "message": f"{room_name} 방에서 오늘 페어를 찾을 수 없습니다",
                "room": room_name,
                "pairs": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # 최신 페어만 반환
        latest_pair = pairs_list[0]
        
        return {
            "success": True,
            "message": f"{room_name} 최신 페어 정보",
            "room": room_name,
            "latest_pair": latest_pair,
            "recent_pairs_count": len(pairs_list),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"실시간 페어 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"실시간 페어 조회 중 오류 발생: {str(e)}")

# 테스트 엔드포인트
@router.get("/pairs/test")
async def test_pair_detector():
    """페어 감지기 테스트"""
    try:
        # 샘플 패킷 데이터로 테스트
        sample_packet = '''
        [08:46:12] {"id":"test","type":"baccarat.encodedShoeState","args":{"stats":{"gameCount":3},"history":"test","history_v2":[
            {"winner":"Banker","playerScore":1,"bankerScore":4,"playerPair":true},
            {"winner":"Player","playerScore":8,"bankerScore":1,"bankerPair":true},
            {"winner":"Tie","playerScore":2,"bankerScore":2,"playerPair":true,"bankerPair":true}
        ],"tableId":"test_table"},"time":1754696775387}
        '''
        
        pairs = improved_pair_detector.analyze_packet_data(sample_packet, "테스트 바카라 A")
        formatted_output = improved_pair_detector.format_pairs_output(pairs)
        summary = improved_pair_detector.get_pairs_summary(pairs)
        
        return {
            "success": True,
            "message": "페어 감지기 테스트 완료",
            "test_data": {
                "pairs_found": pairs,
                "formatted_output": formatted_output,
                "summary": summary
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 중 오류 발생: {str(e)}")