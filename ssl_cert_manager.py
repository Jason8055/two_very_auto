#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSL 인증서 관리 및 갱신 도구
인증서 상태 점검, 만료 알림, 자동 갱신 준비
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import subprocess

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

class SSLCertificateManager:
    """SSL 인증서 관리자"""
    
    def __init__(self):
        self.cert_files = {
            "crt": Path("server.crt"),
            "pfx": Path("server.pfx"),
            "key": Path("server.key")
        }
        
        safe_print("🔐 SSL 인증서 관리자 초기화")
    
    def check_certificate_details(self) -> Dict[str, Any]:
        """인증서 상세 정보 확인"""
        cert_info = {
            "files_status": {},
            "certificate_info": {},
            "warnings": [],
            "recommendations": []
        }
        
        # 파일 존재 여부 확인
        for cert_type, cert_path in self.cert_files.items():
            exists = cert_path.exists()
            cert_info["files_status"][cert_type] = {
                "exists": exists,
                "path": str(cert_path),
                "size_kb": round(cert_path.stat().st_size / 1024, 1) if exists else 0,
                "modified": datetime.fromtimestamp(cert_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if exists else None
            }
            
            if not exists:
                cert_info["warnings"].append(f"{cert_type.upper()} 파일이 존재하지 않습니다: {cert_path}")
        
        # CRT 파일에서 인증서 정보 추출
        if self.cert_files["crt"].exists():
            cert_details = self._parse_certificate_info()
            cert_info["certificate_info"] = cert_details
            
            # 만료 경고 확인
            if cert_details.get("days_until_expiry"):
                days_left = cert_details["days_until_expiry"]
                if days_left <= 30:
                    cert_info["warnings"].append(f"인증서가 {days_left}일 후 만료됩니다!")
                elif days_left <= 90:
                    cert_info["recommendations"].append(f"인증서 갱신 준비 권장 ({days_left}일 남음)")
        
        return cert_info
    
    def _parse_certificate_info(self) -> Dict[str, Any]:
        """CRT 파일에서 인증서 정보 파싱"""
        cert_info = {}
        
        try:
            # OpenSSL 명령어로 인증서 정보 추출
            result = subprocess.run([
                'openssl', 'x509', '-in', str(self.cert_files["crt"]), 
                '-text', '-noout'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout
                cert_info = self._extract_cert_details_from_text(output)
            else:
                # OpenSSL이 없는 경우 파일 직접 읽기로 대체
                cert_info = self._parse_cert_manually()
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # OpenSSL 명령어 사용 불가시 수동 파싱
            cert_info = self._parse_cert_manually()
        except Exception as e:
            logger.error(f"인증서 파싱 오류: {e}")
            cert_info = {"error": str(e)}
        
        return cert_info
    
    def _extract_cert_details_from_text(self, cert_text: str) -> Dict[str, Any]:
        """OpenSSL 출력 텍스트에서 인증서 정보 추출"""
        details = {}
        
        # 발급자 추출
        if "Issuer:" in cert_text:
            issuer_line = [line for line in cert_text.split('\n') if 'Issuer:' in line][0]
            details["issuer"] = issuer_line.split('Issuer:')[1].strip()
        
        # 주체 추출
        if "Subject:" in cert_text:
            subject_line = [line for line in cert_text.split('\n') if 'Subject:' in line][0]
            details["subject"] = subject_line.split('Subject:')[1].strip()
        
        # 유효기간 추출
        if "Not Before:" in cert_text and "Not After:" in cert_text:
            lines = cert_text.split('\n')
            for line in lines:
                if "Not Before:" in line:
                    details["valid_from"] = line.split('Not Before:')[1].strip()
                if "Not After:" in line:
                    details["valid_until"] = line.split('Not After:')[1].strip()
                    
                    # 만료일까지 남은 일수 계산
                    try:
                        expire_date = datetime.strptime(details["valid_until"], "%b %d %H:%M:%S %Y %Z")
                        days_left = (expire_date - datetime.now()).days
                        details["days_until_expiry"] = days_left
                    except:
                        pass
        
        return details
    
    def _parse_cert_manually(self) -> Dict[str, Any]:
        """수동으로 인증서 파일 파싱 (간단한 정보만)"""
        details = {}
        
        try:
            with open(self.cert_files["crt"], 'r') as f:
                content = f.read()
            
            # 인증서 형식 확인
            if "-----BEGIN CERTIFICATE-----" in content and "-----END CERTIFICATE-----" in content:
                details["format"] = "PEM"
                details["status"] = "인증서 파일이 올바른 PEM 형식입니다"
                
                # 파일 생성/수정 시간 기반 추정
                stat = self.cert_files["crt"].stat()
                created = datetime.fromtimestamp(stat.st_ctime)
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                details["file_created"] = created.strftime("%Y-%m-%d %H:%M:%S")
                details["file_modified"] = modified.strftime("%Y-%m-%d %H:%M:%S")
                
                # 일반적으로 1년 유효기간으로 추정
                estimated_expiry = modified + timedelta(days=365)
                days_left = (estimated_expiry - datetime.now()).days
                
                details["estimated_expiry"] = estimated_expiry.strftime("%Y-%m-%d")
                details["days_until_expiry"] = days_left
                details["note"] = "파일 수정 시간 기반 추정값 (정확한 만료일은 OpenSSL로 확인)"
            else:
                details["status"] = "인증서 형식을 인식할 수 없습니다"
                
        except Exception as e:
            details["error"] = f"파일 읽기 오류: {e}"
        
        return details
    
    def generate_renewal_script(self) -> str:
        """인증서 갱신 스크립트 생성"""
        script_content = '''#!/bin/bash
# SSL 인증서 갱신 스크립트
# 사용 전 환경에 맞게 수정 필요

echo "==================================="
echo "SSL 인증서 갱신 스크립트"
echo "==================================="

# 기존 인증서 백업
BACKUP_DIR="ssl_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "server.crt" ]; then
    cp server.crt "$BACKUP_DIR/"
    echo "✅ 기존 CRT 파일 백업"
fi

if [ -f "server.key" ]; then
    cp server.key "$BACKUP_DIR/"
    echo "✅ 기존 KEY 파일 백업"
fi

if [ -f "server.pfx" ]; then
    cp server.pfx "$BACKUP_DIR/"
    echo "✅ 기존 PFX 파일 백업"
fi

echo "📁 백업 디렉터리: $BACKUP_DIR"

# 방법 1: Let's Encrypt (Certbot) 사용 예시
echo "방법 1: Let's Encrypt 갱신 (수정 필요)"
echo "# certbot renew --cert-name your-domain.com"
echo "# certbot certonly --standalone -d your-domain.com"

# 방법 2: 자체 서명 인증서 생성 (개발용)
echo "방법 2: 자체 서명 인증서 생성 (개발용)"
echo "openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes"
echo "openssl pkcs12 -export -out server.pfx -inkey server.key -in server.crt"

# 방법 3: 상용 CA 인증서 설치
echo "방법 3: 상용 CA 인증서 설치"
echo "# 1. CSR 생성: openssl req -new -newkey rsa:2048 -nodes -keyout server.key -out server.csr"
echo "# 2. CA에 CSR 제출하여 인증서 발급 받기"
echo "# 3. 발급받은 인증서를 server.crt로 저장"
echo "# 4. PFX 파일 생성: openssl pkcs12 -export -out server.pfx -inkey server.key -in server.crt"

echo "==================================="
echo "갱신 후 다음 명령어로 인증서 확인:"
echo "python ssl_cert_manager.py"
echo "==================================="
'''
        
        script_path = Path("renew_ssl_certificate.sh")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        safe_print(f"📝 인증서 갱신 스크립트 생성: {script_path}")
        return str(script_path)
    
    def create_monitoring_config(self) -> Dict[str, Any]:
        """인증서 모니터링 설정 생성"""
        config = {
            "ssl_monitoring": {
                "enabled": True,
                "check_interval_hours": 24,
                "warning_days_before_expiry": 30,
                "critical_days_before_expiry": 7,
                "notification_methods": ["email", "log"],
                "auto_backup_before_renewal": True,
                "certificates": [
                    {
                        "name": "main_server",
                        "cert_path": "server.crt",
                        "key_path": "server.key", 
                        "pfx_path": "server.pfx"
                    }
                ]
            }
        }
        
        config_path = Path("ssl_monitoring_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        safe_print(f"⚙️ SSL 모니터링 설정 생성: {config_path}")
        return config
    
    def get_certificate_report(self) -> Dict[str, Any]:
        """인증서 상태 리포트 생성"""
        details = self.check_certificate_details()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "certificate_status": details,
            "security_recommendations": [
                "정기적으로 인증서 만료일 확인",
                "자동 갱신 스크립트 설정",
                "백업 인증서 보관",
                "강력한 암호화 키 사용 (최소 2048비트 RSA)"
            ],
            "renewal_timeline": {
                "30_days_before": "갱신 준비 시작",
                "14_days_before": "갱신 스크립트 테스트", 
                "7_days_before": "실제 갱신 수행",
                "1_day_before": "긴급 갱신 필요"
            }
        }

if __name__ == "__main__":
    safe_print("=== SSL 인증서 관리자 ===")
    
    manager = SSLCertificateManager()
    
    # 인증서 상태 리포트
    report = manager.get_certificate_report()
    safe_print("📋 인증서 상태 리포트:")
    safe_print(json.dumps(report, ensure_ascii=False, indent=2))
    
    # 갱신 스크립트 생성
    script_path = manager.generate_renewal_script()
    
    # 모니터링 설정 생성
    monitoring_config = manager.create_monitoring_config()
    
    safe_print("🏁 SSL 인증서 관리 완료")