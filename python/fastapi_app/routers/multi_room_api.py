#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다중 방 API 라우터
모든 바카라 방의 종합 통계 및 상세 정보 제공
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
import logging
from datetime import datetime

from services.multi_room_analyzer import get_multi_room_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/multi-room", tags=["multi-room"])

@router.get("/rooms")
async def get_all_rooms(
    force_refresh: bool = Query(False, description="강제 새로고침"),
    room_type: Optional[str] = Query(None, description="방 타입 필터")
):
    """모든 방의 목록과 기본 통계 조회"""
    try:
        analyzer = await get_multi_room_analyzer()
        room_stats, global_stats = await analyzer.get_all_rooms_stats(force_refresh)
        
        # 방 타입 필터링
        filtered_rooms = room_stats
        if room_type:
            filtered_rooms = [room for room in room_stats if room.room_type == room_type]
        
        # 응답 데이터 구성
        rooms_data = []
        for room in filtered_rooms:
            room_data = {
                "room_name": room.room_name,
                "room_type": room.room_type,
                "room_id": room.room_id,
                "display_name": f"{room.room_type} {room.room_name}",
                "total_games": room.total_games,
                "player_pairs": room.player_pairs,
                "banker_pairs": room.banker_pairs,
                "both_pairs": room.both_pairs,
                "win_rate": room.win_rate,
                "last_activity": room.last_activity,
                "files_count": room.files_count,
                "status": "active" if room.total_games > 0 else "inactive"
            }
            rooms_data.append(room_data)
        
        # 활성 방 우선 정렬
        rooms_data.sort(key=lambda x: (x["status"] == "inactive", -x["total_games"]))
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "total_rooms": len(rooms_data),
            "rooms": rooms_data,
            "global_stats": {
                "total_rooms": global_stats.total_rooms,
                "total_games": global_stats.total_games,
                "total_player_pairs": global_stats.total_player_pairs,
                "total_banker_pairs": global_stats.total_banker_pairs,
                "total_both_pairs": global_stats.total_both_pairs,
                "active_rooms": global_stats.active_rooms,
                "room_types": global_stats.room_types,
                "last_update": global_stats.last_update
            }
        }
        
    except Exception as e:
        logger.error(f"전체 방 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"방 목록 조회 실패: {str(e)}")

@router.get("/rooms/{room_type}/{room_name}")
async def get_room_details(room_type: str, room_name: str):
    """특정 방의 상세 정보 조회"""
    try:
        analyzer = await get_multi_room_analyzer()
        room_data = await analyzer.get_room_details(room_name, room_type)
        
        if not room_data:
            raise HTTPException(status_code=404, detail="방을 찾을 수 없습니다")
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "room": {
                "room_name": room_data["room_name"],
                "room_type": room_data["room_type"],
                "room_id": room_data["room_id"],
                "display_name": f"{room_data['room_type']} {room_data['room_name']}",
                "statistics": {
                    "total_games": room_data["total_games"],
                    "player_pairs": room_data["player_pairs"],
                    "banker_pairs": room_data["banker_pairs"],
                    "both_pairs": room_data["both_pairs"],
                    "win_rate": room_data["win_rate"],
                    "files_count": room_data["files_count"],
                    "total_lines": room_data["total_lines"]
                },
                "last_activity": room_data["last_activity"],
                "status": "active" if room_data["total_games"] > 0 else "inactive"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"방 상세 정보 조회 실패 ({room_type} {room_name}): {e}")
        raise HTTPException(status_code=500, detail=f"방 상세 정보 조회 실패: {str(e)}")

@router.get("/rooms/{room_type}/{room_name}/pairs")
async def get_room_pairs(
    room_type: str, 
    room_name: str,
    limit: int = Query(50, ge=1, le=200, description="조회할 페어 수")
):
    """특정 방의 페어 목록 조회"""
    try:
        analyzer = await get_multi_room_analyzer()
        pairs = await analyzer.get_room_pairs_list(room_name, room_type, limit)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "room_info": {
                "room_name": room_name,
                "room_type": room_type,
                "display_name": f"{room_type} {room_name}"
            },
            "pairs_count": len(pairs),
            "pairs": pairs
        }
        
    except Exception as e:
        logger.error(f"방 페어 목록 조회 실패 ({room_type} {room_name}): {e}")
        raise HTTPException(status_code=500, detail=f"페어 목록 조회 실패: {str(e)}")

