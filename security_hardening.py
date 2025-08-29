#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
보안 강화 도구
환경 설정, 파일 권한, 네트워크 보안 등을 자동으로 강화
"""

import os
import sys
import json
import stat
import hashlib
import secrets
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 로컬 모듈
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

class SecurityHardening:
    """보안 강화 도구"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.absolute()
        self.security_log = []
        self.vulnerabilities = []
        self.hardening_applied = []
        
        safe_print("🛡️ 보안 강화 도구 초기화")
    
    def log_security_event(self, event_type: str, description: str, severity: str = "info"):
        """보안 이벤트 로그"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "description": description,
            "severity": severity
        }
        self.security_log.append(event)
        
        severity_icons = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "🔶",
            "low": "ℹ️",
            "info": "📝"
        }
        
        icon = severity_icons.get(severity, "📝")
        safe_print(f"{icon} [{severity.upper()}] {description}")
    
    def scan_environment_files(self) -> List[Dict[str, Any]]:
        """환경 파일 보안 스캔"""
        safe_print("🔍 환경 파일 보안 스캔 중...")
        
        sensitive_files = [".env", ".env.local", ".env.production", "config.json", "secrets.json"]
        issues = []
        
        for file_name in sensitive_files:
            file_path = self.project_dir / file_name
            if file_path.exists():
                # 파일 권한 확인
                file_stat = file_path.stat()
                file_mode = stat.filemode(file_stat.st_mode)
                
                # Windows에서는 권한 체크가 제한적
                if os.name != 'nt':
                    if file_stat.st_mode & stat.S_IROTH or file_stat.st_mode & stat.S_IWOTH:
                        issues.append({
                            "file": str(file_path),
                            "issue": "다른 사용자가 읽기/쓰기 권한을 가짐",
                            "severity": "high",
                            "fix": "파일 권한을 600으로 설정"
                        })
                
                # 파일 내용 스캔
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 민감한 정보 패턴 검사
                    sensitive_patterns = [
                        ("password", r"password\s*=\s*['\"]?[\w\d@#$%^&*()_+-=]+['\"]?"),
                        ("api_key", r"(?:api[_-]?key|token)\s*=\s*['\"]?[\w\d-]+['\"]?"),
                        ("secret", r"secret\s*=\s*['\"]?[\w\d@#$%^&*()_+-=]+['\"]?"),
                        ("private_key", r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----")
                    ]
                    
                    for pattern_name, pattern in sensitive_patterns:
                        import re
                        if re.search(pattern, content, re.IGNORECASE):
                            # 실제 값이 있는지 확인 (빈 값이나 플레이스홀더가 아닌)
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                if not any(placeholder in match.lower() for placeholder in 
                                         ['your_', 'enter_', 'replace_', 'example', 'placeholder']):
                                    issues.append({
                                        "file": str(file_path),
                                        "issue": f"민감한 정보 노출: {pattern_name}",
                                        "severity": "high",
                                        "fix": "민감한 정보를 환경변수로 분리"
                                    })
                
                except Exception as e:
                    self.log_security_event("file_scan_error", f"{file_path} 스캔 오류: {e}", "medium")
        
        self.vulnerabilities.extend(issues)
        return issues
    
    def check_file_permissions(self) -> List[Dict[str, Any]]:
        """파일 권한 확인"""
        safe_print("🔐 파일 권한 검사 중...")
        
        issues = []
        critical_files = [
            ".env", "ssl_certificates/*.key", "ssl_certificates/*.pem",
            "backup_*.json", "*_config.json"
        ]
        
        for pattern in critical_files:
            if "*" in pattern:
                # 와일드카드 패턴 처리
                import glob
                files = glob.glob(str(self.project_dir / pattern))
            else:
                files = [str(self.project_dir / pattern)]
            
            for file_path in files:
                path_obj = Path(file_path)
                if path_obj.exists() and path_obj.is_file():
                    try:
                        file_stat = path_obj.stat()
                        
                        # Unix/Linux에서만 권한 확인
                        if os.name != 'nt':
                            # 소유자 외 읽기/쓰기 권한 확인
                            if file_stat.st_mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
                                issues.append({
                                    "file": str(path_obj),
                                    "issue": "그룹/기타 사용자 접근 권한 있음",
                                    "severity": "medium",
                                    "fix": f"chmod 600 {path_obj.name}"
                                })
                    
                    except Exception as e:
                        self.log_security_event("permission_check_error", 
                                              f"{path_obj} 권한 확인 오류: {e}", "low")
        
        self.vulnerabilities.extend(issues)
        return issues
    
    def scan_code_secrets(self) -> List[Dict[str, Any]]:
        """코드 내 하드코딩된 시크릿 스캔"""
        safe_print("🕵️ 코드 내 하드코딩된 시크릿 스캔 중...")
        
        issues = []
        code_files = list(self.project_dir.glob("*.py"))
        
        # 위험한 패턴들
        dangerous_patterns = [
            ("hard_coded_password", r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{3,}['\"]"),
            ("hard_coded_key", r"(?:key|token|secret)\s*=\s*['\"][^'\"]{10,}['\"]"),
            ("database_connection", r"(?:mysql|postgresql|mongodb)://[^'\"]+:[^'\"]+@"),
            ("aws_keys", r"AKIA[0-9A-Z]{16}"),
            ("private_key_content", r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
        ]
        
        for code_file in code_files:
            try:
                with open(code_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern_name, pattern in dangerous_patterns:
                    import re
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        # 주석이나 예시 코드가 아닌지 확인
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line = content[line_start:content.find('\n', match.start())]
                        
                        if not line.strip().startswith('#') and 'example' not in line.lower():
                            issues.append({
                                "file": str(code_file),
                                "issue": f"하드코딩된 시크릿: {pattern_name}",
                                "severity": "high",
                                "fix": "환경변수 또는 설정 파일로 분리",
                                "line": line.strip()
                            })
            
            except Exception as e:
                self.log_security_event("code_scan_error", f"{code_file} 스캔 오류: {e}", "low")
        
        self.vulnerabilities.extend(issues)
        return issues
    
    def check_network_security(self) -> List[Dict[str, Any]]:
        """네트워크 보안 설정 확인"""
        safe_print("🌐 네트워크 보안 설정 확인 중...")
        
        issues = []
        
        # 환경 설정에서 네트워크 관련 설정 확인
        env_file = self.project_dir / ".env"
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                
                # 위험한 네트워크 설정 확인
                if "FASTAPI_HOST=0.0.0.0" in env_content:
                    issues.append({
                        "file": str(env_file),
                        "issue": "모든 인터페이스에 바인딩 (0.0.0.0)",
                        "severity": "medium",
                        "fix": "개발용이 아닌 경우 127.0.0.1로 변경"
                    })
                
                if "DEBUG=true" in env_content or "DEV_MODE=true" in env_content:
                    issues.append({
                        "file": str(env_file),
                        "issue": "프로덕션에서 디버그 모드 활성화",
                        "severity": "high",
                        "fix": "프로덕션에서는 DEBUG=false로 설정"
                    })
                
                # SSL 설정 확인
                if "SSL_VERIFY=false" in env_content:
                    issues.append({
                        "file": str(env_file),
                        "issue": "SSL 검증 비활성화",
                        "severity": "high",
                        "fix": "SSL_VERIFY=true로 설정"
                    })
                
            except Exception as e:
                self.log_security_event("network_config_error", f"네트워크 설정 확인 오류: {e}", "low")
        
        self.vulnerabilities.extend(issues)
        return issues
    
    def generate_secure_keys(self) -> Dict[str, str]:
        """보안 키 생성"""
        safe_print("🔑 보안 키 생성 중...")
        
        keys = {
            "SECRET_KEY": secrets.token_urlsafe(32),
            "JWT_SECRET": secrets.token_urlsafe(32),
            "BACKUP_ENCRYPTION_KEY": secrets.token_urlsafe(32)[:32],  # 32자로 제한
            "SESSION_SECRET": secrets.token_urlsafe(24),
            "CSRF_TOKEN": secrets.token_hex(16)
        }
        
        self.log_security_event("key_generation", f"{len(keys)}개 보안 키 생성", "info")
        return keys
    
    def apply_file_hardening(self) -> bool:
        """파일 보안 강화 적용"""
        safe_print("🔒 파일 보안 강화 적용 중...")
        
        try:
            sensitive_files = [".env", ".env.local", "ssl_certificates", "backup_*.json"]
            hardened_count = 0
            
            for pattern in sensitive_files:
                if "*" in pattern:
                    import glob
                    files = glob.glob(str(self.project_dir / pattern))
                else:
                    files = [str(self.project_dir / pattern)]
                
                for file_path in files:
                    path_obj = Path(file_path)
                    if path_obj.exists():
                        try:
                            # Unix/Linux에서만 권한 설정
                            if os.name != 'nt':
                                if path_obj.is_file():
                                    os.chmod(path_obj, 0o600)  # 소유자만 읽기/쓰기
                                elif path_obj.is_dir():
                                    os.chmod(path_obj, 0o700)  # 소유자만 접근
                                hardened_count += 1
                        except Exception as e:
                            self.log_security_event("file_hardening_error", 
                                                  f"{path_obj} 권한 설정 오류: {e}", "medium")
            
            if hardened_count > 0:
                self.hardening_applied.append(f"파일 권한 강화: {hardened_count}개 파일")
                self.log_security_event("file_hardening", f"{hardened_count}개 파일 권한 강화", "info")
            
            return True
            
        except Exception as e:
            self.log_security_event("file_hardening_error", f"파일 강화 오류: {e}", "high")
            return False
    
    def create_security_env_template(self) -> str:
        """보안 강화된 환경변수 템플릿 생성"""
        safe_print("📋 보안 환경변수 템플릿 생성 중...")
        
        secure_keys = self.generate_secure_keys()
        
        template = f"""# Two Very Auto - 보안 강화된 환경변수 설정
