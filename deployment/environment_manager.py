#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 환경 설정 관리자
다중 환경 설정 및 시크릿 관리 시스템
"""

import os
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import base64
import hashlib

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
    safe_print("✅ 암호화 라이브러리 사용 가능")
except ImportError:
    CRYPTO_AVAILABLE = False
    safe_print("⚠️ cryptography 라이브러리 미설치. pip install cryptography 실행 필요")


class ConfigType(Enum):
    """설정 타입"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    SECRET = "secret"


@dataclass
class ConfigItem:
    """설정 항목"""
    key: str
    value: Any
    config_type: ConfigType
    description: str
    required: bool = True
    default_value: Any = None
    encrypted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (값 제외)"""
        return {
            "key": self.key,
            "type": self.config_type.value,
            "description": self.description,
            "required": self.required,
            "has_value": self.value is not None,
            "encrypted": self.encrypted
        }


@dataclass
class EnvironmentConfig:
    """환경 설정"""
    name: str
    config_items: Dict[str, ConfigItem]
    created_at: datetime
    updated_at: datetime
    version: str = "1.0.0"


class SecretManager:
    """시크릿 관리자"""
    
    def __init__(self, key_file: Optional[Path] = None):
        self.key_file = key_file or Path("secrets/.encryption_key")
        self.key_file.parent.mkdir(exist_ok=True)
        
        # 암호화 키 로드 또는 생성
        self.fernet = None
        if CRYPTO_AVAILABLE:
            self.fernet = self._get_or_create_key()
    
    def _get_or_create_key(self) -> Optional[Fernet]:
        """암호화 키 생성 또는 로드"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # 새 키 생성
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # 키 파일 권한 제한
                os.chmod(self.key_file, 0o600)
                safe_print(f"🔐 새 암호화 키 생성: {self.key_file}")
            
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"암호화 키 처리 실패: {e}")
            return None
    
    def encrypt(self, value: str) -> str:
        """값 암호화"""
        if not self.fernet:
            return value  # 암호화 불가능하면 원본 반환
        
        try:
            encrypted_value = self.fernet.encrypt(value.encode())
            return base64.b64encode(encrypted_value).decode()
        except Exception as e:
            logger.error(f"암호화 실패: {e}")
            return value
    
    def decrypt(self, encrypted_value: str) -> str:
        """값 복호화"""
        if not self.fernet:
            return encrypted_value  # 복호화 불가능하면 원본 반환
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted_value = self.fernet.decrypt(encrypted_bytes)
            return decrypted_value.decode()
        except Exception as e:
            logger.error(f"복호화 실패: {e}")
            return encrypted_value


