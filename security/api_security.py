#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - API 보안 & Rate Limiting 시스템
API 엔드포인트 보안, 속도 제한, DDoS 방어
"""

import time
import json
import hashlib
import hmac
import redis
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from collections import defaultdict, deque
import ipaddress
import re
from threading import Lock
import requests

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """위협 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BlockType(Enum):
    """차단 타입"""
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    WARNING = "warning"


class APIEndpointType(Enum):
    """API 엔드포인트 타입"""
    PUBLIC = "public"          # 인증 불필요
    PROTECTED = "protected"    # 인증 필요
    ADMIN = "admin"           # 관리자 권한 필요
    INTERNAL = "internal"     # 내부 API만
    SENSITIVE = "sensitive"   # 민감한 데이터 처리


@dataclass
class RateLimitRule:
    """Rate Limiting 규칙"""
    name: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 0  # 순간 허용 요청 수
    window_size: int = 60  # 시간 윈도우 (초)
    block_duration: int = 300  # 차단 시간 (초)
    applies_to: List[str] = None  # 적용 대상 (IP, User, API Key 등)


@dataclass
class SecurityRule:
    """보안 규칙"""
    rule_id: str
    name: str
    description: str
    pattern: str  # 정규식 패턴
    threat_level: ThreatLevel
    block_type: BlockType
    block_duration: int = 3600  # 차단 시간 (초)
    enabled: bool = True


@dataclass
class APIRequest:
    """API 요청 정보"""
    request_id: str
    ip_address: str
    user_agent: str
    method: str
    endpoint: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[str]
    user_id: Optional[str]
    api_key: Optional[str]
    timestamp: datetime
    processing_time: Optional[float] = None
    status_code: Optional[int] = None


@dataclass
class SecurityIncident:
    """보안 사고"""
    incident_id: str
    ip_address: str
    user_id: Optional[str]
    threat_level: ThreatLevel
    rule_triggered: str
    description: str
    timestamp: datetime
    blocked: bool = False
    resolved: bool = False


class RateLimitConfig:
    """Rate Limiting 설정"""
    
    # 기본 규칙들
    DEFAULT_RULES = {
        "public": RateLimitRule(
            name="Public API",
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=10,
            block_duration=60
        ),
        "protected": RateLimitRule(
            name="Protected API",
            requests_per_minute=120,
            requests_per_hour=2000,
            requests_per_day=20000,
            burst_limit=20,
            block_duration=300
        ),
        "admin": RateLimitRule(
            name="Admin API",
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=2000,
            burst_limit=5,
            block_duration=600
        ),
        "sensitive": RateLimitRule(
            name="Sensitive API",
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=500,
            burst_limit=2,
            block_duration=1800
        )
    }


