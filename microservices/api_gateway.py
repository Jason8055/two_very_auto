#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - API Gateway
마이크로서비스 통합 관리 및 라우팅 게이트웨이
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from functools import wraps
import asyncio
import aiohttp

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    from flask import Flask, request, jsonify, Response
    import requests
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    FLASK_AVAILABLE = True
    safe_print("✅ Flask 및 HTTP 라이브러리 사용 가능")
except ImportError:
    FLASK_AVAILABLE = False
    safe_print("⚠️ Flask 라이브러리 미설치")


@dataclass
class ServiceEndpoint:
    """서비스 엔드포인트 정보"""
    name: str
    host: str
    port: int
    health_check_path: str = "/health"
    weight: int = 1
    max_connections: int = 100
    timeout_seconds: int = 30
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    response_time_ms: float = 0
    error_count: int = 0


@dataclass
class RouteConfig:
    """라우팅 설정"""
    path: str
    service_name: str
    methods: List[str]
    rate_limit: Optional[str] = None
    auth_required: bool = False
    cache_ttl: int = 0
    retry_count: int = 3
    circuit_breaker: bool = True


@dataclass
class RequestMetrics:
    """요청 메트릭"""
    timestamp: datetime
    path: str
    method: str
    service_name: str
    response_time_ms: float
    status_code: int
    client_ip: str
    user_agent: str


class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class RateLimiter:
    """Rate Limiting 구현"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> bool:
        """요청 허용 여부 확인"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # 오래된 요청 기록 제거
        while self.requests[client_id] and self.requests[client_id][0] < window_start:
            self.requests[client_id].popleft()
        
        # 현재 요청 수 확인
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # 요청 기록 추가
        self.requests[client_id].append(now)
        return True


class ServiceRegistry:
    """서비스 레지스트리"""
    
    def __init__(self):
        self.services: Dict[str, List[ServiceEndpoint]] = defaultdict(list)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def register_service(self, endpoint: ServiceEndpoint):
        """서비스 등록"""
        self.services[endpoint.name].append(endpoint)
        service_key = f"{endpoint.name}:{endpoint.host}:{endpoint.port}"
        self.circuit_breakers[service_key] = CircuitBreaker()
        
        safe_print(f"📡 서비스 등록: {endpoint.name} -> {endpoint.host}:{endpoint.port}")
    
    def get_healthy_endpoint(self, service_name: str) -> Optional[ServiceEndpoint]:
        """건강한 엔드포인트 반환 (로드 밸런싱)"""
        endpoints = [ep for ep in self.services[service_name] if ep.is_healthy]
        
        if not endpoints:
            return None
        
        # 가중치 기반 라운드 로빈
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]
        
        # 응답 시간 기반 선택
        best_endpoint = min(endpoints, key=lambda ep: ep.response_time_ms * (1 / max(ep.weight, 1)))
        return best_endpoint
    
    async def health_check(self):
        """모든 서비스 상태 확인"""
        for service_name, endpoints in self.services.items():
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"http://{endpoint.host}:{endpoint.port}{endpoint.health_check_path}",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            is_healthy = response.status == 200
                            response_time = (time.time() - start_time) * 1000
                    
                    endpoint.is_healthy = is_healthy
                    endpoint.response_time_ms = response_time
                    endpoint.last_health_check = datetime.now()
                    
                    if is_healthy:
                        endpoint.error_count = 0
                    else:
                        endpoint.error_count += 1
                    
                except Exception as e:
                    endpoint.is_healthy = False
                    endpoint.error_count += 1
                    logger.warning(f"헬스체크 실패 {endpoint.name}: {e}")


