# Two Very Auto - 엔터프라이즈 백업 시스템

## 📋 개요

Two Very Auto는 카지노 바카라 게임 데이터를 실시간으로 모니터링하고 자동 백업하는 종합적인 엔터프라이즈급 시스템입니다. 클라우드 멀티 백업, 자동 복원 테스트, 통합 모니터링, 실시간 알림 기능을 제공합니다.

## 🚀 주요 기능

### 🔄 자동 백업 시스템
- **멀티 클라우드 백업**: AWS S3, Google Cloud, Azure Blob Storage 지원
- **로컬 백업**: 빠른 접근을 위한 로컬 스토리지 백업
- **스케줄링**: 일일/주간/월간 자동 백업
- **압축 및 암호화**: 안전하고 효율적인 데이터 저장

### 🏥 백업 건전성 관리
- **무결성 검사**: SHA256 해시 기반 파일 검증
- **자동 복원 테스트**: 정기적인 백업 유효성 확인
- **데이터베이스 구조 검증**: SQLite 스키마 및 데이터 완전성 확인
- **성능 벤치마킹**: 복원 시간 및 처리량 측정

### 📢 통합 알림 시스템
- **다채널 지원**: 이메일, Slack, Discord, Microsoft Teams
- **레벨별 라우팅**: 성공/경고/오류/위험에 따른 차별적 알림
- **쿨다운 관리**: 스팸 방지 및 알림 빈도 제어
- **Rich 메시지**: HTML 이메일, Embed 카드 지원

### 🔍 통합 모니터링
- **시스템 상태 감시**: 디스크 공간, 백업 상태, SSL 인증서
- **실시간 알림**: 문제 발생 시 즉시 알림
- **자동 복구**: 디스크 정리, 긴급 백업 등 자동 액션
- **상세 리포팅**: JSON 기반 구조화된 상태 보고서

### 🔐 보안 관리
- **환경변수 기반 설정**: 민감한 정보 안전 관리
- **SSL 인증서 모니터링**: 만료 추적 및 갱신 알림
- **암호화 키 관리**: 자동 생성 및 순환
- **접근 권한 제어**: 최소 권한 원칙 적용

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Two Very Auto 백업 시스템                      │
├─────────────────────────────────────────────────────────────────┤
│  📊 FastAPI 대시보드                                              │
│  ├── 실시간 모니터링 UI                                           │
│  ├── 백업 상태 관리                                              │
│  └── 알림 설정 관리                                              │
├─────────────────────────────────────────────────────────────────┤
│  🔄 백업 엔진                                                     │
│  ├── 클라우드 백업 매니저 (AWS/GCP/Azure)                          │
│  ├── 로컬 백업 매니저                                             │
│  ├── 압축 및 암호화                                              │
│  └── 스케줄링 엔진                                               │
├─────────────────────────────────────────────────────────────────┤
│  🏥 건전성 관리                                                   │
│  ├── 백업 건전성 점검기                                           │
│  ├── 자동 복원 테스트                                             │
│  ├── 무결성 검증                                                 │
│  └── 성능 벤치마킹                                               │
├─────────────────────────────────────────────────────────────────┤
│  📢 알림 시스템                                                   │
│  ├── 이메일 (SMTP)                                               │
│  ├── Slack (Webhook)                                            │
│  ├── Discord (Webhook)                                          │
│  └── Teams (Webhook)                                            │
├─────────────────────────────────────────────────────────────────┤
│  🔍 모니터링 시스템                                               │
│  ├── 시스템 상태 감시                                             │
│  ├── SSL 인증서 관리                                              │
│  ├── 디스크 공간 모니터링                                          │
│  └── 자동 복구 액션                                              │
├─────────────────────────────────────────────────────────────────┤
│  💾 데이터 소스                                                   │
│  ├── SQLite 게임 데이터베이스                                      │
│  ├── 패킷 데이터 히스토리                                          │
│  └── 시스템 로그                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 설치 및 설정

### 전체 시스템 자동 설정
```bash
# 원클릭 설정 (권장)
python setup_complete_backup_system.py
```

### 개별 구성 요소 설정

#### 1. 의존성 설치
```bash
# 클라우드 백업 라이브러리
pip install boto3 google-cloud-storage azure-storage-blob

# 스케줄링 및 알림
pip install schedule aiohttp

# 추가 유틸리티
pip install tqdm python-dateutil
```