# 이 파일을 복사하여 실제 값으로 수정하세요

# 애플리케이션 보안
SECRET_KEY={secure_keys['SECRET_KEY']}
JWT_SECRET={secure_keys['JWT_SECRET']}
SESSION_SECRET={secure_keys['SESSION_SECRET']}
CSRF_TOKEN={secure_keys['CSRF_TOKEN']}

# 백업 암호화
BACKUP_ENCRYPTION_KEY={secure_keys['BACKUP_ENCRYPTION_KEY']}

# 네트워크 보안 (프로덕션 설정)
FASTAPI_HOST=127.0.0.1
FASTAPI_PORT=8000
SSL_VERIFY=true
SECURE_COOKIES=true
HSTS_ENABLED=true

# 디버그 설정 (프로덕션에서는 false)
DEBUG=false
DEV_MODE=false
FASTAPI_DEBUG=false

# 보안 헤더
CORS_ORIGINS=http://localhost:3000
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
MAX_LOGIN_ATTEMPTS=5

# 로깅 보안
LOG_LEVEL=INFO
LOG_MASK_SENSITIVE=true

# 세션 보안
SESSION_TIMEOUT=3600
SESSION_SECURE=true
SESSION_HTTPONLY=true

# 데이터베이스 보안
DB_SSL_MODE=require
DB_CONNECTION_TIMEOUT=30

