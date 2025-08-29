# Two Very Auto - 서버 연결 문제 해결 보고서

## 🔍 문제 상황
- 사용자가 반복적으로 포트 8080에서 "연결할 수 없음" 오류 경험
- FastAPI 서버는 정상적으로 시작되지만 브라우저에서 접근 불가

## ✅ 완료된 작업

### 1. 서버 시작 스크립트 개선
- `start_server_simple.py` 생성 - 자동 포트 찾기 기능
- `start_server.bat` 업데이트 - 포괄적인 시작 스크립트
- 유니코드 인코딩 문제 해결

### 2. 진단 및 테스트 도구 생성
- `test_server.py` - 간단한 FastAPI 테스트 서버
- `simple_test.py` - 기본 HTTP 서버로 연결 테스트
- 포트 사용 가능성 자동 검증

### 3. 서버 상태 확인
- 서버가 정상적으로 시작됨 확인
- 모든 서비스 (데이터베이스, 캐시, WebSocket 등) 정상 초기화
- 포트 8080에서 uvicorn 실행 중 확인

## ⚠️ 식별된 문제점

### 1. 네트워크 연결 문제
**증상**: 서버는 시작되지만 127.0.0.1:8080 연결 거부
```
ConnectionRefusedError: [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다
```

**가능한 원인**:
1. **방화벽 차단**: Windows Defender 또는 안티바이러스 소프트웨어
2. **포트 바인딩 문제**: 다른 프로세스의 포트 점유
3. **localhost 해석 문제**: 127.0.0.1 vs localhost 차이
4. **관리자 권한 필요**: 일부 포트는 관리자 권한 요구

## 🛠️ 해결 방법

### 방법 1: 방화벽 확인 및 해제
```cmd
# Windows 방화벽에서 Python 허용
netsh advfirewall firewall add rule name="Python FastAPI" dir=in action=allow program=python.exe
```

### 방법 2: 다른 포트 사용
서버가 이미 여러 포트를 자동으로 시도하도록 설정됨:
- 8080 (기본) → 8000 → 3000 → 9999 → 7777 → 5000

### 방법 3: 관리자 권한으로 실행
1. 명령 프롬프트를 "관리자 권한으로 실행"
2. `start_server.bat` 실행

### 방법 4: localhost 대신 127.0.0.1 사용
브라우저에서 직접 접속:
- `http://127.0.0.1:8080`
- `http://127.0.0.1:8000` (포트가 변경된 경우)

## 🚀 권장 실행 순서

### 1단계: 간단한 연결 테스트
```cmd
cd "F:\two very auto 25.08.23\python\fastapi_app"
python simple_test.py
```

### 2단계: FastAPI 테스트 서버
```cmd
python test_server.py
```

### 3단계: 전체 서버 시작
```cmd
start_server.bat
```
또는
```cmd
python start_server_simple.py
```

## 📊 서버 기능 확인

서버가 정상 시작되면 다음 URL에서 확인 가능:
- 메인 대시보드: `http://127.0.0.1:[PORT]/`
- 페어 대시보드: `http://127.0.0.1:[PORT]/pair-dashboard`
- 상태 확인: `http://127.0.0.1:[PORT]/health`
- API 문서: `http://127.0.0.1:[PORT]/docs`

## 🎯 페어 감지 시스템 상태

### 구현 완료된 기능
1. **JSON 패킷 데이터 파싱** - `enhanced_pair_detector.py`
2. **실시간 페어 감지** - playerPair, bankerPair 추출
3. **웹 대시보드** - `pair_dashboard.html`
4. **API 엔드포인트** - `/api/packet-data/pairs`
5. **WebSocket 실시간 알림**

### 테스트 방법
```cmd
cd "F:\two very auto 25.08.23\python\fastapi_app"
python test_pair_detection.py
```

## 🔄 다음 단계

1. **연결 문제 해결** 후 서버 접근
2. 페어 대시보드에서 실시간 데이터 확인
3. 패킷 폴더의 JSON 데이터 분석 결과 검토
4. 필요시 추가 최적화 및 기능 개선

## 📞 추가 지원

서버 연결 문제가 지속될 경우:
1. 방화벽 설정 확인
2. 안티바이러스 소프트웨어 예외 등록
3. 관리자 권한으로 실행 시도
4. 다른 포트(8000, 3000 등) 사용 테스트