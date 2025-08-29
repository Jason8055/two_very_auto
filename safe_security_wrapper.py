#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
안전한 보안 모듈 래퍼
서버 안정성을 해치지 않으면서 보안 기능을 제공
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

class SafeSecurityWrapper:
    """안전한 보안 모듈 래퍼 - 지연 로딩 및 fallback 지원"""
    
    _instance = None
    _security_module = None
    _initialization_failed = False
    _initialization_attempted = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._security_available = False
            self._fallback_data = {
                "status": "unknown",
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "last_scan": datetime.now().isoformat(),
                "recommendations": [
                    "보안 모듈 초기화 대기 중",
                    "수동으로 보안 스캔 실행 권장"
                ]
            }
    
    async def _initialize_security_module(self):
        """보안 모듈 비동기 초기화"""
        if self._initialization_attempted:
            return self._security_available
        
        self._initialization_attempted = True
        
        try:
            # 백그라운드에서 보안 모듈 초기화
            from security_hardening import SecurityHardening
            self._security_module = SecurityHardening()
            self._security_available = True
            logger.info("보안 모듈 초기화 성공")
            return True
            
        except ImportError as e:
            logger.warning(f"보안 모듈 임포트 실패: {e}")
            self._initialization_failed = True
            return False
        except Exception as e:
            logger.warning(f"보안 모듈 초기화 실패: {e}")
            self._initialization_failed = True
            return False
    
    async def scan_environment_files(self) -> List[Dict[str, Any]]:
        """환경 파일 보안 스캔 - 안전한 버전"""
        try:
            if not self._security_available and not self._initialization_failed:
                await self._initialize_security_module()
            
            if self._security_available and self._security_module:
                return self._security_module.scan_environment_files()
            else:
                # fallback: 기본 검사만 수행
                return await self._basic_env_check()
                
        except Exception as e:
            logger.warning(f"환경 파일 스캔 오류: {e}")
            return []
    
    async def check_file_permissions(self) -> List[Dict[str, Any]]:
        """파일 권한 확인 - 안전한 버전"""
        try:
            if not self._security_available and not self._initialization_failed:
                await self._initialize_security_module()
            
            if self._security_available and self._security_module:
                return self._security_module.check_file_permissions()
            else:
                # fallback: 기본 검사
                return await self._basic_permission_check()
                
        except Exception as e:
            logger.warning(f"권한 확인 오류: {e}")
            return []
    
    async def get_security_status(self) -> Dict[str, Any]:
        """보안 상태 조회 - 안전한 버전"""
        try:
            # 환경 파일과 권한 검사 병렬 실행
            env_issues, permission_issues = await asyncio.gather(
                self.scan_environment_files(),
                self.check_file_permissions(),
                return_exceptions=True
            )
            
            # 예외 처리
            if isinstance(env_issues, Exception):
                env_issues = []
            if isinstance(permission_issues, Exception):
                permission_issues = []
            
            all_issues = env_issues + permission_issues
            critical_count = len([i for i in all_issues if i.get("severity") == "critical"])
            high_count = len([i for i in all_issues if i.get("severity") == "high"])
            
            status = {
                "status": "secure" if critical_count == 0 and high_count == 0 else "warning",
                "total_issues": len(all_issues),
                "critical_issues": critical_count,
                "high_issues": high_count,
                "last_scan": datetime.now().isoformat(),
                "security_module_available": self._security_available,
                "recommendations": [
                    "정기적인 보안 스캔 실행",
                    "민감한 파일 권한 확인",
                    "환경변수 보안 검토"
                ]
            }
            
            if not self._security_available:
                status["warning"] = "보안 모듈이 완전히 로드되지 않음. 기본 검사만 수행됨."
            
            return status
            
        except Exception as e:
            logger.error(f"보안 상태 확인 오류: {e}")
            return self._fallback_data.copy()
    
    async def run_security_scan(self) -> Dict[str, Any]:
        """보안 스캔 실행 - 안전한 버전"""
        try:
            if not self._security_available and not self._initialization_failed:
                await self._initialize_security_module()
            
            if self._security_available and self._security_module:
                # 비동기적으로 전체 스캔 실행
                result = await asyncio.to_thread(self._security_module.run_complete_scan)
                
                return {
                    "scan_completed": True,
                    "scan_time": datetime.now().isoformat(),
                    "total_issues": result["total_issues"],
                    "critical_issues": result["critical_issues"],  
                    "high_issues": result["high_issues"],
                    "hardening_applied": result["hardening_applied"],
                    "report_path": result["report_path"]
                }
            else:
                # fallback: 기본 스캔
                return await self._basic_security_scan()
                
        except Exception as e:
            logger.error(f"보안 스캔 오류: {e}")
            return {
                "scan_completed": False,
                "scan_time": datetime.now().isoformat(),
                "error": f"스캔 중 오류 발생: {str(e)}",
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "hardening_applied": 0
            }
    
    async def apply_security_hardening(self) -> Dict[str, Any]:
        """보안 강화 적용 - 안전한 버전"""
        try:
            if not self._security_available and not self._initialization_failed:
                await self._initialize_security_module()
            
            if self._security_available and self._security_module:
                # 비동기적으로 강화 적용
                file_hardening = await asyncio.to_thread(self._security_module.apply_file_hardening)
                template_path = await asyncio.to_thread(self._security_module.create_security_env_template)
                config_path = await asyncio.to_thread(self._security_module.create_security_config)
                
                return {
                    "hardening_applied": True,
                    "file_hardening": file_hardening,
                    "template_created": template_path,
                    "config_created": config_path,
                    "applied_time": datetime.now().isoformat()
                }
            else:
                # fallback: 기본 강화만
                return await self._basic_hardening()
                
        except Exception as e:
            logger.error(f"보안 강화 오류: {e}")
            return {
                "hardening_applied": False,
                "error": f"강화 적용 중 오류: {str(e)}",
                "applied_time": datetime.now().isoformat()
            }
    
    async def _basic_env_check(self) -> List[Dict[str, Any]]:
        """기본 환경 파일 검사"""
        issues = []
        try:
            env_file = Path(".env")
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 기본적인 패턴만 검사
                if "DEBUG=true" in content:
                    issues.append({
                        "file": str(env_file),
                        "issue": "디버그 모드 활성화",
                        "severity": "medium",
                        "fix": "프로덕션에서는 DEBUG=false 설정"
                    })
                
                if "password=" in content.lower() and "your_password" not in content.lower():
                    issues.append({
                        "file": str(env_file),
                        "issue": "환경 파일에 패스워드 포함 가능성",
                        "severity": "high",
                        "fix": "패스워드를 별도 보안 저장소에 보관"
                    })
        
        except Exception as e:
            logger.warning(f"기본 환경 검사 오류: {e}")
        
        return issues
    
    async def _basic_permission_check(self) -> List[Dict[str, Any]]:
        """기본 권한 검사"""
        issues = []
        try:
            import os
            sensitive_files = [".env", "ssl_certificates"]
            
            for file_name in sensitive_files:
                file_path = Path(file_name)
                if file_path.exists():
                    # Windows가 아닌 경우만 권한 검사
                    if os.name != 'nt':
                        stat_info = file_path.stat()
                        # 간단한 권한 확인
                        if stat_info.st_mode & 0o077:  # 그룹/기타 권한 있음
                            issues.append({
                                "file": str(file_path),
                                "issue": "파일 권한이 너무 개방적",
                                "severity": "medium",
                                "fix": f"chmod 600 {file_path.name}"
                            })
        
        except Exception as e:
            logger.warning(f"기본 권한 검사 오류: {e}")
        
        return issues
    
    async def _basic_security_scan(self) -> Dict[str, Any]:
        """기본 보안 스캔"""
        try:
            env_issues = await self._basic_env_check()
            permission_issues = await self._basic_permission_check()
            
            total_issues = len(env_issues + permission_issues)
            high_issues = len([i for i in env_issues + permission_issues if i.get("severity") == "high"])
            
            return {
                "scan_completed": True,
                "scan_time": datetime.now().isoformat(),
                "total_issues": total_issues,
                "critical_issues": 0,
                "high_issues": high_issues,
                "hardening_applied": 0,
                "note": "기본 보안 스캔만 수행됨 (보안 모듈 미사용)"
            }
        
        except Exception as e:
            return {
                "scan_completed": False,
                "error": str(e),
                "scan_time": datetime.now().isoformat()
            }
    
    async def _basic_hardening(self) -> Dict[str, Any]:
        """기본 보안 강화"""
        try:
            # 기본적인 강화만 수행
            actions_taken = []
            
            # .env 파일 권한 설정 (Unix/Linux만)
            env_file = Path(".env")
            if env_file.exists():
                import os
                if os.name != 'nt':
                    try:
                        os.chmod(env_file, 0o600)
                        actions_taken.append("환경변수 파일 권한 강화")
                    except:
                        pass
            
            return {
                "hardening_applied": len(actions_taken) > 0,
                "actions_taken": actions_taken,
                "applied_time": datetime.now().isoformat(),
                "note": "기본 보안 강화만 적용됨"
            }
        
        except Exception as e:
            return {
                "hardening_applied": False,
                "error": str(e),
                "applied_time": datetime.now().isoformat()
            }

# 전역 인스턴스
_safe_security_wrapper = None

def get_safe_security_wrapper() -> SafeSecurityWrapper:
    """안전한 보안 래퍼 인스턴스 반환"""
    global _safe_security_wrapper
    if _safe_security_wrapper is None:
        _safe_security_wrapper = SafeSecurityWrapper()
    return _safe_security_wrapper