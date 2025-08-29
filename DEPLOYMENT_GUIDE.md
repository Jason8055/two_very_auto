# Two Very Auto - 최종 배포 가이드

## 🚀 시스템 개요

Two Very Auto는 카지노 바카라 게임 데이터를 실시간으로 모니터링하고 자동 백업하는 완전한 엔터프라이즈급 시스템입니다.

### ✅ 완성된 주요 기능

#### 🔄 **자동 백업 시스템**
- **멀티 클라우드 지원**: AWS S3, Google Cloud Storage, Azure Blob Storage
- **로컬 백업**: 빠른 접근을 위한 로컬 스토리지
- **자동 압축 및 암호화**: 안전하고 효율적인 데이터 저장
- **스케줄링**: 일일/주간/월간 자동 백업

#### 🏥 **백업 건전성 관리**
- **무결성 검사**: SHA256 해시 기반 파일 검증
- **자동 복원 테스트**: 정기적인 백업 유효성 확인
- **데이터베이스 구조 검증**: SQLite 스키마 및 데이터 완전성
- **성능 벤치마킹**: 복원 시간 및 처리량 측정

#### 📢 **통합 알림 시스템**  
- **다채널 지원**: 이메일, Slack, Discord, Microsoft Teams
- **레벨별 라우팅**: 성공/경고/오류/위험에 따른 차별적 알림
- **스팸 방지**: 쿨다운 관리 및 알림 빈도 제어
- **Rich 메시지**: HTML 이메일, Embed 카드 지원

#### 🔍 **통합 모니터링**
- **실시간 상태 감시**: 디스크 공간, 백업 상태, SSL 인증서
- **자동 복구**: 디스크 정리, 긴급 백업 등 자동 액션
- **상세 리포팅**: JSON 기반 구조화된 상태 보고서
- **스케줄링**: 시간별/일별 자동 점검

#### 📊 **웹 대시보드**
- **실시간 모니터링 UI**: 시스템 상태, 백업 히스토리, 로그
- **WebSocket 통신**: 실시간 상태 업데이트
- **수동 제어**: 백업 실행, 건전성 점검, 알림 테스트
- **반응형 디자인**: 모바일 및 데스크톱 완전 지원

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Two Very Auto v3.0                         │
├─────────────────────────────────────────────────────────────────┤
│  📊 웹 대시보드 (FastAPI + WebSocket)                             │
│  ├── 실시간 상태 모니터링                                           │
│  ├── 백업 관리 인터페이스                                           │  
│  ├── 건전성 점검 및 테스트                                          │
│  └── 시스템 로그 및 히스토리                                        │
├─────────────────────────────────────────────────────────────────┤
│  🔄 백업 엔진                                                     │
│  ├── 클라우드 백업 매니저 (AWS/GCP/Azure)                          │
│  ├── 로컬 백업 매니저                                             │
│  ├── 압축 및 암호화 (gzip + AES-256)                             │
│  └── Windows 작업 스케줄러 통합                                   │
├─────────────────────────────────────────────────────────────────┤
│  🏥 건전성 관리                                                   │
│  ├── 백업 무결성 검증 (SHA256)                                    │
│  ├── 자동 복원 테스트                                             │
│  ├── 데이터베이스 구조 점검                                        │
│  └── 성능 벤치마킹                                               │
├─────────────────────────────────────────────────────────────────┤
│  📢 알림 시스템                                                   │
│  ├── 이메일 (SMTP with HTML)                                    │
│  ├── Slack (Webhook + Rich Cards)                             │
│  ├── Discord (Webhook + Embeds)                               │
│  └── Teams (Adaptive Cards)                                   │
├─────────────────────────────────────────────────────────────────┤
│  🔍 통합 모니터링                                                 │
│  ├── 백업 상태 감시                                              │
│  ├── SSL 인증서 관리                                             │
│  ├── 디스크 공간 모니터링                                         │
│  └── 자동 복구 액션                                              │
├─────────────────────────────────────────────────────────────────┤
│  💾 데이터 소스                                                   │
│  ├── SQLite 게임 데이터베이스                                      │
│  ├── 패킷 데이터 히스토리                                          │
│  └── 시스템 설정 및 로그                                          │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 설치 및 배포

### 1. 시스템 요구사항

#### 최소 요구사항
- **OS**: Windows 10/11 (64bit)
- **Python**: 3.8 이상 (권장: 3.9+)
- **RAM**: 4GB 이상 (권장: 8GB)
- **디스크**: 10GB 여유 공간
- **네트워크**: 인터넷 연결 (클라우드 백업용)

#### 권장 사양
- **OS**: Windows 11 (64bit)
- **Python**: 3.11+
- **RAM**: 16GB
- **디스크**: SSD 50GB 여유 공간
- **네트워크**: 안정적인 광대역 인터넷

### 2. 빠른 시작 (원클릭 배포)