class SecurityRulesEngine:
    """보안 규칙 엔진"""
    
    def __init__(self):
        self.rules = self._initialize_security_rules()
        safe_print("🛡️ 보안 규칙 엔진 초기화 완료")
    
    def _initialize_security_rules(self) -> List[SecurityRule]:
        """보안 규칙 초기화"""
        return [
            # SQL Injection 탐지
            SecurityRule(
                rule_id="sql_injection",
                name="SQL Injection Detection",
                description="SQL 인젝션 공격 탐지",
                pattern=r"(\b(union|select|insert|delete|update|drop|create|alter|exec|execute)\b|--|/\*|\*/|'|\"|\;)",
                threat_level=ThreatLevel.CRITICAL,
                block_type=BlockType.TEMPORARY,
                block_duration=3600
            ),
            
            # XSS 탐지
            SecurityRule(
                rule_id="xss_detection",
                name="XSS Attack Detection",
                description="Cross-Site Scripting 공격 탐지",
                pattern=r"(<script|javascript:|on\w+\s*=|<iframe|<object|<embed)",
                threat_level=ThreatLevel.HIGH,
                block_type=BlockType.TEMPORARY,
                block_duration=1800
            ),
            
            # Path Traversal 탐지
            SecurityRule(
                rule_id="path_traversal",
                name="Path Traversal Detection",
                description="경로 순회 공격 탐지",
                pattern=r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)",
                threat_level=ThreatLevel.HIGH,
                block_type=BlockType.TEMPORARY,
                block_duration=1800
            ),
            
            # Command Injection 탐지
            SecurityRule(
                rule_id="command_injection",
                name="Command Injection Detection",
                description="명령어 인젝션 공격 탐지",
                pattern=r"(\||&|;|\$\(|\`|nc\s|wget\s|curl\s)",
                threat_level=ThreatLevel.CRITICAL,
                block_type=BlockType.TEMPORARY,
                block_duration=3600
            ),
            
            # 악성 User-Agent 탐지
            SecurityRule(
                rule_id="malicious_user_agent",
                name="Malicious User Agent",
                description="악성 사용자 에이전트 탐지",
                pattern=r"(sqlmap|nmap|nikto|w3af|acunetix|burpsuite|owasp)",
                threat_level=ThreatLevel.HIGH,
                block_type=BlockType.TEMPORARY,
                block_duration=7200
            ),
            
            # 과도한 오류 요청 탐지
            SecurityRule(
                rule_id="error_rate",
                name="High Error Rate",
                description="과도한 4xx/5xx 오류 응답",
                pattern=r"",  # 동적 검사
                threat_level=ThreatLevel.MEDIUM,
                block_type=BlockType.WARNING,
                block_duration=600
            ),
            
            # 비정상 요청 크기 탐지
            SecurityRule(
                rule_id="large_request",
                name="Large Request Size",
                description="비정상적으로 큰 요청",
                pattern=r"",  # 동적 검사
                threat_level=ThreatLevel.MEDIUM,
                block_type=BlockType.WARNING,
                block_duration=300
            )
        ]
    
    def evaluate_request(self, request: APIRequest) -> List[SecurityIncident]:
        """요청에 대한 보안 규칙 평가"""
        incidents = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if self._check_rule(rule, request):
                incident = SecurityIncident(
                    incident_id=f"{rule.rule_id}_{int(time.time())}_{hash(request.ip_address) % 10000}",
                    ip_address=request.ip_address,
                    user_id=request.user_id,
                    threat_level=rule.threat_level,
                    rule_triggered=rule.rule_id,
                    description=f"{rule.name}: {rule.description}",
                    timestamp=datetime.now(),
                    blocked=rule.block_type in [BlockType.TEMPORARY, BlockType.PERMANENT]
                )
                incidents.append(incident)
        
        return incidents
    
    def _check_rule(self, rule: SecurityRule, request: APIRequest) -> bool:
        """개별 규칙 검사"""
        if rule.rule_id == "error_rate":
            # 동적 오류율 검사는 별도 처리
            return False
        
        if rule.rule_id == "large_request":
            # 요청 크기 검사 (5MB 초과)
            if request.body and len(request.body.encode('utf-8')) > 5 * 1024 * 1024:
                return True
            return False
        
        # 정규식 패턴 검사
        if rule.pattern:
            # URL, 헤더, 바디에서 패턴 검사
            text_to_check = [
                request.endpoint,
                str(request.query_params),
                request.user_agent,
                request.body or ""
            ]
            
            for text in text_to_check:
                if re.search(rule.pattern, text.lower(), re.IGNORECASE):
                    return True
        
        return False


