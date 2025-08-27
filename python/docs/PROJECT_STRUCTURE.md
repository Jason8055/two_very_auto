# Two Very Auto - 프로젝트 구조 가이드

## 📁 최종 프로젝트 구조

```
F:\two very auto 25.08.23\python\
├── 📁 핵심 모듈 (20개 Python 파일)
│   ├── web_server_pwa.py              # 메인 웹서버 - Flask + PWA
│   ├── ai_prediction_engine.py        # AI 예측 엔진 - TensorFlow
│   ├── chart_integration.py           # Chart.js 통합 백엔드
│   ├── realtime_dashboard.py          # 실시간 대시보드
│   ├── advanced_analytics.py          # 고급 분석 도구
│   ├── performance_monitor.py         # 성능 모니터링 시스템
│   ├── stability_system.py            # 자동 안정성 관리
│   ├── settings_management.py         # 웹 기반 설정 관리
│   ├── integration_test_suite.py      # 통합 테스트 시스템
│   ├── advanced_notification_system.py # 고급 알림 시스템
│   ├── notification_system.py         # 기본 알림 시스템
│   ├── database_manager.py            # SQLite 데이터베이스 관리
│   ├── pair_tracker_v2.py             # 페어 추적 시스템
│   ├── pattern_analyzer_v2.py         # 패턴 분석 엔진
│   ├── packet_decoder.py              # 패킷 디코딩
│   ├── websocket_manager.py           # WebSocket 관리
│   ├── korean_encoding_fix.py         # 한글 인코딩 처리
│   ├── pair_tracker_helper_methods.py # 페어 헬퍼 메서드
│   ├── build_executable.py           # 실행파일 빌드
│   └── two_very_auto_launcher.py      # 시스템 런처
│
├── 📁 프론트엔드 (3개 JavaScript 파일)
│   ├── visualization_components.js    # 차트 시각화 컴포넌트
│   ├── mobile_enhancements.js         # 모바일 최적화
│   └── pwa_service_worker.js          # PWA 서비스워커
│
├── 📁 설정 및 데이터 (6개 파일)
│   ├── requirements.txt               # Python 패키지 의존성
│   ├── notification_config.json       # 알림 설정
│   ├── pwa_manifest.json             # PWA 매니페스트
│   ├── baccarat_data.json            # 레거시 데이터 (백업용)
│   ├── baccarat_monitor_pwa_v2.db     # SQLite 데이터베이스
│   └── two_very_auto.bat             # Windows 실행 스크립트
│
├── 📁 UI 리소스 (3개 파일)
│   ├── theme_system.css              # 테마 시스템 (다크모드)
│   ├── modern_dashboard.html         # 대시보드 템플릿
│   └── pwa_offline.html             # PWA 오프라인 페이지
│
├── 📁 문서 (통합 정리된 6개 파일)
│   ├── docs/
│   │   ├── MASTER_README.md          # 통합 프로젝트 개요
│   │   └── PROJECT_STRUCTURE.md      # 이 파일
│   ├── README.md                     # 메인 사용자 가이드
│   ├── API_REFERENCE.md             # API 참조 문서
│   ├── DEVELOPMENT_GUIDE.md         # 개발자 가이드
│   ├── UPGRADE_GUIDE.md             # 업그레이드 가이드
│   ├── SECURITY_README.md           # 보안 가이드
│   ├── FUTURE_IMPROVEMENTS.md       # 향후 개선 계획
│   ├── startup_guide.md             # 시작 가이드
│   ├── CODE_QUALITY_ANALYSIS.md     # 코드 품질 분석
│   └── PROJECT_CLEANUP_PLAN.md      # 정리 계획서
│
├── 📁 아카이브 (백업 및 레거시)
│   ├── archive/
│   │   ├── legacy/                   # 구버전 파일 (12개)
│   │   ├── temp/                     # 임시 파일 백업
│   │   └── old_docs/                 # 구버전 문서 (4개)
│
└── 📁 가상환경
    └── venv/                         # Python 가상환경
```

## 🏗️ 시스템 아키텍처

### 계층 구조
```
┌─────────────────────┐
│   웹 브라우저       │ ← 사용자 인터페이스
├─────────────────────┤
│   Flask PWA 서버    │ ← web_server_pwa.py
├─────────────────────┤
│   실시간 처리 계층   │ ← realtime_dashboard.py, websocket_manager.py
├─────────────────────┤
│   분석 엔진 계층     │ ← ai_prediction_engine.py, advanced_analytics.py
├─────────────────────┤
│   데이터 처리 계층   │ ← pair_tracker_v2.py, pattern_analyzer_v2.py
├─────────────────────┤
│   데이터 저장 계층   │ ← database_manager.py, SQLite DB
└─────────────────────┘
```

