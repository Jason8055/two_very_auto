# 디버깅 체크리스트 - JSON 파싱 오류 해결

## 🕒 작업 재개 시 첫 단계

### 1. 현재 서버 상태 확인
```bash
# 서버가 여전히 실행 중인지 확인
netstat -ano | findstr :8080
# 또는
tasklist /FI "PID eq 38772"

# 서버 재시작 필요 시
python restart_optimized_server.py
```

### 2. 브라우저에서 실제 오류 확인
1. **브라우저 열기**: http://127.0.0.1:8080
2. **개발자 도구 열기**: F12 → Network 탭
3. **페이지 새로고침**: Ctrl+F5 (하드 리프레시)
4. **빨간색 오류 요청 찾기**: 실제로 실패하는 API 호출 식별

### 3. 콘솔에서 개별 테스트
```javascript
// 브라우저 콘솔(F12 → Console)에서 실행
fetch('/health')
  .then(response => {
    console.log('Status:', response.status);
    console.log('Content-Type:', response.headers.get('content-type'));
    return response.text();
  })
  .then(text => console.log('Response:', text))
  .catch(error => console.error('Error:', error));
```

## 🔍 단계별 디버깅 프로세스

### Phase 1: 문제 엔드포인트 식별 (5-10분)
- [ ] `/health` 엔드포인트 테스트
- [ ] `/api/stats/basic` 테스트  
- [ ] `/api/pair-notifications/service/health` 테스트
- [ ] `/api/packet-data/summary` 테스트
- [ ] WebSocket 연결 `/ws/stats` 테스트

**실행할 명령어들:**
```bash
curl -v http://127.0.0.1:8080/health
curl -v http://127.0.0.1:8080/api/stats/basic
curl -v http://127.0.0.1:8080/api/pair-notifications/service/health
```

### Phase 2: 클라이언트 수정 (10-15분)
실패하는 엔드포인트 식별 후:

1. **dashboard.html 수정**:
```javascript
// 기존 위험한 패턴
fetch(url).then(response => response.json())

// 안전한 패턴으로 교체
fetch(url).then(async response => {
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
        throw new Error(`Non-JSON response: ${await response.text()}`);
    }
    return response.json();
})
```

### Phase 3: 서버 로깅 강화 (5분)
문제가 특정 엔드포인트에 있다면:

```python
# 해당 라우터에 상세 로깅 추가
import logging
logger = logging.getLogger(__name__)

@router.get("/problem-endpoint")
async def problem_endpoint():
    try:
        logger.info("Problem endpoint called")
        # 기존 로직
        result = {"success": True}
        logger.info(f"Returning: {result}")
        return result
    except Exception as e:
        logger.error(f"Exception in problem endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
```

## 📋 빠른 해결책들

### 해결책 1: JavaScript 파일 교체
```bash
# 이미 준비된 개선된 JavaScript 적용
python fix_dashboard_json_handling.py
```

### 해결책 2: 강제 JSON 응답 미들웨어 추가
`main.py`에 추가:

```python
@app.middleware("http")
async def force_json_response(request: Request, call_next):
    try:
        response = await call_next(request)
        # API 요청이고 JSON이 아닌 응답인 경우 강제 변환
        if request.url.path.startswith("/api") and response.headers.get("content-type", "").startswith("text/html"):
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "서버 오류 - 예상치 못한 HTML 응답"}
            )
        return response
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"미들웨어 오류: {str(e)}"}
        )
```

### 해결책 3: 특정 엔드포인트 우회
문제 엔드포인트가 식별되면 임시로 비활성화:

```python
# 문제가 되는 라우터에서
@router.get("/problem-endpoint")
async def problem_endpoint():
    return {"success": False, "message": "임시 비활성화됨", "status": "maintenance"}
```

## 🎯 예상 원인별 해결 방법

### 원인 1: WebSocket 문제
```javascript
// dashboard.html에서 WebSocket 연결 부분 수정
const ws = new WebSocket('ws://127.0.0.1:8080/ws/stats');
ws.onmessage = function(event) {
    try {
        const data = JSON.parse(event.data);
        // 처리 로직
    } catch (e) {
        console.error('WebSocket JSON 파싱 오류:', event.data);
    }
};
```

### 원인 2: 특정 라우터 예외
```python
# 모든 라우터에 try-catch 추가
@router.get("/endpoint")
async def endpoint():
    try:
        # 기존 로직
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Endpoint error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
```

### 원인 3: 백그라운드 태스크 간섭
```python
# main.py의 background_monitoring() 함수에 예외 처리 강화
async def background_monitoring():
    while True:
        try:
            # 기존 로직
            pass
        except Exception as e:
            logger.error(f"Background task error: {e}")
            # 백그라운드 태스크 오류가 HTTP 응답에 영향주지 않도록
            await asyncio.sleep(60)
```

## 🚨 긴급 임시 해결책

모든 방법이 실패하면:

```python
# main.py에 최후의 수단 미들웨어 추가
@app.middleware("http") 
async def emergency_json_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except:
        # 모든 예외를 JSON으로 반환
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "서버 오류", "message": "임시 오류 처리"}
        )
```

## 📞 작업 완료 후 확인사항

- [ ] 브라우저에서 새로고침 시 정상 로드됨
- [ ] 개발자 도구 Console에 "Unexpected token" 오류 없음  
- [ ] 모든 API 엔드포인트가 JSON 응답 반환
- [ ] WebSocket 연결 정상 작동
- [ ] 백그라운드 모니터링 정상 작동

**성공 기준**: 브라우저에서 http://127.0.0.1:8080 접속 시 오류 없이 대시보드 표시