```batch
# 1. 저장소 복제
git clone https://github.com/Jason8055/two_very_auto.git
cd two_very_auto

# 2. 의존성 설치
pip install fastapi uvicorn aiohttp schedule tqdm python-dateutil
pip install boto3 google-cloud-storage azure-storage-blob  # 클라우드 백업용

# 3. 대시보드 실행
python run_dashboard.py
```

### 3. 상세 설정

#### 3.1 환경 변수 설정 (.env)

```env
# AWS 설정
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-northeast-2
AWS_BUCKET_NAME=two-very-auto-backups

# Google Cloud 설정
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
GCP_BUCKET_NAME=two-very-auto-backups-gcp
GCP_PROJECT_ID=your-project-id

# Azure 설정
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
AZURE_STORAGE_ACCOUNT_KEY=your_account_key
AZURE_CONTAINER_NAME=two-very-auto-backups

# 보안 설정
BACKUP_ENCRYPTION_KEY=your_32_character_encryption_key
```

#### 3.2 알림 설정 (notification_config.json)

```json
{
  "enabled": true,
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipients": ["admin@company.com"]
  },
  "slack": {
    "enabled": true,
    "webhook_url": "https://hooks.slack.com/services/...",
    "channel": "#backups"
  }
}
```

#### 3.3 백업 스케줄 설정 (backup_schedule_config.json)

```json
{
  "enabled": true,
  "schedules": {
    "daily_backup": {
      "enabled": true,
      "time": "02:00",
      "configs": ["local_backup", "aws_primary"]
    },
    "weekly_full_backup": {
      "enabled": true,
      "day": "sunday", 
      "time": "01:00",
      "configs": ["local_backup", "aws_primary", "gcp_secondary"]
    }
  }
}
```

## 🚀 실행 방법

### 1. 대시보드 서버 실행

#### 방법 1: 간단한 대시보드 (권장)
```bash
python run_dashboard.py
```
- 자동 포트 탐지 (8000번대)
- 브라우저 자동 실행
- 시스템 상태 실시간 표시

#### 방법 2: 완전한 FastAPI 대시보드
```bash
python dashboard_server.py
```
- 포트: 8888
- 전체 API 엔드포인트
- WebSocket 실시간 통신

### 2. 백업 시스템 실행

#### 수동 백업
```bash
# 로컬 백업
python -c "from cloud.backup_manager import get_backup_manager; print(get_backup_manager().backup_database('local_backup'))"

# 모든 설정으로 백업
python -c "from cloud.backup_manager import get_backup_manager; print(get_backup_manager().backup_all_configs())"
```

#### 건전성 점검
```bash
python backup_health_checker.py
```

#### 통합 모니터링 시작
```bash
# 통합 모니터링 시작
python integrated_monitoring.py --start

# 개별 점검 실행
python integrated_monitoring.py --health-check  # 백업 건전성
python integrated_monitoring.py --ssl-check     # SSL 인증서
python integrated_monitoring.py --disk-check    # 디스크 공간
```

### 3. 알림 시스템 테스트

```bash
python -c "
import asyncio
from notification_system import get_notification_system
notification = get_notification_system()
asyncio.run(notification.send_test_notification())
"
```

## 📊 대시보드 사용법

### 접속 방법
1. 브라우저에서 `http://localhost:8000` 또는 `http://localhost:8888` 접속
2. 실시간 상태 모니터링 화면 확인

### 주요 기능
- **💾 수동 백업**: 즉시 백업 실행
- **🏥 건전성 점검**: 백업 무결성 검사
- **📢 알림 테스트**: 모든 채널 알림 테스트
- **🔄 새로고침**: 상태 정보 업데이트

### 키보드 단축키
- `Ctrl + R`: 새로고침
- `Ctrl + B`: 백업 실행
- `Ctrl + H`: 건전성 점검

## 🔧 고급 설정

### Windows 작업 스케줄러 설정

관리자 권한으로 실행:
```batch
setup_windows_scheduler.bat
```

### 클라우드 인증 설정

```bash
python cloud_auth_setup.py
```

### SSL 인증서 모니터링

```bash
python ssl_cert_manager.py
```

## 📁 프로젝트 구조

