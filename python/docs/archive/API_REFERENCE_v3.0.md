# Two Very Auto v3.0 - API 레퍼런스

**🔗 RESTful API 완전 가이드**

---

## 📋 목차

1. [🌐 개요](#-개요)
2. [🔐 인증](#-인증)
3. [📡 응답 형식](#-응답-형식)
4. [🔔 알림 시스템 API](#-알림-시스템-api)
5. [🖥️ 모니터링 API](#️-모니터링-api)
6. [🎰 멀티 카지노 API](#-멀티-카지노-api)
7. [📊 데이터 API](#-데이터-api)
8. [⚙️ 설정 API](#️-설정-api)
9. [❌ 에러 코드](#-에러-코드)
10. [📝 예제 코드](#-예제-코드)

---

## 🌐 개요

### Base URL
```
http://127.0.0.1:5000
```

### API 버전
```
v3.0
```

### Content-Type
```
application/json
```

### 새로운 엔드포인트 (v3.0)
- **25개 새로운 API 엔드포인트**
- **RESTful 설계 원칙 준수**
- **OpenAPI 3.0 스펙 지원**

---

## 🔐 인증

현재 버전에서는 기본 인증을 사용합니다. 향후 JWT 토큰 기반 인증으로 업그레이드 예정입니다.

### 인증 헤더 (선택사항)
```http
Authorization: Bearer <token>
```

---

## 📡 응답 형식

### 성공 응답
```json
{
  "success": true,
  "data": {},
  "timestamp": "2025-08-25T10:30:00Z",
  "version": "3.0"
}
```

### 에러 응답
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2025-08-25T10:30:00Z"
}
```

---

## 🔔 알림 시스템 API

### 프로필 관리

#### 모든 프로필 조회
```http
GET /api/notifications/profiles
```

**응답 예제:**
```json
{
  "success": true,
  "profiles": [
    {
      "name": "기본",
      "is_current": true,
      "config": {
        "channels": {
          "web": {"enabled": true, "sound": true, "desktop": true},
          "telegram": {"enabled": false},
          "email": {"enabled": false},
          "tts": {"enabled": false}
        },
        "triggers": {
          "pair_detected": {"enabled": true, "priority": "high"},
          "long_streak": {"enabled": true, "priority": "medium", "threshold": 5},
          "multiple_pairs": {"enabled": true, "priority": "high", "threshold": 2}
        },
        "schedule": {
          "active_hours": {"start": "09:00", "end": "23:00"},
          "weekend_enabled": true
        },
        "limits": {
          "max_per_hour": 20,
          "min_interval_seconds": 30
        }
      },
      "created_at": "2025-08-25T09:00:00Z",
      "last_updated": "2025-08-25T10:15:00Z"
    }
  ],
  "current_profile": "기본"
}
```

#### 새 프로필 생성
```http
POST /api/notifications/profiles
Content-Type: application/json

{
  "name": "게이밍_모드",
  "config": {
    "channels": {
      "web": {"enabled": true, "sound": false, "desktop": true},
      "telegram": {"enabled": false}
    },
    "triggers": {
      "pair_detected": {"enabled": true, "priority": "high"}
    },
    "limits": {
      "max_per_hour": 5,
      "min_interval_seconds": 60
    }
  }
}
```

**응답:**
```json
{
  "success": true,
  "message": "프로필 '게이밍_모드'이 생성되었습니다"
}
```

#### 프로필 업데이트
```http
PUT /api/notifications/profiles/{profile_name}
Content-Type: application/json

{
  "config": {
    "channels": {
      "web": {"enabled": true, "sound": true}
    }
  }
}
```

#### 프로필 삭제
```http
DELETE /api/notifications/profiles/{profile_name}
```

### 프로필 전환

#### 현재 프로필 변경
```http
PUT /api/notifications/current-profile
Content-Type: application/json

{
  "profile_name": "조용함"
}
```

### 알림 테스트

#### 테스트 알림 전송
```http
POST /api/notifications/test
Content-Type: application/json

{
  "trigger_type": "pair_detected",
  "message": "테스트 페어 감지 알림"
}
```

**응답:**
```json
{
  "success": true,
  "message": "테스트 알림이 전송되었습니다",
  "allowed": true
}
```

### 알림 상태

#### 현재 알림 상태 조회
```http
GET /api/notifications/status
```

**응답:**
```json
{
  "success": true,
  "current_profile": "기본",
  "current_time": "2025-08-25T10:30:00Z",
  "trigger_status": {
    "pair_detected": {
      "enabled": true,
      "allowed": true,
      "priority": "high"
    },
    "long_streak": {
      "enabled": true,
      "allowed": false,
      "priority": "medium",
      "threshold": 5
    }
  },
  "total_profiles": 3
}
```

### 템플릿

#### 기본 프로필 템플릿 조회
```http
GET /api/notifications/default-templates
```

**응답:**
```json
{
  "success": true,
  "templates": {
    "게이밍_집중": {
      "description": "게임 중 집중을 위한 최소한의 알림",
      "config": {
        "channels": {
          "web": {"enabled": true, "sound": false, "desktop": true}
        },
        "triggers": {
          "pair_detected": {"enabled": true, "priority": "high"}
        },
        "limits": {"max_per_hour": 5}
      }
    }
  }
}
```

---

## 🖥️ 모니터링 API

### 메트릭 조회

#### 현재 시스템 메트릭
```http
GET /api/monitoring/metrics
```

**응답:**
```json
{
  "success": true,
  "timestamp": "2025-08-25T10:30:00Z",
  "metrics": {
    "cpu_percent": 25.4,
    "memory_percent": 45.8,
    "disk_io_read": 1024000,
    "disk_io_write": 512000,
    "network_sent": 2048000,
    "network_received": 4096000,
    "games_processed": 15420,
    "pairs_detected": 89,
    "ai_accuracy": 87.5,
    "websocket_connections": 3,
    "database_size_mb": 125.7,
    "uptime_seconds": 86400
  }
}
```

#### 메트릭 히스토리
```http
GET /api/monitoring/history?hours=1
```

**쿼리 파라미터:**
- `hours`: 조회할 시간 범위 (1-24)

**응답:**
```json
{
  "success": true,
  "hours": 1,
  "history": {
    "timestamps": [
      "2025-08-25T09:30:00Z",
      "2025-08-25T09:45:00Z",
      "2025-08-25T10:00:00Z"
    ],
    "cpu_percent": [23.1, 28.5, 25.4],
    "memory_percent": [42.3, 46.1, 45.8],
    "games_per_minute": [85, 92, 88]
  }
}
```

### 알림 및 상태

#### 활성 알림 조회
```http
GET /api/monitoring/alerts
```

**응답:**
```json
{
  "success": true,
  "alerts": [
    {
      "type": "CPU_HIGH",
      "message": "CPU 사용률이 80%를 초과했습니다",
      "severity": "warning",
      "timestamp": "2025-08-25T10:25:00Z",
      "value": 82.5,
      "threshold": 80.0
    }
  ],
  "count": 1
}
```

#### 시스템 건강도
```http
GET /api/monitoring/health
```

**응답:**
```json
{
  "success": true,
  "health": {
    "overall_status": "healthy",
    "score": 92,
    "components": {
      "web_server": {"status": "healthy", "score": 95},
      "database": {"status": "healthy", "score": 90},
      "ai_engine": {"status": "healthy", "score": 88},
      "notification_system": {"status": "healthy", "score": 96}
    },
    "recommendations": [
      "AI 모델 재학습을 권장합니다 (정확도 향상 가능)"
    ]
  },
  "timestamp": "2025-08-25T10:30:00Z"
}
```

#### 통계 요약
```http
GET /api/monitoring/stats/summary
```

**응답:**
```json
{
  "success": true,
  "summary": {
    "uptime": {
      "current_session": 86400,
      "total_uptime_percentage": 99.8
    },
    "performance": {
      "avg_cpu": 28.5,
      "avg_memory": 45.2,
      "peak_games_per_hour": 5240,
      "avg_response_time_ms": 85
    },
    "ai_stats": {
      "total_predictions": 1542,
      "accuracy": 87.5,
      "confidence_avg": 0.82,
      "model_version": "v2.1"
    },
    "websocket_stats": {
      "total_connections": 12,
      "active_connections": 3,
      "messages_sent": 45230,
      "messages_received": 12890
    },
    "database_stats": {
      "total_games": 125420,
      "total_pairs": 8954,
      "db_size_mb": 125.7,
      "query_avg_time_ms": 12
    }
  },
  "generated_at": "2025-08-25T10:30:00Z"
}
```

### 설정

#### 임계값 조회
```http
GET /api/monitoring/thresholds
```

**응답:**
```json
{
  "success": true,
  "thresholds": {
    "cpu_warning": 70.0,
    "cpu_critical": 90.0,
    "memory_warning": 80.0,
    "memory_critical": 95.0,
    "disk_warning": 85.0,
    "response_time_warning": 200,
    "ai_accuracy_minimum": 75.0
  }
}
```

#### 임계값 업데이트
```http
POST /api/monitoring/thresholds
Content-Type: application/json

{
  "cpu_warning": 75.0,
  "memory_warning": 85.0
}
```

### 대시보드

#### 모니터링 대시보드 (HTML)
```http
GET /api/monitoring/dashboard
```

브라우저에서 실시간 모니터링 대시보드를 제공합니다.

---

## 🎰 멀티 카지노 API

### 카지노 관리

#### 모든 카지노 상태 조회
```http
GET /api/casinos
```

**응답:**
```json
{
  "success": true,
  "casinos": [
    {
      "casino_id": "main_casino",
      "is_active": true,
      "connection_status": "active",
      "last_update": "2025-08-25T10:29:45Z",
      "uptime_hours": 24.5,
      "games_processed": 8540,
      "pairs_detected": 45,
      "average_games_per_hour": 1280.5,
      "error_count": 2,
      "config": {
        "name": "메인 카지노",
        "server_ip": "127.0.0.1",
        "port": 8080,
        "priority": 1
      }
    },
    {
      "casino_id": "backup_casino",
      "is_active": false,
      "connection_status": "disconnected",
      "last_update": null,
      "uptime_hours": 0,
      "games_processed": 0,
      "pairs_detected": 0,
      "average_games_per_hour": 0,
      "error_count": 0,
      "config": {
        "name": "백업 카지노",
        "server_ip": "127.0.0.1", 
        "port": 8081,
        "priority": 2
      }
    }
  ]
}
```

#### 카지노 연결
```http
POST /api/casinos/{casino_id}/connect
```

**응답:**
```json
{
  "success": true,
  "message": "카지노 'main_casino'에 성공적으로 연결되었습니다"
}
```

#### 카지노 연결 해제
```http
POST /api/casinos/{casino_id}/disconnect
```

**응답:**
```json
{
  "success": true,
  "message": "카지노 'main_casino' 연결이 해제되었습니다"
}
```

### 분석 및 비교

#### 카지노 간 비교 분석
```http
GET /api/casinos/comparison
```

**응답:**
```json
{
  "success": true,
  "comparison": {
    "performance_ranking": [
      {
        "casino_id": "main_casino",
        "games_per_hour": 1280.5,
        "pairs_detected": 45,
        "error_rate": 0.02
      },
      {
        "casino_id": "premium_casino", 
        "games_per_hour": 1150.8,
        "pairs_detected": 38,
        "error_rate": 0.01
      }
    ],
    "pair_detection_rates": {
      "main_casino": {
        "rate": 5.27,
        "total_pairs": 45,
        "total_games": 8540
      }
    },
    "uptime_comparison": {
      "main_casino": 99.8,
      "premium_casino": 99.9
    },
    "error_rates": {
      "main_casino": 0.02,
      "premium_casino": 0.01
    }
  }
}
```

#### 추천 카지노 조회
```http
GET /api/casinos/recommended
```

**응답:**
```json
{
  "success": true,
  "recommended": "main_casino",
  "reason": "최고 성능 점수 (games_per_hour: 1280.5, error_rate: 0.02)",
  "score": 95.8,
  "alternatives": [
    {
      "casino_id": "premium_casino",
      "score": 94.2,
      "reason": "낮은 오류율"
    }
  ]
}
```

---

## 📊 데이터 API

### 게임 데이터

#### 최근 게임 조회
```http
GET /api/data/games/recent?limit=10&casino_id=main_casino
```

**쿼리 파라미터:**
- `limit`: 조회할 게임 수 (기본: 50, 최대: 1000)
- `casino_id`: 특정 카지노 필터 (선택사항)

**응답:**
```json
{
  "success": true,
  "games": [
    {
      "id": 15421,
      "casino_id": "main_casino",
      "timestamp": "2025-08-25T10:29:30Z",
      "player_cards": ["K♠", "9♥"],
      "banker_cards": ["A♦", "8♣"],
      "player_total": 9,
      "banker_total": 9,
      "result": "tie",
      "has_pair": true,
      "pair_type": "player_pair",
      "prediction": {
        "predicted_result": "player",
        "confidence": 0.78,
        "actual_match": false
      }
    }
  ],
  "total": 10,
  "filtered_by": "main_casino"
}
```

#### 게임 통계
```http
GET /api/data/stats/games?period=24h&casino_id=main_casino
```

**쿼리 파라미터:**
- `period`: 기간 (`1h`, `24h`, `7d`, `30d`)
- `casino_id`: 카지노 필터 (선택사항)

**응답:**
```json
{
  "success": true,
  "period": "24h",
  "casino_id": "main_casino",
  "stats": {
    "total_games": 8540,
    "results": {
      "player": 4120,
      "banker": 4200,
      "tie": 220
    },
    "pairs": {
      "total": 45,
      "player_pair": 23,
      "banker_pair": 18,
      "both_pair": 4
    },
    "ai_performance": {
      "total_predictions": 8540,
      "correct_predictions": 7473,
      "accuracy": 87.5,
      "avg_confidence": 0.82
    },
    "performance": {
      "games_per_hour": 1280.5,
      "peak_hour": "2025-08-25T14:00:00Z",
      "peak_games": 1450
    }
  }
}
```

### 패턴 분석

#### 패턴 분석 결과
```http
GET /api/data/patterns/analysis?casino_id=main_casino&depth=100
```

**쿼리 파라미터:**
- `casino_id`: 카지노 ID
- `depth`: 분석할 게임 수 (기본: 100)

**응답:**
```json
{
  "success": true,
  "analysis": {
    "streaks": {
      "current_streak": {
        "type": "player",
        "length": 3,
        "probability_break": 0.65
      },
      "longest_streaks": {
        "player": 7,
        "banker": 8,
        "tie": 2
      }
    },
    "patterns": [
      {
        "pattern": "PPBBP",
        "frequency": 12,
        "next_prediction": "banker",
        "confidence": 0.73
      }
    ],
    "hot_cold_analysis": {
      "hot": ["banker", "player_pair"],
      "cold": ["tie", "banker_pair"],
      "neutral": ["player"]
    },
    "pair_predictions": {
      "next_pair_probability": 0.15,
      "recommended_bet": "no_pair",
      "confidence": 0.85
    }
  }
}
```

---

## ⚙️ 설정 API

### 시스템 설정

#### 전체 설정 조회
```http
GET /api/settings
```

**응답:**
```json
{
  "success": true,
  "settings": {
    "server": {
      "host": "127.0.0.1",
      "port": 5000,
      "debug": false
    },
    "database": {
      "path": "./baccarat_monitor_pwa_v3.db",
      "backup_interval": 3600,
      "cleanup_days": 30
    },
    "ai": {
      "model_type": "ensemble",
      "retrain_interval": 86400,
      "confidence_threshold": 0.7
    },
    "notifications": {
      "default_profile": "기본",
      "max_profiles": 10
    }
  }
}
```

#### 설정 업데이트
```http
PUT /api/settings
Content-Type: application/json

{
  "ai": {
    "confidence_threshold": 0.75
  },
  "database": {
    "cleanup_days": 45
  }
}
```

### 백업 및 복원

#### 데이터베이스 백업
```http
POST /api/settings/backup
```

**응답:**
```json
{
  "success": true,
  "backup_file": "backup_2025-08-25_10-30-00.db",
  "size_mb": 125.7,
  "timestamp": "2025-08-25T10:30:00Z"
}
```

#### 백업 목록 조회
```http
GET /api/settings/backups
```

**응답:**
```json
{
  "success": true,
  "backups": [
    {
      "filename": "backup_2025-08-25_10-30-00.db",
      "size_mb": 125.7,
      "created_at": "2025-08-25T10:30:00Z"
    }
  ]
}
```

---

## ❌ 에러 코드

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 리소스 생성 성공 |
| 400 | Bad Request | 잘못된 요청 |
| 401 | Unauthorized | 인증 필요 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 429 | Too Many Requests | 요청 제한 초과 |
| 500 | Internal Server Error | 서버 오류 |
| 503 | Service Unavailable | 서비스 이용 불가 |

### 애플리케이션 에러 코드

| 코드 | 설명 |
|------|------|
| `PROFILE_NOT_FOUND` | 알림 프로필을 찾을 수 없음 |
| `PROFILE_ALREADY_EXISTS` | 프로필이 이미 존재함 |
| `CASINO_NOT_FOUND` | 카지노를 찾을 수 없음 |
| `CASINO_CONNECTION_FAILED` | 카지노 연결 실패 |
| `INVALID_CONFIG` | 잘못된 설정 값 |
| `DATABASE_ERROR` | 데이터베이스 오류 |
| `AI_MODEL_ERROR` | AI 모델 오류 |
| `MONITORING_ERROR` | 모니터링 시스템 오류 |

---

## 📝 예제 코드

### Python 클라이언트 예제

```python
import requests
import json

class TwoAutoClient:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_system_metrics(self):
        """현재 시스템 메트릭 조회"""
        response = self.session.get(f"{self.base_url}/api/monitoring/metrics")
        return response.json()
    
    def create_notification_profile(self, name, config):
        """알림 프로필 생성"""
        data = {"name": name, "config": config}
        response = self.session.post(
            f"{self.base_url}/api/notifications/profiles",
            json=data
        )
        return response.json()
    
    def get_casino_status(self):
        """모든 카지노 상태 조회"""
        response = self.session.get(f"{self.base_url}/api/casinos")
        return response.json()
    
    def connect_casino(self, casino_id):
        """카지노 연결"""
        response = self.session.post(
            f"{self.base_url}/api/casinos/{casino_id}/connect"
        )
        return response.json()

# 사용 예제
client = TwoAutoClient()

# 시스템 메트릭 조회
metrics = client.get_system_metrics()
print(f"CPU: {metrics['metrics']['cpu_percent']}%")

# 알림 프로필 생성
profile_config = {
    "channels": {"web": {"enabled": True, "sound": False}},
    "triggers": {"pair_detected": {"enabled": True}},
    "limits": {"max_per_hour": 10}
}
result = client.create_notification_profile("게이밍모드", profile_config)
print(result["message"])

# 카지노 상태 확인
casinos = client.get_casino_status()
for casino in casinos["casinos"]:
    print(f"{casino['casino_id']}: {casino['connection_status']}")
```

### JavaScript/Node.js 예제

```javascript
const axios = require('axios');

class TwoAutoClient {
    constructor(baseURL = 'http://127.0.0.1:5000') {
        this.client = axios.create({ baseURL });
    }
    
    async getSystemMetrics() {
        try {
            const response = await this.client.get('/api/monitoring/metrics');
            return response.data;
        } catch (error) {
            console.error('Error fetching metrics:', error.message);
            throw error;
        }
    }
    
    async createNotificationProfile(name, config) {
        try {
            const response = await this.client.post('/api/notifications/profiles', {
                name,
                config
            });
            return response.data;
        } catch (error) {
            console.error('Error creating profile:', error.message);
            throw error;
        }
    }
    
    async getCasinoStatus() {
        try {
            const response = await this.client.get('/api/casinos');
            return response.data;
        } catch (error) {
            console.error('Error fetching casino status:', error.message);
            throw error;
        }
    }
}

// 사용 예제
(async () => {
    const client = new TwoAutoClient();
    
    try {
        // 시스템 메트릭 조회
        const metrics = await client.getSystemMetrics();
        console.log(`CPU: ${metrics.metrics.cpu_percent}%`);
        
        // 카지노 상태 확인
        const casinos = await client.getCasinoStatus();
        casinos.casinos.forEach(casino => {
            console.log(`${casino.casino_id}: ${casino.connection_status}`);
        });
        
    } catch (error) {
        console.error('Error:', error.message);
    }
})();
```

### cURL 예제

```bash
# 시스템 메트릭 조회
curl -X GET http://127.0.0.1:5000/api/monitoring/metrics

# 알림 프로필 생성
curl -X POST http://127.0.0.1:5000/api/notifications/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "야간모드",
    "config": {
      "channels": {"web": {"enabled": true, "sound": false}},
      "triggers": {"pair_detected": {"enabled": true}},
      "schedule": {"quiet_hours": {"start": "22:00", "end": "08:00"}}
    }
  }'

# 카지노 연결
curl -X POST http://127.0.0.1:5000/api/casinos/main_casino/connect

# 최근 게임 데이터 조회
curl -X GET "http://127.0.0.1:5000/api/data/games/recent?limit=5&casino_id=main_casino"

# 시스템 설정 업데이트
curl -X PUT http://127.0.0.1:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "ai": {"confidence_threshold": 0.8},
    "database": {"cleanup_days": 60}
  }'
```

---

## 📞 지원 및 피드백

- **GitHub Issues**: [프로젝트 이슈 페이지](https://github.com/your-repo/issues)
- **API 문제 신고**: [API 전용 이슈](https://github.com/your-repo/issues/new?template=api-bug.md)
- **기능 요청**: [새 기능 제안](https://github.com/your-repo/issues/new?template=feature-request.md)

---

**📅 마지막 업데이트**: 2025-08-25  
**📖 API 버전**: v3.0  
**🔄 다음 버전**: v3.1 (예정)