# 백업 보안
BACKUP_VERIFY_INTEGRITY=true
BACKUP_ENCRYPT=true
BACKUP_RETENTION_POLICY=strict

# 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 보안 레벨: 높음
"""
        
        template_path = self.project_dir / ".env.secure.template"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        # Unix/Linux에서 템플릿 파일 권한 설정
        if os.name != 'nt':
            os.chmod(template_path, 0o600)
        
        self.hardening_applied.append(f"보안 환경변수 템플릿 생성: {template_path}")
        return str(template_path)
    
    def create_security_config(self) -> str:
        """보안 설정 파일 생성"""
        safe_print("⚙️ 보안 설정 파일 생성 중...")
        
        security_config = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "security_level": "high",
            "settings": {
                "encryption": {
                    "algorithm": "AES-256",
                    "key_rotation_days": 90,
                    "backup_encryption": True
                },
                "network": {
                    "ssl_required": True,
                    "hsts_enabled": True,
                    "secure_cookies": True,
                    "cors_strict": True
                },
                "authentication": {
                    "max_login_attempts": 5,
                    "session_timeout": 3600,
                    "password_policy": {
                        "min_length": 12,
                        "require_uppercase": True,
                        "require_lowercase": True,
                        "require_numbers": True,
                        "require_symbols": True
                    }
                },
                "logging": {
                    "log_sensitive_data": False,
                    "audit_trail": True,
                    "retention_days": 90
                },
                "file_security": {
                    "restricted_permissions": True,
                    "backup_verification": True,
                    "integrity_checks": True
                }
            },
            "monitoring": {
                "security_events": True,
                "failed_login_tracking": True,
                "file_integrity_monitoring": True,
                "network_activity_logging": True
            }
        }
        
        config_path = self.project_dir / "security_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(security_config, f, ensure_ascii=False, indent=2)
        
        # 설정 파일 권한 보호
        if os.name != 'nt':
            os.chmod(config_path, 0o600)
        
        self.hardening_applied.append(f"보안 설정 파일 생성: {config_path}")
        return str(config_path)
    
    def generate_security_report(self) -> str:
        """보안 검사 보고서 생성"""
        safe_print("📊 보안 검사 보고서 생성 중...")
        
        # 심각도별 분류
        critical_issues = [v for v in self.vulnerabilities if v.get("severity") == "critical"]
        high_issues = [v for v in self.vulnerabilities if v.get("severity") == "high"]
        medium_issues = [v for v in self.vulnerabilities if v.get("severity") == "medium"]
        low_issues = [v for v in self.vulnerabilities if v.get("severity") == "low"]
        
        report = f"""# Two Very Auto - 보안 검사 보고서