```
F:\two very auto 25.08.23\
├── 📊 대시보드
│   ├── dashboard_server.py              # FastAPI 대시보드 서버
│   ├── run_dashboard.py                 # 간단한 HTTP 대시보드
│   ├── templates/backup_dashboard.html   # 웹 UI 템플릿
│   └── static/dashboard.css             # CSS 스타일

├── ☁️ 클라우드 백업
│   ├── cloud/backup_manager.py          # 클라우드 백업 매니저
│   ├── cloud/restore_system.py          # 백업 복원 시스템
│   └── cloud/secure_config_manager.py   # 보안 설정 관리

├── 🏥 건전성 관리
│   ├── backup_health_checker.py         # 백업 건전성 점검
│   └── backup_health_reports/           # 점검 보고서

├── 📢 알림 시스템
│   ├── notification_system.py           # 통합 알림 시스템
│   └── notification_config.json         # 알림 설정

├── 🔍 모니터링
│   ├── integrated_monitoring.py         # 통합 모니터링
│   ├── ssl_cert_manager.py             # SSL 관리
│   └── monitoring_config.json          # 모니터링 설정

├── ⏰ 스케줄링
│   ├── backup_scheduler.py              # 백업 스케줄러
│   ├── windows_task_scheduler.py        # Windows 스케줄러
│   └── setup_windows_scheduler.bat      # 스케줄러 설정

├── 🔧 설정 도구
│   ├── setup_complete_backup_system.py  # 전체 시스템 설정
│   ├── cloud_auth_setup.py             # 클라우드 인증 설정
│   └── install_backup_dependencies.bat  # 의존성 설치

└── 📋 문서
    ├── BACKUP_SYSTEM_README.md          # 시스템 개요
    ├── DEPLOYMENT_GUIDE.md              # 배포 가이드 (본 파일)
    └── setup_completion_report.json     # 설정 완료 보고서
```

## 🔧 문제 해결

### 일반적인 문제

#### 1. 포트 충돌
```bash
# 다른 포트로 실행
python run_dashboard.py  # 자동 포트 탐지
```

#### 2. 클라우드 인증 실패
```bash
# 환경 변수 확인
echo %AWS_ACCESS_KEY_ID%

# 권한 확인
aws sts get-caller-identity
```

#### 3. 데이터베이스 백업 실패
- 데이터베이스 파일 경로 확인
- 읽기 권한 확인
- 디스크 공간 확인

#### 4. 알림 전송 실패
- SMTP 설정 확인 (Gmail: 앱 비밀번호 사용)
- Webhook URL 유효성 확인
- 네트워크 연결 확인

### 로그 위치
- **백업 로그**: `backup_scheduler.log`
- **모니터링 로그**: `integrated_monitoring.log`
- **건전성 점검**: `backup_health_reports/`
- **백업 히스토리**: `backup_history.json`

## 📈 성능 지표

### 백업 성능
- **로컬 백업**: ~0.4MB 파일 기준 < 1초
- **클라우드 업로드**: 네트워크 속도에 따라 가변
- **압축률**: 평균 30-50% 크기 감소
- **암호화 오버헤드**: < 5% 성능 영향

### 복원 성능
- **로컬 복원**: < 5초 (1MB 파일 기준)
- **클라우드 다운로드**: 네트워크 환경에 따라 가변
- **검증 시간**: < 10초 (종합 건전성 점검)

### 모니터링 성능
- **점검 주기**: 시간별/일별 설정 가능
- **알림 지연**: < 30초
- **리소스 사용량**: 메모리 < 100MB, CPU < 5%

## 🛡️ 보안 고려사항

### 데이터 보호
- **전송 중 암호화**: HTTPS/TLS 1.2+
- **저장 중 암호화**: AES-256
- **키 관리**: 환경변수 기반 분리 저장
- **접근 제어**: IAM 역할 기반 최소 권한

### 네트워크 보안
- **방화벽 호환**: 표준 HTTPS 포트 사용
- **VPN 지원**: 기업 네트워크 환경 호환
- **인증서 관리**: 자동 SSL 만료 추적

### 운영 보안
- **로그 관리**: 민감 정보 마스킹
- **감사 추적**: 모든 백업/복원 작업 기록
- **장애 복구**: 자동 백업 무결성 검증

## 🚀 다음 단계

### 운영 환경 배포
1. **프로덕션 설정**: 환경 변수 및 보안 설정 검토
2. **모니터링 활성화**: 24/7 모니터링 시스템 구축
3. **백업 스케줄**: 업무 환경에 맞는 백업 주기 설정
4. **알림 채널**: 운영팀 알림 채널 설정

### 확장 가능성
1. **다중 데이터베이스**: 여러 데이터베이스 동시 백업
2. **분산 백업**: 지역별 백업 센터 구축
3. **API 통합**: 외부 시스템과의 API 연동
4. **로그 분석**: ELK 스택 연동 고급 분석

## 📞 지원 및 유지보수

### 정기 유지보수 체크리스트
- **일간**: 대시보드 상태 확인, 백업 성공 여부 점검
- **주간**: 건전성 점검 리포트 검토, 디스크 공간 관리
- **월간**: SSL 인증서 갱신 확인, 성능 지표 분석
- **분기**: 클라우드 비용 최적화, 보안 설정 검토

### 업그레이드 절차
1. 현재 설정 백업: `cp *.json config_backup/`
2. 새 버전 다운로드: `git pull origin main`
3. 의존성 업데이트: `pip install -r requirements.txt --upgrade`
4. 설정 검증: `python setup_complete_backup_system.py`
5. 테스트 실행: 백업 및 복원 테스트

---

**Two Very Auto v3.0** - 완전한 엔터프라이즈급 자동 백업 시스템  
© 2025 Two Very Auto Team

🎰 **카지노 데이터의 안전한 보호와 실시간 모니터링을 위한 최고의 솔루션**