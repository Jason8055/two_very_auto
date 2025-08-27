#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - ELK 스택 로깅 시스템
Elasticsearch + Logstash + Kibana 통합 로깅
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import threading
from queue import Queue, Empty
import traceback

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import ConnectionError, TransportError
    ELASTICSEARCH_AVAILABLE = True
    safe_print("✅ Elasticsearch 클라이언트 사용 가능")
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    safe_print("⚠️ elasticsearch 라이브러리 미설치. pip install elasticsearch 실행 필요")


class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """로그 카테고리"""
    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    SYSTEM = "system"
    AUDIT = "audit"


@dataclass
class LogEntry:
    """로그 엔트리"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    component: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = {
            "@timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "component": self.component,
            "host": socket.gethostname(),
            "environment": "production",  # 환경에 따라 동적으로 설정
        }
        
        if self.session_id:
            data["session_id"] = self.session_id
        if self.user_id:
            data["user_id"] = self.user_id
        if self.request_id:
            data["request_id"] = self.request_id
        if self.metadata:
            data["metadata"] = self.metadata
        if self.stack_trace:
            data["stack_trace"] = self.stack_trace
            
        return data


class ElasticsearchHandler:
    """Elasticsearch 로그 핸들러"""
    
    def __init__(self, 
                 hosts: List[str] = ["http://localhost:9200"],
                 index_prefix: str = "two-very-auto",
                 username: Optional[str] = None,
                 password: Optional[str] = None):
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.username = username
        self.password = password
        
        # Elasticsearch 클라이언트 초기화
        self.es_client = None
        if ELASTICSEARCH_AVAILABLE:
            self._initialize_client()
        
        # 비동기 로그 처리를 위한 큐
        self.log_queue = Queue(maxsize=10000)
        self.worker_thread = None
        self.running = False
        
        safe_print("🔍 Elasticsearch 로그 핸들러 초기화 완료")
    
    def _initialize_client(self):
        """Elasticsearch 클라이언트 초기화"""
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
            
            self.es_client = Elasticsearch(
                hosts=self.hosts,
                basic_auth=auth,
                verify_certs=False,
                request_timeout=30,
                retry_on_timeout=True,
                max_retries=3
            )
            
            # 연결 테스트
            if self.es_client.ping():
                safe_print("✅ Elasticsearch 연결 성공")
                self._create_index_templates()
            else:
                safe_print("❌ Elasticsearch 연결 실패")
                self.es_client = None
                
        except Exception as e:
            logger.error(f"Elasticsearch 클라이언트 초기화 실패: {e}")
            self.es_client = None
    
    def _create_index_templates(self):
        """인덱스 템플릿 생성"""
        if not self.es_client:
            return
        
        template_name = f"{self.index_prefix}-logs"
        template_body = {
            "index_patterns": [f"{self.index_prefix}-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.refresh_interval": "5s",
                    "index.codec": "best_compression"
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "message": {"type": "text", "analyzer": "standard"},
                        "component": {"type": "keyword"},
                        "host": {"type": "keyword"},
                        "environment": {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "request_id": {"type": "keyword"},
                        "metadata": {"type": "object", "dynamic": True},
                        "stack_trace": {"type": "text"}
                    }
                }
            }
        }
        
        try:
            self.es_client.indices.put_index_template(
                name=template_name,
                body=template_body
            )
            safe_print(f"📋 인덱스 템플릿 생성: {template_name}")
        except Exception as e:
            logger.error(f"인덱스 템플릿 생성 실패: {e}")
    
    def start_worker(self):
        """워커 스레드 시작"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_logs)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        safe_print("🚀 로그 처리 워커 스레드 시작")
    
    def stop_worker(self):
        """워커 스레드 중지"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        safe_print("🛑 로그 처리 워커 스레드 중지")
    
    def _process_logs(self):
        """로그 처리 워커"""
        batch_size = 100
        batch_timeout = 5
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # 큐에서 로그 엔트리 가져오기
                try:
                    log_entry = self.log_queue.get(timeout=1)
                    batch.append(log_entry)
                except Empty:
                    pass
                
                # 배치 처리 조건 확인
                should_flush = (
                    len(batch) >= batch_size or
                    (batch and time.time() - last_flush >= batch_timeout)
                )
                
                if should_flush and batch:
                    self._send_batch(batch)
                    batch.clear()
                    last_flush = time.time()
                    
            except Exception as e:
                logger.error(f"로그 처리 워커 오류: {e}")
                time.sleep(1)
        
        # 남은 로그 처리
        if batch:
            self._send_batch(batch)
    
    def _send_batch(self, batch: List[LogEntry]):
        """배치로 로그 전송"""
        if not self.es_client:
            return
        
        try:
            # 인덱스 이름 생성 (날짜 기반)
            index_date = datetime.now().strftime("%Y.%m.%d")
            index_name = f"{self.index_prefix}-logs-{index_date}"
            
            # 벌크 요청 구성
            bulk_body = []
            for entry in batch:
                bulk_body.append({
                    "index": {
                        "_index": index_name
                    }
                })
                bulk_body.append(entry.to_dict())
            
            # 벌크 인덱싱 실행
            response = self.es_client.bulk(body=bulk_body)
            
            # 에러 확인
            if response.get("errors"):
                error_count = sum(1 for item in response["items"] if "error" in item.get("index", {}))
                logger.warning(f"Elasticsearch 벌크 인덱싱 부분 실패: {error_count}개 오류")
            
        except Exception as e:
            logger.error(f"Elasticsearch 로그 전송 실패: {e}")
    
    def send_log(self, log_entry: LogEntry):
        """로그 엔트리 전송"""
        if not self.running:
            self.start_worker()
        
        try:
            self.log_queue.put_nowait(log_entry)
        except:
            # 큐가 가득 찬 경우, 가장 오래된 로그 제거 후 추가
            try:
                self.log_queue.get_nowait()
                self.log_queue.put_nowait(log_entry)
            except:
                pass


class StructuredLogger:
    """구조화된 로거"""
    
    def __init__(self, 
                 component: str,
                 elasticsearch_handler: Optional[ElasticsearchHandler] = None,
                 file_handler: Optional[logging.FileHandler] = None):
        self.component = component
        self.es_handler = elasticsearch_handler
        self.file_handler = file_handler
        
        # 컨텍스트 저장
        self.context: Dict[str, Any] = {}
        
        safe_print(f"📝 구조화된 로거 초기화: {component}")
    
    def set_context(self, **kwargs):
        """로깅 컨텍스트 설정"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """로깅 컨텍스트 초기화"""
        self.context.clear()
    
    def _create_log_entry(self, 
                         level: LogLevel, 
                         category: LogCategory, 
                         message: str,
                         **kwargs) -> LogEntry:
        """로그 엔트리 생성"""
        metadata = {**self.context, **kwargs}
        
        # 스택 트레이스 추가 (에러인 경우)
        stack_trace = None
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            stack_trace = traceback.format_exc() if traceback.format_exc().strip() != "NoneType: None" else None
        
        return LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            category=category,
            message=message,
            component=self.component,
            session_id=metadata.get("session_id"),
            user_id=metadata.get("user_id"),
            request_id=metadata.get("request_id"),
            metadata=metadata if metadata else None,
            stack_trace=stack_trace
        )
    
    def log(self, level: LogLevel, category: LogCategory, message: str, **kwargs):
        """일반 로그"""
        log_entry = self._create_log_entry(level, category, message, **kwargs)
        
        # Elasticsearch로 전송
        if self.es_handler:
            self.es_handler.send_log(log_entry)
        
        # 파일로 저장
        if self.file_handler:
            log_data = json.dumps(log_entry.to_dict(), ensure_ascii=False, default=str)
            self.file_handler.emit(logging.LogRecord(
                name=self.component,
                level=getattr(logging, level.value),
                pathname="",
                lineno=0,
                msg=log_data,
                args=(),
                exc_info=None
            ))
    
    def debug(self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs):
        """디버그 로그"""
        self.log(LogLevel.DEBUG, category, message, **kwargs)
    
    def info(self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs):
        """정보 로그"""
        self.log(LogLevel.INFO, category, message, **kwargs)
    
    def warning(self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs):
        """경고 로그"""
        self.log(LogLevel.WARNING, category, message, **kwargs)
    
    def error(self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs):
        """에러 로그"""
        self.log(LogLevel.ERROR, category, message, **kwargs)
    
    def critical(self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs):
        """치명적 에러 로그"""
        self.log(LogLevel.CRITICAL, category, message, **kwargs)
    
    # 특화된 로깅 메서드들
    def security_event(self, event_type: str, message: str, **kwargs):
        """보안 이벤트 로그"""
        self.info(message, LogCategory.SECURITY, event_type=event_type, **kwargs)
    
    def performance_metric(self, metric_name: str, value: float, unit: str = "ms", **kwargs):
        """성능 메트릭 로그"""
        self.info(f"Performance metric: {metric_name}",
                 LogCategory.PERFORMANCE,
                 metric_name=metric_name,
                 metric_value=value,
                 metric_unit=unit,
                 **kwargs)
    
    def business_event(self, event_type: str, message: str, **kwargs):
        """비즈니스 이벤트 로그"""
        self.info(message, LogCategory.BUSINESS, event_type=event_type, **kwargs)
    
    def audit_log(self, action: str, resource: str, result: str, **kwargs):
        """감사 로그"""
        self.info(f"Audit: {action} on {resource} - {result}",
                 LogCategory.AUDIT,
                 action=action,
                 resource=resource,
                 result=result,
                 **kwargs)
    
    def system_metric(self, metric_name: str, value: Union[int, float], **kwargs):
        """시스템 메트릭 로그"""
        self.info(f"System metric: {metric_name}={value}",
                 LogCategory.SYSTEM,
                 metric_name=metric_name,
                 metric_value=value,
                 **kwargs)


class LoggingManager:
    """로깅 관리자"""
    
    def __init__(self, 
                 elasticsearch_hosts: List[str] = ["http://localhost:9200"],
                 log_directory: Path = Path("logs")):
        self.log_directory = log_directory
        self.log_directory.mkdir(exist_ok=True)
        
        # Elasticsearch 핸들러 초기화
        self.es_handler = ElasticsearchHandler(hosts=elasticsearch_hosts)
        
        # 파일 핸들러 설정
        self.file_handlers = self._setup_file_handlers()
        
        # 로거 인스턴스들
        self.loggers: Dict[str, StructuredLogger] = {}
        
        safe_print("📋 로깅 관리자 초기화 완료")
    
    def _setup_file_handlers(self) -> Dict[str, logging.FileHandler]:
        """파일 핸들러 설정"""
        handlers = {}
        
        # 카테고리별 로그 파일
        for category in LogCategory:
            log_file = self.log_directory / f"{category.value}.log"
            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(message)s'))
            handlers[category.value] = handler
        
        return handlers
    
    def get_logger(self, component: str) -> StructuredLogger:
        """로거 인스턴스 반환"""
        if component not in self.loggers:
            # 기본적으로 application 카테고리 파일 핸들러 사용
            file_handler = self.file_handlers.get("application")
            
            self.loggers[component] = StructuredLogger(
                component=component,
                elasticsearch_handler=self.es_handler,
                file_handler=file_handler
            )
        
        return self.loggers[component]
    
    def shutdown(self):
        """로깅 시스템 종료"""
        safe_print("📋 로깅 시스템 종료 중...")
        
        # Elasticsearch 워커 중지
        if self.es_handler:
            self.es_handler.stop_worker()
        
        # 파일 핸들러 정리
        for handler in self.file_handlers.values():
            handler.close()
        
        safe_print("✅ 로깅 시스템 종료 완료")


# 전역 로깅 관리자 인스턴스
_logging_manager = None

def get_logging_manager() -> LoggingManager:
    """로깅 관리자 인스턴스 반환"""
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = LoggingManager()
    return _logging_manager

def get_logger(component: str) -> StructuredLogger:
    """로거 인스턴스 반환"""
    return get_logging_manager().get_logger(component)


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== ELK 로깅 시스템 테스트 ===")
    
    # 로거 생성
    logger = get_logger("test_component")
    
    # 컨텍스트 설정
    logger.set_context(session_id="test_session_123", user_id="user_456")
    
    # 다양한 로그 테스트
    logger.info("애플리케이션 시작", startup_time=1.234)
    logger.security_event("login_attempt", "사용자 로그인 시도", ip_address="192.168.1.100")
    logger.performance_metric("response_time", 145.2, "ms", endpoint="/api/status")
    logger.business_event("game_completed", "바카라 게임 완료", outcome="player", bet_amount=100)
    logger.audit_log("data_export", "user_data", "success", exported_records=1500)
    logger.system_metric("cpu_usage", 75.3, unit="percent")
    
    # 에러 로그 테스트
    try:
        raise ValueError("테스트 에러입니다")
    except Exception as e:
        logger.error(f"에러 발생: {e}")
    
    # 몇 초 대기 후 종료
    time.sleep(3)
    get_logging_manager().shutdown()
    
    safe_print("🏁 ELK 로깅 시스템 테스트 완료")