# 🚀 Two Very Auto 개발 연속 계획서

**생성 일시**: 2025-08-27 16:15 KST  
**토큰 상태**: 6% 남음 → 다음 세션 연속 개발용  
**현재 상황**: 요구사항 분석 완료, 구현 준비 완료  

---

## 📋 현재까지 완료된 작업

### ✅ 완료된 분석 작업
1. **전체 프로젝트 헬스체크** 완료 → `PROJECT_HEALTH_REPORT.md`
2. **요구사항 vs 구현 분석** 완료 → `REQUIREMENTS_ANALYSIS_REPORT.md`
3. **거버넌스 프레임워크** 완료 (16개 파일 구축)
4. **문제점 식별 및 우선순위** 설정 완료

### 🎯 핵심 발견사항
- **전체 완성도**: 65% (기반 인프라 우수, 핵심 기능 미완성)
- **주요 문제점**: 카드 상세정보 부족, 실시간 출력 부재, 페어 로직 불일치
- **즉시 해결 가능**: 기존 데이터로 실시간 알림 시스템 구현

---

## 🎯 다음 세션 즉시 실행 계획

### Phase 1: 긴급 수정 (첫 30분)

#### 1.1 실시간 페어 알림 시스템 구현 🚨
```python
# 파일: python/realtime_pair_notifier.py (신규 생성)
"""
즉시 구현할 실시간 페어 알림 시스템
기존 페어 정보(playerPair, bankerPair)를 활용한 즉시 출력
"""

import asyncio
import websockets
from datetime import datetime
from typing import Dict, List, Any
import json

class RealTimePairNotifier:
    def __init__(self):
        self.websocket_clients = set()
        self.is_running = False
        
    async def notify_pair_detected(self, table_name: str, pair_type: str, game_data: Dict):
        """페어 발견 시 즉시 알림 - 최우선 구현"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 1. 콘솔 실시간 출력 (요구사항 충족)
        print(f"🎴 {timestamp} | 방: {table_name} | {pair_type} 페어 발견!")
        print(f"   게임 #{game_data.get('gameCount', 'N/A')}")
        print(f"   Player: {game_data.get('playerScore', 'N/A')} | Banker: {game_data.get('bankerScore', 'N/A')}")
        print("   " + "="*50)
        
        # 2. WebSocket 실시간 푸시
        message = {
            "type": "PAIR_DETECTED",
            "timestamp": timestamp,
            "table": table_name,
            "pair_type": pair_type,
            "game_data": game_data
        }
        
        await self._broadcast_to_clients(message)
        
        # 3. 로그 파일 저장
        self._log_pair_event(table_name, pair_type, game_data)
    
    async def _broadcast_to_clients(self, message: Dict):
        """WebSocket 클라이언트들에게 브로드캐스트"""
        if self.websocket_clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.websocket_clients],
                return_exceptions=True
            )
```

#### 1.2 기존 페어 추적 시스템 연결
```python
# 파일: python/pair_tracker_v2.py (수정)
# 기존 파일에 실시간 알림 연결

from realtime_pair_notifier import RealTimePairNotifier

class PairTrackerV2:
    def __init__(self, db_path: str = "baccarat_monitor.db"):
        # 기존 코드...
        self.notifier = RealTimePairNotifier()  # 추가
        
    async def process_game_data(self, game_data: Dict, table_name: str):
        """게임 데이터 처리 시 실시간 알림 추가"""
        
        # 기존 페어 검출 로직
        if game_data.get('playerPair'):
            await self.notifier.notify_pair_detected(table_name, "Player Pair", game_data)
            
        if game_data.get('bankerPair'):
            await self.notifier.notify_pair_detected(table_name, "Banker Pair", game_data)
        
        # 기존 DB 저장 로직 유지...
```

### Phase 2: 핵심 기능 완성 (30-90분)

#### 2.1 실시간 대시보드 HTML 구현
```html
<!-- 파일: python/templates/realtime_pairs_dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>🎴 실시간 페어 모니터링</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        .pair-alert { 
            background: #ff6b6b; 
            color: white; 
            padding: 15px; 
            margin: 5px 0; 
            border-radius: 8px;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateX(-100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .table-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .table-card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; }
    </style>
</head>
<body>
    <h1>🎴 Two Very Auto - 실시간 페어 모니터링</h1>
    
    <div id="pair-alerts">
        <h2>🚨 실시간 페어 알림</h2>
        <div id="alerts-container"></div>
    </div>
    
    <div id="table-status">
        <h2>📊 테이블 현황</h2>
        <div id="tables-container" class="table-status"></div>
    </div>
    
    <script>
        const ws = new WebSocket('ws://localhost:8000/ws/pairs');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'PAIR_DETECTED') {
                addPairAlert(data);
                updateTableStatus(data.table, data);
            }
        };
        
        function addPairAlert(data) {
            const alertsContainer = document.getElementById('alerts-container');
            const alert = document.createElement('div');
            alert.className = 'pair-alert';
            alert.innerHTML = `
                <strong>${data.timestamp}</strong> | 방: ${data.table} | ${data.pair_type} 발견!<br>
                게임 #${data.game_data.gameCount} | Player: ${data.game_data.playerScore} | Banker: ${data.game_data.bankerScore}
            `;
            alertsContainer.insertBefore(alert, alertsContainer.firstChild);
            
            // 최대 10개 알림만 유지
            while (alertsContainer.children.length > 10) {
                alertsContainer.removeChild(alertsContainer.lastChild);
            }
        }
    </script>
</body>
</html>
```

