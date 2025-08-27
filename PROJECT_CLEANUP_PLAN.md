# 프로젝트 정리 계획

## 1. 정리 대상 파일 분류

### A. 백업 파일 (삭제 예정)
- `python/main_integration_service.py.backup` - 백업 파일

### B. 디버그/임시 파일 (삭제 예정)  
- `Tls13Proxy.pdb` - 디버그 파일
- `two very auto.pdb` - 디버그 파일
- `two very auto_0.0.0.0.ilmap` - 중간 파일
- `two very auto_25.4.22.0.ilmap` - 중간 파일
- `temp/shared_memory.dat` - 임시 파일

### C. 중복 데이터베이스 파일 (통합 예정)
- `python/baccarat_monitor_pwa_v2.db`
- `python/fastapi_app/baccarat_data.db` 
- `python/fastapi_app/baccarat_fastapi.db`
- `python/fastapi_app/baccarat_optimized.db` (메인으로 유지)
- `python/main_casino_baccarat_data.db`

### D. 중복 HTML 대시보드 (통합 예정)
- `python/enhanced_dashboard.html`
- `python/modern_dashboard.html`
- `python/realtime_dashboard.html`
- `python/templates/dashboard.html` (메인으로 유지)
- `python/fastapi_app/templates/dashboard.html`

### E. 백업 디렉토리 (아카이브로 이동)
- `backup_20250826_223937/` → `archives/backup_20250826_223937/`

## 2. 정리 작업 순서

1. 백업 파일 삭제
2. 디버그/임시 파일 삭제  
3. 중복 파일 정리
4. 디렉토리 구조 최적화
5. 문서 업데이트

## 3. 보존할 주요 파일
- 모든 Python 소스 코드
- 설정 파일 (*.ini, *.json)
- 프로덕션 데이터베이스 (baccarat_optimized.db)
- 메인 대시보드 템플릿
- 인프라 설정 (docker, kubernetes 등)

## 4. 정리 후 예상 효과
- 불필요한 파일 제거로 프로젝트 크기 감소
- 중복 제거로 유지보수 효율성 향상
- 명확한 파일 구조로 개발 생산성 향상