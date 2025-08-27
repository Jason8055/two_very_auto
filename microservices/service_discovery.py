#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 서비스 디스커버리
마이크로서비스 자동 발견 및 등록 시스템
"""

import json
import time
import socket
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
import asyncio

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    import requests
    import aiohttp
    HTTP_AVAILABLE = True
    safe_print("✅ HTTP 클라이언트 라이브러리 사용 가능")
except ImportError:
    HTTP_AVAILABLE = False
    safe_print("⚠️ HTTP 라이브러리 미설치")


@dataclass
class ServiceInstance:
    """서비스 인스턴스 정보"""
    service_id: str
    service_name: str
    host: str
    port: int
    version: str
    metadata: Dict[str, Any]
    health_check_url: str
    registration_time: datetime
    last_heartbeat: datetime
    status: str = "UP"  # UP, DOWN, OUT_OF_SERVICE
    load: float = 0.0  # CPU 사용률 등
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['registration_time'] = self.registration_time.isoformat()
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInstance':
        """딕셔너리에서 생성"""
        data['registration_time'] = datetime.fromisoformat(data['registration_time'])
        data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
        return cls(**data)


class ServiceRegistry:
    """서비스 레지스트리"""
    
    def __init__(self, heartbeat_timeout: int = 60):
        self.services: Dict[str, List[ServiceInstance]] = defaultdict(list)
        self.service_instances: Dict[str, ServiceInstance] = {}  # service_id -> instance
        self.heartbeat_timeout = heartbeat_timeout
        self.event_listeners: List[callable] = []
        
        # 백그라운드 정리 작업
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        safe_print("📋 서비스 레지스트리 초기화 완료")
    
    def register_service(self, instance: ServiceInstance) -> bool:
        """서비스 등록"""
        try:
            # 중복 등록 확인
            if instance.service_id in self.service_instances:
                existing = self.service_instances[instance.service_id]
                if existing.host == instance.host and existing.port == instance.port:
                    # 기존 인스턴스 업데이트
                    existing.last_heartbeat = datetime.now()
                    existing.status = instance.status
                    existing.version = instance.version
                    existing.metadata.update(instance.metadata)
                    
                    self._notify_event('service_updated', existing)
                    safe_print(f"🔄 서비스 업데이트: {instance.service_name} ({instance.service_id})")
                    return True
            
            # 새 인스턴스 등록
            instance.registration_time = datetime.now()
            instance.last_heartbeat = datetime.now()
            
            self.services[instance.service_name].append(instance)
            self.service_instances[instance.service_id] = instance
            
            self._notify_event('service_registered', instance)
            safe_print(f"✅ 서비스 등록: {instance.service_name} -> {instance.host}:{instance.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"서비스 등록 실패: {e}")
            return False
    
    def deregister_service(self, service_id: str) -> bool:
        """서비스 등록 해제"""
        try:
            if service_id not in self.service_instances:
                return False
            
            instance = self.service_instances[service_id]
            
            # 서비스 목록에서 제거
            self.services[instance.service_name] = [
                inst for inst in self.services[instance.service_name]
                if inst.service_id != service_id
            ]
            
            # 빈 서비스는 제거
            if not self.services[instance.service_name]:
                del self.services[instance.service_name]
            
            # 인스턴스 제거
            del self.service_instances[service_id]
            
            self._notify_event('service_deregistered', instance)
            safe_print(f"🗑️ 서비스 등록 해제: {instance.service_name} ({service_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"서비스 등록 해제 실패: {e}")
            return False
    
    def update_heartbeat(self, service_id: str, load: float = 0.0) -> bool:
        """서비스 하트비트 업데이트"""
        if service_id not in self.service_instances:
            return False
        
        instance = self.service_instances[service_id]
        instance.last_heartbeat = datetime.now()
        instance.load = load
        instance.status = "UP"
        
        return True
    
    def get_service_instances(self, service_name: str) -> List[ServiceInstance]:
        """서비스 인스턴스 목록 조회"""
        return [inst for inst in self.services.get(service_name, []) if inst.status == "UP"]
    
    def get_healthy_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """건강한 서비스 인스턴스 반환 (로드 밸런싱)"""
        instances = self.get_service_instances(service_name)
        
        if not instances:
            return None
        
        # 로드 기반 선택 (낮은 로드 우선)
        return min(instances, key=lambda x: x.load)
    
    def get_all_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """모든 서비스 정보 반환"""
        result = {}
        for service_name, instances in self.services.items():
            result[service_name] = [inst.to_dict() for inst in instances]
        
        return result
    
    def add_event_listener(self, listener: callable):
        """이벤트 리스너 추가"""
        self.event_listeners.append(listener)
    
    def _notify_event(self, event_type: str, instance: ServiceInstance):
        """이벤트 알림"""
        for listener in self.event_listeners:
            try:
                listener(event_type, instance)
            except Exception as e:
                logger.error(f"이벤트 리스너 오류: {e}")
    
    def _cleanup_worker(self):
        """백그라운드 정리 작업"""
        while True:
            try:
                self._cleanup_dead_services()
                time.sleep(30)  # 30초마다 정리
            except Exception as e:
                logger.error(f"서비스 정리 작업 오류: {e}")
                time.sleep(60)
    
    def _cleanup_dead_services(self):
        """죽은 서비스 인스턴스 정리"""
        cutoff_time = datetime.now() - timedelta(seconds=self.heartbeat_timeout)
        dead_services = []
        
        for service_id, instance in self.service_instances.items():
            if instance.last_heartbeat < cutoff_time and instance.status != "OUT_OF_SERVICE":
                instance.status = "DOWN"
                dead_services.append(service_id)
        
        # 죽은 서비스 제거
        for service_id in dead_services:
            self.deregister_service(service_id)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """레지스트리 통계 정보"""
        total_instances = len(self.service_instances)
        up_instances = sum(1 for inst in self.service_instances.values() if inst.status == "UP")
        down_instances = sum(1 for inst in self.service_instances.values() if inst.status == "DOWN")
        
        service_stats = {}
        for service_name, instances in self.services.items():
            service_stats[service_name] = {
                "total": len(instances),
                "up": sum(1 for inst in instances if inst.status == "UP"),
                "down": sum(1 for inst in instances if inst.status == "DOWN"),
                "avg_load": sum(inst.load for inst in instances) / len(instances) if instances else 0
            }
        
        return {
            "total_services": len(self.services),
            "total_instances": total_instances,
            "up_instances": up_instances,
            "down_instances": down_instances,
            "service_details": service_stats,
            "heartbeat_timeout": self.heartbeat_timeout
        }


class ServiceDiscoveryServer:
    """서비스 디스커버리 서버"""
    
    def __init__(self, port: int = 8761):
        self.port = port
        self.registry = ServiceRegistry()
        self.app = None
        
        if HTTP_AVAILABLE:
            self.init_flask_app()
        
        safe_print(f"🔍 서비스 디스커버리 서버 초기화: 포트 {port}")
    
    def init_flask_app(self):
        """Flask 앱 초기화"""
        try:
            from flask import Flask, request, jsonify
            
            self.app = Flask(__name__)
            
            # 서비스 등록
            @self.app.route('/eureka/apps/<service_name>', methods=['POST'])
            def register_service(service_name):
                try:
                    data = request.get_json()
                    
                    instance = ServiceInstance(
                        service_id=data['service_id'],
                        service_name=service_name,
                        host=data['host'],
                        port=data['port'],
                        version=data.get('version', '1.0.0'),
                        metadata=data.get('metadata', {}),
                        health_check_url=data.get('health_check_url', f"http://{data['host']}:{data['port']}/health"),
                        registration_time=datetime.now(),
                        last_heartbeat=datetime.now()
                    )
                    
                    if self.registry.register_service(instance):
                        return jsonify({"status": "registered"}), 201
                    else:
                        return jsonify({"error": "Registration failed"}), 500
                        
                except Exception as e:
                    logger.error(f"서비스 등록 API 오류: {e}")
                    return jsonify({"error": str(e)}), 400
            
            # 서비스 등록 해제
            @self.app.route('/eureka/apps/<service_name>/<service_id>', methods=['DELETE'])
            def deregister_service(service_name, service_id):
                if self.registry.deregister_service(service_id):
                    return jsonify({"status": "deregistered"}), 200
                else:
                    return jsonify({"error": "Service not found"}), 404
            
            # 하트비트
            @self.app.route('/eureka/apps/<service_name>/<service_id>', methods=['PUT'])
            def heartbeat(service_name, service_id):
                data = request.get_json() or {}
                load = data.get('load', 0.0)
                
                if self.registry.update_heartbeat(service_id, load):
                    return jsonify({"status": "ok"}), 200
                else:
                    return jsonify({"error": "Service not found"}), 404
            
            # 서비스 조회
            @self.app.route('/eureka/apps/<service_name>', methods=['GET'])
            def get_service(service_name):
                instances = self.registry.get_service_instances(service_name)
                return jsonify({
                    "service_name": service_name,
                    "instances": [inst.to_dict() for inst in instances]
                })
            
            # 모든 서비스 조회
            @self.app.route('/eureka/apps', methods=['GET'])
            def get_all_services():
                return jsonify(self.registry.get_all_services())
            
            # 서비스 상태
            @self.app.route('/eureka/status', methods=['GET'])
            def get_status():
                return jsonify(self.registry.get_registry_stats())
            
            # 헬스체크
            @self.app.route('/health', methods=['GET'])
            def health_check():
                return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()})
            
        except ImportError:
            safe_print("⚠️ Flask 라이브러리 미설치")
    
    def run(self, host: str = "0.0.0.0", debug: bool = False):
        """서버 실행"""
        if not self.app:
            safe_print("❌ Flask 앱이 초기화되지 않음")
            return
        
        safe_print(f"🚀 서비스 디스커버리 서버 시작: http://{host}:{self.port}")
        self.app.run(host=host, port=self.port, debug=debug)


class ServiceDiscoveryClient:
    """서비스 디스커버리 클라이언트"""
    
    def __init__(self, discovery_server_url: str = "http://localhost:8761"):
        self.discovery_server_url = discovery_server_url.rstrip('/')
        self.registered_services: Set[str] = set()
        self.heartbeat_threads: Dict[str, threading.Thread] = {}
        
        safe_print(f"📡 서비스 디스커버리 클라이언트 초기화: {discovery_server_url}")
    
    def register_service(self, service_name: str, service_id: str, host: str, port: int,
                        version: str = "1.0.0", metadata: Dict[str, Any] = None,
                        heartbeat_interval: int = 30) -> bool:
        """서비스 등록"""
        if not HTTP_AVAILABLE:
            safe_print("⚠️ HTTP 라이브러리 필요")
            return False
        
        try:
            # 등록 데이터
            registration_data = {
                "service_id": service_id,
                "host": host,
                "port": port,
                "version": version,
                "metadata": metadata or {},
                "health_check_url": f"http://{host}:{port}/health"
            }
            
            # 등록 요청
            response = requests.post(
                f"{self.discovery_server_url}/eureka/apps/{service_name}",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 201:
                self.registered_services.add(service_id)
                
                # 하트비트 스레드 시작
                self._start_heartbeat_thread(service_name, service_id, heartbeat_interval)
                
                safe_print(f"✅ 서비스 등록 완료: {service_name} ({service_id})")
                return True
            else:
                safe_print(f"❌ 서비스 등록 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"서비스 등록 오류: {e}")
            return False
    
    def deregister_service(self, service_name: str, service_id: str) -> bool:
        """서비스 등록 해제"""
        if not HTTP_AVAILABLE:
            return False
        
        try:
            # 하트비트 스레드 중지
            if service_id in self.heartbeat_threads:
                thread = self.heartbeat_threads[service_id]
                thread.do_run = False  # 스레드 종료 신호
                del self.heartbeat_threads[service_id]
            
            # 등록 해제 요청
            response = requests.delete(
                f"{self.discovery_server_url}/eureka/apps/{service_name}/{service_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                self.registered_services.discard(service_id)
                safe_print(f"✅ 서비스 등록 해제 완료: {service_name} ({service_id})")
                return True
            else:
                safe_print(f"❌ 서비스 등록 해제 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"서비스 등록 해제 오류: {e}")
            return False
    
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """서비스 발견"""
        if not HTTP_AVAILABLE:
            return []
        
        try:
            response = requests.get(
                f"{self.discovery_server_url}/eureka/apps/{service_name}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('instances', [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"서비스 발견 오류: {e}")
            return []
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """서비스 URL 조회 (로드 밸런싱)"""
        instances = self.discover_service(service_name)
        
        if not instances:
            return None
        
        # 로드가 낮은 인스턴스 선택
        best_instance = min(instances, key=lambda x: x.get('load', 0))
        
        return f"http://{best_instance['host']}:{best_instance['port']}"
    
    def _start_heartbeat_thread(self, service_name: str, service_id: str, interval: int):
        """하트비트 스레드 시작"""
        def heartbeat_worker():
            thread = threading.current_thread()
            while getattr(thread, "do_run", True):
                try:
                    # 시스템 로드 가져오기
                    import psutil
                    cpu_percent = psutil.cpu_percent(interval=1)
                    
                    # 하트비트 전송
                    response = requests.put(
                        f"{self.discovery_server_url}/eureka/apps/{service_name}/{service_id}",
                        json={"load": cpu_percent},
                        timeout=5
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"하트비트 전송 실패: {response.status_code}")
                    
                except Exception as e:
                    logger.error(f"하트비트 오류: {e}")
                
                time.sleep(interval)
        
        thread = threading.Thread(target=heartbeat_worker, daemon=True)
        thread.do_run = True
        thread.start()
        self.heartbeat_threads[service_id] = thread
    
    def shutdown(self):
        """클라이언트 종료"""
        # 모든 등록된 서비스 해제
        for service_id in list(self.registered_services):
            # 서비스 이름을 찾아서 등록 해제 (간단화를 위해 생략)
            pass
        
        # 하트비트 스레드 종료
        for thread in self.heartbeat_threads.values():
            thread.do_run = False


# 전역 인스턴스들
_discovery_server = None
_discovery_client = None

def get_discovery_server(port: int = 8761) -> ServiceDiscoveryServer:
    """디스커버리 서버 인스턴스 반환"""
    global _discovery_server
    if _discovery_server is None:
        _discovery_server = ServiceDiscoveryServer(port)
    return _discovery_server

def get_discovery_client(server_url: str = "http://localhost:8761") -> ServiceDiscoveryClient:
    """디스커버리 클라이언트 인스턴스 반환"""
    global _discovery_client
    if _discovery_client is None:
        _discovery_client = ServiceDiscoveryClient(server_url)
    return _discovery_client


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 서비스 디스커버리 테스트 ===")
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['server', 'client'], default='server',
                       help='실행 모드 선택')
    parser.add_argument('--port', type=int, default=8761,
                       help='서버 포트')
    args = parser.parse_args()
    
    if args.mode == 'server':
        # 서버 모드
        server = get_discovery_server(args.port)
        if server.app:
            server.run(debug=True)
        else:
            safe_print("❌ Flask 라이브러리 설치 필요")
    
    else:
        # 클라이언트 테스트 모드
        client = get_discovery_client()
        
        # 테스트 서비스 등록
        success = client.register_service(
            service_name="test-service",
            service_id="test-001",
            host="localhost",
            port=9999,
            metadata={"environment": "development"}
        )
        
        if success:
            safe_print("✅ 테스트 서비스 등록 성공")
            
            # 서비스 발견 테스트
            time.sleep(2)
            instances = client.discover_service("test-service")
            safe_print(f"🔍 발견된 인스턴스: {len(instances)}개")
            
            # 정리
            time.sleep(5)
            client.deregister_service("test-service", "test-001")
        
        else:
            safe_print("❌ 테스트 서비스 등록 실패")
    
    safe_print("🏁 서비스 디스커버리 테스트 완료")