class EnvironmentManager:
    """환경 설정 관리자"""
    
    def __init__(self, config_dir: Path = Path("config/environments")):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.secret_manager = SecretManager()
        self.environments: Dict[str, EnvironmentConfig] = {}
        
        # 기본 환경 템플릿
        self.default_templates = {
            "development": self._create_development_template(),
            "staging": self._create_staging_template(),
            "production": self._create_production_template()
        }
        
        self.load_all_environments()
        safe_print("⚙️ 환경 설정 관리자 초기화 완료")
    
    def _create_development_template(self) -> Dict[str, ConfigItem]:
        """개발 환경 템플릿"""
        return {
            "DEBUG": ConfigItem("DEBUG", True, ConfigType.BOOLEAN, "디버그 모드 활성화"),
            "LOG_LEVEL": ConfigItem("LOG_LEVEL", "DEBUG", ConfigType.STRING, "로그 레벨"),
            "DATABASE_URL": ConfigItem("DATABASE_URL", "sqlite:///python/baccarat_monitor_pwa_v3.db", 
                                     ConfigType.STRING, "데이터베이스 연결 URL"),
            "REDIS_URL": ConfigItem("REDIS_URL", "redis://localhost:6379/0", 
                                  ConfigType.STRING, "Redis 연결 URL"),
            "SECRET_KEY": ConfigItem("SECRET_KEY", None, ConfigType.SECRET, 
                                   "Flask 비밀 키", encrypted=True),
            "WEBSOCKET_PORT": ConfigItem("WEBSOCKET_PORT", 5001, ConfigType.INTEGER, 
                                       "WebSocket 서버 포트"),
            "API_PORT": ConfigItem("API_PORT", 8080, ConfigType.INTEGER, "API 서버 포트"),
            "CORS_ORIGINS": ConfigItem("CORS_ORIGINS", ["http://localhost:3000"], 
                                     ConfigType.JSON, "CORS 허용 도메인"),
            "EMAIL_ENABLED": ConfigItem("EMAIL_ENABLED", False, ConfigType.BOOLEAN, "이메일 기능 활성화"),
            "NOTIFICATION_WEBHOOK": ConfigItem("NOTIFICATION_WEBHOOK", None, 
                                             ConfigType.STRING, "알림 웹훅 URL", required=False),
        }
    
    def _create_staging_template(self) -> Dict[str, ConfigItem]:
        """스테이징 환경 템플릿"""
        template = self._create_development_template().copy()
        
        # 스테이징 환경 특화 설정
        template.update({
            "DEBUG": ConfigItem("DEBUG", False, ConfigType.BOOLEAN, "디버그 모드 비활성화"),
            "LOG_LEVEL": ConfigItem("LOG_LEVEL", "INFO", ConfigType.STRING, "로그 레벨"),
            "DATABASE_URL": ConfigItem("DATABASE_URL", None, ConfigType.SECRET, 
                                     "데이터베이스 연결 URL", encrypted=True),
            "REDIS_URL": ConfigItem("REDIS_URL", "redis://redis:6379/0", 
                                  ConfigType.STRING, "Redis 연결 URL"),
            "CORS_ORIGINS": ConfigItem("CORS_ORIGINS", ["https://staging.two-very-auto.com"], 
                                     ConfigType.JSON, "CORS 허용 도메인"),
            "SSL_ENABLED": ConfigItem("SSL_ENABLED", True, ConfigType.BOOLEAN, "SSL 활성화"),
            "MONITORING_ENABLED": ConfigItem("MONITORING_ENABLED", True, ConfigType.BOOLEAN, 
                                           "모니터링 활성화"),
        })
        
        return template
    
    def _create_production_template(self) -> Dict[str, ConfigItem]:
        """프로덕션 환경 템플릿"""
        template = self._create_staging_template().copy()
        
        # 프로덕션 환경 특화 설정
        template.update({
            "LOG_LEVEL": ConfigItem("LOG_LEVEL", "WARNING", ConfigType.STRING, "로그 레벨"),
            "CORS_ORIGINS": ConfigItem("CORS_ORIGINS", ["https://two-very-auto.com"], 
                                     ConfigType.JSON, "CORS 허용 도메인"),
            "RATE_LIMITING": ConfigItem("RATE_LIMITING", True, ConfigType.BOOLEAN, "Rate Limiting 활성화"),
            "BACKUP_ENABLED": ConfigItem("BACKUP_ENABLED", True, ConfigType.BOOLEAN, "백업 활성화"),
            "BACKUP_SCHEDULE": ConfigItem("BACKUP_SCHEDULE", "0 2 * * *", ConfigType.STRING, 
                                        "백업 스케줄 (Cron)"),
            "AWS_ACCESS_KEY_ID": ConfigItem("AWS_ACCESS_KEY_ID", None, ConfigType.SECRET, 
                                          "AWS 액세스 키", encrypted=True),
            "AWS_SECRET_ACCESS_KEY": ConfigItem("AWS_SECRET_ACCESS_KEY", None, ConfigType.SECRET, 
                                              "AWS 시크릿 키", encrypted=True),
            "SMTP_PASSWORD": ConfigItem("SMTP_PASSWORD", None, ConfigType.SECRET, 
                                      "SMTP 비밀번호", encrypted=True),
        })
        
        return template
    
    def create_environment(self, name: str, template_name: Optional[str] = None) -> bool:
        """환경 생성"""
        if name in self.environments:
            safe_print(f"환경이 이미 존재합니다: {name}")
            return False
        
        try:
            # 템플릿 기반 설정 생성
            if template_name and template_name in self.default_templates:
                config_items = self.default_templates[template_name].copy()
            else:
                config_items = self.default_templates["development"].copy()
            
            # 시크릿 값 생성
            for item in config_items.values():
                if item.config_type == ConfigType.SECRET and item.value is None:
                    if item.key == "SECRET_KEY":
                        item.value = self._generate_secret_key()
                    elif "PASSWORD" in item.key:
                        item.value = self._generate_password()
            
            # 환경 설정 생성
            environment = EnvironmentConfig(
                name=name,
                config_items=config_items,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.environments[name] = environment
            self.save_environment(name)
            
            safe_print(f"✅ 환경 생성 완료: {name}")
            return True
            
        except Exception as e:
            logger.error(f"환경 생성 실패: {e}")
            return False
    
    def _generate_secret_key(self) -> str:
        """시크릿 키 생성"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _generate_password(self) -> str:
        """패스워드 생성"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(16))
    
    def load_environment(self, name: str) -> bool:
        """환경 설정 로드"""
        config_file = self.config_dir / f"{name}.yml"
        
        if not config_file.exists():
            return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            config_items = {}
            for key, item_data in data.get('config_items', {}).items():
                config_items[key] = ConfigItem(
                    key=item_data['key'],
                    value=item_data['value'],
                    config_type=ConfigType(item_data['type']),
                    description=item_data['description'],
                    required=item_data.get('required', True),
                    default_value=item_data.get('default_value'),
                    encrypted=item_data.get('encrypted', False)
                )
            
            environment = EnvironmentConfig(
                name=data['name'],
                config_items=config_items,
                created_at=datetime.fromisoformat(data['created_at']),
                updated_at=datetime.fromisoformat(data['updated_at']),
                version=data.get('version', '1.0.0')
            )
            
            self.environments[name] = environment
            return True
            
        except Exception as e:
            logger.error(f"환경 설정 로드 실패 ({name}): {e}")
            return False
    
    def save_environment(self, name: str) -> bool:
        """환경 설정 저장"""
        if name not in self.environments:
            return False
        
        environment = self.environments[name]
        config_file = self.config_dir / f"{name}.yml"
        
        try:
            # 설정 데이터 준비
            config_data = {
                'name': environment.name,
                'created_at': environment.created_at.isoformat(),
                'updated_at': environment.updated_at.isoformat(),
                'version': environment.version,
                'config_items': {}
            }
            
            for key, item in environment.config_items.items():
                # 암호화된 값 처리
                value = item.value
                if item.encrypted and value is not None:
                    value = self.secret_manager.encrypt(str(value))
                
                config_data['config_items'][key] = {
                    'key': item.key,
                    'value': value,
                    'type': item.config_type.value,
                    'description': item.description,
                    'required': item.required,
                    'default_value': item.default_value,
                    'encrypted': item.encrypted
                }
            
            # YAML 파일로 저장
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            # 파일 권한 설정 (보안)
            os.chmod(config_file, 0o600)
            
            return True
            
        except Exception as e:
            logger.error(f"환경 설정 저장 실패 ({name}): {e}")
            return False
    
    def load_all_environments(self):
        """모든 환경 설정 로드"""
        for config_file in self.config_dir.glob("*.yml"):
            env_name = config_file.stem
            self.load_environment(env_name)
        
        safe_print(f"📁 환경 설정 로드 완료: {len(self.environments)}개")
    
    def get_config_value(self, environment: str, key: str, decrypt: bool = True) -> Any:
        """설정 값 조회"""
        if environment not in self.environments:
            return None
        
        env_config = self.environments[environment]
        if key not in env_config.config_items:
            return None
        
        item = env_config.config_items[key]
        value = item.value
        
        # 복호화 처리
        if decrypt and item.encrypted and value is not None:
            value = self.secret_manager.decrypt(str(value))
        
        # 타입 변환
        if value is not None:
            if item.config_type == ConfigType.INTEGER:
                return int(value)
            elif item.config_type == ConfigType.FLOAT:
                return float(value)
            elif item.config_type == ConfigType.BOOLEAN:
                return bool(value) if isinstance(value, bool) else str(value).lower() in ('true', '1', 'yes')
            elif item.config_type == ConfigType.JSON:
                return json.loads(value) if isinstance(value, str) else value
        
        return value
    
    def set_config_value(self, environment: str, key: str, value: Any) -> bool:
        """설정 값 설정"""
        if environment not in self.environments:
            return False
        
        env_config = self.environments[environment]
        if key not in env_config.config_items:
            return False
        
        try:
            item = env_config.config_items[key]
            
            # 타입 검증 및 변환
            if item.config_type == ConfigType.JSON and not isinstance(value, (dict, list)):
                value = json.loads(str(value))
            
            item.value = value
            env_config.updated_at = datetime.now()
            
            # 저장
            return self.save_environment(environment)
            
        except Exception as e:
            logger.error(f"설정 값 설정 실패 ({environment}.{key}): {e}")
            return False
    
    def export_env_file(self, environment: str, output_path: Optional[Path] = None) -> bool:
        """환경 변수 파일로 내보내기"""
        if environment not in self.environments:
            return False
        
        if output_path is None:
            output_path = Path(f".env.{environment}")
        
        try:
            env_config = self.environments[environment]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Two Very Auto - {environment.upper()} Environment\n")
                f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
                
                for key, item in env_config.config_items.items():
                    value = self.get_config_value(environment, key, decrypt=True)
                    
                    if value is not None:
                        # 주석으로 설명 추가
                        f.write(f"# {item.description}\n")
                        
                        # JSON 값 처리
                        if item.config_type == ConfigType.JSON:
                            value = json.dumps(value)
                        
                        f.write(f"{key}={value}\n\n")
            
            # 파일 권한 설정
            os.chmod(output_path, 0o600)
            
            safe_print(f"📄 환경 파일 내보내기 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"환경 파일 내보내기 실패: {e}")
            return False
    
    def validate_environment(self, environment: str) -> Dict[str, Any]:
        """환경 설정 검증"""
        if environment not in self.environments:
            return {"valid": False, "error": "Environment not found"}
        
        env_config = self.environments[environment]
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "items_count": len(env_config.config_items)
        }
        
        for key, item in env_config.config_items.items():
            # 필수 값 확인
            if item.required and item.value is None:
                validation_result["missing_required"].append(key)
                validation_result["errors"].append(f"Required config missing: {key}")
            
            # 타입 검증
            if item.value is not None:
                try:
                    if item.config_type == ConfigType.INTEGER:
                        int(item.value)
                    elif item.config_type == ConfigType.FLOAT:
                        float(item.value)
                    elif item.config_type == ConfigType.JSON:
                        if isinstance(item.value, str):
                            json.loads(item.value)
                except (ValueError, json.JSONDecodeError) as e:
                    validation_result["errors"].append(f"Invalid type for {key}: {e}")
        
        validation_result["valid"] = len(validation_result["errors"]) == 0
        
        return validation_result
    
    def get_environment_summary(self, environment: str) -> Dict[str, Any]:
        """환경 설정 요약"""
        if environment not in self.environments:
            return {}
        
        env_config = self.environments[environment]
        
        # 설정 타입별 개수
        type_counts = {}
        for item in env_config.config_items.values():
            type_name = item.config_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # 암호화된 항목 개수
        encrypted_count = sum(1 for item in env_config.config_items.values() if item.encrypted)
        
        # 설정된 값 개수
        configured_count = sum(1 for item in env_config.config_items.values() if item.value is not None)
        
        return {
            "name": environment,
            "version": env_config.version,
            "created_at": env_config.created_at.isoformat(),
            "updated_at": env_config.updated_at.isoformat(),
            "total_items": len(env_config.config_items),
            "configured_items": configured_count,
            "encrypted_items": encrypted_count,
            "type_distribution": type_counts,
            "config_items": [item.to_dict() for item in env_config.config_items.values()]
        }
    
    def list_environments(self) -> List[Dict[str, Any]]:
        """모든 환경 목록"""
        return [self.get_environment_summary(name) for name in self.environments.keys()]


# 전역 인스턴스
_environment_manager = None

def get_environment_manager() -> EnvironmentManager:
    """환경 관리자 인스턴스 반환"""
    global _environment_manager
    if _environment_manager is None:
        _environment_manager = EnvironmentManager()
    return _environment_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 환경 설정 관리자 테스트 ===")
    
    manager = get_environment_manager()
    
    # 개발 환경 생성
    if "development" not in manager.environments:
        manager.create_environment("development", "development")
    
    # 스테이징 환경 생성
    if "staging" not in manager.environments:
        manager.create_environment("staging", "staging")
    
    # 환경 목록 출력
    environments = manager.list_environments()
    safe_print(f"📋 환경 목록: {len(environments)}개")
    
    for env in environments:
        safe_print(f"  - {env['name']}: {env['configured_items']}/{env['total_items']} 항목 설정됨")
    
    # 개발 환경 설정 테스트
    dev_validation = manager.validate_environment("development")
    safe_print(f"✅ 개발 환경 검증: {dev_validation['valid']}")
    
    if dev_validation["missing_required"]:
        safe_print(f"⚠️ 필수 설정 누락: {dev_validation['missing_required']}")
    
    # 환경 파일 내보내기
    manager.export_env_file("development")
    safe_print("📄 .env.development 파일 생성 완료")
    
    safe_print("🏁 환경 설정 관리자 테스트 완료")