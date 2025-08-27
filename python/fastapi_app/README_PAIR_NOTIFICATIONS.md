# 실시간 페어 알림 시스템 (Real-time Pair Notification System)

FastAPI 기반의 실시간 바카라 페어 감지 및 알림 시스템입니다.

## 🎯 주요 기능

### 📊 페어 감지
- **실시간 페어 감지**: 플레이어 페어, 뱅커 페어, 양쪽 페어 감지
- **패턴 분석**: 연속 페어, 교대 패턴, 희귀 패턴 식별
- **신뢰도 평가**: 감지된 페어의 신뢰도 계산
- **다중 테이블 지원**: 여러 바카라 테이블 동시 모니터링

### 🔔 실시간 알림
- **WebSocket 브로드캐스트**: 실시간 페어 알림 전송
- **다중 채널 지원**: WebSocket, 푸시 알림, 이메일, SMS (확장 가능)
- **우선순위 기반**: 페어 타입과 패턴에 따른 우선순위 처리
- **알림 제어**: 쿨다운, 속도 제한, 필터링

### ⚙️ 설정 관리
- **동적 설정**: 런타임 설정 변경 가능
- **알림 조건**: 최소 신뢰도, 알림 타입, 쿨다운 시간
- **성능 튜닝**: 분당 최대 알림 수, 패턴 감지 활성화

### 📈 통계 및 모니터링
- **실시간 통계**: 감지된 페어, 전송된 알림 통계
- **테이블별 분석**: 각 테이블의 페어 발생 패턴
- **이력 관리**: 최근 페어 이벤트 이력 조회

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Game Data     │ => │  Pair Detection  │ => │  Notification   │
│   Input         │    │     Engine       │    │   Broadcasting  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                       ┌────────▼────────┐      ┌────────▼────────┐
                       │  Pattern        │      │  Multi-Channel  │
                       │  Analysis       │      │  Distribution   │
                       └─────────────────┘      └─────────────────┘
                                │                        │
                       ┌────────▼────────┐      ┌────────▼────────┐
                       │  Statistics &   │      │  WebSocket,     │
                       │  History        │      │  Push, Email... │
                       └─────────────────┘      └─────────────────┘
```

## 🚀 시작하기

### 서버 실행
```bash
cd /path/to/fastapi_app
python main.py
```

### 테스트 실행
```bash
python test_pair_notification_system.py
```

## 📡 API 엔드포인트

### 페어 감지
```http
POST /api/pair-notifications/detect
Content-Type: application/json

{
    "table_name": "바카라 A",
    "game_number": 123,
    "player_cards": ["A♠", "A♥"],
    "banker_cards": ["K♦", "Q♣"],
    "additional_data": {"dealer": "김딜러"}
}
```

### 설정 관리
```http
GET /api/pair-notifications/settings
PUT /api/pair-notifications/settings

{
    "enabled": true,
    "min_confidence": 0.8,
    "notification_cooldown_seconds": 10,
    "max_notifications_per_minute": 5
}
```

### 통계 조회
```http
GET /api/pair-notifications/stats
GET /api/pair-notifications/history?limit=50&table_name=바카라A
GET /api/pair-notifications/tables/stats
```

### 서비스 관리
```http
POST /api/pair-notifications/service/start
POST /api/pair-notifications/service/stop
GET /api/pair-notifications/service/health
```

### 테스트
```http
POST /api/pair-notifications/test?table_name=테스트테이블&pair_type=player_pair
```

## 🔌 WebSocket 연결

### 연결
```javascript
const ws = new WebSocket('ws://localhost:8004/ws/realtime?client_id=client123');

// 페어 알림 구독
ws.send(JSON.stringify({
    command: 'subscribe',
    data: { type: 'pairs' }
}));
```

### 알림 수신
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'pair_notification') {
        const pairEvent = data.data.pair_event;
        console.log(`페어 감지: ${pairEvent.table_name} - ${pairEvent.pair_type}`);
        
        // UI 업데이트
        updatePairNotification(pairEvent);
    }
};
```

