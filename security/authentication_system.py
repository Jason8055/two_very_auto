#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - JWT 인증 & 권한 관리 시스템
엔터프라이즈급 보안 인증 및 권한 관리
"""

import jwt
import hashlib
import secrets
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import bcrypt
import time
from functools import wraps
import redis
import sqlite3
from threading import Lock

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class UserRole(Enum):
    """사용자 역할"""
    SUPER_ADMIN = "super_admin"      # 최고 관리자
    ADMIN = "admin"                  # 관리자
    OPERATOR = "operator"            # 운영자
    ANALYST = "analyst"              # 분석가
    VIEWER = "viewer"                # 조회자
    USER = "user"                    # 일반 사용자
    GUEST = "guest"                  # 게스트


class Permission(Enum):
    """권한 정의"""
    # 시스템 관리
    SYSTEM_ADMIN = "system.admin"
    SYSTEM_CONFIG = "system.config"
    SYSTEM_MONITOR = "system.monitor"
    
    # 사용자 관리
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    
    # 바카라 게임
    GAME_PLAY = "game.play"
    GAME_ANALYZE = "game.analyze"
    GAME_MANAGE = "game.manage"
    
    # 데이터 관리
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # AI 기능
    AI_PREDICT = "ai.predict"
    AI_TRAIN = "ai.train"
    AI_MANAGE = "ai.manage"
    
    # 보고서 및 분석
    REPORT_VIEW = "report.view"
    REPORT_CREATE = "report.create"
    REPORT_EXPORT = "report.export"
    
    # 감사 및 로그
    AUDIT_VIEW = "audit.view"
    AUDIT_MANAGE = "audit.manage"


class AuthStatus(Enum):
    """인증 상태"""
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"


@dataclass
class User:
    """사용자 정보"""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    role: UserRole
    permissions: Set[Permission]
    is_active: bool = True
    is_locked: bool = False
    failed_attempts: int = 0
    last_login: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    session_timeout: int = 3600  # 1시간
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class AuthToken:
    """인증 토큰"""
    token: str
    user_id: str
    issued_at: datetime
    expires_at: datetime
    token_type: str = "access"  # access, refresh
    permissions: Set[Permission] = None


@dataclass
class LoginAttempt:
    """로그인 시도 기록"""
    username: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    status: AuthStatus
    details: Optional[Dict[str, Any]] = None


class SecurityConfig:
    """보안 설정"""
    
    # JWT 설정
    JWT_SECRET_KEY = secrets.token_urlsafe(64)
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # 패스워드 정책
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    PASSWORD_HISTORY_COUNT = 5
    
    # 계정 보안
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    SESSION_TIMEOUT_MINUTES = 60
    
    # Rate Limiting
    LOGIN_RATE_LIMIT = 10  # per minute
    API_RATE_LIMIT = 100   # per minute


class PasswordManager:
    """패스워드 관리자"""
    
    @staticmethod
    def generate_salt() -> str:
        """솔트 생성"""
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """패스워드 해싱"""
        # bcrypt 사용
        password_bytes = (password + salt).encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, salt: str, password_hash: str) -> bool:
        """패스워드 검증"""
        password_bytes = (password + salt).encode('utf-8')
        hash_bytes = password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    
    @staticmethod
    def validate_password_policy(password: str) -> Dict[str, Any]:
        """패스워드 정책 검증"""
        result = {
            "valid": True,
            "errors": []
        }
        
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            result["errors"].append(f"패스워드는 최소 {SecurityConfig.MIN_PASSWORD_LENGTH}자 이상이어야 합니다")
        
        if SecurityConfig.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            result["errors"].append("패스워드는 대문자를 포함해야 합니다")
        
        if SecurityConfig.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            result["errors"].append("패스워드는 소문자를 포함해야 합니다")
        
        if SecurityConfig.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            result["errors"].append("패스워드는 숫자를 포함해야 합니다")
        
        if SecurityConfig.REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            result["errors"].append("패스워드는 특수문자를 포함해야 합니다")
        
        result["valid"] = len(result["errors"]) == 0
        return result


class RolePermissionManager:
    """역할 권한 관리자"""
    
    def __init__(self):
        self.role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, Set[Permission]]:
        """역할별 기본 권한 설정"""
        return {
            UserRole.SUPER_ADMIN: {
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_MONITOR,
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_DELETE,
                Permission.GAME_PLAY,
                Permission.GAME_ANALYZE,
                Permission.GAME_MANAGE,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_DELETE,
                Permission.DATA_EXPORT,
                Permission.AI_PREDICT,
                Permission.AI_TRAIN,
                Permission.AI_MANAGE,
                Permission.REPORT_VIEW,
                Permission.REPORT_CREATE,
                Permission.REPORT_EXPORT,
                Permission.AUDIT_VIEW,
                Permission.AUDIT_MANAGE
            },
            
            UserRole.ADMIN: {
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_MONITOR,
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.GAME_PLAY,
                Permission.GAME_ANALYZE,
                Permission.GAME_MANAGE,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_EXPORT,
                Permission.AI_PREDICT,
                Permission.AI_TRAIN,
                Permission.REPORT_VIEW,
                Permission.REPORT_CREATE,
                Permission.REPORT_EXPORT,
                Permission.AUDIT_VIEW
            },
            
            UserRole.OPERATOR: {
                Permission.SYSTEM_MONITOR,
                Permission.USER_READ,
                Permission.GAME_PLAY,
                Permission.GAME_ANALYZE,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.AI_PREDICT,
                Permission.REPORT_VIEW,
                Permission.REPORT_CREATE
            },
            
            UserRole.ANALYST: {
                Permission.GAME_ANALYZE,
                Permission.DATA_READ,
                Permission.AI_PREDICT,
                Permission.REPORT_VIEW,
                Permission.REPORT_CREATE,
                Permission.REPORT_EXPORT
            },
            
            UserRole.VIEWER: {
                Permission.DATA_READ,
                Permission.REPORT_VIEW
            },
            
            UserRole.USER: {
                Permission.GAME_PLAY,
                Permission.DATA_READ,
                Permission.AI_PREDICT
            },
            
            UserRole.GUEST: {
                Permission.GAME_PLAY
            }
        }
    
    def get_permissions(self, role: UserRole) -> Set[Permission]:
        """역할의 권한 조회"""
        return self.role_permissions.get(role, set())
    
    def has_permission(self, role: UserRole, permission: Permission) -> bool:
        """권한 확인"""
        return permission in self.get_permissions(role)


class JWTManager:
    """JWT 토큰 관리자"""
    
    def __init__(self, secret_key: str = SecurityConfig.JWT_SECRET_KEY):
        self.secret_key = secret_key
        self.algorithm = SecurityConfig.JWT_ALGORITHM
    
    def create_access_token(self, user: User) -> str:
        """액세스 토큰 생성"""
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "permissions": [perm.value for perm in user.permissions],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES),
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """리프레시 토큰 생성"""
        payload = {
            "user_id": user.user_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """토큰 검증"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 만료 시간 확인
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                return {"valid": False, "error": "token_expired"}
            
            return {"valid": True, "payload": payload}
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "token_expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "token_invalid"}
        except Exception as e:
            return {"valid": False, "error": f"token_error: {str(e)}"}


