# 🎯 실시간 페어 정보 확인 방법

## 📊 개요

Two Very Auto 시스템에는 **실시간 바카라 페어 감지 및 알림 시스템**이 완전히 구축되어 있습니다!

## 🚀 실시간 페어 서버 시작 방법

### 🎯 권장 방법 - 향상된 시작 스크립트 (NEW!)
```bash
cd "F:\two very auto 25.08.23\python\fastapi_app"
python start_pair_system.py
```
**특징**:
- ✅ 포트 자동 감지 및 선택 (8080 → 8000 → 3000 → ... → 자동할당)
- ✅ 기존 프로세스 자동 정리
- ✅ 브라우저 자동 열기
- ✅ 연결 문제 완전 해결
- ✅ 상세한 시작 가이드 제공

### 🪟 Windows 원클릭 실행
```
"페어정보시스템실행.bat" 더블클릭
```

### 🔧 기본 방법 (기존)
```bash
cd "F:\two very auto 25.08.23\python\fastapi_app"
python main.py
```

**실행 결과**:
```
================================================================================
🎯 Two Very Auto FastAPI Server - 페어 정보 시스템
================================================================================
✨ AsyncIO 네이티브 지원
📡 실시간 WebSocket 통신
📚 자동 API 문서화
🛡️ 타입 안전성 보장
⚡ 고성능 비동기 처리
🎰 실시간 페어 감지 및 알림
📊 패턴 분석 및 통계
================================================================================
🌐 메인 URL: http://127.0.0.1:8080
🎯 페어 대시보드: http://127.0.0.1:8080/pair-display  
📖 API 문서: http://127.0.0.1:8080/docs
💚 상태 확인: http://127.0.0.1:8080/health
================================================================================
🎮 실시간 페어 정보 확인 방법:
   1. 브라우저에서 http://127.0.0.1:8080 접속
   2. 페어 전용 화면: http://127.0.0.1:8080/pair-display
   3. 실시간 WebSocket 알림 자동 수신
================================================================================
```

### 2️⃣ 페어 대시보드 접속

#### 🎯 메인 페어 대시보드
- **URL**: http://127.0.0.1:8080 (또는 자동 할당된 포트)
- **기능**: 실시간 페어 발생 모니터링, 통계, 상세 분석

#### 📊 전용 페어 디스플레이 
- **URL**: http://127.0.0.1:8080/pair-display
- **기능**: 시각적 페어 데이터 표시, 필터링, 상세 정보
- **특징**: 실시간 WebSocket 연결, 브라우저 알림, 필터링

#### 🔧 포트 변경 시 자동 안내
서버 시작 시 포트 충돌이 있으면 다음 순서로 자동 선택:
1. 8080 (기본) → 2. 8000 → 3. 3000 → 4. 9999 → 5. 7777 → ... → 자동 할당

## 📡 실시간 페어 기능

### 🔔 페어 감지 기능
- ✅ **플레이어 페어**: 플레이어 카드 2장이 같은 숫자
- ✅ **뱅커 페어**: 뱅커 카드 2장이 같은 숫자  
- ✅ **양쪽 페어**: 플레이어와 뱅커 모두 페어
- ✅ **패턴 분석**: 연속 페어, 교대 패턴, 희귀 패턴

### 🌐 실시간 알림 방식
- ✅ **WebSocket 실시간 브로드캐스트**
- ✅ **브라우저 푸시 알림**
- ✅ **페이지 제목 깜빡임 효과**
- ✅ **다중 채널 지원** (Email, Slack 확장 가능)

### 📊 상세 정보 제공
- ✅ **카드 정보**: 플레이어/뱅커 카드 시각 표시
- ✅ **게임 결과**: 점수, 승부, 내추럴 여부
- ✅ **AI 예측**: 딥러닝 기반 페어 예측
- ✅ **통계 분석**: 테이블별 페어 발생 패턴

## 🔧 API 엔드포인트

### 📈 페어 데이터 조회
```http
GET /api/pair-notifications/history?limit=50&table_name=바카라A
GET /api/pair-notifications/stats
GET /api/pair-notifications/tables/stats
```

### 📊 실시간 통계
```http
GET /api/stats/overview
GET /api/tables/list
GET /api/pairs/recent?limit=100
```

### ⚙️ 서비스 관리  
```http
GET /api/pair-notifications/service/health
POST /api/pair-notifications/service/start
POST /api/pair-notifications/service/stop
```

### 🧪 테스트 기능
```http
POST /api/pair-notifications/test?table_name=테스트테이블&pair_type=player_pair
```

## 🔌 WebSocket 실시간 연결

### JavaScript 연결 코드
```javascript
// WebSocket 연결
const ws = new WebSocket('ws://127.0.0.1:8080/ws/realtime?client_id=client123');

// 페어 알림 구독
ws.send(JSON.stringify({
    command: 'subscribe',
    data: { type: 'pairs' }
}));

// 실시간 알림 수신
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'pair_notification') {
        const pairEvent = data.data.pair_event;
        console.log(`🎰 페어 감지: ${pairEvent.table_name} - ${pairEvent.pair_type}`);
        
        // UI 업데이트
        updatePairNotification(pairEvent);
    }
};
```