@router.get("/statistics")
async def get_global_statistics(force_refresh: bool = Query(False)):
    """전체 통계 조회"""
    try:
        analyzer = await get_multi_room_analyzer()
        room_stats, global_stats = await analyzer.get_all_rooms_stats(force_refresh)
        
        # 방 타입별 상위 방들
        top_rooms_by_type = {}
        for room in room_stats[:20]:  # 상위 20개 방
            room_type = room.room_type
            if room_type not in top_rooms_by_type:
                top_rooms_by_type[room_type] = []
            
            if len(top_rooms_by_type[room_type]) < 5:  # 타입당 최대 5개
                top_rooms_by_type[room_type].append({
                    "room_name": room.room_name,
                    "display_name": f"{room.room_type} {room.room_name}",
                    "total_games": room.total_games,
                    "player_pairs": room.player_pairs,
                    "banker_pairs": room.banker_pairs,
                    "win_rate": room.win_rate
                })
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "overview": {
                    "total_rooms": global_stats.total_rooms,
                    "active_rooms": global_stats.active_rooms,
                    "inactive_rooms": global_stats.total_rooms - global_stats.active_rooms,
                    "total_games": global_stats.total_games,
                    "total_player_pairs": global_stats.total_player_pairs,
                    "total_banker_pairs": global_stats.total_banker_pairs,
                    "total_both_pairs": global_stats.total_both_pairs,
                    "overall_player_pair_rate": round((global_stats.total_player_pairs / global_stats.total_games * 100) if global_stats.total_games > 0 else 0, 2),
                    "overall_banker_pair_rate": round((global_stats.total_banker_pairs / global_stats.total_games * 100) if global_stats.total_games > 0 else 0, 2)
                },
                "room_types": global_stats.room_types,
                "top_rooms_by_type": top_rooms_by_type,
                "last_update": global_stats.last_update
            }
        }
        
    except Exception as e:
        logger.error(f"전체 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.get("/room-types")
async def get_room_types():
    """방 타입 목록 조회"""
    try:
        analyzer = await get_multi_room_analyzer()
        room_stats, global_stats = await analyzer.get_all_rooms_stats()
        
        room_types_detail = []
        for room_type, count in global_stats.room_types.items():
            # 해당 타입의 방들 통계
            type_rooms = [room for room in room_stats if room.room_type == room_type]
            type_games = sum(room.total_games for room in type_rooms)
            type_player_pairs = sum(room.player_pairs for room in type_rooms)
            type_banker_pairs = sum(room.banker_pairs for room in type_rooms)
            active_count = sum(1 for room in type_rooms if room.total_games > 0)
            
            room_types_detail.append({
                "room_type": room_type,
                "total_rooms": count,
                "active_rooms": active_count,
                "total_games": type_games,
                "player_pairs": type_player_pairs,
                "banker_pairs": type_banker_pairs,
                "player_pair_rate": round((type_player_pairs / type_games * 100) if type_games > 0 else 0, 2)
            })
        
        # 게임 수 기준으로 정렬
        room_types_detail.sort(key=lambda x: x["total_games"], reverse=True)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "room_types": room_types_detail
        }
        
    except Exception as e:
        logger.error(f"방 타입 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"방 타입 조회 실패: {str(e)}")

@router.post("/refresh")
async def refresh_all_data():
    """모든 데이터 강제 새로고침"""
    try:
        analyzer = await get_multi_room_analyzer()
        
        # 캐시 클리어 및 강제 새로고침
        analyzer._cache.clear()
        analyzer._cache_timestamp.clear()
        
        room_stats, global_stats = await analyzer.get_all_rooms_stats(force_refresh=True)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "message": "모든 데이터가 성공적으로 새로고침되었습니다",
            "refreshed_rooms": len(room_stats),
            "total_games": global_stats.total_games
        }
        
    except Exception as e:
        logger.error(f"데이터 새로고침 실패: {e}")
        raise HTTPException(status_code=500, detail=f"새로고침 실패: {str(e)}")