class AuthenticationSystem:
    """인증 시스템"""
    
    def __init__(self, db_path: Path = Path("security/auth.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(exist_ok=True)
        
        # 컴포넌트 초기화
        self.password_manager = PasswordManager()
        self.role_manager = RolePermissionManager()
        self.jwt_manager = JWTManager()
        
        # 세션 관리 (Redis 사용 권장, 여기서는 메모리 사용)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.login_attempts: List[LoginAttempt] = []
        self.session_lock = Lock()
        
        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = {}
        
        # 데이터베이스 초기화
        self._initialize_database()
        
        # 기본 사용자 생성
        self._create_default_users()
        
        safe_print("🔐 JWT 인증 & 권한 관리 시스템 초기화 완료")
    
    def _initialize_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                permissions TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_locked BOOLEAN DEFAULT FALSE,
                failed_attempts INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_timeout INTEGER DEFAULT 3600
            )
        """)
        
        # 로그인 시도 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                details TEXT
            )
        """)
        
        # 세션 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _create_default_users(self):
        """기본 사용자 생성"""
        default_users = [
            {
                "username": "admin",
                "email": "admin@two-very-auto.com",
                "password": "Admin123!@#",
                "role": UserRole.SUPER_ADMIN
            },
            {
                "username": "operator",
                "email": "operator@two-very-auto.com",
                "password": "Operator123!",
                "role": UserRole.OPERATOR
            }
        ]
        
        for user_data in default_users:
            if not self.get_user_by_username(user_data["username"]):
                self.create_user(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=user_data["password"],
                    role=user_data["role"]
                )
                safe_print(f"✅ 기본 사용자 생성: {user_data['username']}")
    
    def create_user(self, username: str, email: str, password: str, role: UserRole) -> Dict[str, Any]:
        """사용자 생성"""
        try:
            # 패스워드 정책 검증
            policy_check = self.password_manager.validate_password_policy(password)
            if not policy_check["valid"]:
                return {
                    "success": False,
                    "error": "password_policy_violation",
                    "details": policy_check["errors"]
                }
            
            # 중복 확인
            if self.get_user_by_username(username):
                return {"success": False, "error": "username_exists"}
            
            if self.get_user_by_email(email):
                return {"success": False, "error": "email_exists"}
            
            # 사용자 생성
            user_id = secrets.token_urlsafe(16)
            salt = self.password_manager.generate_salt()
            password_hash = self.password_manager.hash_password(password, salt)
            permissions = self.role_manager.get_permissions(role)
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                role=role,
                permissions=permissions
            )
            
            # 데이터베이스 저장
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, email, password_hash, salt, role, permissions,
                    is_active, is_locked, failed_attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.user_id, user.username, user.email, user.password_hash, user.salt,
                user.role.value, json.dumps([p.value for p in user.permissions]),
                user.is_active, user.is_locked, user.failed_attempts,
                user.created_at, user.updated_at
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "user_id": user_id,
                "message": "사용자 생성 완료"
            }
            
        except Exception as e:
            logger.error(f"사용자 생성 실패: {e}")
            return {"success": False, "error": "creation_failed", "details": str(e)}
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """사용자명으로 사용자 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        permissions = {Permission(p) for p in json.loads(row[6])}
        
        return User(
            user_id=row[0],
            username=row[1],
            email=row[2],
            password_hash=row[3],
            salt=row[4],
            role=UserRole(row[5]),
            permissions=permissions,
            is_active=row[7],
            is_locked=row[8],
            failed_attempts=row[9],
            last_login=datetime.fromisoformat(row[10]) if row[10] else None,
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
            session_timeout=row[13]
        )
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        permissions = {Permission(p) for p in json.loads(row[6])}
        
        return User(
            user_id=row[0],
            username=row[1],
            email=row[2],
            password_hash=row[3],
            salt=row[4],
            role=UserRole(row[5]),
            permissions=permissions,
            is_active=row[7],
            is_locked=row[8],
            failed_attempts=row[9],
            last_login=datetime.fromisoformat(row[10]) if row[10] else None,
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
            session_timeout=row[13]
        )
    
    def authenticate(self, username: str, password: str, ip_address: str = "", 
                    user_agent: str = "") -> Dict[str, Any]:
        """사용자 인증"""
        try:
            # Rate limiting 확인
            if self._is_rate_limited(ip_address):
                self._log_login_attempt(username, ip_address, user_agent, AuthStatus.RATE_LIMITED)
                return {
                    "success": False,
                    "status": AuthStatus.RATE_LIMITED,
                    "message": "너무 많은 로그인 시도입니다. 잠시 후 다시 시도하세요."
                }
            
            # 사용자 조회
            user = self.get_user_by_username(username)
            if not user:
                self._log_login_attempt(username, ip_address, user_agent, AuthStatus.INVALID_CREDENTIALS)
                return {
                    "success": False,
                    "status": AuthStatus.INVALID_CREDENTIALS,
                    "message": "잘못된 사용자명 또는 패스워드입니다."
                }
            
            # 계정 잠금 확인
            if user.is_locked:
                self._log_login_attempt(username, ip_address, user_agent, AuthStatus.ACCOUNT_LOCKED)
                return {
                    "success": False,
                    "status": AuthStatus.ACCOUNT_LOCKED,
                    "message": "계정이 잠겨있습니다. 관리자에게 문의하세요."
                }
            
            # 패스워드 검증
            if not self.password_manager.verify_password(password, user.salt, user.password_hash):
                # 실패 횟수 증가
                user.failed_attempts += 1
                if user.failed_attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
                    user.is_locked = True
                    self._update_user(user)
                    
                    self._log_login_attempt(username, ip_address, user_agent, AuthStatus.ACCOUNT_LOCKED)
                    return {
                        "success": False,
                        "status": AuthStatus.ACCOUNT_LOCKED,
                        "message": f"계정이 잠겼습니다. {SecurityConfig.MAX_LOGIN_ATTEMPTS}회 이상 실패했습니다."
                    }
                else:
                    self._update_user(user)
                    self._log_login_attempt(username, ip_address, user_agent, AuthStatus.INVALID_CREDENTIALS)
                    return {
                        "success": False,
                        "status": AuthStatus.INVALID_CREDENTIALS,
                        "message": f"잘못된 패스워드입니다. ({user.failed_attempts}/{SecurityConfig.MAX_LOGIN_ATTEMPTS})"
                    }
            
            # 인증 성공
            user.failed_attempts = 0
            user.last_login = datetime.now()
            self._update_user(user)
            
            # 토큰 생성
            access_token = self.jwt_manager.create_access_token(user)
            refresh_token = self.jwt_manager.create_refresh_token(user)
            
            # 세션 생성
            session_id = self._create_session(user, access_token, refresh_token)
            
            self._log_login_attempt(username, ip_address, user_agent, AuthStatus.SUCCESS)
            
            return {
                "success": True,
                "status": AuthStatus.SUCCESS,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "session_id": session_id,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "role": user.role.value,
                    "permissions": [p.value for p in user.permissions]
                },
                "expires_in": SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            
        except Exception as e:
            logger.error(f"인증 실패: {e}")
            return {
                "success": False,
                "status": AuthStatus.INVALID_CREDENTIALS,
                "message": "인증 처리 중 오류가 발생했습니다."
            }
    
    def _is_rate_limited(self, ip_address: str) -> bool:
        """Rate limiting 확인"""
        if not ip_address:
            return False
        
        current_time = time.time()
        attempts = self.rate_limits.get(ip_address, [])
        
        # 1분 이내의 시도만 유지
        attempts = [t for t in attempts if current_time - t < 60]
        
        # 시도 횟수 확인
        if len(attempts) >= SecurityConfig.LOGIN_RATE_LIMIT:
            return True
        
        # 현재 시도 기록
        attempts.append(current_time)
        self.rate_limits[ip_address] = attempts
        
        return False
    
    def _create_session(self, user: User, access_token: str, refresh_token: str) -> str:
        """세션 생성"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=user.session_timeout)
        
        with self.session_lock:
            # 메모리 세션 저장
            self.active_sessions[session_id] = {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role.value,
                "permissions": [p.value for p in user.permissions],
                "created_at": datetime.now(),
                "expires_at": expires_at,
                "last_activity": datetime.now()
            }
        
        # 데이터베이스 세션 저장
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, access_token, refresh_token, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user.user_id, access_token, refresh_token, expires_at))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def _update_user(self, user: User):
        """사용자 정보 업데이트"""
        user.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET 
                is_active = ?, is_locked = ?, failed_attempts = ?,
                last_login = ?, updated_at = ?
            WHERE user_id = ?
        """, (
            user.is_active, user.is_locked, user.failed_attempts,
            user.last_login, user.updated_at, user.user_id
        ))
        
        conn.commit()
        conn.close()
    
    def _log_login_attempt(self, username: str, ip_address: str, user_agent: str, status: AuthStatus):
        """로그인 시도 기록"""
        attempt = LoginAttempt(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(),
            status=status
        )
        
        self.login_attempts.append(attempt)
        
        # 데이터베이스 기록
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO login_attempts (username, ip_address, user_agent, status)
            VALUES (?, ?, ?, ?)
        """, (username, ip_address, user_agent, status.value))
        
        conn.commit()
        conn.close()
    
    def verify_session(self, session_id: str) -> Dict[str, Any]:
        """세션 검증"""
        with self.session_lock:
            session = self.active_sessions.get(session_id)
            
            if not session:
                return {"valid": False, "error": "session_not_found"}
            
            # 만료 확인
            if datetime.now() > session["expires_at"]:
                del self.active_sessions[session_id]
                return {"valid": False, "error": "session_expired"}
            
            # 마지막 활동 시간 업데이트
            session["last_activity"] = datetime.now()
            
            return {"valid": True, "session": session}
    
    def logout(self, session_id: str) -> bool:
        """로그아웃"""
        with self.session_lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
        
        # 데이터베이스에서도 제거
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE sessions SET is_active = FALSE WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def require_permission(self, permission: Permission):
        """권한 데코레이터"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 세션에서 권한 확인 (실제 구현에서는 request context에서 가져옴)
                session_id = kwargs.get('session_id')
                if not session_id:
                    return {"error": "unauthorized", "message": "세션이 필요합니다"}
                
                session_result = self.verify_session(session_id)
                if not session_result["valid"]:
                    return {"error": "unauthorized", "message": "유효하지 않은 세션입니다"}
                
                session = session_result["session"]
                user_permissions = {Permission(p) for p in session["permissions"]}
                
                if permission not in user_permissions:
                    return {"error": "forbidden", "message": "권한이 부족합니다"}
                
                return func(*args, **kwargs)
            return wrapper
        return decorator


# 전역 인증 시스템 인스턴스
_auth_system = None

def get_auth_system() -> AuthenticationSystem:
    """인증 시스템 인스턴스 반환"""
    global _auth_system
    if _auth_system is None:
        _auth_system = AuthenticationSystem()
    return _auth_system


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== JWT 인증 & 권한 관리 시스템 테스트 ===")
    
    auth = get_auth_system()
    
    # 로그인 테스트
    login_result = auth.authenticate(
        username="admin",
        password="Admin123!@#",
        ip_address="192.168.1.100",
        user_agent="Test Browser"
    )
    
    if login_result["success"]:
        safe_print("✅ 관리자 로그인 성공")
        safe_print(f"🔑 액세스 토큰: {login_result['access_token'][:50]}...")
        safe_print(f"👤 사용자 역할: {login_result['user']['role']}")
        
        # 세션 검증 테스트
        session_result = auth.verify_session(login_result["session_id"])
        if session_result["valid"]:
            safe_print("✅ 세션 검증 성공")
        
        # 로그아웃 테스트
        auth.logout(login_result["session_id"])
        safe_print("✅ 로그아웃 완료")
    else:
        safe_print(f"❌ 로그인 실패: {login_result['message']}")
    
    # 잘못된 패스워드 테스트
    failed_login = auth.authenticate("admin", "wrongpassword", "192.168.1.100")
    safe_print(f"⚠️ 잘못된 패스워드 테스트: {failed_login['message']}")
    
    safe_print("🏁 JWT 인증 & 권한 관리 시스템 테스트 완료")