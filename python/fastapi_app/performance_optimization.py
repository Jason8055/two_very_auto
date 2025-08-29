#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Optimization Tools - Two Very Auto
성능 최적화 도구 및 분석
"""

import asyncio
import time
import logging
import functools
from typing import Dict, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.metrics = defaultdict(lambda: deque(maxlen=max_samples))
        self.start_time = datetime.now()
    
    def record_metric(self, name: str, value: float, timestamp: datetime = None):
        """메트릭 기록"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.metrics[name].append({
            'value': value,
            'timestamp': timestamp.isoformat()
        })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약 정보"""
        summary = {}
        
        for metric_name, samples in self.metrics.items():
            if samples:
                values = [s['value'] for s in samples]
                summary[metric_name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[-1],
                    'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
                }
        
        summary['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
        return summary

# 전역 성능 모니터
performance_monitor = PerformanceMonitor()

def measure_time(metric_name: str):
    """함수 실행 시간 측정 데코레이터"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                performance_monitor.record_metric(f"{metric_name}_duration", execution_time)
                performance_monitor.record_metric(f"{metric_name}_success", 1)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                performance_monitor.record_metric(f"{metric_name}_duration", execution_time)
                performance_monitor.record_metric(f"{metric_name}_error", 1)
                raise e
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                performance_monitor.record_metric(f"{metric_name}_duration", execution_time)
                performance_monitor.record_metric(f"{metric_name}_success", 1)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                performance_monitor.record_metric(f"{metric_name}_duration", execution_time)
                performance_monitor.record_metric(f"{metric_name}_error", 1)
                raise e
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

class ConnectionPool:
    """연결 풀 최적화"""
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.active_connections = 0
        self.connection_queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(max_connections)
    
    async def acquire_connection(self):
        """연결 획득"""
        await self.semaphore.acquire()
        self.active_connections += 1
        performance_monitor.record_metric("active_connections", self.active_connections)
        return f"connection_{self.active_connections}"
    
    async def release_connection(self, connection):
        """연결 해제"""
        self.active_connections -= 1
        performance_monitor.record_metric("active_connections", self.active_connections)
        self.semaphore.release()

class QueryOptimizer:
    """쿼리 최적화 도구"""
    
    def __init__(self):
        self.query_cache = {}
        self.query_stats = defaultdict(list)
    
    @measure_time("database_query")
    async def execute_optimized_query(self, query: str, params: tuple = None):
        """최적화된 쿼리 실행"""
        # 쿼리 캐싱 로직
        cache_key = f"{query}_{params}"
        
        if cache_key in self.query_cache:
            # 캐시된 결과 반환 (실제 구현 시 TTL 체크 필요)
            performance_monitor.record_metric("query_cache_hit", 1)
            return self.query_cache[cache_key]
        
        # 실제 쿼리 실행 (시뮬레이션)
        start_time = time.time()
        await asyncio.sleep(0.01)  # DB 쿼리 시뮬레이션
        execution_time = time.time() - start_time
        
        # 쿼리 통계 기록
        self.query_stats[query].append(execution_time)
        performance_monitor.record_metric("query_cache_miss", 1)
        
        # 결과 캐싱 (실제 구현에서는 결과 데이터)
        result = {"simulated": "result"}
        self.query_cache[cache_key] = result
        
        return result
    
    def get_slow_queries(self, threshold: float = 0.1) -> Dict[str, Any]:
        """느린 쿼리 분석"""
        slow_queries = {}
        
        for query, times in self.query_stats.items():
            avg_time = sum(times) / len(times)
            if avg_time > threshold:
                slow_queries[query] = {
                    'avg_time': avg_time,
                    'max_time': max(times),
                    'count': len(times),
                    'total_time': sum(times)
                }
        
        return slow_queries

# 전역 최적화 도구들
connection_pool = ConnectionPool()
query_optimizer = QueryOptimizer()

async def optimize_background_tasks():
    """백그라운드 최적화 작업"""
    while True:
        try:
            # 성능 메트릭 정리
            metrics_summary = performance_monitor.get_metrics_summary()
            
            # 느린 쿼리 체크
            slow_queries = query_optimizer.get_slow_queries()
            if slow_queries:
                logger.warning(f"Slow queries detected: {len(slow_queries)} queries")
            
            # 메모리 사용량 체크
            import psutil
            memory_percent = psutil.virtual_memory().percent
            performance_monitor.record_metric("system_memory_usage", memory_percent)
            
            if memory_percent > 80:
                logger.warning(f"High memory usage: {memory_percent}%")
            
            # 30초마다 최적화 체크
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Background optimization error: {e}")
            await asyncio.sleep(60)