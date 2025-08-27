#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Handler Utilities - FastAPI
에러 처리 및 로깅 유틸리티
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio

logger = logging.getLogger(__name__)

class PairNotificationError(Exception):
    """페어 알림 관련 에러"""
    
    def __init__(self, message: str, error_code: str = "PAIR_ERROR", details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """에러 정보를 딕셔너리로 변환"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

class PairDetectionError(PairNotificationError):
    """페어 감지 에러"""
    
    def __init__(self, message: str, table_name: str = None, cards: Dict[str, Any] = None):
        details = {}
        if table_name:
            details['table_name'] = table_name
        if cards:
            details['cards'] = cards
        
        super().__init__(message, "PAIR_DETECTION_ERROR", details)

class BroadcastError(PairNotificationError):
    """브로드캐스트 에러"""
    
    def __init__(self, message: str, channel: str = None, recipient_count: int = None):
        details = {}
        if channel:
            details['channel'] = channel
        if recipient_count is not None:
            details['recipient_count'] = recipient_count
        
        super().__init__(message, "BROADCAST_ERROR", details)

class ConfigurationError(PairNotificationError):
    """설정 에러"""
    
    def __init__(self, message: str, setting_name: str = None, invalid_value: Any = None):
        details = {}
        if setting_name:
            details['setting_name'] = setting_name
        if invalid_value is not None:
            details['invalid_value'] = str(invalid_value)
        
        super().__init__(message, "CONFIGURATION_ERROR", details)

class ErrorHandler:
    """에러 처리 클래스"""
    
    def __init__(self):
        self.error_stats = {
            'total_errors': 0,
            'by_type': {},
            'by_endpoint': {},
            'recent_errors': []
        }
        self.max_recent_errors = 100
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """에러 로깅"""
        try:
            error_info = {
                'type': type(error).__name__,
                'message': str(error),
                'timestamp': datetime.now().isoformat(),
                'traceback': traceback.format_exc(),
                'context': context or {}
            }
            
            # 통계 업데이트
            self.error_stats['total_errors'] += 1
            error_type = type(error).__name__
            self.error_stats['by_type'][error_type] = self.error_stats['by_type'].get(error_type, 0) + 1
            
            # 최근 에러 목록에 추가
            self.error_stats['recent_errors'].append(error_info)
            if len(self.error_stats['recent_errors']) > self.max_recent_errors:
                self.error_stats['recent_errors'].pop(0)
            
            # 로그 레벨 결정
            if isinstance(error, (PairDetectionError, BroadcastError)):
                logger.warning(f"[{error_type}] {str(error)}")
            elif isinstance(error, ConfigurationError):
                logger.error(f"[{error_type}] {str(error)}")
            else:
                logger.error(f"[{error_type}] {str(error)}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
        except Exception as e:
            logger.error(f"에러 로깅 중 오류 발생: {e}")
    
    async def handle_pair_detection_error(self, error: PairDetectionError, 
                                         table_name: str = None, 
                                         game_number: int = None) -> Dict[str, Any]:
        """페어 감지 에러 처리"""
        context = {
            'operation': 'pair_detection',
            'table_name': table_name,
            'game_number': game_number
        }
        
        self.log_error(error, context)
        
        # 에러 응답 생성
        return {
            'success': False,
            'error': error.to_dict(),
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
    
    async def handle_broadcast_error(self, error: BroadcastError, 
                                   pair_event_id: str = None) -> Dict[str, Any]:
        """브로드캐스트 에러 처리"""
        context = {
            'operation': 'broadcast',
            'pair_event_id': pair_event_id
        }
        
        self.log_error(error, context)
        
        return {
            'success': False,
            'error': error.to_dict(),
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
    
    async def handle_configuration_error(self, error: ConfigurationError) -> Dict[str, Any]:
        """설정 에러 처리"""
        context = {
            'operation': 'configuration'
        }
        
        self.log_error(error, context)
        
        return {
            'success': False,
            'error': error.to_dict(),
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 반환"""
        return {
            'stats': self.error_stats,
            'summary': {
                'total_errors': self.error_stats['total_errors'],
                'most_common_error': max(self.error_stats['by_type'].keys(), 
                                       key=lambda k: self.error_stats['by_type'][k]) 
                                   if self.error_stats['by_type'] else None,
                'error_rate': self._calculate_error_rate()
            }
        }
    
    def _calculate_error_rate(self) -> float:
        """최근 1시간 에러율 계산"""
        try:
            now = datetime.now()
            one_hour_ago = now.replace(hour=now.hour-1) if now.hour > 0 else now.replace(day=now.day-1, hour=23)
            
            recent_errors = [
                e for e in self.error_stats['recent_errors']
                if datetime.fromisoformat(e['timestamp']) >= one_hour_ago
            ]
            
            return len(recent_errors) / 60.0  # 분당 에러 수
            
        except Exception:
            return 0.0

# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler()

def create_error_response(error: Exception, status_code: int = 500) -> JSONResponse:
    """HTTP 에러 응답 생성"""
    try:
        if isinstance(error, PairNotificationError):
            error_data = error.to_dict()
        else:
            error_data = {
                'error_code': 'INTERNAL_ERROR',
                'message': str(error),
                'details': {},
                'timestamp': datetime.now().isoformat()
            }
        
        # 에러 로깅
        error_handler.log_error(error)
        
        return JSONResponse(
            status_code=status_code,
            content={
                'success': False,
                'error': error_data,
                'timestamp': datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"에러 응답 생성 중 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': {
                    'error_code': 'RESPONSE_GENERATION_ERROR',
                    'message': '에러 응답 생성 중 오류가 발생했습니다',
                    'timestamp': datetime.now().isoformat()
                }
            }
        )

async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리기"""
    try:
        # 요청 정보 추출
        context = {
            'url': str(request.url),
            'method': request.method,
            'client': request.client.host if request.client else 'unknown'
        }
        
        # 에러 타입별 처리
        if isinstance(exc, HTTPException):
            return create_error_response(exc, exc.status_code)
        elif isinstance(exc, PairNotificationError):
            return create_error_response(exc, 400)
        else:
            return create_error_response(exc, 500)
            
    except Exception as e:
        logger.error(f"전역 예외 처리기에서 오류 발생: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': {
                    'error_code': 'EXCEPTION_HANDLER_ERROR',
                    'message': '예외 처리 중 오류가 발생했습니다',
                    'timestamp': datetime.now().isoformat()
                }
            }
        )

# 재시도 데코레이터
def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """실패 시 재시도 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"함수 {func.__name__} 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                        await asyncio.sleep(delay * (2 ** attempt))  # 지수 백오프
                    else:
                        logger.error(f"함수 {func.__name__} 최종 실패: {e}")
            
            raise last_error
        
        return wrapper
    return decorator

# 회로 차단기 패턴
class CircuitBreaker:
    """회로 차단기"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
    
    async def call(self, func, *args, **kwargs):
        """함수 호출"""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half_open'
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부"""
        if self.last_failure_time is None:
            return False
        
        return (datetime.now().timestamp() - self.last_failure_time) >= self.timeout
    
    def _on_success(self):
        """성공 시 처리"""
        self.failure_count = 0
        self.state = 'closed'
    
    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'