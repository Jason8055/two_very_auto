#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 데이터 암호화 & 개인정보 보호 시스템
AES-256 암호화, 개인정보 마스킹, GDPR 컴플라이언스
"""

import os
import json
import base64
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import re
import hmac

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
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
    safe_print("✅ 암호화 라이브러리 사용 가능")
except ImportError:
    CRYPTO_AVAILABLE = False
    safe_print("⚠️ cryptography 라이브러리 미설치. pip install cryptography 실행 필요")


class DataClassification(Enum):
    """데이터 분류"""
    PUBLIC = "public"              # 공개 데이터
    INTERNAL = "internal"          # 내부 데이터
    CONFIDENTIAL = "confidential"  # 기밀 데이터
    RESTRICTED = "restricted"      # 제한 데이터 (개인정보)
    TOP_SECRET = "top_secret"      # 극비 데이터


class PIIType(Enum):
    """개인정보 타입"""
    NAME = "name"                  # 이름
    EMAIL = "email"                # 이메일
    PHONE = "phone"                # 전화번호
    SSN = "ssn"                    # 주민등록번호
    CREDIT_CARD = "credit_card"    # 신용카드
    BANK_ACCOUNT = "bank_account"  # 계좌번호
    IP_ADDRESS = "ip_address"      # IP 주소
    DEVICE_ID = "device_id"        # 디바이스 ID
    LOCATION = "location"          # 위치 정보
    BIOMETRIC = "biometric"        # 생체정보


class EncryptionMethod(Enum):
    """암호화 방식"""
    FERNET = "fernet"              # 대칭키 (Fernet)
    AES_GCM = "aes_gcm"           # AES-GCM 모드
    AES_CBC = "aes_cbc"           # AES-CBC 모드
    RSA = "rsa"                   # RSA 비대칭키
    HASH = "hash"                 # 해시 (비가역)


@dataclass
class EncryptionConfig:
    """암호화 설정"""
    method: EncryptionMethod
    key_size: int
    use_salt: bool = True
    iterations: int = 100000
    backup_keys: bool = True


@dataclass
class EncryptedData:
    """암호화된 데이터"""
    encrypted_value: str
    encryption_method: EncryptionMethod
    key_id: str
    salt: Optional[str] = None
    iv: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class PIIRecord:
    """개인정보 기록"""
    record_id: str
    user_id: str
    pii_type: PIIType
    original_value: str
    encrypted_value: str
    masked_value: str
    classification: DataClassification
    created_at: datetime
    last_accessed: Optional[datetime] = None
    retention_until: Optional[datetime] = None
    consent_given: bool = False
    purpose: str = ""


class KeyManager:
    """암호화 키 관리자"""
    
    def __init__(self, key_store_path: Path = Path("security/keys")):
        self.key_store_path = key_store_path
        self.key_store_path.mkdir(parents=True, exist_ok=True)
        
        # 마스터 키
        self.master_key_file = self.key_store_path / "master.key"
        self.master_key = self._get_or_create_master_key()
        
        # 키 저장소
        self.keys: Dict[str, bytes] = {}
        self.key_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 키 회전 설정
        self.key_rotation_days = 90
        
        self._load_keys()
        safe_print("🔑 암호화 키 관리자 초기화 완료")
    
    def _get_or_create_master_key(self) -> bytes:
        """마스터 키 생성 또는 로드"""
        if self.master_key_file.exists():
            with open(self.master_key_file, 'rb') as f:
                master_key = f.read()
            safe_print("🔑 마스터 키 로드 완료")
        else:
            master_key = Fernet.generate_key()
            with open(self.master_key_file, 'wb') as f:
                f.write(master_key)
            os.chmod(self.master_key_file, 0o600)
            safe_print("🔑 새 마스터 키 생성 완료")
        
        return master_key
    
    def _load_keys(self):
        """저장된 키들 로드"""
        keys_db_path = self.key_store_path / "keys.db"
        if not keys_db_path.exists():
            return
        
        try:
            conn = sqlite3.connect(keys_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT key_id, encrypted_key, metadata FROM encryption_keys WHERE active = 1")
            rows = cursor.fetchall()
            
            fernet = Fernet(self.master_key)
            
            for key_id, encrypted_key, metadata_json in rows:
                try:
                    decrypted_key = fernet.decrypt(encrypted_key.encode())
                    self.keys[key_id] = decrypted_key
                    self.key_metadata[key_id] = json.loads(metadata_json)
                except Exception as e:
                    logger.error(f"키 로드 실패: {key_id}, {e}")
            
            conn.close()
            safe_print(f"🔑 {len(self.keys)}개 키 로드 완료")
            
        except Exception as e:
            logger.error(f"키 데이터베이스 로드 실패: {e}")
    
    def create_key(self, key_id: str, method: EncryptionMethod, key_size: int = 256) -> str:
        """새 암호화 키 생성"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("암호화 라이브러리를 사용할 수 없습니다")
        
        if method == EncryptionMethod.FERNET:
            key = Fernet.generate_key()
        elif method in [EncryptionMethod.AES_GCM, EncryptionMethod.AES_CBC]:
            key = secrets.token_bytes(key_size // 8)
        elif method == EncryptionMethod.RSA:
            # RSA 키 쌍 생성
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        else:
            raise ValueError(f"지원하지 않는 암호화 방식: {method}")
        
        # 키 저장
        self.keys[key_id] = key
        self.key_metadata[key_id] = {
            "method": method.value,
            "key_size": key_size,
            "created_at": datetime.now().isoformat(),
            "last_rotated": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        # 데이터베이스에 저장
        self._save_key_to_db(key_id, key)
        
        safe_print(f"🔑 새 키 생성: {key_id} ({method.value})")
        return key_id
    
    def _save_key_to_db(self, key_id: str, key: bytes):
        """키를 데이터베이스에 저장"""
        keys_db_path = self.key_store_path / "keys.db"
        
        # 데이터베이스 초기화
        conn = sqlite3.connect(keys_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS encryption_keys (
                key_id TEXT PRIMARY KEY,
                encrypted_key TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # 마스터 키로 암호화하여 저장
        fernet = Fernet(self.master_key)
        encrypted_key = fernet.encrypt(key).decode()
        
        cursor.execute("""
            INSERT OR REPLACE INTO encryption_keys (key_id, encrypted_key, metadata)
            VALUES (?, ?, ?)
        """, (key_id, encrypted_key, json.dumps(self.key_metadata[key_id])))
        
        conn.commit()
        conn.close()
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """키 조회"""
        key = self.keys.get(key_id)
        if key and key_id in self.key_metadata:
            # 사용 횟수 증가
            self.key_metadata[key_id]["usage_count"] += 1
        return key
    
    def rotate_key(self, key_id: str) -> str:
        """키 회전"""
        if key_id not in self.key_metadata:
            raise ValueError(f"키를 찾을 수 없습니다: {key_id}")
        
        metadata = self.key_metadata[key_id]
        method = EncryptionMethod(metadata["method"])
        key_size = metadata["key_size"]
        
        # 새 키 생성
        new_key_id = f"{key_id}_v{int(datetime.now().timestamp())}"
        self.create_key(new_key_id, method, key_size)
        
        # 이전 키 비활성화 (즉시 삭제하지 않음)
        metadata["rotated_at"] = datetime.now().isoformat()
        metadata["active"] = False
        
        safe_print(f"🔄 키 회전 완료: {key_id} → {new_key_id}")
        return new_key_id
    
    def check_key_rotation_needed(self) -> List[str]:
        """회전이 필요한 키 목록"""
        keys_to_rotate = []
        cutoff_date = datetime.now() - timedelta(days=self.key_rotation_days)
        
        for key_id, metadata in self.key_metadata.items():
            last_rotated = datetime.fromisoformat(metadata["last_rotated"])
            if last_rotated < cutoff_date:
                keys_to_rotate.append(key_id)
        
        return keys_to_rotate


class DataEncryption:
    """데이터 암호화"""
    
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.default_configs = {
            DataClassification.PUBLIC: EncryptionConfig(
                EncryptionMethod.HASH, 256, use_salt=True
            ),
            DataClassification.INTERNAL: EncryptionConfig(
                EncryptionMethod.FERNET, 256, use_salt=True
            ),
            DataClassification.CONFIDENTIAL: EncryptionConfig(
                EncryptionMethod.AES_GCM, 256, use_salt=True
            ),
            DataClassification.RESTRICTED: EncryptionConfig(
                EncryptionMethod.AES_GCM, 256, use_salt=True, backup_keys=True
            ),
            DataClassification.TOP_SECRET: EncryptionConfig(
                EncryptionMethod.AES_GCM, 256, use_salt=True, backup_keys=True
            )
        }
        
        safe_print("🔒 데이터 암호화 시스템 초기화 완료")
    
    def encrypt(self, data: Union[str, bytes], classification: DataClassification, 
                key_id: Optional[str] = None) -> EncryptedData:
        """데이터 암호화"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("암호화 라이브러리를 사용할 수 없습니다")
        
        config = self.default_configs[classification]
        
        # 키 ID 결정
        if not key_id:
            key_id = f"{classification.value}_{config.method.value}"
            if key_id not in self.key_manager.keys:
                self.key_manager.create_key(key_id, config.method, config.key_size)
        
        # 데이터 준비
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 암호화 수행
        if config.method == EncryptionMethod.FERNET:
            return self._encrypt_fernet(data, key_id)
        elif config.method == EncryptionMethod.AES_GCM:
            return self._encrypt_aes_gcm(data, key_id, config.use_salt)
        elif config.method == EncryptionMethod.AES_CBC:
            return self._encrypt_aes_cbc(data, key_id, config.use_salt)
        elif config.method == EncryptionMethod.HASH:
            return self._hash_data(data, config.use_salt)
        else:
            raise ValueError(f"지원하지 않는 암호화 방식: {config.method}")
    
    def _encrypt_fernet(self, data: bytes, key_id: str) -> EncryptedData:
        """Fernet 암호화"""
        key = self.key_manager.get_key(key_id)
        if not key:
            raise ValueError(f"키를 찾을 수 없습니다: {key_id}")
        
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data)
        
        return EncryptedData(
            encrypted_value=base64.b64encode(encrypted).decode(),
            encryption_method=EncryptionMethod.FERNET,
            key_id=key_id
        )
    
    def _encrypt_aes_gcm(self, data: bytes, key_id: str, use_salt: bool) -> EncryptedData:
        """AES-GCM 암호화"""
        key = self.key_manager.get_key(key_id)
        if not key:
            raise ValueError(f"키를 찾을 수 없습니다: {key_id}")
        
        # IV 생성
        iv = secrets.token_bytes(12)  # GCM에서는 12바이트 권장
        
        # 솔트 처리
        salt = None
        if use_salt:
            salt = secrets.token_bytes(16)
            # PBKDF2로 키 파생
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            derived_key = kdf.derive(key)
        else:
            derived_key = key[:32]  # AES-256
        
        # 암호화
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        
        # 태그 추가
        encrypted_with_tag = encrypted_data + encryptor.tag
        
        return EncryptedData(
            encrypted_value=base64.b64encode(encrypted_with_tag).decode(),
            encryption_method=EncryptionMethod.AES_GCM,
            key_id=key_id,
            salt=base64.b64encode(salt).decode() if salt else None,
            iv=base64.b64encode(iv).decode()
        )
    
    def _encrypt_aes_cbc(self, data: bytes, key_id: str, use_salt: bool) -> EncryptedData:
        """AES-CBC 암호화"""
        key = self.key_manager.get_key(key_id)
        if not key:
            raise ValueError(f"키를 찾을 수 없습니다: {key_id}")
        
        # 패딩 추가 (PKCS7)
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padded_data = data + bytes([padding_length]) * padding_length
        
        # IV 생성
        iv = secrets.token_bytes(16)
        
        # 솔트 처리
        salt = None
        if use_salt:
            salt = secrets.token_bytes(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            derived_key = kdf.derive(key)
        else:
            derived_key = key[:32]
        
        # 암호화
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        return EncryptedData(
            encrypted_value=base64.b64encode(encrypted_data).decode(),
            encryption_method=EncryptionMethod.AES_CBC,
            key_id=key_id,
            salt=base64.b64encode(salt).decode() if salt else None,
            iv=base64.b64encode(iv).decode()
        )
    
    def _hash_data(self, data: bytes, use_salt: bool) -> EncryptedData:
        """데이터 해싱 (비가역)"""
        salt = None
        if use_salt:
            salt = secrets.token_bytes(16)
            data = salt + data
        
        hash_digest = hashlib.sha256(data).digest()
        
        return EncryptedData(
            encrypted_value=base64.b64encode(hash_digest).decode(),
            encryption_method=EncryptionMethod.HASH,
            key_id="hash",
            salt=base64.b64encode(salt).decode() if salt else None
        )
    
    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """데이터 복호화"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("암호화 라이브러리를 사용할 수 없습니다")
        
        if encrypted_data.encryption_method == EncryptionMethod.HASH:
            raise ValueError("해시된 데이터는 복호화할 수 없습니다")
        
        encrypted_bytes = base64.b64decode(encrypted_data.encrypted_value)
        
        if encrypted_data.encryption_method == EncryptionMethod.FERNET:
            return self._decrypt_fernet(encrypted_bytes, encrypted_data.key_id)
        elif encrypted_data.encryption_method == EncryptionMethod.AES_GCM:
            return self._decrypt_aes_gcm(encrypted_bytes, encrypted_data)
        elif encrypted_data.encryption_method == EncryptionMethod.AES_CBC:
            return self._decrypt_aes_cbc(encrypted_bytes, encrypted_data)
        else:
            raise ValueError(f"지원하지 않는 복호화 방식: {encrypted_data.encryption_method}")
    
    def _decrypt_fernet(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Fernet 복호화"""
        key = self.key_manager.get_key(key_id)
        if not key:
            raise ValueError(f"키를 찾을 수 없습니다: {key_id}")
        
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data)
    
    def _decrypt_aes_gcm(self, encrypted_data: bytes, encrypted_info: EncryptedData) -> bytes:
        """AES-GCM 복호화"""
        key = self.key_manager.get_key(encrypted_info.key_id)
        if not key:
            raise ValueError(f"키를 찾을 수 없습니다: {encrypted_info.key_id}")
        
        # IV와 솔트 복원
        iv = base64.b64decode(encrypted_info.iv)
        
        # 키 파생
        if encrypted_info.salt:
            salt = base64.b64decode(encrypted_info.salt)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            derived_key = kdf.derive(key)
        else:
            derived_key = key[:32]
        
        # 태그 분리 (마지막 16바이트)
        encrypted_content = encrypted_data[:-16]
        tag = encrypted_data[-16:]
        
        # 복호화
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_content) + decryptor.finalize()
    
    def _decrypt_aes_cbc(self, encrypted_data: bytes, encrypted_info: EncryptedData) -> bytes:
        """AES-CBC 복호화"""
        key = self.key_manager.get_key(encrypted_info.key_id)
        if not key:
            raise ValueError(f"키를 찾을 수 없습니다: {encrypted_info.key_id}")
        
        # IV와 솔트 복원
        iv = base64.b64decode(encrypted_info.iv)
        
        # 키 파생
        if encrypted_info.salt:
            salt = base64.b64decode(encrypted_info.salt)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            derived_key = kdf.derive(key)
        else:
            derived_key = key[:32]
        
        # 복호화
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # 패딩 제거
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]


class PIIMasker:
    """개인정보 마스킹"""
    
    def __init__(self):
        self.masking_patterns = {
            PIIType.NAME: self._mask_name,
            PIIType.EMAIL: self._mask_email,
            PIIType.PHONE: self._mask_phone,
            PIIType.SSN: self._mask_ssn,
            PIIType.CREDIT_CARD: self._mask_credit_card,
            PIIType.BANK_ACCOUNT: self._mask_bank_account,
            PIIType.IP_ADDRESS: self._mask_ip_address,
        }
        
        # 자동 탐지 패턴
        self.detection_patterns = {
            PIIType.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            PIIType.PHONE: re.compile(r'\b\d{2,3}-\d{3,4}-\d{4}\b'),
            PIIType.CREDIT_CARD: re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
            PIIType.IP_ADDRESS: re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
        }
        
        safe_print("🎭 개인정보 마스킹 시스템 초기화 완료")
    
    def mask_data(self, data: str, pii_type: PIIType) -> str:
        """데이터 마스킹"""
        masker = self.masking_patterns.get(pii_type)
        if masker:
            return masker(data)
        else:
            # 기본 마스킹 (중간 부분 마스킹)
            return self._mask_default(data)
    
    def _mask_name(self, name: str) -> str:
        """이름 마스킹"""
        if len(name) <= 2:
            return name[0] + "*"
        elif len(name) <= 4:
            return name[0] + "*" * (len(name) - 2) + name[-1]
        else:
            return name[0] + name[1] + "*" * (len(name) - 3) + name[-1]
    
    def _mask_email(self, email: str) -> str:
        """이메일 마스킹"""
        if "@" not in email:
            return self._mask_default(email)
        
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def _mask_phone(self, phone: str) -> str:
        """전화번호 마스킹"""
        # 숫자만 추출
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 11:
            return digits[:3] + "-" + "*" * 4 + "-" + digits[-4:]
        elif len(digits) >= 8:
            return digits[:2] + "-" + "*" * 3 + "-" + digits[-4:]
        else:
            return self._mask_default(phone)
    
    def _mask_ssn(self, ssn: str) -> str:
        """주민등록번호 마스킹"""
        digits = re.sub(r'\D', '', ssn)
        if len(digits) == 13:
            return digits[:6] + "-" + digits[6] + "******"
        else:
            return self._mask_default(ssn)
    
    def _mask_credit_card(self, card: str) -> str:
        """신용카드 마스킹"""
        digits = re.sub(r'\D', '', card)
        if len(digits) >= 12:
            return digits[:4] + "-" + "*" * 4 + "-" + "*" * 4 + "-" + digits[-4:]
        else:
            return self._mask_default(card)
    
    def _mask_bank_account(self, account: str) -> str:
        """계좌번호 마스킹"""
        if len(account) > 6:
            return account[:3] + "*" * (len(account) - 6) + account[-3:]
        else:
            return "*" * len(account)
    
    def _mask_ip_address(self, ip: str) -> str:
        """IP 주소 마스킹"""
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.**"
        else:
            return self._mask_default(ip)
    
    def _mask_default(self, data: str) -> str:
        """기본 마스킹"""
        if len(data) <= 2:
            return "*" * len(data)
        elif len(data) <= 6:
            return data[0] + "*" * (len(data) - 2) + data[-1]
        else:
            visible_chars = max(2, len(data) // 4)
            masked_chars = len(data) - (visible_chars * 2)
            return data[:visible_chars] + "*" * masked_chars + data[-visible_chars:]
    
    def detect_pii_in_text(self, text: str) -> Dict[PIIType, List[str]]:
        """텍스트에서 개인정보 자동 탐지"""
        detected = {}
        
        for pii_type, pattern in self.detection_patterns.items():
            matches = pattern.findall(text)
            if matches:
                detected[pii_type] = matches
        
        return detected
    
    def mask_text_pii(self, text: str) -> str:
        """텍스트의 개인정보 자동 마스킹"""
        result = text
        
        for pii_type, pattern in self.detection_patterns.items():
            def replace_match(match):
                return self.mask_data(match.group(), pii_type)
            
            result = pattern.sub(replace_match, result)
        
        return result


class PIIManager:
    """개인정보 관리자"""
    
    def __init__(self, db_path: Path = Path("security/pii.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.key_manager = KeyManager()
        self.encryptor = DataEncryption(self.key_manager)
        self.masker = PIIMasker()
        
        # 보존 기간 설정 (GDPR 준수)
        self.retention_periods = {
            PIIType.NAME: 2555,      # 7년
            PIIType.EMAIL: 1095,     # 3년
            PIIType.PHONE: 1095,     # 3년
            PIIType.SSN: 2555,       # 7년
            PIIType.CREDIT_CARD: 90, # 3개월
            PIIType.BANK_ACCOUNT: 365, # 1년
        }
        
        self._initialize_database()
        safe_print("👤 개인정보 관리자 초기화 완료")
    
    def _initialize_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 개인정보 기록 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pii_records (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                pii_type TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                masked_value TEXT NOT NULL,
                classification TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                retention_until TIMESTAMP,
                consent_given BOOLEAN DEFAULT FALSE,
                purpose TEXT,
                key_id TEXT NOT NULL,
                encryption_method TEXT NOT NULL
            )
        """)
        
        # 개인정보 처리 로그
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pii_access_log (
                log_id TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                user_id TEXT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                purpose TEXT,
                FOREIGN KEY (record_id) REFERENCES pii_records (record_id)
            )
        """)
        
        # 동의 기록
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consent_records (
                consent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                purpose TEXT NOT NULL,
                given_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                revoked_at TIMESTAMP,
                version TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def store_pii(self, user_id: str, pii_type: PIIType, value: str, 
                  purpose: str, consent_given: bool = False) -> str:
        """개인정보 저장"""
        try:
            # 분류 결정
            classification = DataClassification.RESTRICTED
            
            # 암호화
            encrypted_data = self.encryptor.encrypt(value, classification)
            
            # 마스킹
            masked_value = self.masker.mask_data(value, pii_type)
            
            # 보존 기간 계산
            retention_days = self.retention_periods.get(pii_type, 365)
            retention_until = datetime.now() + timedelta(days=retention_days)
            
            # 기록 ID 생성
            record_id = f"pii_{secrets.token_urlsafe(16)}"
            
            # 데이터베이스 저장
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO pii_records (
                    record_id, user_id, pii_type, encrypted_value, masked_value,
                    classification, retention_until, consent_given, purpose,
                    key_id, encryption_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id, user_id, pii_type.value, encrypted_data.encrypted_value,
                masked_value, classification.value, retention_until, consent_given,
                purpose, encrypted_data.key_id, encrypted_data.encryption_method.value
            ))
            
            conn.commit()
            conn.close()
            
            # 접근 로그
            self._log_pii_access(record_id, user_id, "store", purpose)
            
            safe_print(f"🔒 개인정보 저장 완료: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"개인정보 저장 실패: {e}")
            raise
    
    def retrieve_pii(self, record_id: str, user_id: str, purpose: str, 
                    masked_only: bool = False) -> Optional[str]:
        """개인정보 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT encrypted_value, masked_value, key_id, encryption_method,
                       retention_until, consent_given
                FROM pii_records 
                WHERE record_id = ? AND user_id = ?
            """, (record_id, user_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            encrypted_value, masked_value, key_id, encryption_method, retention_until, consent_given = row
            
            # 보존 기간 확인
            if retention_until and datetime.now() > datetime.fromisoformat(retention_until):
                logger.warning(f"보존 기간 만료된 개인정보 접근 시도: {record_id}")
                return None
            
            # 동의 확인
            if not consent_given:
                logger.warning(f"동의 없는 개인정보 접근 시도: {record_id}")
            
            # 마스킹된 데이터만 요청하는 경우
            if masked_only:
                self._log_pii_access(record_id, user_id, "retrieve_masked", purpose)
                return masked_value
            
            # 복호화
            encrypted_data = EncryptedData(
                encrypted_value=encrypted_value,
                encryption_method=EncryptionMethod(encryption_method),
                key_id=key_id
            )
            
            decrypted_data = self.encryptor.decrypt(encrypted_data)
            
            # 접근 로그
            self._log_pii_access(record_id, user_id, "retrieve", purpose)
            
            # 마지막 접근 시간 업데이트
            self._update_last_accessed(record_id)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"개인정보 조회 실패: {e}")
            raise
    
    def delete_pii(self, record_id: str, user_id: str, reason: str) -> bool:
        """개인정보 삭제 (GDPR 잊혀질 권리)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 존재 확인
            cursor.execute("""
                SELECT record_id FROM pii_records 
                WHERE record_id = ? AND user_id = ?
            """, (record_id, user_id))
            
            if not cursor.fetchone():
                conn.close()
                return False
            
            # 삭제
            cursor.execute("""
                DELETE FROM pii_records 
                WHERE record_id = ? AND user_id = ?
            """, (record_id, user_id))
            
            conn.commit()
            conn.close()
            
            # 삭제 로그
            self._log_pii_access(record_id, user_id, "delete", reason)
            
            safe_print(f"🗑️ 개인정보 삭제 완료: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"개인정보 삭제 실패: {e}")
            return False
    
    def _log_pii_access(self, record_id: str, user_id: str, action: str, purpose: str):
        """개인정보 접근 로그"""
        log_id = f"log_{secrets.token_urlsafe(12)}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pii_access_log (log_id, record_id, user_id, action, purpose)
            VALUES (?, ?, ?, ?, ?)
        """, (log_id, record_id, user_id, action, purpose))
        
        conn.commit()
        conn.close()
    
    def _update_last_accessed(self, record_id: str):
        """마지막 접근 시간 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE pii_records SET last_accessed = CURRENT_TIMESTAMP
            WHERE record_id = ?
        """, (record_id,))
        
        conn.commit()
        conn.close()
    
    def cleanup_expired_data(self) -> int:
        """보존 기간 만료 데이터 정리"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 만료된 데이터 조회
        cursor.execute("""
            SELECT record_id, user_id FROM pii_records
            WHERE retention_until < CURRENT_TIMESTAMP
        """)
        
        expired_records = cursor.fetchall()
        
        # 만료된 데이터 삭제
        cursor.execute("""
            DELETE FROM pii_records
            WHERE retention_until < CURRENT_TIMESTAMP
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        # 삭제 로그
        for record_id, user_id in expired_records:
            self._log_pii_access(record_id, user_id, "auto_delete", "retention_period_expired")
        
        if deleted_count > 0:
            safe_print(f"🧹 만료된 개인정보 정리: {deleted_count}건")
        
        return deleted_count
    
    def get_user_pii_report(self, user_id: str) -> Dict[str, Any]:
        """사용자 개인정보 처리 현황 보고서 (GDPR 준수)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 저장된 개인정보
        cursor.execute("""
            SELECT pii_type, masked_value, created_at, retention_until, purpose
            FROM pii_records WHERE user_id = ?
        """, (user_id,))
        
        stored_pii = cursor.fetchall()
        
        # 접근 로그
        cursor.execute("""
            SELECT action, timestamp, purpose FROM pii_access_log
            WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50
        """, (user_id,))
        
        access_logs = cursor.fetchall()
        
        # 동의 기록
        cursor.execute("""
            SELECT consent_type, purpose, given_at, expires_at, revoked_at
            FROM consent_records WHERE user_id = ?
        """, (user_id,))
        
        consents = cursor.fetchall()
        
        conn.close()
        
        return {
            "user_id": user_id,
            "report_generated": datetime.now().isoformat(),
            "stored_pii": [
                {
                    "type": pii[0],
                    "masked_value": pii[1],
                    "stored_since": pii[2],
                    "retention_until": pii[3],
                    "purpose": pii[4]
                } for pii in stored_pii
            ],
            "recent_access": [
                {
                    "action": log[0],
                    "timestamp": log[1],
                    "purpose": log[2]
                } for log in access_logs
            ],
            "consents": [
                {
                    "type": consent[0],
                    "purpose": consent[1],
                    "given_at": consent[2],
                    "expires_at": consent[3],
                    "revoked_at": consent[4]
                } for consent in consents
            ]
        }


# 전역 개인정보 관리자 인스턴스
_pii_manager = None

def get_pii_manager() -> PIIManager:
    """개인정보 관리자 인스턴스 반환"""
    global _pii_manager
    if _pii_manager is None:
        _pii_manager = PIIManager()
    return _pii_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 데이터 암호화 & 개인정보 보호 시스템 테스트 ===")
    
    if not CRYPTO_AVAILABLE:
        safe_print("❌ 암호화 라이브러리가 필요합니다. pip install cryptography")
        sys.exit(1)
    
    pii_manager = get_pii_manager()
    
    # 개인정보 저장 테스트
    record_id = pii_manager.store_pii(
        user_id="user_123",
        pii_type=PIIType.EMAIL,
        value="user@example.com",
        purpose="사용자 계정 관리",
        consent_given=True
    )
    safe_print(f"📧 이메일 저장: {record_id}")
    
    # 마스킹된 데이터 조회 테스트
    masked_email = pii_manager.retrieve_pii(
        record_id=record_id,
        user_id="user_123",
        purpose="화면 표시",
        masked_only=True
    )
    safe_print(f"🎭 마스킹된 이메일: {masked_email}")
    
    # 원본 데이터 조회 테스트
    original_email = pii_manager.retrieve_pii(
        record_id=record_id,
        user_id="user_123",
        purpose="이메일 발송"
    )
    safe_print(f"📧 원본 이메일: {original_email}")
    
    # 텍스트 PII 자동 마스킹 테스트
    masker = PIIMasker()
    test_text = "연락처: 010-1234-5678, 이메일: test@example.com"
    masked_text = masker.mask_text_pii(test_text)
    safe_print(f"🔍 자동 마스킹: {masked_text}")
    
    # 사용자 개인정보 보고서 테스트
    report = pii_manager.get_user_pii_report("user_123")
    safe_print(f"📋 개인정보 보고서: {len(report['stored_pii'])}개 항목")
    
    safe_print("🏁 데이터 암호화 & 개인정보 보호 시스템 테스트 완료")