#### 2. 클라우드 인증 설정
```bash
python cloud_auth_setup.py
```

#### 3. 알림 시스템 설정
```bash
python notification_system.py
```

#### 4. Windows 스케줄러 설정 (관리자 권한)
```batch
setup_windows_scheduler.bat
```

## 🔧 구성 파일

### 환경 변수 (.env)
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

### 백업 스케줄 (backup_schedule_config.json)
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

### 알림 설정 (notification_config.json)
```json
{
  "enabled": true,
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "sender_email": "your-email@gmail.com",
    "recipients": ["admin@company.com"]
  },
  "slack": {
    "enabled": true,
    "webhook_url": "https://hooks.slack.com/...",
    "channel": "#backups"
  }
}
```

## 🚀 사용법

### 기본 백업 작업

```bash
# 즉시 백업 실행
python -c "from cloud.backup_manager import get_backup_manager; print(get_backup_manager().backup_database('local_backup'))"

# 모든 설정으로 백업
python -c "from cloud.backup_manager import get_backup_manager; print(get_backup_manager().backup_all_configs())"

# 백업 상태 확인
python -c "from cloud.restore_system import get_restore_system; print(f'{len(get_restore_system().discover_restore_points())}개 백업 발견')"
```

### 백업 건전성 점검

```bash
# 종합 건전성 점검
python backup_health_checker.py

# 특정 백업 테스트
python -c "
import asyncio
from backup_health_checker import BackupHealthChecker
checker = BackupHealthChecker()
result = asyncio.run(checker.run_comprehensive_health_check())
print(f'상태: {result[\"overall_status\"]}')
"
```

### 모니터링 시스템

```bash
# 통합 모니터링 시작
python integrated_monitoring.py --start

# 개별 점검 실행
python integrated_monitoring.py --health-check  # 백업 건전성
python integrated_monitoring.py --ssl-check     # SSL 인증서
python integrated_monitoring.py --disk-check    # 디스크 공간
python integrated_monitoring.py --system-check  # 시스템 상태
```

### 알림 테스트

```bash
# 테스트 알림 전송
python -c "
import asyncio
from notification_system import get_notification_system
notification = get_notification_system()
asyncio.run(notification.send_test_notification())
"
```

## 📁 프로젝트 구조

```
F:\two very auto 25.08.23\
├── 📊 대시보드
│   ├── dashboard_server.py              # FastAPI 대시보드 서버
│   ├── templates/
│   │   └── backup_dashboard.html        # 대시보드 UI
│   └── static/                          # CSS/JS 리소스
│
├── ☁️ 클라우드 백업
│   ├── cloud/
│   │   ├── backup_manager.py            # 클라우드 백업 매니저
│   │   ├── restore_system.py            # 백업 복원 시스템
│   │   └── secure_config_manager.py     # 보안 설정 관리
│   └── cloud_config.json               # 클라우드 설정
│
├── 🏥 건전성 관리
│   ├── backup_health_checker.py         # 백업 건전성 점검
│   ├── backup_health_config.json        # 건전성 점검 설정
│   └── backup_health_reports/           # 점검 보고서
│
├── 📢 알림 시스템
│   ├── notification_system.py           # 통합 알림 시스템
│   └── notification_config.json         # 알림 설정
│
├── 🔍 모니터링
│   ├── integrated_monitoring.py         # 통합 모니터링
│   ├── monitoring_config.json           # 모니터링 설정
│   └── ssl_cert_manager.py             # SSL 관리
│
├── ⏰ 스케줄링
│   ├── backup_scheduler.py              # 백업 스케줄러
│   ├── windows_task_scheduler.py        # Windows 스케줄러
│   ├── setup_windows_scheduler.bat      # 스케줄러 설정
│   └── backup_schedule_config.json      # 스케줄 설정
│
├── 🔧 설정 및 도구
│   ├── setup_complete_backup_system.py # 원클릭 설정
│   ├── cloud_auth_setup.py             # 클라우드 인증 설정
│   ├── install_backup_dependencies.bat # 의존성 설치
│   └── test_cloud_backups.py           # 백업 테스트
│
├── 📄 설정 파일
│   ├── .env.example                     # 환경변수 템플릿
│   ├── cloud_config.json               # 클라우드 백업 설정
│   ├── backup_schedule_config.json      # 백업 스케줄
│   ├── notification_config.json         # 알림 설정
│   ├── monitoring_config.json           # 모니터링 설정
│   └── ssl_monitoring_config.json       # SSL 모니터링
│
└── 📋 문서화
    ├── BACKUP_SYSTEM_README.md          # 시스템 개요
    ├── Windows_Task_Scheduler_Guide.md  # 수동 설정 가이드
    └── setup_completion_report.json     # 설정 완료 보고서
```

