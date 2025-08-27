#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 성능 최적화 - 메모리 캐싱 시스템
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import json
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """캐시 엔트리"""
    data: Any
    created_at: datetime
    ttl_seconds: int
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """생성 후 경과 시간 (초)"""
        return (datetime.now() - self.created_at).total_seconds()

class PerformanceCacheManager:
    """고성능 메모리 캐싱 매니저"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0,
            'cache_size': 0
        }
        self._lock = asyncio.Lock()
        
        # 캐시 타입별 TTL 설정
        self.ttl_config = {
            'stats': 60,           # 통계: 1분
            'table_stats': 120,    # 테이블 통계: 2분
            'system_health': 30,   # 시스템 상태: 30초
            'demo_data': 300,      # 데모 데이터: 5분
            'real_data': 600,      # 실제 데이터: 10분
            'pair_analysis': 180,  # 페어 분석: 3분
        }
        
    async def get(self, key: str, cache_type: str = 'default') -> Tuple[Any, bool]:
        """캐시에서 데이터 조회"""
        async with self._lock:
            self.stats['total_requests'] += 1
            
            if key not in self.cache:
                self.stats['misses'] += 1
                return None, False
            
            entry = self.cache[key]
            
            # 만료 확인
            if entry.is_expired:
                del self.cache[key]
                self.stats['misses'] += 1
                self.stats['evictions'] += 1
                logger.debug(f"Cache expired for key: {key}")
                return None, False
            
            # LRU 구현 - 최근 사용된 항목을 끝으로 이동
            self.cache.move_to_end(key)
            entry.hit_count += 1
            self.stats['hits'] += 1
            
            logger.debug(f"Cache hit for key: {key}, age: {entry.age_seconds:.1f}s")
            return entry.data, True
    
    async def set(self, key: str, data: Any, cache_type: str = 'default', ttl: Optional[int] = None) -> bool:
        """캐시에 데이터 저장"""
        async with self._lock:
            # TTL 결정
            if ttl is None:
                ttl = self.ttl_config.get(cache_type, self.default_ttl)
            
            # 캐시 크기 관리 - LRU 방식으로 오래된 항목 제거
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats['evictions'] += 1
                logger.debug(f"Cache eviction: {oldest_key}")
            
            # 새 엔트리 저장
            entry = CacheEntry(
                data=data,
                created_at=datetime.now(),
                ttl_seconds=ttl,
                hit_count=0
            )
            
            self.cache[key] = entry
            self.stats['cache_size'] = len(self.cache)
            
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s, type: {cache_type}")
            return True
    
    async def delete(self, key: str) -> bool:
        """캐시에서 특정 키 삭제"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['cache_size'] = len(self.cache)
                logger.debug(f"Cache delete: {key}")
                return True
            return False
    
    async def clear_by_pattern(self, pattern: str) -> int:
        """패턴으로 캐시 일괄 삭제"""
        async with self._lock:
            keys_to_delete = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self.cache[key]
            
            self.stats['cache_size'] = len(self.cache)
            logger.info(f"Cache cleared by pattern '{pattern}': {len(keys_to_delete)} entries")
            return len(keys_to_delete)
    
    async def clear_expired(self) -> int:
        """만료된 캐시 엔트리 정리"""
        async with self._lock:
            expired_keys = [
                key for key, entry in self.cache.items() 
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            self.stats['cache_size'] = len(self.cache)
            self.stats['evictions'] += len(expired_keys)
            
            if expired_keys:
                logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        async with self._lock:
            hit_rate = (
                self.stats['hits'] / self.stats['total_requests'] * 100
                if self.stats['total_requests'] > 0 else 0.0
            )
            
            # 캐시 엔트리별 통계
            entry_stats = {}
            for key, entry in self.cache.items():
                entry_stats[key] = {
                    'age_seconds': entry.age_seconds,
                    'hit_count': entry.hit_count,
                    'ttl_seconds': entry.ttl_seconds,
                    'expires_in': entry.ttl_seconds - entry.age_seconds
                }
            
            return {
                'enabled': True,
                'hit_rate': round(hit_rate, 2),
                'total_requests': self.stats['total_requests'],
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions'],
                'cache_size': self.stats['cache_size'],
                'max_size': self.max_size,
                'memory_usage_estimate_kb': self._estimate_memory_usage(),
                'entry_details': entry_stats
            }
    
    def _estimate_memory_usage(self) -> float:
        """메모리 사용량 추정 (KB)"""
        try:
            total_size = 0
            for key, entry in self.cache.items():
                # 키 크기 + 데이터 크기 추정
                key_size = len(key.encode('utf-8'))
                data_size = len(json.dumps(entry.data, default=str, ensure_ascii=False).encode('utf-8'))
                entry_overhead = 200  # CacheEntry 객체 오버헤드
                total_size += key_size + data_size + entry_overhead
            
            return total_size / 1024  # KB로 변환
        except Exception as e:
            logger.error(f"Memory usage estimation error: {e}")
            return 0.0
    
    async def warm_up(self, db_manager):
        """캐시 워밍업 - 자주 사용되는 데이터 미리 로드"""
        try:
            logger.info("Starting cache warm-up...")
            
            # 시스템 통계 워밍업
            stats = await db_manager.get_system_stats()
            await self.set('system_stats', stats, 'stats')
            
            # 테이블별 통계 워밍업
            if hasattr(stats, 'table_breakdown') and stats.table_breakdown:
                for table_name in stats.table_breakdown.keys():
                    table_stats = await db_manager.get_table_stats(table_name)
                    await self.set(f'table_stats:{table_name}', table_stats, 'table_stats')
            
            logger.info("Cache warm-up completed successfully")
            
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")
    
    async def start_background_cleanup(self):
        """백그라운드 캐시 정리 작업 시작"""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(60)  # 1분마다 정리
                    expired_count = await self.clear_expired()
                    if expired_count > 0:
                        logger.info(f"Background cleanup: removed {expired_count} expired entries")
                except Exception as e:
                    logger.error(f"Background cache cleanup error: {e}")
        
        asyncio.create_task(cleanup_task())
        logger.info("Background cache cleanup task started")

# 글로벌 캐시 매니저 인스턴스
cache_manager = PerformanceCacheManager(max_size=500, default_ttl=300)