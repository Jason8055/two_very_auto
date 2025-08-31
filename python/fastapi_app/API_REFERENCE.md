# Two Very Auto - API 참조 문서

## 🔗 기본 정보

**서버 주소**: `http://127.0.0.1:8080`  
**API 버전**: v2.0.0  
**문서화**: `http://127.0.0.1:8080/docs` (Swagger UI)

## 📊 주요 API 엔드포인트

### 🏠 방 통계 API (신규)

#### 1. 전체 방 통계 조회
```http
GET /api/rooms/statistics
```

**응답 예시**:
```json
{
  "success": true,
  "message": "총 18개 방의 통계 분석 완료",
  "rooms": [
    {
      "room_name": "바카라 B",
      "total_pairs": 318,
      "player_pairs": 125,
      "banker_pairs": 233,
      "both_pairs": 40,
      "last_activity": "2025-08-20T15:27:21.810000",
      "games_processed": 2,
      "sample_pairs": [...]
    }
  ]
}
```

#### 2. 방별 상세 페어 목록
```http
GET /api/rooms/{room_name}/pairs?limit=20
```

**매개변수**:
- `room_name`: 방 이름 (URL 인코딩 필요)
- `limit`: 결과 제한수 (1-100, 기본값: 20)
- `date_filter`: 날짜 필터 (YYYY-MM-DD)

**사용 예시**:
```bash
# 바카라 B 방의 최근 5개 페어
curl "http://127.0.0.1:8080/api/rooms/바카라%20B/pairs?limit=5"

# 스피드 바카라 J 방의 특정 날짜
curl "http://127.0.0.1:8080/api/rooms/스피드%20바카라%20J/pairs?date_filter=2025-08-20"
```

### 🎯 기존 페어 API

#### 1. 패킷 데이터 페어 조회
```http
GET /api/packet-data/pairs?limit=50
```

**매개변수**:
- `limit`: 결과 제한수 (기본값: 50)

#### 2. 개선된 페어 목록
```http
GET /api/pairs/list?limit=100&room_filter=바카라&pair_type=player
```

**매개변수**:
- `limit`: 결과 제한수 (1-1000)
- `room_filter`: 방명 필터
- `date_filter`: 날짜 필터 (YYYYMMDD)
- `pair_type`: 페어 타입 (player, banker, both)

#### 3. 테스트 페어 API
```http
GET /api/test-pairs?limit=5
```

**용도**: 시스템 테스트 및 개발용

### 📈 통계 API

#### 1. 통계 개요
```http
GET /api/stats/overview
```

#### 2. 최근 페어 데이터
```http
GET /api/pairs/recent?limit=100
```

#### 3. 테이블 목록
```http
GET /api/tables/list
```

### 🔧 시스템 API

#### 1. 서버 상태 확인
```http
GET /health
```

**응답**:
```json
{
  "success": true,
  "status": "healthy",
  "version": "2.0.0",
  "database_status": "healthy",
  "services": {
    "api": "running",
    "websocket": "running",
    "background_tasks": "running"
  }
}
```

#### 2. 실시간 WebSocket
```javascript
const ws = new WebSocket('ws://127.0.0.1:8080/ws/pair-notifications');
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('새로운 페어:', data);
};
```

## 🎨 대시보드 페이지

### 주요 대시보드
```http
GET /pair-dashboard    # 메인 페어 대시보드
GET /pair-display      # 기존 페어 표시
GET /                  # 메인 페이지
```

## 📝 API 사용 예시

### JavaScript 프론트엔드 연동
```javascript
// 방 통계 로드
async function loadRoomsStatistics() {
    const response = await fetch('/api/rooms/statistics');
    const data = await response.json();
    return data.rooms;
}

// 특정 방 페어 목록
async function loadRoomPairs(roomName, limit = 20) {
    const response = await fetch(`/api/rooms/${encodeURIComponent(roomName)}/pairs?limit=${limit}`);
    return await response.json();
}

// 자동 새로고침 구현
function setupAutoRefresh(intervalMs = 30000) {
    setInterval(async () => {
        const data = await loadRoomsStatistics();
        updateUI(data);
    }, intervalMs);
}
```

### Python 클라이언트 연동
```python
import requests
import json

# 서버 상태 확인
def check_server_health():
    response = requests.get('http://127.0.0.1:8080/health')
    return response.json()

# 방 통계 조회
def get_rooms_statistics():
    response = requests.get('http://127.0.0.1:8080/api/rooms/statistics')
    return response.json()['rooms']

# 특정 방 페어 조회
def get_room_pairs(room_name, limit=20):
    url = f'http://127.0.0.1:8080/api/rooms/{room_name}/pairs'
    params = {'limit': limit}
    response = requests.get(url, params=params)
    return response.json()['pairs']
```

## 🛡️ 보안 고려사항

### 현재 보안 상태
- ✅ CORS 설정 완료
- ✅ 입력 검증 구현
- ✅ 오류 정보 노출 방지
- ⚠️ 인증 시스템 미구현
- ⚠️ HTTPS 미적용

### 보안 개선 권장사항
1. **기본 인증** 시스템 추가
2. **API 키** 기반 접근 제어
3. **요청 제한** (Rate Limiting)
4. **HTTPS** 적용
5. **로그 보안** 강화

## 🔍 모니터링 포인트

### 성능 지표
- **API 응답시간**: < 100ms 목표
- **메모리 사용량**: < 500MB
- **파일 처리 속도**: 20개/5초
- **동시 연결 수**: 모니터링 필요

### 오류 추적
- **JSON 파싱 오류**: 완전 해결
- **타임아웃 오류**: 5초 제한으로 방지
- **메모리 누수**: 주기적 모니터링 필요

## 🔄 업데이트 로그

### v2.0.0 (2025.08.31)
- ✨ 18개 방 종합 통계 대시보드 추가
- 🐛 페어 카드 표시 오류 수정 (같은 무늬로 변경)
- ⚡ API 성능 최적화 (5초 타임아웃)
- 🎛️ 자동 새로고침 사용자 제어 추가

### v1.5.0 (2025.08.30)
- 🐛 JSON 파싱 오류 완전 해결
- 🚀 성능 최적화 (파일 처리 제한)
- 🔧 B: 드라이브 오류 방지 시스템

### v1.0.0 (2025.08.20)
- 🎯 초기 페어 감지 시스템 구축
- 📊 기본 통계 API 구현
- 🌐 웹 대시보드 구현

---

**API 문서 버전**: 2.0.0  
**마지막 업데이트**: 2025.08.31  
**다음 업데이트 예정**: 실시간 알림 시스템 추가