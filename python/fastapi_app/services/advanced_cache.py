#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Cache Service - FastAPI
고급 캐싱 서비스 with TTL, LRU, 압축 지원
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import json
import pickle
import zlib
import hashlib
from collections import OrderedDict
from enum import Enum
import threading

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """캐시 전략"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out

class SerializationType(Enum):
    """직렬화 방식"""
    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_PICKLE = "compressed_pickle"

class CacheEntry:
    """캐시 엔트리"""
    
    def __init__(self, key: str, value: Any, ttl_seconds: int = None, 
                 serialize_type: SerializationType = SerializationType.PICKLE):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.last_accessed = self.created_at
        self.access_count = 1
        self.ttl_seconds = ttl_seconds
        self.serialize_type = serialize_type
        self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """캐시 엔트리 크기 계산"""
        try:
            if self.serialize_type == SerializationType.JSON:
                return len(json.dumps(self.value, default=str).encode())
            elif self.serialize_type == SerializationType.PICKLE:
                return len(pickle.dumps(self.value))
            elif self.serialize_type == SerializationType.COMPRESSED_PICKLE:
                return len(zlib.compress(pickle.dumps(self.value)))
            else:
                return len(str(self.value).encode())
        except:
            return len(str(self.value).encode())
    
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if self.ttl_seconds is None:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    def access(self):
        """액세스 기록"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def serialize_value(self) -> bytes:
        """값 직렬화"""
        if self.serialize_type == SerializationType.JSON:
            return json.dumps(self.value, default=str).encode()
        elif self.serialize_type == SerializationType.PICKLE:
            return pickle.dumps(self.value)
        elif self.serialize_type == SerializationType.COMPRESSED_PICKLE:
            return zlib.compress(pickle.dumps(self.value))
        else:
            return str(self.value).encode()
    
    @staticmethod
    def deserialize_value(data: bytes, serialize_type: SerializationType) -> Any:
        """값 역직렬화"""
        if serialize_type == SerializationType.JSON:
            return json.loads(data.decode())
        elif serialize_type == SerializationType.PICKLE:
            return pickle.loads(data)
        elif serialize_type == SerializationType.COMPRESSED_PICKLE:
            return pickle.loads(zlib.decompress(data))
        else:
            return data.decode()