## 검사 요약
- **검사 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **총 발견된 이슈**: {len(self.vulnerabilities)}개
- **적용된 강화 조치**: {len(self.hardening_applied)}개

## 심각도별 이슈

### 🚨 Critical ({len(critical_issues)}개)
"""
        for issue in critical_issues:
            report += f"- **{issue['file']}**: {issue['issue']}\n"
            report += f"  - 해결책: {issue['fix']}\n\n"
        
        report += f"""
### ⚠️ High ({len(high_issues)}개)
"""
        for issue in high_issues:
            report += f"- **{issue['file']}**: {issue['issue']}\n"
            report += f"  - 해결책: {issue['fix']}\n\n"
        
        report += f"""
### 🔶 Medium ({len(medium_issues)}개)
"""
        for issue in medium_issues:
            report += f"- **{issue['file']}**: {issue['issue']}\n"
            report += f"  - 해결책: {issue['fix']}\n\n"
        
        report += f"""
### ℹ️ Low ({len(low_issues)}개)
"""
        for issue in low_issues:
            report += f"- **{issue['file']}**: {issue['issue']}\n\n"
        
        report += """
## 적용된 보안 강화 조치
"""
        for hardening in self.hardening_applied:
            report += f"- ✅ {hardening}\n"
        
        report += """
## 권장사항

### 즉시 조치 필요
1. Critical 및 High 심각도 이슈 해결
2. 민감한 정보를 환경변수로 분리
3. 파일 권한 적절히 설정
4. SSL/TLS 활성화

### 장기적 보안 강화
1. 정기적인 보안 스캔 실행
2. 보안 패치 업데이트
3. 접근 로그 모니터링
4. 백업 데이터 암호화

### 추천 도구
- 정기 스캔: `python security_hardening.py --scan`
- 자동 강화: `python security_hardening.py --harden`
- 키 로테이션: `python security_hardening.py --rotate-keys`

