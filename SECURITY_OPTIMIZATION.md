# Two Very Auto - 보안 및 성능 최적화 가이드

## 🛡️ 보안 최적화

### 1. 환경 변수 보안 강화

#### .env 파일 보호
```bash
# .env 파일 권한 제한
icacls .env /inheritance:r /grant:r %USERNAME%:F

# Git에서 제외 (.gitignore)
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
echo "*password*" >> .gitignore
```

#### 민감한 정보 암호화
```python
# encryption_helper.py 예시
from cryptography.fernet import Fernet

def generate_key():
    """새 암호화 키 생성"""
    return Fernet.generate_key()

def encrypt_sensitive_data(data: str, key: bytes) -> str:
    """민감한 데이터 암호화"""
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data: str, key: bytes) -> str:
    """암호화된 데이터 복호화"""
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()
```

### 2. 네트워크 보안

#### HTTPS 강제 사용
```python
# dashboard_server.py에 추가
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# HTTPS 리다이렉트 미들웨어 추가 (프로덕션 환경)
if os.getenv("PRODUCTION", "false").lower() == "true":
    app.add_middleware(HTTPSRedirectMiddleware)
```

#### CORS 정책 강화
```python
# 프로덕션 환경에서는 특정 도메인만 허용
if os.getenv("PRODUCTION", "false").lower() == "true":
    allowed_origins = ["https://yourdomain.com", "https://admin.yourdomain.com"]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 3. 접근 제어

#### API 인증 토큰
```python
# auth.py
import secrets
from datetime import datetime, timedelta
from typing import Optional

class APIAuthManager:
    def __init__(self):
        self.valid_tokens = {}
        self.master_token = os.getenv("MASTER_API_TOKEN", secrets.token_urlsafe(32))
    
    def generate_token(self, expires_hours: int = 24) -> str:
        """임시 접근 토큰 생성"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        self.valid_tokens[token] = expires_at
        return token
    
    def validate_token(self, token: str) -> bool:
        """토큰 유효성 검사"""
        if token == self.master_token:
            return True
            
        if token in self.valid_tokens:
            if datetime.now() < self.valid_tokens[token]:
                return True
            else:
                del self.valid_tokens[token]
        
        return False
```

### 4. 로그 보안

#### 민감한 정보 마스킹
```python
import re

def sanitize_log_message(message: str) -> str:
    """로그 메시지에서 민감한 정보 제거"""
    patterns = [
        (r'password["\s]*[:=]["\s]*([^"\s,}]+)', r'password": "***"'),
        (r'token["\s]*[:=]["\s]*([^"\s,}]+)', r'token": "***"'),
        (r'key["\s]*[:=]["\s]*([^"\s,}]+)', r'key": "***"'),
        (r'(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})', r'****-****-****-****'),  # 카드번호
        (r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', r'***@***.***'),  # 이메일
    ]
    
    for pattern, replacement in patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    
    return message
```

## ⚡ 성능 최적화

### 1. 데이터베이스 최적화

#### 연결 풀링
```python
import sqlite3
from contextlib import contextmanager
from threading import Lock
from queue import Queue

class DatabaseConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool = Queue(maxsize=max_connections)
        self.lock = Lock()
        
        # 초기 연결 생성
        for _ in range(max_connections):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # WAL 모드로 성능 향상
            conn.execute("PRAGMA synchronous=NORMAL")
            self.pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기"""
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)
```

#### 백업 압축 최적화
```python
import lzma
import bz2
from typing import Tuple

