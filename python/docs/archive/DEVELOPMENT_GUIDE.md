# Development Guide

**시스템**: Two Very Auto Baccarat Monitor v3.0  
**개발 환경**: Python 3.13, Flask 3.1  
**최종 업데이트**: 2025-08-23

---

## 🏗️ 시스템 아키텍처

### 전체 구조

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Packet Data   │───▶│  Packet Decoder  │───▶│  Pair Tracker   │
│   (Text Files)  │    │   (Parsing)      │    │   (Analysis)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Web Browser    │◀───│   Web Server     │◀───│  JSON Storage   │
│  (Dashboard)    │    │   (Flask)        │    │   (Data)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 데이터 흐름

1. **Input**: 패킷 텍스트 파일
2. **Processing**: 패킷 디코더가 게임 데이터 추출
3. **Analysis**: 페어 추적기가 통계 분석
4. **Storage**: JSON 파일로 데이터 저장
5. **Output**: 웹 서버가 대시보드 제공

---

## 📦 모듈 구조

### 1. packet_decoder.py

**목적**: 패킷 데이터를 파싱하여 게임 정보 추출

**주요 클래스**:
- `BaccaratPacketDecoder`: 메인 디코더
- `DemoDataGenerator`: 테스트 데이터 생성

**핵심 메소드**:
```python
def parse_packet_file(file_path: str) -> List[Dict[str, Any]]
def _parse_packet_content(content: str) -> List[Dict[str, Any]]
def _calculate_pair_info(player_cards: List[str], banker_cards: List[str]) -> Dict[str, Any]
```

**입력 형식**:
```
table_001_12345_20250823153045_PLAYER_AH KS QD JC
```

**출력 형식**:
```python
{
    'table_name': 'table_001',
    'game_id': 12345,
    'game_time': '2025-08-23T15:30:45',
    'result': 'PLAYER',
    'player_cards': ['AH', 'KS'],
    'banker_cards': ['QD', 'JC'],
    'pair_info': {
        'has_any_pair': True,
        'pair_type': 'PLAYER_PAIR',
        'pair_cards': ['AH', 'AS']
    }
}
```

### 2. pair_tracker.py

**목적**: 페어 발생 추적 및 통계 관리

**주요 클래스**:
- `PairTracker`: 메인 추적기

**핵심 메소드**:
```python
def track_game(game_data: Dict[str, Any]) -> Dict[str, Any]
def get_table_summary(table_name: str) -> Optional[Dict[str, Any]]
def get_all_tables_summary() -> Dict[str, Any]
def get_recent_pairs(table_name: str = None, limit: int = 10) -> List[Dict[str, Any]]
```

**저장 구조**:
```python
{
    'tables': {
        'table_001': {
            'total_games': 45,
            'pair_count': 7,
            'player_pairs': 4,
            'banker_pairs': 3,
            'recent_pairs': [...],
            'statistics': {
                'pair_rate': 0.1556,
                'avg_games_between_pairs': 6.43
            }
        }
    },
    'global_stats': {
        'total_games': 150,
        'total_pairs': 23
    }
}
```

### 3. web_server.py

**목적**: 웹 서버 및 API 제공

**주요 구성**:
- Flask 앱 설정
- HTML 템플릿 (인라인)
- API 엔드포인트
- 에러 처리

**라우트 구조**:
```python
@app.route('/')                           # 메인 대시보드
@app.route('/api/status')                 # 서버 상태
@app.route('/api/data')                   # 전체 데이터
@app.route('/api/table/<table_name>')     # 테이블별 데이터
@app.route('/api/demo')                   # 데모 데이터
```

---

## 🛠️ 개발 환경 설정

### 1. 필수 도구

```bash
# Python 3.13 설치 확인
python --version

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 패키지 설치
pip install flask flask-cors requests
```

### 2. 개발용 설정

```python
# web_server.py 개발 모드
if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5555,
        debug=True,  # 개발 모드
        threaded=True
    )
```

### 3. 로깅 설정

```python
import logging

# 개발용 상세 로깅
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```

---

## 🔧 기능 확장 가이드

### 1. 새로운 분석 기능 추가

**단계 1**: 분석 모듈 생성
```python
# analysis_module.py
class PatternAnalyzer:
    def __init__(self):
        self.patterns = {}
    
    def analyze_pattern(self, games: List[Dict]) -> Dict:
        # 패턴 분석 로직
        return {'pattern_type': 'streak', 'confidence': 0.8}
```

**단계 2**: 페어 추적기에 통합
```python
# pair_tracker.py에 추가
from analysis_module import PatternAnalyzer

class PairTracker:
    def __init__(self):
        # 기존 코드...
        self.pattern_analyzer = PatternAnalyzer()
    
    def track_game(self, game_data):
        # 기존 추적 로직...
        
        # 새로운 분석 추가
        pattern = self.pattern_analyzer.analyze_pattern(
            list(self.recent_games[table_name])
        )
        tracking_result['pattern_analysis'] = pattern
        
        return tracking_result
```