## 📊 알림 메시지 구조

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
        "cards": {
            "player_display": "A♠ A♥",
            "banker_display": "K♦ Q♣"
        },
        "analytics": {
            "betting_recommendation": "플레이어 페어 베팅 고려",
            "risk_level": "매우 낮음",
            "follow_up_action": "일반적인 관찰 지속"
        }
    }
}
```

## 🎮 페어 타입

### 기본 페어 타입
- **`player_pair`**: 플레이어 페어 (같은 숫자 2장)
- **`banker_pair`**: 뱅커 페어 (같은 숫자 2장)
- **`both_pairs`**: 양쪽 페어 (플레이어, 뱅커 모두 페어)
- **`no_pair`**: 페어 없음

### 패턴 타입
- **`single_pair`**: 단일 페어
- **`consecutive_pairs`**: 연속 페어 (2게임 이상)
- **`alternating_pairs`**: 교대 패턴 (플레이어-뱅커-플레이어...)
- **`rare_pattern`**: 희귀 패턴 (5분 내 5회 이상 페어)

## ⚙️ 설정 옵션

### 기본 설정
```json
{
    "enabled": true,
    "notification_types": ["player_pair", "banker_pair", "both_pairs"],
    "min_confidence": 0.8,
    "pattern_detection_enabled": true,
    "consecutive_pair_threshold": 2,
    "notification_cooldown_seconds": 5,
    "max_notifications_per_minute": 10
}
```

### 설정 설명
- **`enabled`**: 알림 시스템 활성화 여부
- **`notification_types`**: 알림을 받을 페어 타입 목록
- **`min_confidence`**: 알림을 보낼 최소 신뢰도 (0.0-1.0)
- **`pattern_detection_enabled`**: 패턴 감지 기능 활성화
- **`consecutive_pair_threshold`**: 연속 페어로 인식할 최소 횟수
- **`notification_cooldown_seconds`**: 테이블별 알림 쿨다운 시간
- **`max_notifications_per_minute`**: 테이블별 분당 최대 알림 수

## 📈 성능 최적화

### 브로드캐스트 우선순위
- **`REAL_TIME`**: 100ms 이내 (양쪽 페어)
- **`HIGH`**: 500ms 이내 (연속/희귀 패턴)
- **`NORMAL`**: 1초 이내 (일반 페어)
- **`LOW`**: 5초 이내 (낮은 신뢰도)

### 메모리 관리
- 최근 페어 이벤트: 최대 1000개 유지
- 브로드캐스트 이력: 최대 500개 유지
- 자동 정리: 24시간 이상 된 데이터 삭제

## 🛠️ 개발 가이드

### 새로운 페어 타입 추가
1. `models/pair_notification.py`에서 `PairTypeEnum` 수정
2. `services/pair_notification_service.py`에서 감지 로직 추가
3. 테스트 케이스 작성

### 새로운 브로드캐스트 채널 추가
1. `services/pair_broadcast_service.py`에서 `BroadcastChannelType` 확장
2. `_send_to_channel` 메서드에 처리 로직 추가
3. 채널별 설정 추가

### 커스텀 패턴 추가
1. `PairPattern` 열거형에 새 패턴 추가
2. `PairDetector.analyze_pair_pattern`에서 감지 로직 구현
3. 패턴별 우선순위 및 메시지 설정

## 🧪 테스트

### 자동화 테스트
```bash
# 전체 시스템 테스트
python test_pair_notification_system.py

# 개별 기능 테스트
python -m pytest tests/test_pair_detection.py
python -m pytest tests/test_notification_service.py
```

### 수동 테스트
```bash
# 테스트 알림 전송
curl -X POST "http://localhost:8004/api/pair-notifications/test?table_name=테스트&pair_type=player_pair"

# 서비스 상태 확인
curl "http://localhost:8004/api/pair-notifications/service/health"
```

## 🔧 문제 해결

### 일반적인 문제

**1. 알림이 전송되지 않음**
- 서비스 활성화 상태 확인: `/service/health`
- 설정 확인: `enabled: true`, 적절한 `min_confidence`
- WebSocket 연결 상태 확인

**2. 페어 감지가 정확하지 않음**
- 카드 형식 확인: `["A♠", "A♥"]` 형식 사용
- 신뢰도 임계값 조정: `min_confidence` 설정
- 로그 확인: 감지 과정 상세 로그 분석

**3. 성능 문제**
- 알림 빈도 조절: `max_notifications_per_minute` 제한
- 쿨다운 시간 조정: `notification_cooldown_seconds` 증가
- 불필요한 패턴 감지 비활성화

### 로그 레벨 조정
```python
import logging
logging.getLogger('pair_notification').setLevel(logging.DEBUG)
```

## 📝 변경 이력

### v2.0.0 (현재)
- ✅ 실시간 페어 감지 시스템 구현
- ✅ WebSocket 기반 브로드캐스트
- ✅ 패턴 분석 기능
- ✅ 동적 설정 관리
- ✅ 통계 및 모니터링
- ✅ 에러 핸들링 및 복구
- ✅ 종합 테스트 시스템

### 향후 계획
- 📧 이메일 알림 채널 구현
- 📱 푸시 알림 지원
- 🤖 AI 기반 패턴 예측
- 📊 고급 통계 대시보드
- 🔐 사용자별 알림 필터링

## 🤝 기여하기

1. 이슈 리포트: 버그나 개선사항 제안
2. 풀 리퀘스트: 코드 기여
3. 문서 개선: README나 코드 주석 개선
4. 테스트 케이스: 새로운 테스트 시나리오 추가

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.