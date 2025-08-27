# Two Very Auto v3.2 - 시작 가이드

## 🚀 빠른 시작

### 방법 1: 배치 파일 실행 (권장)
```bash
# 가장 간단한 방법
two_very_auto.bat
```

### 방법 2: Python 직접 실행
```bash
# 가상환경 활성화 (있는 경우)
venv\Scripts\activate

# 런처 실행
python two_very_auto_launcher.py
```

### 방법 3: 실행파일 생성 후 실행
```bash
# 실행파일 빌드
python build_executable.py

# 생성된 실행파일 실행
two_very_auto.exe
```

---

## 🎯 자동 실행되는 서비스들

### 1. **웹 서버** (우선순위 1) ⭐
- **파일**: `web_server.py`
- **포트**: 5555
- **URL**: http://127.0.0.1:5555
- **기능**: 메인 대시보드, API 서비스
- **자동 브라우저 열기**: ✅

### 2. **현대적 대시보드 서버** (우선순위 2) 🎨
- **타입**: HTTP 정적 파일 서버
- **포트**: 8080
- **URL**: http://127.0.0.1:8080/modern_dashboard.html
- **기능**: 현대적 UI, PWA 지원
- **자동 브라우저 열기**: ❌ (메뉴에서 수동 열기)

### 3. **패킷 디코더** (우선순위 3) 📡
- **파일**: `packet_decoder.py`
- **기능**: 백그라운드 패킷 처리
- **상태**: 선택적 (파일이 있는 경우)

### 4. **알림 시스템** (우선순위 4) 🔔
- **파일**: `notification_system.py`
- **기능**: 백그라운드 알림 서비스
- **상태**: 선택적 (파일이 있는 경우)

---

## 📋 런처 기능

### 대화형 메뉴
```
📋 Two Very Auto 런처 메뉴
============================
1. 서비스 상태 보기
2. 접속 URL 보기
3. 브라우저에서 메인 대시보드 열기
4. 브라우저에서 현대적 대시보드 열기
5. 설정 보기
0. 종료
```

### 자동 기능
- ✅ **서비스 상태 모니터링**
- ✅ **자동 재시작** (실패한 서비스)
- ✅ **브라우저 자동 열기**
- ✅ **실시간 상태 확인**
- ✅ **설정 자동 저장**

---

## ⚙️ 설정 파일 (launcher_config.json)

```json
{
  "auto_open_browser": true,
  "startup_delay": 2,
  "check_interval": 5,
  "max_retries": 3,
  "enabled_services": [
    "web_server",
    "static_server"
  ],
  "window_title": "Two Very Auto v3.2 - 통합 런처",
  "last_updated": "2025-01-XX"
}
```

### 설정 항목 설명
- **auto_open_browser**: 시작시 자동으로 브라우저 열기
- **startup_delay**: 서비스 간 시작 지연 시간 (초)
- **check_interval**: 서비스 상태 확인 간격 (초)
- **max_retries**: 최대 재시도 횟수
- **enabled_services**: 활성화할 서비스 목록

---

## 🔧 문제 해결

### Python 관련
```bash
# Python 설치 확인
python --version

# 필수 모듈 설치
pip install flask flask-cors

# 가상환경 생성 (선택사항)
python -m venv venv
venv\Scripts\activate
```

### 포트 충돌
```bash
# 포트 사용 중 확인
netstat -ano | find "5555"
netstat -ano | find "8080"

# 프로세스 종료
taskkill /PID [PID번호] /F
```

### 파일 권한
- 관리자 권한으로 실행
- 바이러스 백신 예외 처리 추가

---

## 📊 시스템 요구사항

### 최소 요구사항
- **OS**: Windows 10/11
- **Python**: 3.7+
- **메모리**: 200MB
- **저장공간**: 50MB

### 권장 요구사항
- **OS**: Windows 11
- **Python**: 3.11+
- **메모리**: 500MB
- **저장공간**: 100MB

---

## 🌐 접속 URL 가이드

### 메인 대시보드 (기존)
- **URL**: http://127.0.0.1:5555
- **기능**: 
  - 실시간 모니터링
  - 기본 대시보드
  - API 엔드포인트

### 현대적 대시보드 (신규) ⭐
- **URL**: http://127.0.0.1:8080/modern_dashboard.html
- **기능**:
  - 현대적 UI/UX
  - 다크/라이트 모드
  - PWA 지원
  - 모바일 반응형

### API 엔드포인트
- **상태**: http://127.0.0.1:5555/api/status
- **데이터**: http://127.0.0.1:5555/api/data
- **차트**: http://127.0.0.1:5555/api/charts
- **패턴**: http://127.0.0.1:5555/api/patterns
- **알림**: http://127.0.0.1:5555/api/notifications

---

## 🚨 주의사항

1. **방화벽 설정**: Windows 방화벽에서 Python 허용 필요
2. **포트 충돌**: 5555, 8080 포트가 사용 중이면 충돌 발생
3. **가상환경**: 권장하지만 필수는 아님
4. **백그라운드 실행**: 콘솔 창을 닫으면 모든 서비스 종료

---

## 📞 지원

### 로그 파일 확인
- **파일**: `two_very_auto.log`
- **위치**: 런처와 같은 디렉토리
- **내용**: 모든 시스템 이벤트 기록

### 일반적인 오류 해결
1. **"ModuleNotFoundError"**: `pip install flask flask-cors`
2. **"Port already in use"**: 포트 충돌, 다른 프로그램 종료
3. **"Permission denied"**: 관리자 권한으로 실행
4. **브라우저 열리지 않음**: 수동으로 URL 접속

---

**🎰 Happy Monitoring! 🎯**

시작 명령어:
```bash
two_very_auto.bat
```