**단계 3**: API 엔드포인트 추가
```python
# web_server.py에 추가
@app.route('/api/patterns/<table_name>')
def api_patterns(table_name):
    try:
        # 패턴 분석 데이터 조회
        pattern_data = tracker.get_pattern_analysis(table_name)
        return jsonify({
            'success': True,
            'patterns': pattern_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 2. 새로운 데이터 소스 추가

**단계 1**: 새 디코더 생성
```python
# csv_decoder.py
class CSVDataDecoder:
    def parse_csv_file(self, file_path: str) -> List[Dict]:
        import csv
        games = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                game = self._convert_csv_row(row)
                games.append(game)
        
        return games
    
    def _convert_csv_row(self, row: Dict) -> Dict:
        # CSV 행을 게임 데이터로 변환
        return {
            'table_name': row['table'],
            'game_id': int(row['id']),
            # ... 기타 필드
        }
```

**단계 2**: 웹 서버에 통합
```python
# web_server.py에 추가
from csv_decoder import CSVDataDecoder

csv_decoder = CSVDataDecoder()

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    # 파일 업로드 처리
    file = request.files['csv_file']
    
    # CSV 파싱
    games = csv_decoder.parse_csv_file(file.filename)
    
    # 페어 추적기에 추가
    for game in games:
        tracker.track_game(game)
    
    return jsonify({'message': f'Processed {len(games)} games'})
```

### 3. 실시간 알림 기능

**단계 1**: 알림 클래스 생성
```python
# notification.py
class NotificationManager:
    def __init__(self):
        self.subscribers = []
        self.alert_threshold = 0.7  # 70% 이상일 때 알림
    
    def subscribe(self, callback):
        self.subscribers.append(callback)
    
    def notify_pair_alert(self, table_name, pair_info):
        message = f"PAIR ALERT: {pair_info['pair_type']} at {table_name}"
        
        for callback in self.subscribers:
            try:
                callback(message, pair_info)
            except Exception as e:
                print(f"Notification error: {e}")
```

**단계 2**: 페어 추적기에 연동
```python
# pair_tracker.py 수정
from notification import NotificationManager

class PairTracker:
    def __init__(self):
        # 기존 코드...
        self.notification_manager = NotificationManager()
        
        # 알림 콜백 등록
        self.notification_manager.subscribe(self._log_alert)
        self.notification_manager.subscribe(self._save_alert)
    
    def track_game(self, game_data):
        # 기존 로직...
        
        if pair_info.get('has_any_pair'):
            # 알림 발송
            self.notification_manager.notify_pair_alert(
                table_name, pair_info
            )
        
        return tracking_result
    
    def _log_alert(self, message, pair_info):
        logger.info(f"ALERT: {message}")
    
    def _save_alert(self, message, pair_info):
        # 알림 이력 저장
        pass
```

---

## 🧪 테스트 가이드

### 1. 단위 테스트

**테스트 파일 구조**:
```
python/
├── tests/
│   ├── __init__.py
│   ├── test_packet_decoder.py
│   ├── test_pair_tracker.py
│   └── test_web_server.py
└── pytest.ini
```

**테스트 예시**:
```python
# tests/test_packet_decoder.py
import unittest
from packet_decoder import BaccaratPacketDecoder

class TestPacketDecoder(unittest.TestCase):
    def setUp(self):
        self.decoder = BaccaratPacketDecoder()
    
    def test_parse_valid_packet(self):
        # 테스트 데이터
        packet_line = "table_001_12345_20250823153045_PLAYER_AH KS QD JC"
        
        # 파싱 실행
        games = self.decoder._parse_packet_content(packet_line)
        
        # 검증
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]['table_name'], 'table_001')
        self.assertEqual(games[0]['result'], 'PLAYER')
        self.assertEqual(games[0]['player_cards'], ['AH', 'KS'])
    
    def test_pair_detection(self):
        # 페어가 있는 게임 테스트
        player_cards = ['AH', 'AS']
        banker_cards = ['KD', 'QC']
        
        pair_info = self.decoder._calculate_pair_info(player_cards, banker_cards)
        
        self.assertTrue(pair_info['has_any_pair'])
        self.assertEqual(pair_info['pair_type'], 'PLAYER_PAIR')

if __name__ == '__main__':
    unittest.main()
```

**테스트 실행**:
```bash
# 단일 테스트 파일
python -m pytest tests/test_packet_decoder.py -v

# 전체 테스트
python -m pytest tests/ -v

# 커버리지 포함
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=html
```

### 2. API 테스트

```python
# tests/test_api.py
import unittest
import json
from web_server import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_status_endpoint(self):
        response = self.app.get('/api/status')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'running')
        self.assertEqual(data['port'], 5555)
    
    def test_demo_endpoint(self):
        response = self.app.get('/api/demo')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('Added', data['message'])
