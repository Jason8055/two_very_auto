#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check System - Two Very Auto
시스템 상태 모니터링 및 헬스체크
"""

import asyncio
import logging
import psutil
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class HealthChecker:
    """시스템 헬스체크 클래스"""
    
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'memory': self._check_memory,
            'disk': self._check_disk,
            'cpu': self._check_cpu,
            'files': self._check_files
        }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """종합 헬스체크 실행"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        for check_name, check_func in self.checks.items():
            try:
                result = await check_func()
                results['checks'][check_name] = result
                
                if not result.get('healthy', False):
                    results['overall_status'] = 'unhealthy'
                    
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                results['checks'][check_name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results['overall_status'] = 'unhealthy'
        
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        """데이터베이스 상태 확인"""
        try:
            # 실제 데이터베이스 연결 테스트 로직 구현
            db_file = Path("baccarat_optimized.db")
            return {
                'healthy': db_file.exists(),
                'size_mb': db_file.stat().st_size / (1024*1024) if db_file.exists() else 0,
                'message': 'Database accessible' if db_file.exists() else 'Database file not found'
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_memory(self) -> Dict[str, Any]:
        """메모리 상태 확인"""
        try:
            memory = psutil.virtual_memory()
            return {
                'healthy': memory.percent < 90,
                'usage_percent': memory.percent,
                'available_mb': memory.available / (1024*1024),
                'message': 'Memory usage normal' if memory.percent < 90 else 'High memory usage'
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_disk(self) -> Dict[str, Any]:
        """디스크 상태 확인"""
        try:
            disk = psutil.disk_usage('.')
            usage_percent = (disk.used / disk.total) * 100
            return {
                'healthy': usage_percent < 85,
                'usage_percent': usage_percent,
                'free_gb': disk.free / (1024*1024*1024),
                'message': 'Disk space normal' if usage_percent < 85 else 'Low disk space'
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_cpu(self) -> Dict[str, Any]:
        """CPU 상태 확인"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            return {
                'healthy': cpu_percent < 80,
                'usage_percent': cpu_percent,
                'core_count': psutil.cpu_count(),
                'message': 'CPU usage normal' if cpu_percent < 80 else 'High CPU usage'
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_files(self) -> Dict[str, Any]:
        """중요 파일 상태 확인"""
        try:
            important_files = [
                'main.py',
                'requirements.txt',
                '../database_manager.py'
            ]
            
            missing_files = []
            for file_path in important_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            return {
                'healthy': len(missing_files) == 0,
                'missing_files': missing_files,
                'message': 'All files present' if not missing_files else f'Missing: {missing_files}'
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

# 전역 헬스체커 인스턴스
health_checker = HealthChecker()