#### 2.2 FastAPI 엔드포인트 추가
```python
# 파일: python/fastapi_app/main.py (수정)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from realtime_pair_notifier import RealTimePairNotifier

app = FastAPI()
notifier = RealTimePairNotifier()

@app.websocket("/ws/pairs")
async def websocket_endpoint(websocket: WebSocket):
    """실시간 페어 알림 WebSocket"""
    await websocket.accept()
    notifier.websocket_clients.add(websocket)
    
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        notifier.websocket_clients.remove(websocket)

@app.get("/dashboard/pairs")
async def pairs_dashboard():
    """페어 모니터링 대시보드 페이지"""
    with open("templates/realtime_pairs_dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
```

### Phase 3: 통합 및 테스트 (90-120분)

#### 3.1 통합 테스트 스크립트
```python
# 파일: python/test_realtime_pairs.py
"""실시간 페어 시스템 통합 테스트"""

async def test_realtime_pair_system():
    # 1. 기존 packet 파일에서 페어 데이터 찾기
    # 2. 실시간 알림 시스템 테스트  
    # 3. WebSocket 연결 테스트
    # 4. 대시보드 렌더링 테스트
    pass

if __name__ == "__main__":
    asyncio.run(test_realtime_pair_system())
```

---

## 📚 필요한 리소스 및 참고사항

### 기존 파일 위치
```
핵심 파일들:
├── python/pair_tracker_v2.py          # 페어 추적 메인 로직
├── python/enhanced_packet_decoder.py  # 패킷 디코딩
├── python/realtime_packet_monitor.py  # 실시간 모니터링
├── python/fastapi_app/main.py         # FastAPI 메인
└── packet/20250810/바카라 A_10.txt    # 샘플 데이터

분석 결과 문서들:
├── PROJECT_HEALTH_REPORT.md           # 전체 프로젝트 상태
├── REQUIREMENTS_ANALYSIS_REPORT.md    # 요구사항 분석
└── GOVERNANCE_IMPLEMENTATION_SUMMARY.md  # 거버넌스 현황
```

### 핵심 데이터 구조 참고
```json
// packet 파일 내 JSON 구조 (참고용)
{
  "type": "baccarat.encodedShoeState",
  "args": {
    "stats": {
      "gameCount": 21,
      "playerWins": 11,
      "bankerWins": 9,
      "playerPairs": 1,
      "bankerPairs": 2
    },
    "history_v2": [
      {
        "winner": "Player",
        "playerScore": 8,
        "bankerScore": 4,
        "playerPair": true,    // ← 이 필드 활용
        "bankerPair": false
      }
    ],
    "tableId": "oytmvb9m1zysmc44"
  }
}
```

---

## 🎯 다음 세션 목표

### 즉시 달성 목표 (2시간 내)
1. ✅ **실시간 페어 알림** → 콘솔 출력 시스템 구현
2. ✅ **WebSocket 기반** → 실시간 대시보드 연결  
3. ✅ **기존 시스템 통합** → 페어 추적과 알림 연결
4. ✅ **기본 테스트** → 동작 확인

### 최종 사용자 경험
```
🎴 16:23:45 | 방: 바카라 A | Player Pair 페어 발견!
   게임 #24
   Player: 8 | Banker: 4
   ==================================================

🎴 16:24:12 | 방: 스피드 바카라 1 | Banker Pair 페어 발견!
   게임 #157  
   Player: 6 | Banker: 7
   ==================================================
```

---

## 🚀 실행 명령어 (다음 세션 시작 시)

```bash
# 1. 개발 환경 활성화
cd "F:\two very auto 25.08.23"
pip install -e ".[dev,test]"

# 2. 실시간 페어 시스템 구현 시작
# /sc:implement 실시간 페어 알림 시스템 --type feature --framework fastapi

# 3. 테스트 및 검증
python python/test_realtime_pairs.py

# 4. 대시보드 확인
# http://localhost:8000/dashboard/pairs
```

---

**✨ 다음 세션에서 바로 핵심 기능 구현에 집중할 수 있도록 모든 준비가 완료되었습니다!**

**우선순위**: 실시간 알림 → WebSocket 연결 → 대시보드 → 테스트 → 최적화