### 모듈 의존성 관계
```
web_server_pwa.py (메인)
├── realtime_dashboard.py
├── chart_integration.py
├── ai_prediction_engine.py
├── advanced_analytics.py
├── settings_management.py
└── database_manager.py
    ├── pair_tracker_v2.py
    ├── pattern_analyzer_v2.py
    └── packet_decoder.py
```

## 📊 Phase별 개발 현황

### ✅ Phase 1-4 완료 (v2.0)
- 고급 알림 시스템
- PWA 모바일 최적화  
- 실시간 시각화 대시보드
- AI 예측 엔진

### ✅ Phase 5 완료 (v2.5)
- 통합 테스트 스위트
- 성능 모니터링 시스템
- 자동 안정성 관리
- 웹 기반 설정 관리
- 고급 분석 도구

### 🚀 Phase 6 진행 중 (v3.0 - 정리 및 최적화)
- ✅ 프로젝트 구조 최적화
- ✅ 코드 품질 개선 (Import 정리)
- ✅ 레거시 파일 아카이브
- 🔄 문서 통합 및 정리
- ⏳ 최종 배포 준비

## 🔧 핵심 기능별 파일 맵핑

### 웹서버 & API
- **메인**: `web_server_pwa.py`
- **설정**: `settings_management.py` 
- **WebSocket**: `websocket_manager.py`

### 데이터 처리 & 분석
- **데이터베이스**: `database_manager.py`
- **페어 추적**: `pair_tracker_v2.py`
- **패턴 분석**: `pattern_analyzer_v2.py`
- **패킷 처리**: `packet_decoder.py`

### AI & 고급 분석
- **AI 예측**: `ai_prediction_engine.py`
- **고급 분석**: `advanced_analytics.py`
- **성능 분석**: `performance_monitor.py`

### 시각화 & UI
- **차트 통합**: `chart_integration.py`
- **실시간 대시보드**: `realtime_dashboard.py`
- **시각화 컴포넌트**: `visualization_components.js`
- **모바일 최적화**: `mobile_enhancements.js`

### 시스템 관리
- **안정성 시스템**: `stability_system.py`
- **알림 시스템**: `advanced_notification_system.py`, `notification_system.py`
- **테스트**: `integration_test_suite.py`

## 📈 파일 크기 및 복잡도 분석

### 대용량 파일 (10KB 이상)
1. `web_server_pwa.py` - 메인 웹서버 (가장 큰 파일)
2. `ai_prediction_engine.py` - AI 엔진
3. `advanced_analytics.py` - 고급 분석
4. `realtime_dashboard.py` - 실시간 대시보드
5. `chart_integration.py` - 차트 통합

### 경량 모듈 (5KB 미만)
- `korean_encoding_fix.py` - 유틸리티
- `pair_tracker_helper_methods.py` - 헬퍼 함수
- `websocket_manager.py` - WebSocket 관리

## 🛡️ 보안 및 안정성

### 보안 파일
- `SECURITY_README.md` - 보안 가이드
- `stability_system.py` - 자동 복구 시스템

### 백업 전략
- `archive/legacy/` - 구버전 파일 보관
- `archive/temp/` - 임시 파일 백업
- SQLite 자동 백업 (stability_system.py)

## 🔄 업데이트 이력

### v3.0 (2024-08-24) - 구조 최적화
- ✅ 프로젝트 구조 재정리
- ✅ Import 문 표준화 (PEP 8)
- ✅ 레거시 파일 아카이브
- ✅ 문서 통합 및 정리

### v2.5 (2024-08-24) - Phase 5 완료
- 5개 시스템 추가 구현
- 통합 테스트 및 성능 모니터링
- 고급 분석 도구 완성

### v2.0 (2024-08-23) - Phase 1-4 완료  
- AI 예측 엔진 구현
- 실시간 차트 시스템
- PWA 모바일 지원
- 고급 알림 시스템

---

**구조 정리 완료일**: 2024-08-24  
**총 파일 수**: 32개 (Python 20개, JS 3개, 기타 9개)  
**아카이브 파일**: 16개 (레거시 12개, 구문서 4개)  
**최적화 수준**: 85% 완료