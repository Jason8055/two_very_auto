#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
과거 게임 데이터 조회 API 라우터 - FastAPI
패킷 처리된 과거 게임 데이터를 조회하고 분석하는 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import json

from services.database import DatabaseManager
from services.optimized_database import OptimizedDatabaseManager
from models.response import StatsResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 데이터베이스 의존성
async def get_db():
    db = DatabaseManager()
    await db.initialize()
    try:
        yield db
    finally:
        await db.close()

async def get_optimized_db():
    db = OptimizedDatabaseManager()
    await db.initialize()
    try:
        yield db
    finally:
        await db.close()

@router.get("/games/history")
async def get_games_history(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(50, ge=1, le=500, description="페이지당 항목 수"),
    date: Optional[str] = Query(None, description="날짜 필터 (YYYYMMDD)"),
    table_name: Optional[str] = Query(None, description="테이블명 필터"),
    winner: Optional[str] = Query(None, description="승자 필터 (Player/Banker/Tie)"),
    has_pair: Optional[bool] = Query(None, description="페어 여부 필터"),
    sort_by: str = Query("timestamp", description="정렬 기준 (timestamp, game_number)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    db: OptimizedDatabaseManager = Depends(get_optimized_db)
):
    """과거 게임 데이터 조회 (페이징 지원)"""
    try:
        logger.info(f"게임 히스토리 조회 요청: page={page}, limit={limit}, date={date}")
        
        # 쿼리 조건 구성
        conditions = []
        params = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        if table_name:
            conditions.append("table_name LIKE ?")
            params.append(f"%{table_name}%")
        
        if winner:
            conditions.append("winner = ?")
            params.append(winner)
        
        if has_pair is not None:
            conditions.append("(player_pair = 1 OR banker_pair = 1) = ?")
            params.append(has_pair)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # 정렬 검증
        valid_sort_columns = ["timestamp", "game_number", "id"]
        if sort_by not in valid_sort_columns:
            sort_by = "timestamp"
        
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"
        
        # 오프셋 계산
        offset = (page - 1) * limit
        
        # 메인 쿼리
        query = f"""
        SELECT 
            id, table_id, table_name, game_number, winner,
            player_score, banker_score, player_pair, banker_pair,
            natural, timestamp, date, source_file
        FROM games 
        {where_clause}
        ORDER BY {sort_by} {sort_order.upper()}
        LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        # 데이터 조회
        async with db.pool.get_connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            # 컬럼명 가져오기
            columns = [description[0] for description in cursor.description]
            
            # 결과를 딕셔너리로 변환
            games = []
            for row in rows:
                game = dict(zip(columns, row))
                # 페어 정보 추가 처리
                game['has_any_pair'] = bool(game.get('player_pair') or game.get('banker_pair'))
                games.append(game)
            
            # 총 개수 조회
            count_query = f"SELECT COUNT(*) FROM games {where_clause}"
            count_cursor = await conn.execute(count_query, params[:-2])  # limit, offset 제외
            total_count = (await count_cursor.fetchone())[0]
        
        # 페이징 정보
        total_pages = (total_count + limit - 1) // limit
        
        response = {
            "success": True,
            "data": {
                "games": games,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "limit": limit,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                },
                "filters": {
                    "date": date,
                    "table_name": table_name,
                    "winner": winner,
                    "has_pair": has_pair,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"게임 히스토리 조회 완료: {len(games)}개 게임, 총 {total_count}개")
        return response
        
    except Exception as e:
        logger.error(f"게임 히스토리 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"게임 히스토리 조회 실패: {str(e)}")

@router.get("/games/by-table/{table_name}")
async def get_games_by_table(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000, description="최대 게임 수"),
    date: Optional[str] = Query(None, description="날짜 필터 (YYYYMMDD)"),
    db: OptimizedDatabaseManager = Depends(get_optimized_db)
):
    """특정 테이블의 최근 게임 조회"""
    try:
        logger.info(f"테이블별 게임 조회: {table_name}, limit={limit}")
        
        # 쿼리 조건
        conditions = ["table_name LIKE ?"]
        params = [f"%{table_name}%"]
        
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            id, table_id, table_name, game_number, winner,
            player_score, banker_score, player_pair, banker_pair,
            natural, timestamp, date, source_file
        FROM games 
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ?
        """
        
        params.append(limit)
        
        async with db.pool.get_connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            games = []
            for row in rows:
                game = dict(zip(columns, row))
                game['has_any_pair'] = bool(game.get('player_pair') or game.get('banker_pair'))
                games.append(game)
        
        # 간단한 통계 계산
        if games:
            total_games = len(games)
            player_wins = sum(1 for g in games if g['winner'] == 'Player')
            banker_wins = sum(1 for g in games if g['winner'] == 'Banker')
            ties = sum(1 for g in games if g['winner'] == 'Tie')
            pairs = sum(1 for g in games if g['has_any_pair'])
            
            stats = {
                "total_games": total_games,
                "player_wins": player_wins,
                "banker_wins": banker_wins,
                "ties": ties,
                "pairs": pairs,
                "win_rates": {
                    "player": round(player_wins / total_games * 100, 1) if total_games > 0 else 0,
                    "banker": round(banker_wins / total_games * 100, 1) if total_games > 0 else 0,
                    "tie": round(ties / total_games * 100, 1) if total_games > 0 else 0
                },
                "pair_rate": round(pairs / total_games * 100, 1) if total_games > 0 else 0
            }
        else:
            stats = {
                "total_games": 0,
                "player_wins": 0,
                "banker_wins": 0,
                "ties": 0,
                "pairs": 0,
                "win_rates": {"player": 0, "banker": 0, "tie": 0},
                "pair_rate": 0
            }
        
        response = {
            "success": True,
            "data": {
                "table_name": table_name,
                "games": games,
                "statistics": stats
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"테이블별 게임 조회 완료: {len(games)}개 게임")
        return response
        
    except Exception as e:
        logger.error(f"테이블별 게임 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"테이블별 게임 조회 실패: {str(e)}")

@router.get("/games/by-date/{date}")
async def get_games_by_date(
    date: str,
    db: OptimizedDatabaseManager = Depends(get_optimized_db)
):
    """특정 날짜의 게임 조회 및 통계"""
    try:
        logger.info(f"날짜별 게임 조회: {date}")
        
        # 날짜 형식 검증
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYYMMDD)")
        
        query = """
        SELECT 
            table_name, winner, player_score, banker_score,
            player_pair, banker_pair, natural, timestamp,
            COUNT(*) as game_count
        FROM games 
        WHERE date = ?
        GROUP BY table_name, winner, player_score, banker_score, 
                 player_pair, banker_pair, natural, timestamp
        ORDER BY timestamp DESC
        """
        
        async with db.pool.get_connection() as conn:
            cursor = await conn.execute(query, [date])
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            games = [dict(zip(columns, row)) for row in rows]
            
            # 날짜별 전체 통계
            stats_query = """
            SELECT 
                COUNT(*) as total_games,
                COUNT(DISTINCT table_name) as total_tables,
                SUM(CASE WHEN winner = 'Player' THEN 1 ELSE 0 END) as player_wins,
                SUM(CASE WHEN winner = 'Banker' THEN 1 ELSE 0 END) as banker_wins,
                SUM(CASE WHEN winner = 'Tie' THEN 1 ELSE 0 END) as ties,
                SUM(CASE WHEN player_pair = 1 OR banker_pair = 1 THEN 1 ELSE 0 END) as pairs,
                SUM(CASE WHEN natural = 1 THEN 1 ELSE 0 END) as naturals
            FROM games 
            WHERE date = ?
            """
            
            stats_cursor = await conn.execute(stats_query, [date])
            stats_row = await stats_cursor.fetchone()
            stats_columns = [description[0] for description in stats_cursor.description]
            stats = dict(zip(stats_columns, stats_row))
            
            # 테이블별 통계
            table_stats_query = """
            SELECT 
                table_name,
                COUNT(*) as games,
                SUM(CASE WHEN winner = 'Player' THEN 1 ELSE 0 END) as player_wins,
                SUM(CASE WHEN winner = 'Banker' THEN 1 ELSE 0 END) as banker_wins,
                SUM(CASE WHEN winner = 'Tie' THEN 1 ELSE 0 END) as ties
            FROM games 
            WHERE date = ?
            GROUP BY table_name
            ORDER BY games DESC
            """
            
            table_cursor = await conn.execute(table_stats_query, [date])
            table_rows = await table_cursor.fetchall()
            table_columns = [description[0] for description in table_cursor.description]
            table_stats = [dict(zip(table_columns, row)) for row in table_rows]
        
        # 승률 계산
        total_games = stats.get('total_games', 0)
        if total_games > 0:
            stats['win_rates'] = {
                "player": round(stats.get('player_wins', 0) / total_games * 100, 1),
                "banker": round(stats.get('banker_wins', 0) / total_games * 100, 1),
                "tie": round(stats.get('ties', 0) / total_games * 100, 1)
            }
            stats['pair_rate'] = round(stats.get('pairs', 0) / total_games * 100, 1)
            stats['natural_rate'] = round(stats.get('naturals', 0) / total_games * 100, 1)
        else:
            stats['win_rates'] = {"player": 0, "banker": 0, "tie": 0}
            stats['pair_rate'] = 0
            stats['natural_rate'] = 0
        
        response = {
            "success": True,
            "data": {
                "date": date,
                "games": games,
                "overall_statistics": stats,
                "table_statistics": table_stats
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"날짜별 게임 조회 완료: {total_games}개 게임, {len(table_stats)}개 테이블")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"날짜별 게임 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"날짜별 게임 조회 실패: {str(e)}")

@router.get("/games/statistics/summary")
async def get_overall_statistics(
    days: int = Query(7, ge=1, le=90, description="통계 기간 (일)"),
    db: OptimizedDatabaseManager = Depends(get_optimized_db)
):
    """전체 게임 통계 요약"""
    try:
        logger.info(f"전체 통계 조회: {days}일간")
        
        # 날짜 범위 계산
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        query = """
        SELECT 
            COUNT(*) as total_games,
            COUNT(DISTINCT table_name) as total_tables,
            COUNT(DISTINCT date) as total_days,
            SUM(CASE WHEN winner = 'Player' THEN 1 ELSE 0 END) as player_wins,
            SUM(CASE WHEN winner = 'Banker' THEN 1 ELSE 0 END) as banker_wins,
            SUM(CASE WHEN winner = 'Tie' THEN 1 ELSE 0 END) as ties,
            SUM(CASE WHEN player_pair = 1 THEN 1 ELSE 0 END) as player_pairs,
            SUM(CASE WHEN banker_pair = 1 THEN 1 ELSE 0 END) as banker_pairs,
            SUM(CASE WHEN natural = 1 THEN 1 ELSE 0 END) as naturals,
            MIN(timestamp) as earliest_game,
            MAX(timestamp) as latest_game
        FROM games 
        WHERE date BETWEEN ? AND ?
        """
        
        async with db.pool.get_connection() as conn:
            cursor = await conn.execute(query, [start_date, end_date])
            row = await cursor.fetchone()
            columns = [description[0] for description in cursor.description]
            stats = dict(zip(columns, row))
            
            # 일별 통계
            daily_query = """
            SELECT 
                date,
                COUNT(*) as games,
                COUNT(DISTINCT table_name) as tables
            FROM games 
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date DESC
            """
            
            daily_cursor = await conn.execute(daily_query, [start_date, end_date])
            daily_rows = await daily_cursor.fetchall()
            daily_columns = [description[0] for description in daily_cursor.description]
            daily_stats = [dict(zip(daily_columns, row)) for row in daily_rows]
            
            # 테이블별 통계 (상위 10개)
            top_tables_query = """
            SELECT 
                table_name,
                COUNT(*) as games,
                SUM(CASE WHEN winner = 'Player' THEN 1 ELSE 0 END) as player_wins,
                SUM(CASE WHEN winner = 'Banker' THEN 1 ELSE 0 END) as banker_wins
            FROM games 
            WHERE date BETWEEN ? AND ?
            GROUP BY table_name
            ORDER BY games DESC
            LIMIT 10
            """
            
            tables_cursor = await conn.execute(top_tables_query, [start_date, end_date])
            tables_rows = await tables_cursor.fetchall()
            tables_columns = [description[0] for description in tables_cursor.description]
            top_tables = [dict(zip(tables_columns, row)) for row in tables_rows]
        
        # 통계 계산
        total_games = stats.get('total_games', 0)
        if total_games > 0:
            stats['win_rates'] = {
                "player": round(stats.get('player_wins', 0) / total_games * 100, 1),
                "banker": round(stats.get('banker_wins', 0) / total_games * 100, 1),
                "tie": round(stats.get('ties', 0) / total_games * 100, 1)
            }
            stats['pair_rates'] = {
                "player": round(stats.get('player_pairs', 0) / total_games * 100, 1),
                "banker": round(stats.get('banker_pairs', 0) / total_games * 100, 1),
                "total": round((stats.get('player_pairs', 0) + stats.get('banker_pairs', 0)) / total_games * 100, 1)
            }
            stats['natural_rate'] = round(stats.get('naturals', 0) / total_games * 100, 1)
            stats['games_per_day'] = round(total_games / max(stats.get('total_days', 1), 1), 1)
        else:
            stats['win_rates'] = {"player": 0, "banker": 0, "tie": 0}
            stats['pair_rates'] = {"player": 0, "banker": 0, "total": 0}
            stats['natural_rate'] = 0
            stats['games_per_day'] = 0
        
        response = {
            "success": True,
            "data": {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": days
                },
                "overall_statistics": stats,
                "daily_statistics": daily_stats,
                "top_tables": top_tables
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"전체 통계 조회 완료: {total_games}개 게임")
        return response
        
    except Exception as e:
        logger.error(f"전체 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"전체 통계 조회 실패: {str(e)}")

@router.get("/tables/list")
async def get_tables_list(
    db: OptimizedDatabaseManager = Depends(get_optimized_db)
):
    """사용 가능한 테이블 목록 조회"""
    try:
        logger.info("테이블 목록 조회")
        
        query = """
        SELECT 
            table_name,
            COUNT(*) as total_games,
            MIN(date) as first_date,
            MAX(date) as last_date,
            MAX(timestamp) as last_game_time
        FROM games 
        GROUP BY table_name
        ORDER BY total_games DESC
        """
        
        async with db.pool.get_connection() as conn:
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            tables = [dict(zip(columns, row)) for row in rows]
        
        response = {
            "success": True,
            "data": {
                "tables": tables,
                "total_tables": len(tables)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"테이블 목록 조회 완료: {len(tables)}개 테이블")
        return response
        
    except Exception as e:
        logger.error(f"테이블 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"테이블 목록 조회 실패: {str(e)}")

@router.post("/data/process-historical")
async def trigger_historical_processing(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """과거 데이터 처리 트리거 (관리용)"""
    try:
        logger.info(f"과거 데이터 처리 트리거: {start_date} ~ {end_date}")
        
        # 백그라운드에서 처리하도록 비동기 태스크 생성
        from services.historical_data_processor import HistoricalDataProcessor
        
        processor = HistoricalDataProcessor()
        await processor.initialize()
        
        # 비동기 작업으로 처리 (논블로킹)
        import asyncio
        asyncio.create_task(processor.process_all_historical_data(start_date, end_date))
        
        response = {
            "success": True,
            "message": "과거 데이터 처리가 백그라운드에서 시작되었습니다.",
            "data": {
                "start_date": start_date,
                "end_date": end_date
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("과거 데이터 처리 트리거 완료")
        return response
        
    except Exception as e:
        logger.error(f"과거 데이터 처리 트리거 오류: {e}")
        raise HTTPException(status_code=500, detail=f"과거 데이터 처리 트리거 실패: {str(e)}")