## 보안 체크리스트
- [ ] 모든 민감한 파일 권한 확인
- [ ] 환경변수에서 하드코딩된 시크릿 제거
- [ ] SSL/HTTPS 설정
- [ ] 디버그 모드 프로덕션에서 비활성화
- [ ] 정기적인 백업 암호화 확인
- [ ] 로그 파일 보안 설정
- [ ] 네트워크 접근 제한 확인

---
🛡️ Two Very Auto 보안 검사 완료
"""
        
        report_path = self.project_dir / "SECURITY_SCAN_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return str(report_path)
    
    def run_complete_scan(self) -> Dict[str, Any]:
        """전체 보안 스캔 실행"""
        safe_print("🛡️ 전체 보안 스캔 시작")
        safe_print("=" * 40)
        
        # 각종 보안 검사 실행
        env_issues = self.scan_environment_files()
        permission_issues = self.check_file_permissions()
        code_issues = self.scan_code_secrets()
        network_issues = self.check_network_security()
        
        # 보안 강화 적용
        self.apply_file_hardening()
        secure_template = self.create_security_env_template()
        security_config = self.create_security_config()
        
        # 보고서 생성
        report_path = self.generate_security_report()
        
        # 결과 요약
        total_issues = len(self.vulnerabilities)
        critical_count = len([v for v in self.vulnerabilities if v.get("severity") == "critical"])
        high_count = len([v for v in self.vulnerabilities if v.get("severity") == "high"])
        
        safe_print("\n" + "=" * 40)
        safe_print("🛡️ 보안 스캔 완료!")
        safe_print(f"📊 총 이슈: {total_issues}개 (Critical: {critical_count}, High: {high_count})")
        safe_print(f"⚡ 적용된 강화: {len(self.hardening_applied)}개")
        safe_print(f"📋 보고서: {report_path}")
        
        if critical_count > 0 or high_count > 0:
            safe_print("⚠️ 심각한 보안 이슈가 발견되었습니다. 즉시 조치가 필요합니다!")
        else:
            safe_print("✅ 심각한 보안 이슈가 발견되지 않았습니다.")
        
        return {
            "total_issues": total_issues,
            "critical_issues": critical_count,
            "high_issues": high_count,
            "hardening_applied": len(self.hardening_applied),
            "report_path": report_path
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Two Very Auto 보안 강화 도구")
    parser.add_argument("--scan", action="store_true", help="보안 스캔 실행")
    parser.add_argument("--harden", action="store_true", help="보안 강화 적용")
    parser.add_argument("--generate-keys", action="store_true", help="보안 키 생성")
    parser.add_argument("--create-template", action="store_true", help="보안 환경변수 템플릿")
    parser.add_argument("--full", action="store_true", help="전체 스캔 및 강화")
    
    args = parser.parse_args()
    
    hardening = SecurityHardening()
    
    if args.full:
        hardening.run_complete_scan()
    elif args.scan:
        hardening.scan_environment_files()
        hardening.check_file_permissions()
        hardening.scan_code_secrets()
        hardening.check_network_security()
        report_path = hardening.generate_security_report()
        safe_print(f"📋 스캔 보고서: {report_path}")
    elif args.harden:
        hardening.apply_file_hardening()
        safe_print("🔒 보안 강화 적용 완료")
    elif args.generate_keys:
        keys = hardening.generate_secure_keys()
        safe_print("🔑 생성된 보안 키:")
        for key_name, key_value in keys.items():
            safe_print(f"  {key_name}={key_value}")
    elif args.create_template:
        template_path = hardening.create_security_env_template()
        safe_print(f"📋 보안 템플릿 생성: {template_path}")
    else:
        safe_print("🛡️ Two Very Auto 보안 강화 도구")
        safe_print("사용법:")
        safe_print("  --full           : 전체 스캔 및 강화")
        safe_print("  --scan           : 보안 스캔만")
        safe_print("  --harden         : 보안 강화 적용")
        safe_print("  --generate-keys  : 보안 키 생성")
        safe_print("  --create-template: 보안 템플릿 생성")