class RateLimiter:
    """Rate Limiter"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.memory_store: Dict[str, deque] = defaultdict(deque)
        self.memory_lock = Lock()
        self.rules = RateLimitConfig.DEFAULT_RULES
        
        safe_print("⏱️ Rate Limiter 초기화 완료")
    
    def check_rate_limit(self, identifier: str, rule_name: str = "public") -> Dict[str, Any]:
        """Rate limit 검사"""
        rule = self.rules.get(rule_name)
        if not rule:
            return {"allowed": True, "message": "No rule found"}
        
        current_time = time.time()
        
        # Redis 사용 가능한 경우
        if self.redis:
            return self._check_redis_rate_limit(identifier, rule, current_time)
        else:
            return self._check_memory_rate_limit(identifier, rule, current_time)
    
    def _check_redis_rate_limit(self, identifier: str, rule: RateLimitRule, current_time: float) -> Dict[str, Any]:
        """Redis 기반 rate limiting"""
        minute_key = f"rate_limit:{identifier}:minute:{int(current_time // 60)}"
        hour_key = f"rate_limit:{identifier}:hour:{int(current_time // 3600)}"
        day_key = f"rate_limit:{identifier}:day:{int(current_time // 86400)}"
        
        pipe = self.redis.pipeline()
        
        # 현재 요청 수 조회
        pipe.get(minute_key)
        pipe.get(hour_key)
        pipe.get(day_key)
        
        results = pipe.execute()
        minute_count = int(results[0] or 0)
        hour_count = int(results[1] or 0)
        day_count = int(results[2] or 0)
        
        # 제한 확인
        if minute_count >= rule.requests_per_minute:
            return {
                "allowed": False,
                "reason": "minute_limit_exceeded",
                "retry_after": 60 - (current_time % 60),
                "current_count": minute_count,
                "limit": rule.requests_per_minute
            }
        
        if hour_count >= rule.requests_per_hour:
            return {
                "allowed": False,
                "reason": "hour_limit_exceeded",
                "retry_after": 3600 - (current_time % 3600),
                "current_count": hour_count,
                "limit": rule.requests_per_hour
            }
        
        if day_count >= rule.requests_per_day:
            return {
                "allowed": False,
                "reason": "day_limit_exceeded",
                "retry_after": 86400 - (current_time % 86400),
                "current_count": day_count,
                "limit": rule.requests_per_day
            }
        
        # 요청 수 증가
        pipe = self.redis.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)
        pipe.execute()
        
        return {
            "allowed": True,
            "remaining": {
                "minute": rule.requests_per_minute - minute_count - 1,
                "hour": rule.requests_per_hour - hour_count - 1,
                "day": rule.requests_per_day - day_count - 1
            }
        }
    
    def _check_memory_rate_limit(self, identifier: str, rule: RateLimitRule, current_time: float) -> Dict[str, Any]:
        """메모리 기반 rate limiting"""
        with self.memory_lock:
            requests = self.memory_store[identifier]
            
            # 시간 윈도우 밖의 요청 제거
            while requests and current_time - requests[0] > rule.window_size:
                requests.popleft()
            
            # 제한 확인
            if len(requests) >= rule.requests_per_minute:
                oldest_request = requests[0]
                retry_after = rule.window_size - (current_time - oldest_request)
                
                return {
                    "allowed": False,
                    "reason": "rate_limit_exceeded",
                    "retry_after": max(0, retry_after),
                    "current_count": len(requests),
                    "limit": rule.requests_per_minute
                }
            
            # 요청 기록
            requests.append(current_time)
            
            return {
                "allowed": True,
                "remaining": rule.requests_per_minute - len(requests)
            }
    
    def is_blocked(self, identifier: str) -> Dict[str, Any]:
        """차단 상태 확인"""
        if self.redis:
            blocked_until = self.redis.get(f"blocked:{identifier}")
            if blocked_until:
                blocked_until = float(blocked_until)
                if time.time() < blocked_until:
                    return {
                        "blocked": True,
                        "blocked_until": blocked_until,
                        "remaining_time": blocked_until - time.time()
                    }
                else:
                    # 차단 해제
                    self.redis.delete(f"blocked:{identifier}")
        
        return {"blocked": False}
    
    def block_identifier(self, identifier: str, duration: int, reason: str = ""):
        """식별자 차단"""
        blocked_until = time.time() + duration
        
        if self.redis:
            self.redis.setex(f"blocked:{identifier}", duration, blocked_until)
            
            # 차단 정보 저장
            block_info = {
                "identifier": identifier,
                "blocked_at": time.time(),
                "blocked_until": blocked_until,
                "duration": duration,
                "reason": reason
            }
            self.redis.setex(f"block_info:{identifier}", duration, json.dumps(block_info))
        
        logger.warning(f"식별자 차단: {identifier}, 시간: {duration}초, 이유: {reason}")


class IPGeolocation:
    """IP 지리적 위치 정보"""
    
    def __init__(self):
        # 실제 구현에서는 MaxMind GeoIP2 또는 다른 서비스 사용
        self.blocked_countries = ["CN", "RU", "KP"]  # 차단할 국가 코드
        self.suspicious_asns = []  # 의심스러운 ASN 목록
    
    def get_location(self, ip_address: str) -> Dict[str, Any]:
        """IP 위치 정보 조회"""
        # 실제 구현에서는 GeoIP 데이터베이스 사용
        try:
            # 예시: 공개 API 사용 (실제로는 로컬 데이터베이스 권장)
            response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {"country": "Unknown", "country_code": "XX"}
    
    def is_suspicious_location(self, ip_address: str) -> bool:
        """의심스러운 위치 확인"""
        location = self.get_location(ip_address)
        country_code = location.get("country_code", "XX")
        
        return country_code in self.blocked_countries


class APISecurityManager:
    """API 보안 관리자"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.rate_limiter = RateLimiter(redis_client)
        self.security_engine = SecurityRulesEngine()
        self.geo_locator = IPGeolocation()
        
        # 보안 사고 기록
        self.incidents: List[SecurityIncident] = []
        self.max_incidents = 10000
        
        # 화이트리스트/블랙리스트
        self.ip_whitelist = set()
        self.ip_blacklist = set()
        
        # API 키 관리
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
        safe_print("🔒 API 보안 관리자 초기화 완료")
    
    def validate_request(self, request: APIRequest, endpoint_type: APIEndpointType = APIEndpointType.PUBLIC) -> Dict[str, Any]:
        """요청 검증"""
        result = {
            "allowed": True,
            "incidents": [],
            "rate_limit_info": {},
            "security_warnings": []
        }
        
        # 1. IP 블랙리스트 확인
        if request.ip_address in self.ip_blacklist:
            result["allowed"] = False
            result["reason"] = "ip_blacklisted"
            return result
        
        # 2. IP 화이트리스트 확인
        if self.ip_whitelist and request.ip_address not in self.ip_whitelist:
            if endpoint_type in [APIEndpointType.ADMIN, APIEndpointType.INTERNAL]:
                result["allowed"] = False
                result["reason"] = "ip_not_whitelisted"
                return result
        
        # 3. 지리적 위치 확인
        if self.geo_locator.is_suspicious_location(request.ip_address):
            result["security_warnings"].append("suspicious_location")
        
        # 4. Rate limiting 확인
        rate_limit_result = self.rate_limiter.check_rate_limit(
            request.ip_address, 
            endpoint_type.value
        )
        result["rate_limit_info"] = rate_limit_result
        
        if not rate_limit_result["allowed"]:
            result["allowed"] = False
            result["reason"] = "rate_limit_exceeded"
            
            # Rate limit 위반 시 차단
            if rate_limit_result.get("current_count", 0) > rate_limit_result.get("limit", 0) * 2:
                self.rate_limiter.block_identifier(
                    request.ip_address, 
                    1800, 
                    "Excessive rate limit violations"
                )
            
            return result
        
        # 5. 보안 규칙 검사
        incidents = self.security_engine.evaluate_request(request)
        result["incidents"] = incidents
        
        # 보안 사고 기록
        for incident in incidents:
            self.incidents.append(incident)
            if len(self.incidents) > self.max_incidents:
                self.incidents = self.incidents[-self.max_incidents:]
            
            # 심각한 위협 시 차단
            if incident.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                result["allowed"] = False
                result["reason"] = f"security_violation_{incident.rule_triggered}"
                
                # 자동 차단
                if incident.blocked:
                    block_duration = 3600 if incident.threat_level == ThreatLevel.CRITICAL else 1800
                    self.rate_limiter.block_identifier(
                        request.ip_address,
                        block_duration,
                        f"Security violation: {incident.rule_triggered}"
                    )
                break
        
        # 6. API 키 검증 (필요한 경우)
        if endpoint_type in [APIEndpointType.PROTECTED, APIEndpointType.ADMIN]:
            if not self._validate_api_key(request):
                result["allowed"] = False
                result["reason"] = "invalid_api_key"
                return result
        
        return result
    
    def _validate_api_key(self, request: APIRequest) -> bool:
        """API 키 검증"""
        api_key = request.api_key
        if not api_key:
            return False
        
        key_info = self.api_keys.get(api_key)
        if not key_info:
            return False
        
        # 만료 확인
        if key_info.get("expires_at") and datetime.now() > key_info["expires_at"]:
            return False
        
        # 사용 횟수 업데이트
        key_info["usage_count"] = key_info.get("usage_count", 0) + 1
        key_info["last_used"] = datetime.now()
        
        return True
    
    def create_api_key(self, user_id: str, name: str, permissions: List[str], 
                      expires_in_days: Optional[int] = None) -> str:
        """API 키 생성"""
        api_key = f"tva_{secrets.token_urlsafe(32)}"
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        self.api_keys[api_key] = {
            "user_id": user_id,
            "name": name,
            "permissions": permissions,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "usage_count": 0,
            "last_used": None,
            "active": True
        }
        
        return api_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """API 키 취소"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            return True
        return False
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """보안 통계"""
        total_incidents = len(self.incidents)
        
        # 위협 레벨별 통계
        threat_stats = {level.value: 0 for level in ThreatLevel}
        rule_stats = {}
        
        for incident in self.incidents:
            threat_stats[incident.threat_level.value] += 1
            rule_stats[incident.rule_triggered] = rule_stats.get(incident.rule_triggered, 0) + 1
        
        return {
            "total_incidents": total_incidents,
            "threat_level_distribution": threat_stats,
            "rule_trigger_count": rule_stats,
            "blocked_ips": len(self.ip_blacklist),
            "whitelisted_ips": len(self.ip_whitelist),
            "active_api_keys": sum(1 for key in self.api_keys.values() if key["active"])
        }
    
    def add_to_whitelist(self, ip_address: str):
        """IP 화이트리스트 추가"""
        try:
            ipaddress.ip_address(ip_address)  # 유효성 검증
            self.ip_whitelist.add(ip_address)
            safe_print(f"✅ IP 화이트리스트 추가: {ip_address}")
        except ValueError:
            logger.error(f"잘못된 IP 주소: {ip_address}")
    
    def add_to_blacklist(self, ip_address: str, reason: str = ""):
        """IP 블랙리스트 추가"""
        try:
            ipaddress.ip_address(ip_address)  # 유효성 검증
            self.ip_blacklist.add(ip_address)
            logger.warning(f"IP 블랙리스트 추가: {ip_address}, 이유: {reason}")
        except ValueError:
            logger.error(f"잘못된 IP 주소: {ip_address}")
    
    def get_recent_incidents(self, hours: int = 24) -> List[SecurityIncident]:
        """최근 보안 사고 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            incident for incident in self.incidents
            if incident.timestamp >= cutoff_time
        ]