class APIGateway:
    """API Gateway 메인 클래스"""
    
    def __init__(self, config_path: str = "gateway_config.json"):
        self.config_path = Path(config_path)
        self.service_registry = ServiceRegistry()
        self.routes: Dict[str, RouteConfig] = {}
        self.rate_limiter = RateLimiter()
        self.metrics: List[RequestMetrics] = []
        self.max_metrics = 10000
        
        # Flask 앱 초기화
        self.app = None
        if FLASK_AVAILABLE:
            self.init_flask_app()
        
        self.load_config()
        safe_print("🚪 API Gateway 초기화 완료")
    
    def init_flask_app(self):
        """Flask 앱 초기화"""
        self.app = Flask(__name__)
        
        # Rate Limiter 설정
        limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["1000 per hour"]
        )
        
        # 모든 요청에 대한 프록시 핸들러
        @self.app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        def proxy_request(path):
            return self.handle_request(path)
        
        # 루트 요청 처리
        @self.app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        def proxy_root():
            return self.handle_request('')
        
        # Gateway 상태 정보
        @self.app.route('/gateway/status')
        def gateway_status():
            return jsonify(self.get_status())
        
        # 서비스 상태 정보
        @self.app.route('/gateway/services')
        def service_status():
            return jsonify(self.get_services_status())
        
        # 메트릭 정보
        @self.app.route('/gateway/metrics')
        def gateway_metrics():
            return jsonify(self.get_metrics_summary())
    
    def load_config(self):
        """설정 로드"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 서비스 등록
                for service_config in config.get('services', []):
                    endpoint = ServiceEndpoint(
                        name=service_config['name'],
                        host=service_config['host'],
                        port=service_config['port'],
                        health_check_path=service_config.get('health_check_path', '/health'),
                        weight=service_config.get('weight', 1),
                        max_connections=service_config.get('max_connections', 100),
                        timeout_seconds=service_config.get('timeout_seconds', 30)
                    )
                    self.service_registry.register_service(endpoint)
                
                # 라우팅 설정
                for route_config in config.get('routes', []):
                    route = RouteConfig(
                        path=route_config['path'],
                        service_name=route_config['service_name'],
                        methods=route_config.get('methods', ['GET', 'POST']),
                        rate_limit=route_config.get('rate_limit'),
                        auth_required=route_config.get('auth_required', False),
                        cache_ttl=route_config.get('cache_ttl', 0),
                        retry_count=route_config.get('retry_count', 3),
                        circuit_breaker=route_config.get('circuit_breaker', True)
                    )
                    self.routes[route.path] = route
                
                safe_print(f"✅ Gateway 설정 로드: {len(self.service_registry.services)}개 서비스, {len(self.routes)}개 라우트")
                
            except Exception as e:
                logger.error(f"설정 로드 실패: {e}")
                self.create_default_config()
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """기본 설정 생성"""
        default_config = {
            "services": [
                {
                    "name": "web-service",
                    "host": "web",
                    "port": 5000,
                    "health_check_path": "/api/health",
                    "weight": 2,
                    "timeout_seconds": 30
                },
                {
                    "name": "ai-service",
                    "host": "ai-engine",
                    "port": 5001,
                    "health_check_path": "/health",
                    "weight": 1,
                    "timeout_seconds": 60
                }
            ],
            "routes": [
                {
                    "path": "/api/ai/*",
                    "service_name": "ai-service",
                    "methods": ["GET", "POST"],
                    "rate_limit": "10 per minute",
                    "retry_count": 2,
                    "circuit_breaker": True
                },
                {
                    "path": "/api/*",
                    "service_name": "web-service",
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "rate_limit": "100 per minute"
                },
                {
                    "path": "/*",
                    "service_name": "web-service",
                    "methods": ["GET", "POST"],
                    "rate_limit": "200 per minute"
                }
            ]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        safe_print(f"📝 기본 Gateway 설정 생성: {self.config_path}")
    
    def find_matching_route(self, path: str) -> Optional[RouteConfig]:
        """경로에 맞는 라우트 찾기"""
        # 정확한 매치 우선
        if path in self.routes:
            return self.routes[path]
        
        # 와일드카드 매치
        for route_path, route_config in self.routes.items():
            if route_path.endswith('/*'):
                prefix = route_path[:-2]
                if path.startswith(prefix):
                    return route_config
        
        # 기본 라우트
        if '/*' in self.routes:
            return self.routes['/*']
        
        return None
    
    def handle_request(self, path: str = '') -> Response:
        """요청 처리"""
        start_time = time.time()
        client_ip = request.remote_addr
        method = request.method
        
        try:
            # 1. 라우트 찾기
            route = self.find_matching_route(path)
            if not route:
                return jsonify({"error": "Route not found"}), 404
            
            # 2. 메서드 확인
            if method not in route.methods:
                return jsonify({"error": "Method not allowed"}), 405
            
            # 3. Rate Limiting 확인
            if route.rate_limit:
                if not self.rate_limiter.is_allowed(client_ip):
                    return jsonify({"error": "Rate limit exceeded"}), 429
            
            # 4. 인증 확인 (구현 생략)
            if route.auth_required:
                # JWT 토큰 검증 로직 추가
                pass
            
            # 5. 서비스 엔드포인트 찾기
            endpoint = self.service_registry.get_healthy_endpoint(route.service_name)
            if not endpoint:
                return jsonify({"error": "Service unavailable"}), 503
            
            # 6. 요청 프록시
            response = self.proxy_request_to_service(endpoint, path, route)
            
            # 7. 메트릭 기록
            response_time = (time.time() - start_time) * 1000
            self.record_metrics(path, method, route.service_name, response_time, 
                              response.status_code, client_ip)
            
            return response
            
        except Exception as e:
            logger.error(f"요청 처리 오류: {e}")
            response_time = (time.time() - start_time) * 1000
            self.record_metrics(path, method, "error", response_time, 500, client_ip)
            
            return jsonify({"error": "Internal server error"}), 500
    
    def proxy_request_to_service(self, endpoint: ServiceEndpoint, path: str, 
                                route: RouteConfig) -> Response:
        """서비스로 요청 프록시"""
        service_key = f"{endpoint.name}:{endpoint.host}:{endpoint.port}"
        circuit_breaker = self.service_registry.circuit_breakers.get(service_key)
        
        def make_request():
            # 대상 URL 구성
            target_url = f"http://{endpoint.host}:{endpoint.port}/{path}"
            
            # 요청 데이터 준비
            headers = dict(request.headers)
            headers.pop('Host', None)  # Host 헤더 제거
            
            params = request.args
            data = request.get_data()
            
            # 요청 전송
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=params,
                data=data,
                timeout=endpoint.timeout_seconds,
                allow_redirects=False
            )
            
            return response
        
        # 서킷 브레이커를 통한 요청
        try:
            if circuit_breaker and route.circuit_breaker:
                upstream_response = circuit_breaker.call(make_request)
            else:
                upstream_response = make_request()
            
            # Flask Response 객체로 변환
            flask_response = Response(
                response=upstream_response.content,
                status=upstream_response.status_code,
                headers=list(upstream_response.headers.items())
            )
            
            return flask_response
            
        except Exception as e:
            logger.error(f"프록시 요청 실패: {e}")
            
            # 재시도 로직
            if route.retry_count > 1:
                for retry in range(route.retry_count - 1):
                    try:
                        time.sleep(0.1 * (retry + 1))  # 백오프
                        upstream_response = make_request()
                        return Response(
                            response=upstream_response.content,
                            status=upstream_response.status_code,
                            headers=list(upstream_response.headers.items())
                        )
                    except:
                        continue
            
            return jsonify({"error": "Service temporarily unavailable"}), 502
    
    def record_metrics(self, path: str, method: str, service_name: str,
                      response_time_ms: float, status_code: int, client_ip: str):
        """메트릭 기록"""
        metric = RequestMetrics(
            timestamp=datetime.now(),
            path=path,
            method=method,
            service_name=service_name,
            response_time_ms=response_time_ms,
            status_code=status_code,
            client_ip=client_ip,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        self.metrics.append(metric)
        
        # 메트릭 개수 제한
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_status(self) -> Dict[str, Any]:
        """Gateway 상태 정보"""
        recent_metrics = [
            m for m in self.metrics 
            if m.timestamp > datetime.now() - timedelta(minutes=5)
        ]
        
        return {
            "status": "healthy",
            "uptime": "운영 중",
            "total_services": len(self.service_registry.services),
            "total_routes": len(self.routes),
            "recent_requests_5m": len(recent_metrics),
            "avg_response_time_ms": sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0,
            "error_rate": sum(1 for m in recent_metrics if m.status_code >= 400) / len(recent_metrics) if recent_metrics else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_services_status(self) -> Dict[str, Any]:
        """서비스 상태 정보"""
        services_status = {}
        
        for service_name, endpoints in self.service_registry.services.items():
            healthy_count = sum(1 for ep in endpoints if ep.is_healthy)
            avg_response_time = sum(ep.response_time_ms for ep in endpoints) / len(endpoints)
            
            services_status[service_name] = {
                "total_endpoints": len(endpoints),
                "healthy_endpoints": healthy_count,
                "avg_response_time_ms": round(avg_response_time, 2),
                "endpoints": [
                    {
                        "host": ep.host,
                        "port": ep.port,
                        "is_healthy": ep.is_healthy,
                        "response_time_ms": round(ep.response_time_ms, 2),
                        "error_count": ep.error_count,
                        "last_health_check": ep.last_health_check.isoformat() if ep.last_health_check else None
                    }
                    for ep in endpoints
                ]
            }
        
        return services_status
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약"""
        if not self.metrics:
            return {"message": "No metrics available"}
        
        # 최근 1시간 메트릭
        recent_metrics = [
            m for m in self.metrics 
            if m.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        # 서비스별 통계
        service_stats = defaultdict(lambda: {"requests": 0, "response_time": 0, "errors": 0})
        
        for metric in recent_metrics:
            stats = service_stats[metric.service_name]
            stats["requests"] += 1
            stats["response_time"] += metric.response_time_ms
            if metric.status_code >= 400:
                stats["errors"] += 1
        
        # 평균 계산
        for service, stats in service_stats.items():
            if stats["requests"] > 0:
                stats["avg_response_time"] = round(stats["response_time"] / stats["requests"], 2)
                stats["error_rate"] = round(stats["errors"] / stats["requests"], 3)
            stats.pop("response_time")  # 중간 계산값 제거
        
        return {
            "total_requests": len(self.metrics),
            "recent_requests_1h": len(recent_metrics),
            "service_statistics": dict(service_stats),
            "top_paths": self._get_top_paths(recent_metrics),
            "status_code_distribution": self._get_status_code_distribution(recent_metrics)
        }
    
    def _get_top_paths(self, metrics: List[RequestMetrics], limit: int = 10) -> List[Dict[str, Any]]:
        """상위 요청 경로"""
        path_counts = defaultdict(int)
        for metric in metrics:
            path_counts[metric.path] += 1
        
        return [
            {"path": path, "requests": count}
            for path, count in sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        ]
    
    def _get_status_code_distribution(self, metrics: List[RequestMetrics]) -> Dict[str, int]:
        """상태 코드 분포"""
        status_counts = defaultdict(int)
        for metric in metrics:
            status_group = f"{metric.status_code // 100}xx"
            status_counts[status_group] += 1
        
        return dict(status_counts)
    
    async def start_health_check_scheduler(self):
        """헬스체크 스케줄러 시작"""
        while True:
            try:
                await self.service_registry.health_check()
                await asyncio.sleep(30)  # 30초마다 헬스체크
            except Exception as e:
                logger.error(f"헬스체크 스케줄러 오류: {e}")
                await asyncio.sleep(60)
    
    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """Gateway 서버 실행"""
        if not FLASK_AVAILABLE:
            safe_print("❌ Flask 라이브러리가 필요합니다")
            return
        
        # 헬스체크 스케줄러 시작 (백그라운드)
        import threading
        def health_check_worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_health_check_scheduler())
        
        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()
        
        safe_print(f"🚪 API Gateway 시작: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


# 전역 인스턴스
_api_gateway = None

def get_api_gateway() -> APIGateway:
    """API Gateway 인스턴스 반환"""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== API Gateway 테스트 ===")
    
    gateway = get_api_gateway()
    
    if FLASK_AVAILABLE:
        # 상태 정보 출력
        status = gateway.get_status()
        safe_print(f"📊 Gateway 상태: {status}")
        
        services = gateway.get_services_status()
        safe_print(f"🔧 서비스 상태: {list(services.keys())}")
        
        # 개발 모드로 실행 (실제 운영에서는 주석 처리)
        if input("Gateway를 시작하시겠습니까? (y/N): ").lower() == 'y':
            gateway.run(debug=True)
    
    else:
        safe_print("❌ Flask 라이브러리 설치 필요: pip install flask flask-limiter")
    
    safe_print("🏁 API Gateway 테스트 완료")