```

### 3. 통합 테스트

```python
# tests/test_integration.py
import unittest
import tempfile
import os
from packet_decoder import BaccaratPacketDecoder, DemoDataGenerator
from pair_tracker import PairTracker

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # 임시 데이터 파일
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        
        self.decoder = BaccaratPacketDecoder()
        self.tracker = PairTracker(self.temp_file.name)
        self.demo_gen = DemoDataGenerator()
    
    def tearDown(self):
        # 임시 파일 정리
        os.unlink(self.temp_file.name)
    
    def test_full_pipeline(self):
        # 1. 데모 데이터 생성
        demo_data = self.demo_gen.generate_demo_packet(10)
        
        # 2. 패킷 파싱
        games = self.decoder._parse_packet_content(demo_data)
        
        # 3. 페어 추적
        pair_count = 0
        for game in games:
            result = self.tracker.track_game(game)
            if result.get('has_pair'):
                pair_count += 1
        
        # 4. 결과 검증
        summary = self.tracker.get_all_tables_summary()
        
        self.assertEqual(summary['global_stats']['total_games'], 10)
        self.assertEqual(summary['global_stats']['total_pairs'], pair_count)
```

---

## 📊 성능 최적화

### 1. 메모리 최적화

**메모리 사용량 모니터링**:
```python
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

# 메모리 사용량 로깅
logger.info(f"Memory usage: {get_memory_usage():.1f} MB")
```

**최적화 기법**:
```python
# 1. deque 사용으로 메모리 제한
from collections import deque

self.recent_games = defaultdict(lambda: deque(maxlen=100))

# 2. 주기적 데이터 정리
def cleanup_old_data(self):
    cutoff_time = datetime.now() - timedelta(hours=24)
    # 24시간 이전 데이터 정리
    
# 3. 제너레이터 사용
def get_games_generator(self, file_path):
    with open(file_path, 'r') as f:
        for line in f:
            yield self.parse_line(line)
```

### 2. 응답 속도 최적화

**캐싱 구현**:
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedTracker:
    def __init__(self):
        self.cache_timeout = 10  # 10초 캐시
        self.last_cache_time = None
        self.cached_summary = None
    
    def get_summary_cached(self):
        now = datetime.now()
        
        if (self.cached_summary is None or 
            self.last_cache_time is None or
            now - self.last_cache_time > timedelta(seconds=self.cache_timeout)):
            
            self.cached_summary = self.get_all_tables_summary()
            self.last_cache_time = now
        
        return self.cached_summary
```

**비동기 처리**:
```python
# 향후 확장: asyncio 사용
import asyncio
from flask import Flask
from quart import Quart  # Flask의 비동기 버전

app = Quart(__name__)

@app.route('/api/async-data')
async def async_data():
    # 비동기 데이터 처리
    result = await process_data_async()
    return jsonify(result)
```

---

## 🔒 보안 가이드

### 1. 입력 검증

```python
def validate_table_name(table_name: str) -> bool:
    """테이블명 유효성 검증"""
    import re
    
    # 영숫자, 언더스코어만 허용
    pattern = r'^[a-zA-Z0-9_]{1,50}$'
    return bool(re.match(pattern, table_name))

@app.route('/api/table/<table_name>')
def api_table(table_name):
    if not validate_table_name(table_name):
        return jsonify({'error': 'Invalid table name'}), 400
    
    # 정상 처리
    table_info = tracker.get_table_summary(table_name)
    return jsonify({'table_info': table_info})
```

### 2. 에러 처리

```python
from functools import wraps

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({'error': 'Invalid input'}), 400
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return jsonify({'error': 'Resource not found'}), 404
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return decorated_function

@app.route('/api/protected-endpoint')
@handle_errors
def protected_endpoint():
    # 보호된 엔드포인트 로직
    pass
```

### 3. 로깅 및 모니터링

```python
import logging
from logging.handlers import RotatingFileHandler

# 로그 설정
if not app.debug:
    file_handler = RotatingFileHandler(
        'logs/web_server.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Web server startup')

# 요청 로깅
@app.before_request
def log_request_info():
    app.logger.debug('Request: %s %s', request.method, request.url)

@app.after_request
def log_response_info(response):
    app.logger.debug('Response: %s', response.status_code)
    return response
```

---

## 📈 배포 가이드

### 1. 프로덕션 설정

```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # 프로덕션 전용 설정

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

### 2. 프로세스 관리

**윈도우 서비스로 등록**:
```python
# service_wrapper.py
import win32serviceutil
import win32service
import win32event
import socket

class BaccaratMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BaccaratMonitor"
    _svc_display_name_ = "Baccarat Monitor Service"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
    
    def SvcDoRun(self):
        import servicemanager
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # 웹 서버 실행
        from web_server import main
        main()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(BaccaratMonitorService)
```

---

**🛠️ Development Guide Complete!**

**시작**: `python web_server.py` → 개발 시작!

---

*Last Updated: 2025-08-23 21:15 by Claude Code Assistant*