# 보안 데코레이터들
def require_api_security(endpoint_type: APIEndpointType = APIEndpointType.PUBLIC):
    """API 보안 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 실제 구현에서는 Flask/FastAPI request context에서 정보 추출
            request_info = APIRequest(
                request_id=f"req_{int(time.time())}",
                ip_address=kwargs.get('ip_address', '127.0.0.1'),
                user_agent=kwargs.get('user_agent', 'Unknown'),
                method=kwargs.get('method', 'GET'),
                endpoint=kwargs.get('endpoint', '/unknown'),
                headers=kwargs.get('headers', {}),
                query_params=kwargs.get('query_params', {}),
                body=kwargs.get('body'),
                user_id=kwargs.get('user_id'),
                api_key=kwargs.get('api_key'),
                timestamp=datetime.now()
            )
            
            # 보안 검증
            security_manager = get_api_security_manager()
            validation_result = security_manager.validate_request(request_info, endpoint_type)
            
            if not validation_result["allowed"]:
                return {
                    "error": "access_denied",
                    "reason": validation_result["reason"],
                    "message": "요청이 거부되었습니다."
                }
            
            # 보안 경고가 있는 경우 로깅
            if validation_result["security_warnings"]:
                logger.warning(f"보안 경고: {validation_result['security_warnings']}, IP: {request_info.ip_address}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60):
    """Rate limit 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            identifier = kwargs.get('ip_address', '127.0.0.1')
            
            # 커스텀 규칙 생성
            custom_rule = RateLimitRule(
                name="Custom",
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_minute * 60,
                requests_per_day=requests_per_minute * 1440
            )
            
            rate_limiter = RateLimiter()
            rate_limiter.rules["custom"] = custom_rule
            
            result = rate_limiter.check_rate_limit(identifier, "custom")
            
            if not result["allowed"]:
                return {
                    "error": "rate_limit_exceeded",
                    "message": "요청 한도를 초과했습니다.",
                    "retry_after": result.get("retry_after", 60)
                }
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 전역 API 보안 관리자 인스턴스
_api_security_manager = None

