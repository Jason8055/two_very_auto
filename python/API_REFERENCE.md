# API Reference Guide

**시스템**: Two Very Auto Baccarat Monitor v3.0  
**서버**: http://127.0.0.1:5555  
**최종 업데이트**: 2025-08-23

---

## 📡 기본 정보

### Base URL

```
http://127.0.0.1:5555
```

### 응답 형식

모든 API는 JSON 형식으로 응답합니다.

```json
{
  "success": true,
  "data": {},
  "timestamp": "2025-08-23T21:15:00"
}
```

### 에러 응답

```json
{
  "success": false,
  "error": "Error message",
  "timestamp": "2025-08-23T21:15:00"
}
```

---

## 🌐 웹 인터페이스 API

### GET /

**메인 대시보드**

HTML 페이지를 반환합니다.

**응답**:
- `Content-Type: text/html`
- 반응형 웹 대시보드

**기능**:
- 실시간 통계 표시
- 테이블별 현황
- 30초 자동 새로고침
- 모바일 반응형 디자인

---

## 📊 시스템 상태 API

### GET /api/status

**서버 상태 조회**

서버의 현재 상태와 기본 정보를 반환합니다.

**응답 예시**:
```json
{
  "status": "running",
  "server": "web_server.py",
  "port": 5555,
  "timestamp": "2025-08-23T21:15:00",
  "summary": {
    "global_stats": {
      "total_games": 150,
      "total_pairs": 23,
      "last_updated": "2025-08-23T21:14:30"
    },
    "active_tables": 3,
    "total_tables": 5
  }
}
```

**필드 설명**:
- `status`: 서버 상태 ("running", "error")
- `server`: 서버 프로그램명
- `port`: 서버 포트 번호
- `summary`: 전체 시스템 요약 정보

---

## 📈 데이터 조회 API

### GET /api/data

**전체 데이터 조회**

모든 테이블 정보와 최근 페어 데이터를 반환합니다.

**응답 예시**:
```json
{
  "success": true,
  "timestamp": "2025-08-23T21:15:00",
  "summary": {
    "global_stats": {
      "total_games": 150,
      "total_pairs": 23,
      "last_updated": "2025-08-23T21:14:30"
    },
    "active_tables": 3,
    "total_tables": 5,
    "tables": {
      "table_001": {
        "table_name": "table_001",
        "total_games": 45,
        "pair_count": 7,
        "player_pairs": 4,
        "banker_pairs": 3,
        "both_pairs": 0,
        "games_since_last_pair": 3,
        "statistics": {
          "pair_rate": 0.1556,
          "player_pair_rate": 0.0889,
          "banker_pair_rate": 0.0667,
          "avg_games_between_pairs": 6.43
        },
        "last_game_time": "2025-08-23T21:10:15",
        "latest_pair_info": {
          "game_id": 12340,
          "game_time": "2025-08-23T21:05:30",
          "pair_type": "PLAYER_PAIR",
          "pair_cards": ["KH", "KD"]
        }
      }
    }
  },
  "recent_pairs": [
    {
      "game_id": 12340,
      "game_time": "2025-08-23T21:05:30",
      "pair_type": "PLAYER_PAIR",
      "pair_cards": ["KH", "KD"],
      "player_cards": ["KH", "KD", "5C"],
      "banker_cards": ["9S", "2H"],
      "result": "PLAYER",
      "table_name": "table_001"
    }
  ]
}
```

**필드 설명**:

#### Global Stats
- `total_games`: 전체 게임 수
- `total_pairs`: 전체 페어 수
- `last_updated`: 마지막 업데이트 시간

#### Table Info
- `total_games`: 테이블별 총 게임 수
- `pair_count`: 페어 발생 수
- `player_pairs`: 플레이어 페어 수
- `banker_pairs`: 뱅커 페어 수
- `games_since_last_pair`: 마지막 페어 이후 게임 수
- `statistics.pair_rate`: 페어 발생 비율 (0.0-1.0)

#### Recent Pairs
- `pair_type`: 페어 타입 ("PLAYER_PAIR", "BANKER_PAIR", "BOTH_PAIR")
- `pair_cards`: 페어가 된 카드들
- `result`: 게임 결과 ("PLAYER", "BANKER", "TIE")

---

## 🎯 테이블별 API

### GET /api/table/\<table_name\>

**특정 테이블 정보 조회**

개별 테이블의 상세 정보를 반환합니다.

**URL 파라미터**:
- `table_name`: 테이블명 (예: "table_001")

**응답 예시**:
```json
{
  "success": true,
  "table_info": {
    "table_name": "table_001",
    "total_games": 45,
    "pair_count": 7,
    "games_since_last_pair": 3,
    "statistics": {
      "pair_rate": 0.1556,
      "avg_games_between_pairs": 6.43
    },
    "recent_games_cached": 45,
    "last_game_time": "2025-08-23T21:10:15"
  },
  "timestamp": "2025-08-23T21:15:00"
}
```

**에러 응답** (테이블 없음):
```json
{
  "error": "Table table_999 not found"
}
```
HTTP Status: 404

---

## 🧪 데모 및 테스트 API

