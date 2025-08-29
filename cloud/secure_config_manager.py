#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
백업 시스템 보안 설정 관리자
환경변수 기반 보안 설정 로드 및 검증
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import base64
import hashlib

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

@dataclass
class BackupSecurityConfig:
    """백업 보안 설정 클래스"""
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_region: str = "ap-northeast-2"
    aws_bucket_name: str = "two-very-auto-backups"
    
    gcp_credentials_path: Optional[str] = None
    gcp_bucket_name: str = "two-very-auto-backups-gcp"
    gcp_project_id: Optional[str] = None
    
    azure_account_name: Optional[str] = None
    azure_account_key: Optional[str] = None
    azure_container_name: str = "two-very-auto-backups"
    
    encryption_key: Optional[str] = None
    max_size_mb: int = 1000
    retention_days: int = 30
    
    ssl_cert_path: str = "server.crt"
    ssl_key_path: str = "server.key"
    ssl_pfx_path: str = "server.pfx"
    ssl_expiry_alert_days: int = 30

class SecureConfigManager:
    """보안 설정 관리자"""
    
    def __init__(self, env_file_path: str = ".env"):
        self.env_file_path = Path(env_file_path)
        self.config = BackupSecurityConfig()
        
        # 환경변수 로드 시도
        self.load_from_env()
        
        safe_print("🔐 보안 설정 관리자 초기화 완료")
    
    def load_from_env(self):
        """환경변수에서 설정 로드"""
        try:
            # .env 파일이 있으면 로드
            if self.env_file_path.exists():
                self._load_env_file()
                safe_print(f"✅ 환경 설정 파일 로드: {self.env_file_path}")
            
            # 환경변수에서 백업 설정 추출
            self.config.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            self.config.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            self.config.aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
            self.config.aws_bucket_name = os.getenv('AWS_BUCKET_NAME', 'two-very-auto-backups')
            
            self.config.gcp_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            self.config.gcp_bucket_name = os.getenv('GCP_BUCKET_NAME', 'two-very-auto-backups-gcp')
            self.config.gcp_project_id = os.getenv('GCP_PROJECT_ID')
            
            self.config.azure_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
            self.config.azure_account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
            self.config.azure_container_name = os.getenv('AZURE_CONTAINER_NAME', 'two-very-auto-backups')
            
            self.config.encryption_key = os.getenv('BACKUP_ENCRYPTION_KEY')
            self.config.max_size_mb = int(os.getenv('BACKUP_MAX_SIZE_MB', '1000'))
            self.config.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
            
            self.config.ssl_cert_path = os.getenv('SSL_CERT_PATH', 'server.crt')
            self.config.ssl_key_path = os.getenv('SSL_KEY_PATH', 'server.key')
            self.config.ssl_pfx_path = os.getenv('SSL_PFX_PATH', 'server.pfx')
            self.config.ssl_expiry_alert_days = int(os.getenv('SSL_CERT_EXPIRY_ALERT_DAYS', '30'))
            
        except Exception as e:
            logger.error(f"환경변수 로드 오류: {e}")
    
    def _load_env_file(self):
        """환경 파일 로드"""
        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        except Exception as e:
            logger.error(f"환경 파일 로드 오류: {e}")
    
    def validate_security_settings(self) -> Dict[str, Any]:
        """보안 설정 검증"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # AWS 설정 검증
        if self.config.aws_access_key and self.config.aws_secret_key:
            if len(self.config.aws_access_key) < 16:
                validation_result["warnings"].append("AWS Access Key가 너무 짧습니다")
            if len(self.config.aws_secret_key) < 32:
                validation_result["warnings"].append("AWS Secret Key가 너무 짧습니다")
        else:
            validation_result["recommendations"].append("AWS 백업을 위한 인증 정보를 설정하세요")
        
        # 암호화 키 검증
        if not self.config.encryption_key:
            validation_result["warnings"].append("백업 암호화 키가 설정되지 않았습니다")
        elif len(self.config.encryption_key) < 32:
            validation_result["errors"].append("암호화 키는 최소 32자 이상이어야 합니다")
            validation_result["valid"] = False
        
        # SSL 인증서 검증
        ssl_status = self.check_ssl_certificate_status()
        if not ssl_status["exists"]:
            validation_result["warnings"].append("SSL 인증서 파일이 없습니다")
        elif ssl_status["expires_soon"]:
            validation_result["warnings"].append(f"SSL 인증서가 {ssl_status['days_until_expiry']}일 후 만료됩니다")
        
        return validation_result
    
    def check_ssl_certificate_status(self) -> Dict[str, Any]:
        """SSL 인증서 상태 확인"""
        cert_path = Path(self.config.ssl_cert_path)
        
        status = {
            "exists": cert_path.exists(),
            "expires_soon": False,
            "days_until_expiry": None,
            "expiry_date": None
        }
        
        if cert_path.exists():
            try:
                import ssl
                import socket
                from datetime import datetime
                
                # 인증서 정보 읽기 (간단한 방법)
                with open(cert_path, 'r') as cert_file:
                    cert_content = cert_file.read()
                    
                # 만료일 파싱 (실제로는 cryptography 라이브러리 사용 권장)
                if "-----BEGIN CERTIFICATE-----" in cert_content:
                    # 여기서는 파일 생성 시간으로 추정 (실제 구현에서는 인증서 파싱 필요)
                    cert_mtime = datetime.fromtimestamp(cert_path.stat().st_mtime)
                    # 일반적으로 1년 유효기간
                    estimated_expiry = cert_mtime + timedelta(days=365)
                    
                    days_until_expiry = (estimated_expiry - datetime.now()).days
                    status["days_until_expiry"] = days_until_expiry
                    status["expiry_date"] = estimated_expiry.strftime("%Y-%m-%d")
                    status["expires_soon"] = days_until_expiry <= self.config.ssl_expiry_alert_days
                    
            except Exception as e:
                logger.warning(f"SSL 인증서 상태 확인 오류: {e}")
        
        return status
    
    def generate_encryption_key(self) -> str:
        """안전한 암호화 키 생성"""
        import secrets
        
        # 32바이트 (256비트) 키 생성
        key_bytes = secrets.token_bytes(32)
        key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        
        safe_print("🔑 새로운 암호화 키가 생성되었습니다")
        safe_print("⚠️ 이 키를 안전한 곳에 보관하고 환경변수에 설정하세요")
        
        return key_b64
    
    def update_cloud_config(self, config_path: str = "cloud_config.json") -> bool:
        """클라우드 설정 파일 업데이트 (민감한 정보 제외)"""
        try:
            config_data = {
                "backup_configs": {
                    "aws_primary": {
                        "provider": "aws_s3",
                        "bucket_name": self.config.aws_bucket_name,
                        "region": self.config.aws_region,
                        "compression": True,
                        "encryption": True,
                        "retention_days": self.config.retention_days,
                        "max_backup_size_mb": self.config.max_size_mb
                    },
                    "gcp_secondary": {
                        "provider": "google_cloud",
                        "bucket_name": self.config.gcp_bucket_name,
                        "compression": True,
                        "encryption": True,
                        "retention_days": self.config.retention_days
                    },
                    "azure_tertiary": {
                        "provider": "azure_blob",
                        "bucket_name": self.config.azure_container_name,
                        "compression": True,
                        "encryption": True,
                        "retention_days": self.config.retention_days
                    },
                    "local_backup": {
                        "provider": "local",
                        "bucket_name": "./backups",
                        "compression": True,
                        "retention_days": 7
                    }
                }
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            safe_print(f"✅ 클라우드 설정 파일 업데이트 완료: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"클라우드 설정 파일 업데이트 오류: {e}")
            return False
    
    def get_security_report(self) -> Dict[str, Any]:
        """보안 상태 리포트 생성"""
        validation = self.validate_security_settings()
        ssl_status = self.check_ssl_certificate_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "validation_result": validation,
            "ssl_certificate": ssl_status,
            "configured_providers": {
                "aws": bool(self.config.aws_access_key and self.config.aws_secret_key),
                "gcp": bool(self.config.gcp_credentials_path),
                "azure": bool(self.config.azure_account_name and self.config.azure_account_key)
            },
            "encryption_enabled": bool(self.config.encryption_key),
            "recommendations": validation.get("recommendations", [])
        }

# 전역 인스턴스
_secure_config_manager = None

def get_secure_config_manager() -> SecureConfigManager:
    """보안 설정 관리자 인스턴스 반환"""
    global _secure_config_manager
    if _secure_config_manager is None:
        _secure_config_manager = SecureConfigManager()
    return _secure_config_manager

if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 보안 설정 관리자 테스트 ===")
    
    manager = get_secure_config_manager()
    
    # 보안 리포트 생성
    report = manager.get_security_report()
    safe_print(f"📋 보안 상태 리포트:")
    safe_print(json.dumps(report, ensure_ascii=False, indent=2))
    
    # 새 암호화 키 생성 예시 (실제로는 생성하지 않음)
    if input("새 암호화 키를 생성하시겠습니까? (y/N): ").lower() == 'y':
        new_key = manager.generate_encryption_key()
        safe_print(f"생성된 키: {new_key[:20]}...")
    
    # 클라우드 설정 파일 업데이트
    manager.update_cloud_config()
    
    safe_print("🏁 보안 설정 관리자 테스트 완료")