class OptimizedCompression:
    @staticmethod
    def compress_file(file_path: str, compression_type: str = "lzma") -> Tuple[str, float]:
        """최적화된 파일 압축"""
        input_path = Path(file_path)
        
        if compression_type == "lzma":
            output_path = input_path.with_suffix(input_path.suffix + ".xz")
            with open(input_path, 'rb') as f_in:
                with lzma.open(output_path, 'wb', preset=6) as f_out:  # 균형잡힌 압축레벨
                    shutil.copyfileobj(f_in, f_out)
        elif compression_type == "bz2":
            output_path = input_path.with_suffix(input_path.suffix + ".bz2")
            with open(input_path, 'rb') as f_in:
                with bz2.open(output_path, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:  # gzip (기본값)
            output_path = input_path.with_suffix(input_path.suffix + ".gz")
            with open(input_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        # 압축률 계산
        original_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        return str(output_path), compression_ratio
```

### 2. 비동기 처리 최적화

#### 백그라운드 작업 큐
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class BackgroundTask:
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 5  # 1-10, 낮을수록 우선순위 높음

class BackgroundTaskManager:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = asyncio.PriorityQueue()
        self.running = False
    
    async def add_task(self, task: BackgroundTask):
        """백그라운드 작업 추가"""
        await self.task_queue.put((task.priority, task))
    
    async def start_worker(self):
        """백그라운드 워커 시작"""
        self.running = True
        while self.running:
            try:
                priority, task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                # 별도 스레드에서 실행
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, task.func, *task.args, **task.kwargs)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"백그라운드 작업 오류: {e}")
    
    def stop_worker(self):
        """백그라운드 워커 중지"""
        self.running = False
        self.executor.shutdown(wait=True)
```

### 3. 메모리 최적화

#### 대용량 파일 스트리밍
```python
async def stream_large_file(file_path: str, chunk_size: int = 8192):
    """대용량 파일 스트리밍 처리"""
    async def file_generator():
        with open(file_path, 'rb') as file:
            while chunk := file.read(chunk_size):
                yield chunk
    
    return file_generator()

# FastAPI에서 사용
from fastapi.responses import StreamingResponse

@app.get("/download-backup/{backup_id}")
async def download_backup(backup_id: str):
    file_path = f"backups/{backup_id}"
    if not Path(file_path).exists():
        raise HTTPException(404, "백업 파일을 찾을 수 없습니다")
    
    return StreamingResponse(
        stream_large_file(file_path),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={backup_id}"}
    )
```

### 4. 캐싱 최적화

#### 메모리 캐시
```python
from functools import lru_cache
import time
from typing import Any, Optional

class TimedCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear_expired(self):
        """만료된 캐시 정리"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp >= self.ttl
        ]
        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
            del self.timestamps[key]

# 시스템 상태 캐시
status_cache = TimedCache(ttl_seconds=30)

@lru_cache(maxsize=100)
def get_backup_configs():
    """백업 설정 캐시 (변경되지 않는 설정)"""
    # 설정 로드 로직
    pass
```

## 📊 모니터링 및 프로파일링

### 1. 성능 모니터링

#### 시스템 리소스 모니터링
```python
import psutil
import time
from dataclasses import dataclass
from typing import Dict

@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    disk_usage: Dict[str, float]
    network_io: Dict[str, int]
    timestamp: float

class SystemMonitor:
    def __init__(self):
        self.metrics_history = []
        self.max_history = 1000
    
    def collect_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 디스크 사용률
        disk_usage = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = usage.percent
            except PermissionError:
                continue
        
        # 네트워크 I/O
        net_io = psutil.net_io_counters()._asdict()
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_usage=disk_usage,
            network_io=net_io,
            timestamp=time.time()
        )
        
        # 히스토리 관리
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
        
        return metrics
    
    def get_average_metrics(self, minutes: int = 5) -> SystemMetrics:
        """평균 메트릭 계산"""
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return self.collect_metrics()
        
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        
        return SystemMetrics(
            cpu_percent=avg_cpu,
            memory_percent=avg_memory,
            disk_usage=recent_metrics[-1].disk_usage,  # 최신 값
            network_io=recent_metrics[-1].network_io,   # 최신 값
            timestamp=time.time()
        )
```

### 2. 애플리케이션 성능 추적

#### 함수 실행 시간 측정
```python
import functools
import time
import logging
from typing import Callable

def performance_monitor(func: Callable) -> Callable:
    """함수 실행 성능 모니터링 데코레이터"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time
            
            if execution_time > 1.0:  # 1초 이상 걸리면 로깅
                logging.info(f"성능 주의: {func.__name__} 실행시간 {execution_time:.2f}초")
            
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logging.error(f"함수 오류: {func.__name__} 실행시간 {execution_time:.2f}초, 오류: {e}")
            raise
    
    return wrapper

# 사용 예시
@performance_monitor
def backup_database(config_name: str):
    # 백업 로직
    pass
```

## 🔧 배포 최적화

### 1. 프로덕션 설정

#### 환경별 설정 분리
```python
# config.py
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Config:
    def __init__(self):
        self.environment = Environment(os.getenv("ENVIRONMENT", "development"))
        self.debug = self.environment == Environment.DEVELOPMENT
        self.log_level = "DEBUG" if self.debug else "INFO"
        
        # 보안 설정
        self.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
        
        # 성능 설정
        self.max_backup_concurrent = int(os.getenv("MAX_BACKUP_CONCURRENT", "3"))
        self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        
        # 모니터링 설정
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.metrics_port = int(os.getenv("METRICS_PORT", "9090"))

# 전역 설정 객체
config = Config()
```

### 2. 서비스 등록

#### Windows 서비스 등록
```python
# windows_service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
from pathlib import Path

class TwoVeryAutoService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TwoVeryAutoBackup"
    _svc_display_name_ = "Two Very Auto Backup Service"
    _svc_description_ = "Two Very Auto 백업 시스템 서비스"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        # 백업 시스템 실행
        from integrated_monitoring import run_monitoring_daemon
        run_monitoring_daemon()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(TwoVeryAutoService)
```

### 3. 자동 시작 스크립트

#### Windows 자동 시작 배치파일
```batch
@echo off
:: Two Very Auto Backup System 자동 시작 스크립트

echo Two Very Auto 백업 시스템을 시작합니다...

:: Python 경로 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 오류: Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    pause
    exit /b 1
)

:: 작업 디렉토리로 이동
cd /d "F:\two very auto 25.08.23"

:: 의존성 확인
echo 의존성을 확인하는 중...
python -c "import fastapi, uvicorn, aiohttp, schedule" >nul 2>&1
if %errorlevel% neq 0 (
    echo 의존성을 설치하는 중...
    pip install fastapi uvicorn aiohttp schedule tqdm
)

:: 대시보드 서버 시작
echo 대시보드 서버를 시작하는 중...
start "Two Very Auto Dashboard" python run_dashboard.py

:: 모니터링 시스템 시작
echo 모니터링 시스템을 시작하는 중...
start "Two Very Auto Monitoring" python integrated_monitoring.py --start

echo Two Very Auto 백업 시스템이 성공적으로 시작되었습니다!
echo 대시보드: http://localhost:8000
echo 모니터링이 백그라운드에서 실행 중입니다.

pause
```

## 📋 체크리스트

### 보안 체크리스트
- [ ] 환경 변수로 민감한 정보 관리
- [ ] API 접근 토큰 구현
- [ ] HTTPS 강제 사용 (프로덕션)
- [ ] CORS 정책 제한
- [ ] 로그에서 민감한 정보 마스킹
- [ ] 정기적인 보안 업데이트

### 성능 체크리스트
- [ ] 데이터베이스 연결 풀링
- [ ] 파일 스트리밍 처리
- [ ] 메모리 캐시 구현
- [ ] 백그라운드 작업 큐
- [ ] 압축 알고리즘 최적화
- [ ] 시스템 리소스 모니터링

### 배포 체크리스트
- [ ] 환경별 설정 분리
- [ ] Windows 서비스 등록
- [ ] 자동 시작 스크립트
- [ ] 로그 로테이션 설정
- [ ] 백업 보관 정책
- [ ] 장애 복구 계획

---

**Two Very Auto v3.0** - 보안과 성능을 갖춘 엔터프라이즈급 백업 시스템  
© 2025 Two Very Auto Team