### GET /api/demo

**데모 데이터 추가**

테스트용 데모 게임 데이터를 생성하고 추가합니다.

**응답 예시**:
```json
{
  "success": true,
  "message": "Added 5 demo games",
  "results": [
    {
      "table_name": "table_003",
      "game_id": 10001,
      "has_pair": true,
      "pair_type": "BANKER_PAIR",
      "pair_cards": ["QH", "QD"],
      "games_since_last_pair": 0,
      "alert": true,
      "message": "BANKER_PAIR detected!"
    },
    {
      "table_name": "table_001",
      "game_id": 10002,
      "has_pair": false,
      "games_since_last_pair": 5,
      "alert": false
    }
  ],
  "timestamp": "2025-08-23T21:15:00"
}
```

**사용법**:
- 시스템 테스트용
- 데모 환경 구성
- 페어 추적 기능 확인

---

## 🔧 사용 예제

### Python 예제

```python
import requests
import json

# 서버 상태 확인
response = requests.get('http://127.0.0.1:5555/api/status')
if response.status_code == 200:
    data = response.json()
    print(f"Server status: {data['status']}")
    print(f"Total games: {data['summary']['global_stats']['total_games']}")

# 전체 데이터 조회
response = requests.get('http://127.0.0.1:5555/api/data')
data = response.json()

for table_name, table_info in data['summary']['tables'].items():
    print(f"{table_name}: {table_info['pair_count']} pairs in {table_info['total_games']} games")

# 특정 테이블 조회
response = requests.get('http://127.0.0.1:5555/api/table/table_001')
if response.status_code == 200:
    table = response.json()['table_info']
    print(f"Table 001 pair rate: {table['statistics']['pair_rate']:.1%}")

# 데모 데이터 추가
response = requests.get('http://127.0.0.1:5555/api/demo')
result = response.json()
print(f"Demo result: {result['message']}")
```

### JavaScript 예제

```javascript
// 서버 상태 확인
fetch('/api/status')
    .then(response => response.json())
    .then(data => {
        console.log('Server status:', data.status);
        console.log('Active tables:', data.summary.active_tables);
    });

// 전체 데이터 조회
fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        const tables = data.summary.tables;
        Object.keys(tables).forEach(tableName => {
            const table = tables[tableName];
            console.log(`${tableName}: ${table.pair_count} pairs`);
        });
    });

// 특정 테이블 조회
fetch('/api/table/table_001')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const pairRate = (data.table_info.statistics.pair_rate * 100).toFixed(1);
            console.log(`Table 001 pair rate: ${pairRate}%`);
        }
    });

// 데모 데이터 추가
fetch('/api/demo')
    .then(response => response.json())
    .then(data => {
        console.log('Demo result:', data.message);
        data.results.forEach(result => {
            if (result.alert) {
                console.log(`PAIR ALERT: ${result.message}`);
            }
        });
    });
```

### curl 예제

```bash
# 서버 상태 확인
curl http://127.0.0.1:5555/api/status

# 전체 데이터 조회 (정렬된 JSON)
curl -s http://127.0.0.1:5555/api/data | python -m json.tool

# 특정 테이블 조회
curl http://127.0.0.1:5555/api/table/table_001

# 데모 데이터 추가
curl http://127.0.0.1:5555/api/demo
```

---

## ⚡ 성능 및 제한사항

### API 성능

- **응답 시간**: 일반적으로 <50ms
- **동시 요청**: 50+ 지원
- **데이터 크기**: 일반 응답 <10KB

### 제한사항

- **Rate Limiting**: 현재 없음 (향후 추가 예정)
- **인증**: 현재 없음 (로컬 환경용)
- **HTTPS**: HTTP만 지원 (개발 환경)

### 캐싱 정책

- **시스템 상태**: 실시간 (캐시 없음)
- **테이블 데이터**: 메모리 캐시 (최대 100게임)
- **통계 데이터**: 10게임마다 파일 저장

---

## 🚨 에러 코드

| HTTP 코드 | 설명 | 응답 예시 |
|-----------|------|-----------|
| 200 | 성공 | `{"success": true}` |
| 404 | 리소스 없음 | `{"error": "Table not found"}` |
| 500 | 서버 오류 | `{"error": "Internal server error"}` |

### 일반적인 에러 메시지

- `"Table {name} not found"`: 존재하지 않는 테이블
- `"No data available"`: 데이터 없음
- `"Internal server error"`: 서버 내부 오류

---

## 🔄 실시간 업데이트

### 웹 인터페이스

- **자동 새로고침**: 30초 간격
- **수동 새로고침**: "Refresh Now" 버튼
- **실시간 카운트다운**: 다음 새로고침까지 시간 표시

### API 호출

API는 실시간 데이터를 반환하므로 주기적 호출로 실시간 모니터링 가능:

```javascript
// 5초마다 상태 확인
setInterval(() => {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => updateUI(data));
}, 5000);
```

---

**🎯 API Reference Complete!**

**테스트**: `curl http://127.0.0.1:5555/api/status`

---

*Last Updated: 2025-08-23 21:15 by Claude Code Assistant*