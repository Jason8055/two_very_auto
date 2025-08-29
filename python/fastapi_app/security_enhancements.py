#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Enhancements - Two Very Auto
보안 강화 기능
"""

import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict
import asyncio
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

class RateLimiter:
    """요청 속도 제한기"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    async def is_allowed(self, client_id: str) -> bool:
        """요청 허용 여부 확인"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # 오래된 요청 제거
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
        
        # 현재 요청 수 확인
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # 새 요청 기록
        self.requests[client_id].append(now)
        return True
    
    def get_remaining_requests(self, client_id: str) -> int:
        """남은 요청 수"""
        current_requests = len(self.requests.get(client_id, []))
        return max(0, self.max_requests - current_requests)

class SecurityValidator:
    """보안 검증기"""
    
    def __init__(self):
        self.blocked_ips = set()
        self.suspicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'SELECT.*FROM',
            r'UNION.*SELECT',
            r'\.\./\.\.',
            r'cmd\.exe',
            r'powershell'
        ]
    
    async def validate_request(self, request: Request) -> bool:
        """요청 보안 검증"""
        try:
            # IP 차단 확인
            client_ip = self.get_client_ip(request)
            if client_ip in self.blocked_ips:
                raise HTTPException(status_code=403, detail="IP blocked")
            
            # 요청 내용 검증
            if hasattr(request, '_body'):
                body = request._body.decode('utf-8', errors='ignore')
                if self.contains_malicious_content(body):
                    logger.warning(f"Malicious content detected from {client_ip}")
                    return False
            
            # 헤더 검증
            user_agent = request.headers.get('user-agent', '')
            if self.is_suspicious_user_agent(user_agent):
                logger.warning(f"Suspicious user agent from {client_ip}: {user_agent}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Security validation error: {e}")
            return False
    
    def get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # Proxy를 고려한 실제 IP 추출
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def contains_malicious_content(self, content: str) -> bool:
        """악성 콘텐츠 탐지"""
        import re
        content_lower = content.lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    def is_suspicious_user_agent(self, user_agent: str) -> bool:
        """의심스러운 User-Agent 탐지"""
        suspicious_agents = [
            'sqlmap',
            'nikto',
            'dirb',
            'nmap',
            'masscan',
            'python-requests',  # 의심스러운 경우만
            'wget',
            'curl'  # API 사용이 아닌 직접적인 scraping의 경우
        ]
        
        ua_lower = user_agent.lower()
        return any(agent in ua_lower for agent in suspicious_agents)
    
    def block_ip(self, ip: str, reason: str = "Security violation"):
        """IP 차단"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP {ip} blocked: {reason}")
    
    def unblock_ip(self, ip: str):
        """IP 차단 해제"""
        self.blocked_ips.discard(ip)
        logger.info(f"IP {ip} unblocked")

class PasswordSecurity:
    """비밀번호 보안"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해싱"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)
        return f"{salt}:{password_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """비밀번호 검증"""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256',
                                                    password.encode('utf-8'),
                                                    salt.encode('utf-8'),
                                                    100000)
            return stored_hash == password_hash_check.hex()
        except ValueError:
            return False
    
    @staticmethod
    def generate_secure_token() -> str:
        """보안 토큰 생성"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def is_strong_password(password: str) -> tuple[bool, str]:
        """강한 비밀번호 확인"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        import re
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"

class AuditLogger:
    """감사 로거"""
    
    def __init__(self):
        self.audit_log = []
    
    async def log_security_event(self, event_type: str, details: Dict[str, Any], 
                                request: Request = None):
        """보안 이벤트 로깅"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details,
            'client_ip': self.get_client_ip(request) if request else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown') if request else 'unknown'
        }
        
        self.audit_log.append(event)
        
        # 중요한 보안 이벤트는 즉시 로깅
        if event_type in ['failed_login', 'blocked_request', 'suspicious_activity']:
            logger.warning(f"Security event: {event_type} - {details}")
    
    def get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        if not request:
            return 'unknown'
        return request.client.host if request.client else 'unknown'
    
    def get_recent_events(self, hours: int = 24) -> list:
        """최근 보안 이벤트 조회"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            event for event in self.audit_log
            if datetime.fromisoformat(event['timestamp']) > cutoff
        ]

# 전역 보안 인스턴스들
rate_limiter = RateLimiter()
security_validator = SecurityValidator()
audit_logger = AuditLogger()

class SecurityMiddleware:
    """보안 미들웨어"""
    
    def __init__(self):
        self.security_validator = security_validator
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 실행"""
        start_time = time.time()
        client_ip = self.security_validator.get_client_ip(request)
        
        try:
            # 속도 제한 확인
            if not await self.rate_limiter.is_allowed(client_ip):
                await self.audit_logger.log_security_event(
                    'rate_limit_exceeded',
                    {'client_ip': client_ip},
                    request
                )
                raise HTTPException(status_code=429, detail="Too many requests")
            
            # 보안 검증
            if not await self.security_validator.validate_request(request):
                await self.audit_logger.log_security_event(
                    'blocked_request',
                    {'client_ip': client_ip, 'reason': 'Failed security validation'},
                    request
                )
                raise HTTPException(status_code=403, detail="Request blocked")
            
            # 요청 처리
            response = await call_next(request)
            
            # 성공적인 요청 로깅
            processing_time = time.time() - start_time
            if processing_time > 5.0:  # 5초 이상 걸린 요청 로깅
                await self.audit_logger.log_security_event(
                    'slow_request',
                    {'client_ip': client_ip, 'processing_time': processing_time, 'path': str(request.url)},
                    request
                )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            await self.audit_logger.log_security_event(
                'server_error',
                {'client_ip': client_ip, 'error': str(e)},
                request
            )
            raise HTTPException(status_code=500, detail="Internal server error")