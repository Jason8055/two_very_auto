#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 테스트 페어 API - 타임아웃 방지
"""

from fastapi import APIRouter, Query
from typing import Dict, Any
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test-pairs", response_model=Dict[str, Any])
async def get_test_pairs(limit: int = Query(5, ge=1, le=20)):
    """테스트용 간단한 페어 API"""
    try:
        # 테스트 데이터 생성
        test_pairs = []
        for i in range(min(limit, 5)):
            test_pairs.append({
                "game_number": f"TEST_{i+1}",
                "pair_type": ["플레이어 페어"],
                "pair_details": {
                    "player_pair": True,
                    "banker_pair": False,
                    "both_pairs": False
                },
                "player_score": 7,
                "banker_score": 5,
                "winner": "플레이어",
                "table_id": f"테스트테이블{i+1}",
                "room_name": f"테스트룸{i+1}",
                "timestamp": datetime.now().isoformat(),
                "visualization": {
                    "game_info": {},
                    "pair_visualization": []
                }
            })
        
        stats = {
            "total_pairs": len(test_pairs),
            "player_pairs": len([p for p in test_pairs if p["pair_details"]["player_pair"]]),
            "banker_pairs": len([p for p in test_pairs if p["pair_details"]["banker_pair"]]),
            "both_pairs": len([p for p in test_pairs if p["pair_details"]["both_pairs"]])
        }
        
        return {
            "success": True,
            "message": f"테스트 데이터 {len(test_pairs)}개 생성",
            "statistics": stats,
            "pairs": test_pairs,
            "total_files_scanned": 0,
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "test_mode": True,
                "processing_time_seconds": 0.001
            }
        }
        
    except Exception as e:
        logger.error(f"테스트 페어 API 오류: {e}")
        return {
            "success": False,
            "message": "테스트 API 오류",
            "error": str(e),
            "statistics": {"total_pairs": 0, "player_pairs": 0, "banker_pairs": 0, "both_pairs": 0},
            "pairs": [],
            "total_files_scanned": 0,
            "timestamp": datetime.now().isoformat()
        }