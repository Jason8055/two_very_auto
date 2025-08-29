# Two Very Auto - JSON 파싱 오류 해결 문서

## 현재 상황 (2025-08-29)

### 문제 현상
- 브라우저에서 "서버 연결 실패: Unexpected token 'I', Internal S... is not valid JSON" 오류 지속 발생
- 새로고침 후 화면이 정상적으로 로드되지 않음
- 서버는 정상적으로 실행 중 (PID: 38772, Port: 8080)

### 이미 구현된 해결책들

#### 1. 전역 예외 처리기 구현 ✅
- 파일: `global_exception_handler.py`
- 모든 서버 오류를 JSON 형식으로 응답하도록 보장
- HTTPException, RequestValidationError, 일반 Exception 모두 처리
- `main.py`에 등록 완료

#### 2. Enhanced Pair Detector 최적화 ✅
- 파일: `enhanced_pair_detector.py`
- JSON 파싱 실패로 인한 로그 스팸 제거
- 균형 괄호 파싱 방식으로 개선
- 대량의 WARNING 로그 문제 해결

#### 3. 서버 성능 최적화 ✅
- 응답 시간 16초 → 1초 미만으로 개선
- Worker 설정 최적화
- 프로세스 정리 및 재시작 스크립트 작성

#### 4. 테스트 엔드포인트 생성 ✅
- 파일: `routers/test_error.py`
- `/api/test-500-error`, `/api/test-404-error` 테스트용 엔드포인트

## 🔍 다음 단계 디버깅 계획

### 1. 개별 API 엔드포인트 테스트
브라우저 개발자 도구(F12)에서 실제로 어떤 요청이 실패하는지 확인:

```javascript
// 브라우저 콘솔에서 실행
const testEndpoints = [
    '/health',
    '/api/pair-notifications/service/health',
    '/api/stats/basic',
    '/api/packet-data/summary',
    '/api/improved-pairs/summary'
];

for (const endpoint of testEndpoints) {
    try {
        const response = await fetch(endpoint);
        const contentType = response.headers.get('content-type');
        console.log(`${endpoint}: ${response.status} - ${contentType}`);
        
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            console.log(`${endpoint} JSON:`, data);
        } else {
            const text = await response.text();
            console.log(`${endpoint} Text:`, text.substring(0, 200));
        }
    } catch (error) {
        console.error(`${endpoint} ERROR:`, error);
    }
}
```

### 2. WebSocket 연결 문제 확인
WebSocket 연결이 문제를 일으킬 수 있음:

```javascript
// WebSocket 연결 테스트
const ws = new WebSocket('ws://127.0.0.1:8080/ws/stats');
ws.onopen = () => console.log('WebSocket 연결됨');
ws.onerror = (error) => console.error('WebSocket 오류:', error);
ws.onmessage = (msg) => console.log('WebSocket 메시지:', msg.data);
```

### 3. 특정 라우터별 문제 확인
각 라우터에서 오류가 발생하는지 확인:

```bash
# 각각 개별적으로 테스트
curl -v http://127.0.0.1:8080/health
curl -v http://127.0.0.1:8080/api/stats/basic
curl -v http://127.0.0.1:8080/api/pair-notifications/service/health
curl -v http://127.0.0.1:8080/api/packet-data/summary
```

### 4. 클라이언트 측 JavaScript 개선 필요
현재 `templates/dashboard.html`에서:

```javascript
// 현재 문제가 있는 코드 패턴
const response = await fetch('/api/endpoint');
const data = await response.json(); // ← 여기서 오류 발생 가능

// 개선된 안전한 패턴으로 교체 필요
const response = await fetch('/api/endpoint');
const contentType = response.headers.get('content-type');
if (contentType && contentType.includes('application/json')) {
    const data = await response.json();
} else {
    const errorText = await response.text();
    console.error('Non-JSON response:', errorText);
}
```

## 📋 내일 작업 계획

### 우선순위 1: 실제 실패 엔드포인트 식별
1. 브라우저 개발자 도구에서 Network 탭 확인
2. 어떤 요청이 실제로 JSON이 아닌 응답을 반환하는지 식별
3. 해당 엔드포인트의 라우터 코드 검사

### 우선순위 2: 클라이언트 측 JavaScript 강화
1. `templates/dashboard.html` 수정
2. 모든 `fetch().then(response.json())` 패턴을 안전한 방식으로 교체
3. 전역 오류 처리 함수 구현

### 우선순위 3: WebSocket 연결 문제 해결
1. WebSocket 연결 오류 처리 개선
2. WebSocket 메시지 형식 검증
3. 연결 실패 시 적절한 폴백 제공

### 우선순위 4: 추가 디버깅 도구
1. 서버 로그에 요청/응답 상세 로깅 추가
2. 오류 발생 시점의 스택 트레이스 수집
3. 실시간 오류 모니터링 구현

## 🔧 사용 가능한 스크립트들

### 서버 재시작
```bash
python restart_optimized_server.py
```

### 오류 테스트
```bash
python test_error_simulation.py
```

### 대시보드 JSON 처리 개선 (아직 실행 안됨)
```bash
python fix_dashboard_json_handling.py
```

## 📊 현재 서버 상태
- **PID**: 38772
- **Port**: 8080  
- **URL**: http://127.0.0.1:8080
- **상태**: 실행 중
- **전역 예외 처리기**: 활성화됨
- **로그 레벨**: INFO

## 🎯 핵심 문제 추정
1. **가능성 1**: 특정 API 엔드포인트에서 예외가 발생하여 HTML 오류 페이지 반환
2. **가능성 2**: WebSocket 연결 중 JSON이 아닌 데이터 전송
3. **가능성 3**: 클라이언트 측 JavaScript에서 응답 타입 미확인
4. **가능성 4**: 미들웨어 또는 백그라운드 태스크에서 발생하는 예외

내일 작업 시 우선적으로 브라우저 개발자 도구에서 실제 실패하는 요청을 식별하는 것이 가장 중요합니다.