## 📱 실시간 알림 메시지 구조

```json
{
    "type": "pair_notification",
    "data": {
        "type": "pair_alert",
        "pair_event": {
            "id": "바카라A_123_143052",
            "table_name": "바카라 A",
            "game_number": 123,
            "pair_type": "player_pair",
            "timestamp": "2024-01-01T14:30:52",
            "player_cards": ["A♠", "A♥"],
            "banker_cards": ["K♦", "Q♣"],
            "pattern": "single_pair",
            "confidence": 1.0
        },
        "display": {
            "emoji": "🎰",
            "title": "🎰 Player Pair",
            "subtitle": "바카라 A 게임 #123",
            "confidence_text": "신뢰도: 100.0%",
            "color": "#32cd32"
        },
        "analytics": {
            "betting_recommendation": "플레이어 페어 베팅 고려",
            "risk_level": "매우 낮음",
            "follow_up_action": "일반적인 관찰 지속"
        }
    }
}
```

## 🎮 페어 타입 설명

### 기본 페어 타입
- **🎰 `player_pair`**: 플레이어 페어 (예: A♠ A♥)
- **🃏 `banker_pair`**: 뱅커 페어 (예: K♦ K♣)  
- **💎 `both_pairs`**: 양쪽 페어 (매우 희귀)
- **❌ `no_pair`**: 페어 없음

### 패턴 타입
- **📈 `single_pair`**: 단일 페어 발생
- **🔄 `consecutive_pairs`**: 2게임 이상 연속 페어
- **⚖️ `alternating_pairs`**: 플레이어-뱅커 교대 패턴
- **💫 `rare_pattern`**: 5분 내 5회 이상 희귀 패턴

## 🎯 사용 시나리오

### 1️⃣ 실시간 모니터링
1. **서버 실행**: `python main.py`
2. **브라우저 접속**: http://127.0.0.1:8080
3. **실시간 확인**: 페어 발생 시 즉시 알림

### 2️⃣ API 통합 사용
```bash
# 최근 페어 목록 확인
curl http://127.0.0.1:8080/api/pair-notifications/history?limit=10

# 실시간 통계 확인
curl http://127.0.0.1:8080/api/pair-notifications/stats

# 테스트 알림 전송
curl -X POST "http://127.0.0.1:8080/api/pair-notifications/test?table_name=테스트&pair_type=player_pair"
```

### 3️⃣ 개발자 도구 활용
- **API 문서**: http://127.0.0.1:8080/docs
- **서버 상태**: http://127.0.0.1:8080/health
- **WebSocket 테스트**: 브라우저 개발자 도구 콘솔

## ⚙️ 설정 및 커스터마이징

### 알림 설정 변경
```http
PUT /api/pair-notifications/settings
Content-Type: application/json

{
    "enabled": true,
    "min_confidence": 0.8,
    "notification_cooldown_seconds": 10,
    "max_notifications_per_minute": 5,
    "notification_types": ["player_pair", "banker_pair", "both_pairs"]
}
```

### 필터링 옵션
- **테이블별 필터링**: 특정 테이블만 모니터링
- **페어 타입 필터**: 원하는 페어 타입만 알림
- **날짜별 조회**: 특정 날짜 범위의 페어 이력
- **신뢰도 임계값**: 최소 신뢰도 이상만 알림

## 🔧 문제 해결

### 서버가 시작되지 않는 경우
```bash
# 포트 사용 확인
netstat -an | findstr :8080

# 다른 포트로 시도
python main.py  # 자동으로 8000, 3000, 9999, 7777 순으로 시도
```

### WebSocket 연결 문제
1. **방화벽 확인**: Windows 방화벽 설정
2. **브라우저 권한**: 알림 권한 허용
3. **개발자 도구**: 콘솔에서 연결 상태 확인

### 데이터가 표시되지 않는 경우
1. **서비스 상태 확인**: `/api/pair-notifications/service/health`
2. **테스트 알림**: `/api/pair-notifications/test`
3. **로그 확인**: 서버 콘솔 출력 모니터링

## 📞 추가 도움

### 📚 상세 문서
- `F:\two very auto 25.08.23\python\fastapi_app\README_PAIR_NOTIFICATIONS.md`

### 🧪 테스트 파일
- `F:\two very auto 25.08.23\python\fastapi_app\test_pair_notification_system.py`

### 🎨 UI 템플릿
- `F:\two very auto 25.08.23\python\fastapi_app\templates\pair_display.html`

---

## 🎯 요약

**실시간 페어 정보 확인 방법**:
1. **`python main.py`** 실행 (fastapi_app 폴더)
2. **http://127.0.0.1:8080** 접속
3. **실시간 페어 발생** 자동 알림 수신
4. **상세 분석 및 통계** 확인 가능

**핵심 기능**: 실시간 감지, WebSocket 알림, 패턴 분석, AI 예측, 상세 통계

이제 모든 바카라 페어 정보를 실시간으로 모니터링하고 분석할 수 있습니다! 🎰✨