def get_api_security_manager() -> APISecurityManager:
    """API 보안 관리자 인스턴스 반환"""
    global _api_security_manager
    if _api_security_manager is None:
        _api_security_manager = APISecurityManager()
    return _api_security_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== API 보안 & Rate Limiting 시스템 테스트 ===")
    
    security_manager = get_api_security_manager()
    
    # 테스트 요청 생성
    test_request = APIRequest(
        request_id="test_001",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 Test Browser",
        method="GET",
        endpoint="/api/game/status",
        headers={"Authorization": "Bearer test_token"},
        query_params={},
        body=None,
        user_id="user_123",
        api_key=None,
        timestamp=datetime.now()
    )
    
    # 요청 검증 테스트
    result = security_manager.validate_request(test_request)
    if result["allowed"]:
        safe_print("✅ 정상 요청 통과")
    else:
        safe_print(f"❌ 요청 거부: {result['reason']}")
    
    # 악성 요청 테스트
    malicious_request = APIRequest(
        request_id="test_002",
        ip_address="192.168.1.100",
        user_agent="sqlmap/1.0",
        method="GET",
        endpoint="/api/data?id=1' OR 1=1--",
        headers={},
        query_params={"id": "1' OR 1=1--"},
        body=None,
        user_id=None,
        api_key=None,
        timestamp=datetime.now()
    )
    
    malicious_result = security_manager.validate_request(malicious_request)
    if not malicious_result["allowed"]:
        safe_print("✅ 악성 요청 차단")
        safe_print(f"🔍 탐지된 사고: {len(malicious_result['incidents'])}건")
    
    # 통계 조회
    stats = security_manager.get_security_statistics()
    safe_print(f"📊 보안 통계: {stats['total_incidents']}건의 사고")
    
    # API 키 생성 테스트
    api_key = security_manager.create_api_key(
        user_id="user_123",
        name="Test API Key",
        permissions=["read", "write"],
        expires_in_days=30
    )
    safe_print(f"🔑 API 키 생성: {api_key[:20]}...")
    
    safe_print("🏁 API 보안 & Rate Limiting 시스템 테스트 완료")