class AdvancedCache:
    """고급 캐시 서비스"""
    
    def __init__(self, 
                 max_size: int = 10000,
                 max_memory_mb: int = 100,
                 default_ttl: int = 3600,  # 1시간
                 strategy: CacheStrategy = CacheStrategy.LRU,
                 serialize_type: SerializationType = SerializationType.COMPRESSED_PICKLE,
                 enable_stats: bool = True):
        
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.strategy = strategy
        self.serialize_type = serialize_type
        self.enable_stats = enable_stats
        
        # 캐시 저장소
        if strategy == CacheStrategy.LRU:
            self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        else:
            self._cache: Dict[str, CacheEntry] = {}
        
        # 스레드 안전성을 위한 락
        self._lock = threading.RLock()
        
        # 통계
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_items': 0,
            'total_memory_bytes': 0,
            'total_items': 0,
            'hit_rate': 0.0
        } if enable_stats else {}
        
        # 백그라운드 작업
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start_background_tasks(self):
        """백그라운드 작업 시작"""
        if self.running:
            return
        
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        logger.info("🧹 캐시 백그라운드 정리 작업 시작")
    
    async def stop_background_tasks(self):
        """백그라운드 작업 중지"""
        self.running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ 캐시 백그라운드 작업 중지")
    
    def _generate_key(self, key: Union[str, Dict, List, tuple]) -> str:
        """키 생성/정규화"""
        if isinstance(key, str):
            return key
        
        # 복잡한 객체는 해시로 변환
        key_str = json.dumps(key, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: Union[str, Dict, List, tuple]) -> Optional[Any]:
        """캐시에서 값 조회"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            entry = self._cache.get(cache_key)
            
            if entry is None:
                if self.enable_stats:
                    self.stats['misses'] += 1
                    self._update_hit_rate()
                return None
            
            # 만료 확인
            if entry.is_expired():
                del self._cache[cache_key]
                if self.enable_stats:
                    self.stats['expired_items'] += 1
                    self.stats['misses'] += 1
                    self._update_hit_rate()
                return None
            
            # 액세스 기록
            entry.access()
            
            # LRU 전략: 최근 사용된 항목을 맨 끝으로 이동
            if self.strategy == CacheStrategy.LRU:
                self._cache.move_to_end(cache_key)
            
            if self.enable_stats:
                self.stats['hits'] += 1
                self._update_hit_rate()
            
            return entry.value
    
    async def set(self, key: Union[str, Dict, List, tuple], value: Any, 
                  ttl: int = None, serialize_type: SerializationType = None) -> bool:
        """캐시에 값 저장"""
        cache_key = self._generate_key(key)
        
        if ttl is None:
            ttl = self.default_ttl
        
        if serialize_type is None:
            serialize_type = self.serialize_type
        
        entry = CacheEntry(cache_key, value, ttl, serialize_type)
        
        with self._lock:
            # 메모리 제한 확인
            if not await self._ensure_space(entry.size_bytes):
                logger.warning(f"❌ 캐시 저장 실패: 공간 부족 - {cache_key}")
                return False
            
            # 기존 엔트리가 있다면 크기 차감
            if cache_key in self._cache:
                old_entry = self._cache[cache_key]
                if self.enable_stats:
                    self.stats['total_memory_bytes'] -= old_entry.size_bytes
            
            # 새 엔트리 저장
            self._cache[cache_key] = entry
            
            if self.enable_stats:
                self.stats['total_memory_bytes'] += entry.size_bytes
                self.stats['total_items'] = len(self._cache)
            
            # LRU 전략: 새 항목을 맨 끝으로 이동
            if self.strategy == CacheStrategy.LRU:
                self._cache.move_to_end(cache_key)
            
            return True
    
    async def delete(self, key: Union[str, Dict, List, tuple]) -> bool:
        """캐시에서 값 삭제"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                del self._cache[cache_key]
                
                if self.enable_stats:
                    self.stats['total_memory_bytes'] -= entry.size_bytes
                    self.stats['total_items'] = len(self._cache)
                
                return True
            
            return False
    
    async def exists(self, key: Union[str, Dict, List, tuple]) -> bool:
        """캐시에 키가 존재하는지 확인"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key not in self._cache:
                return False
            
            entry = self._cache[cache_key]
            if entry.is_expired():
                del self._cache[cache_key]
                if self.enable_stats:
                    self.stats['expired_items'] += 1
                    self.stats['total_memory_bytes'] -= entry.size_bytes
                    self.stats['total_items'] = len(self._cache)
                return False
            
            return True
    
    async def clear(self) -> int:
        """캐시 전체 삭제"""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            
            if self.enable_stats:
                self.stats['total_memory_bytes'] = 0
                self.stats['total_items'] = 0
            
            return cleared_count
    
    async def _ensure_space(self, required_bytes: int) -> bool:
        """필요한 공간 확보"""
        # 현재 메모리 사용량 + 필요 바이트가 제한을 초과하는지 확인
        if self.stats.get('total_memory_bytes', 0) + required_bytes <= self.max_memory_bytes:
            return True
        
        # 공간 확보를 위한 eviction
        return await self._evict_items(required_bytes)
    
    async def _evict_items(self, required_bytes: int) -> bool:
        """아이템 제거를 통한 공간 확보"""
        freed_bytes = 0
        items_to_remove = []
        
        if self.strategy == CacheStrategy.LRU:
            # LRU: 가장 오래된 항목부터 제거
            for key, entry in self._cache.items():
                items_to_remove.append(key)
                freed_bytes += entry.size_bytes
                
                if freed_bytes >= required_bytes:
                    break
        
        elif self.strategy == CacheStrategy.LFU:
            # LFU: 가장 적게 사용된 항목부터 제거
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: (x[1].access_count, x[1].last_accessed)
            )
            
            for key, entry in sorted_items:
                items_to_remove.append(key)
                freed_bytes += entry.size_bytes
                
                if freed_bytes >= required_bytes:
                    break
        
        elif self.strategy == CacheStrategy.TTL:
            # TTL: 만료된 항목 우선, 그 다음 가장 오래된 항목
            expired_items = [
                (k, v) for k, v in self._cache.items() if v.is_expired()
            ]
            
            # 만료된 항목 먼저 제거
            for key, entry in expired_items:
                items_to_remove.append(key)
                freed_bytes += entry.size_bytes
                
                if freed_bytes >= required_bytes:
                    break
            
            # 여전히 공간이 부족하면 오래된 항목 제거
            if freed_bytes < required_bytes:
                remaining_items = [
                    (k, v) for k, v in self._cache.items() 
                    if k not in items_to_remove
                ]
                
                sorted_remaining = sorted(
                    remaining_items,
                    key=lambda x: x[1].created_at
                )
                
                for key, entry in sorted_remaining:
                    items_to_remove.append(key)
                    freed_bytes += entry.size_bytes
                    
                    if freed_bytes >= required_bytes:
                        break
        
        # 실제로 항목들 제거
        for key in items_to_remove:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                
                if self.enable_stats:
                    self.stats['evictions'] += 1
                    self.stats['total_memory_bytes'] -= entry.size_bytes
        
        if self.enable_stats:
            self.stats['total_items'] = len(self._cache)
        
        return freed_bytes >= required_bytes
    
    def _update_hit_rate(self):
        """히트율 업데이트"""
        if not self.enable_stats:
            return
        
        total = self.stats['hits'] + self.stats['misses']
        if total > 0:
            self.stats['hit_rate'] = self.stats['hits'] / total
    
    async def _cleanup_worker(self):
        """백그라운드 정리 워커"""
        logger.info("🧹 캐시 정리 워커 시작")
        
        while self.running:
            try:
                await asyncio.sleep(300)  # 5분마다 실행
                
                with self._lock:
                    expired_keys = []
                    
                    for key, entry in self._cache.items():
                        if entry.is_expired():
                            expired_keys.append(key)
                    
                    # 만료된 항목 제거
                    for key in expired_keys:
                        if key in self._cache:
                            entry = self._cache[key]
                            del self._cache[key]
                            
                            if self.enable_stats:
                                self.stats['expired_items'] += 1
                                self.stats['total_memory_bytes'] -= entry.size_bytes
                    
                    if self.enable_stats:
                        self.stats['total_items'] = len(self._cache)
                    
                    if expired_keys:
                        logger.info(f"🗑️ 만료된 캐시 {len(expired_keys)}개 정리 완료")
                
            except Exception as e:
                logger.error(f"❌ 캐시 정리 워커 오류: {e}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        if not self.enable_stats:
            return {'stats_disabled': True}
        
        with self._lock:
            return {
                'cache_config': {
                    'max_size': self.max_size,
                    'max_memory_mb': self.max_memory_bytes // (1024 * 1024),
                    'default_ttl': self.default_ttl,
                    'strategy': self.strategy.value,
                    'serialize_type': self.serialize_type.value
                },
                'current_stats': self.stats.copy(),
                'memory_usage': {
                    'used_bytes': self.stats['total_memory_bytes'],
                    'used_mb': self.stats['total_memory_bytes'] / (1024 * 1024),
                    'usage_percent': (self.stats['total_memory_bytes'] / self.max_memory_bytes) * 100
                },
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_cache_keys(self, pattern: str = None, limit: int = 100) -> List[str]:
        """캐시 키 목록 조회"""
        with self._lock:
            keys = list(self._cache.keys())
            
            if pattern:
                import re
                regex = re.compile(pattern)
                keys = [k for k in keys if regex.search(k)]
            
            return keys[:limit]

# 전역 캐시 인스턴스들
_global_caches: Dict[str, AdvancedCache] = {}

def get_cache(name: str = "default", **kwargs) -> AdvancedCache:
    """캐시 인스턴스 반환"""
    if name not in _global_caches:
        _global_caches[name] = AdvancedCache(**kwargs)
    
    return _global_caches[name]

async def init_all_caches():
    """모든 캐시 백그라운드 작업 시작"""
    for cache in _global_caches.values():
        await cache.start_background_tasks()

async def stop_all_caches():
    """모든 캐시 백그라운드 작업 중지"""
    for cache in _global_caches.values():
        await cache.stop_background_tasks()

# 기본 캐시 인스턴스들
default_cache = get_cache("default", max_memory_mb=50)
prediction_cache = get_cache("predictions", max_memory_mb=30, default_ttl=1800)  # 30분
stats_cache = get_cache("stats", max_memory_mb=10, default_ttl=60)  # 1분
session_cache = get_cache("sessions", max_memory_mb=20, default_ttl=7200)  # 2시간