## 🔄 백업 워크플로우

### 1. 자동 백업 프로세스
```
데이터베이스 → 압축 → 암호화 → 클라우드 업로드 → 검증 → 알림
     ↓
[게임 데이터] → [.tar.gz] → [AES-256] → [S3/GCS/Azure] → [해시 검증] → [Slack/Email]
```

### 2. 건전성 점검 프로세스
```
백업 발견 → 다운로드 → 압축 해제 → 임시 복원 → 구조 검증 → 데이터 검증 → 리포트
     ↓
[복원 지점] → [로컬 파일] → [SQLite DB] → [테이블 확인] → [레코드 수] → [JSON 보고서]
```

### 3. 모니터링 워크플로우
```
정기 점검 → 상태 평가 → 임계값 비교 → 알림 전송 → 자동 액션
     ↓
[시간별/일별] → [시스템 상태] → [경고/위험] → [다채널 알림] → [백업/정리]
```

## 📊 성능 지표

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
- **VPN 호환**: 기업 네트워크 환경 지원
- **방화벽 친화적**: 표준 HTTPS 포트 사용
- **인증서 관리**: 자동 SSL 만료 추적

### 운영 보안
- **로그 관리**: 민감 정보 마스킹
- **감사 추적**: 모든 백업/복원 작업 기록
- **장애 복구**: 자동 백업 무결성 검증

## 🚨 문제 해결

### 일반적인 문제

#### 1. 클라우드 인증 실패
```bash
# AWS 자격증명 확인
aws sts get-caller-identity

# 환경변수 확인
echo $AWS_ACCESS_KEY_ID

# 권한 확인 (S3 버킷 접근)
aws s3 ls s3://your-bucket-name
```

#### 2. 백업 실패
```bash
# 디스크 공간 확인
df -h

# 네트워크 연결 확인
ping google.com

# 백업 로그 확인
tail -f backup_scheduler.log
```

#### 3. 알림 전송 실패
```bash
# SMTP 설정 테스트
python -c "
import smtplib, ssl
context = ssl.create_default_context()
with smtplib.SMTP('smtp.gmail.com', 587) as server:
    server.starttls(context=context)
    server.login('your-email', 'your-password')
    print('SMTP 연결 성공')
"

# Webhook 테스트
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"테스트 메시지"}' \
  YOUR_SLACK_WEBHOOK_URL
```

### 로그 위치
- **백업 로그**: `logs/backup_*.log`
- **모니터링 로그**: `integrated_monitoring.log`
- **스케줄러 로그**: `backup_scheduler.log`
- **건전성 점검**: `backup_health_reports/`

## 📈 모니터링 대시보드

웹 기반 대시보드를 통해 실시간으로 백업 시스템 상태를 확인할 수 있습니다:

```bash
# 대시보드 서버 시작
python dashboard_server.py
```

### 대시보드 기능
- 📊 **실시간 상태 모니터링**
- 📈 **백업 통계 및 차트**  
- 🔔 **알림 이력 관리**
- ⚙️ **설정 관리 인터페이스**
- 🧪 **수동 테스트 실행**

## 🔄 업그레이드 및 유지보수

### 정기 유지보수
1. **월간**: SSL 인증서 갱신 확인
2. **주간**: 백업 건전성 점검 리포트 검토
3. **일간**: 알림 로그 및 오류 확인

### 버전 업그레이드
```bash
# 현재 설정 백업
cp -r *.json config_backup/

# 새 버전 설치
git pull origin main

# 설정 병합 및 테스트
python setup_complete_backup_system.py
```

## 📞 지원 및 기여

### 문제 보고
- 이슈 등록: GitHub Issues
- 로그 첨부: 관련 로그 파일 포함
- 환경 정보: OS, Python 버전, 설정 파일

### 기여 방법
1. Fork 프로젝트
2. 기능 브랜치 생성
3. 코드 작성 및 테스트
4. Pull Request 제출

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 LICENSE 파일을 참조하세요.

---

**Two Very Auto** - 엔터프라이즈급 자동 백업 시스템  
© 2025 Two Very Auto Team