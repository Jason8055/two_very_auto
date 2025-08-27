#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 백업 복원 시스템
클라우드 백업으로부터 데이터 복원 및 시스템 복구
"""

import os
import json
import shutil
import tarfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


@dataclass
class RestorePoint:
    """복원 지점 정보"""
    backup_id: str
    provider: str
    file_path: str
    timestamp: datetime
    size_mb: float
    backup_type: str
    metadata: Dict[str, Any]


@dataclass
class RestoreResult:
    """복원 결과"""
    success: bool
    restore_point: RestorePoint
    restored_path: str
    duration_seconds: float
    error_message: Optional[str] = None


class BackupRestoreSystem:
    """백업 복원 시스템"""
    
    def __init__(self):
        self.restore_history: List[RestoreResult] = []
        self.temp_dir = Path("temp_restore")
        self.temp_dir.mkdir(exist_ok=True)
        
        # 백업 매니저들 (lazy loading)
        self._backup_manager = None
        self._s3_integration = None
        
        safe_print("🔄 백업 복원 시스템 초기화 완료")
    
    @property
    def backup_manager(self):
        """백업 매니저 가져오기"""
        if self._backup_manager is None:
            try:
                from backup_manager import get_backup_manager
                self._backup_manager = get_backup_manager()
            except ImportError:
                safe_print("⚠️ 백업 매니저 모듈 없음")
        return self._backup_manager
    
    @property
    def s3_integration(self):
        """S3 통합 모듈 가져오기"""
        if self._s3_integration is None:
            try:
                from s3_integration import get_s3_integration
                self._s3_integration = get_s3_integration()
            except ImportError:
                safe_print("⚠️ S3 통합 모듈 없음")
        return self._s3_integration
    
    def discover_restore_points(self) -> List[RestorePoint]:
        """복원 가능한 백업 지점 검색"""
        restore_points = []
        
        # S3 백업 검색
        if self.s3_integration and self.s3_integration.s3_client:
            s3_backups = self.s3_integration.list_backups()
            
            for backup in s3_backups:
                restore_point = RestorePoint(
                    backup_id=backup['etag'],
                    provider="aws_s3",
                    file_path=backup['key'],
                    timestamp=datetime.fromisoformat(backup['last_modified'].replace('Z', '+00:00')),
                    size_mb=backup['size_mb'],
                    backup_type="database",
                    metadata=backup.get('metadata', {})
                )
                restore_points.append(restore_point)
        
        # 로컬 백업 검색
        local_backup_dir = Path("./backups")
        if local_backup_dir.exists():
            for backup_file in local_backup_dir.glob("*"):
                if backup_file.is_file():
                    # 파일명에서 타임스탬프 추출
                    try:
                        timestamp_str = backup_file.stem.split('_')[3] + backup_file.stem.split('_')[4]
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    except:
                        timestamp = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    restore_point = RestorePoint(
                        backup_id=backup_file.stem,
                        provider="local",
                        file_path=str(backup_file),
                        timestamp=timestamp,
                        size_mb=backup_file.stat().st_size / (1024 * 1024),
                        backup_type="database",
                        metadata={}
                    )
                    restore_points.append(restore_point)
        
        # 시간순 정렬 (최신순)
        restore_points.sort(key=lambda x: x.timestamp, reverse=True)
        
        safe_print(f"🔍 복원 지점 발견: {len(restore_points)}개")
        return restore_points
    
    def download_backup_file(self, restore_point: RestorePoint) -> Optional[str]:
        """백업 파일 다운로드"""
        if restore_point.provider == "local":
            # 로컬 파일은 그대로 반환
            return restore_point.file_path
        
        elif restore_point.provider == "aws_s3":
            if not self.s3_integration:
                safe_print("❌ S3 통합 모듈 없음")
                return None
            
            # S3에서 다운로드
            local_filename = f"restore_{restore_point.backup_id}_{datetime.now().strftime('%H%M%S')}"
            local_path = self.temp_dir / local_filename
            
            result = self.s3_integration.download_file(restore_point.file_path, str(local_path))
            
            if result['success']:
                safe_print(f"📥 S3 백업 다운로드 완료: {result['size_mb']:.1f}MB")
                return str(local_path)
            else:
                safe_print(f"❌ S3 다운로드 실패: {result['error']}")
                return None
        
        else:
            safe_print(f"❌ 지원하지 않는 백업 제공업체: {restore_point.provider}")
            return None
    
    def extract_backup_file(self, backup_file_path: str) -> Optional[str]:
        """백업 파일 압축 해제"""
        backup_path = Path(backup_file_path)
        
        if not backup_path.exists():
            safe_print(f"❌ 백업 파일 없음: {backup_file_path}")
            return None
        
        extract_dir = self.temp_dir / f"extract_{datetime.now().strftime('%H%M%S')}"
        extract_dir.mkdir(exist_ok=True)
        
        try:
            if backup_path.suffix == '.gz' and '.tar' in backup_path.name:
                # tar.gz 압축 해제
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
                    
                # 추출된 파일 찾기
                extracted_files = list(extract_dir.glob("*"))
                if extracted_files:
                    extracted_file = extracted_files[0]
                    safe_print(f"📦 압축 해제 완료: {extracted_file.name}")
                    return str(extracted_file)
            
            elif backup_path.suffix == '.bak':
                # 백업 파일 그대로 복사
                extracted_file = extract_dir / backup_path.name
                shutil.copy2(backup_path, extracted_file)
                safe_print(f"📄 백업 파일 복사 완료: {extracted_file.name}")
                return str(extracted_file)
            
            else:
                # 지원하지 않는 형식
                safe_print(f"❌ 지원하지 않는 백업 파일 형식: {backup_path.suffix}")
                return None
                
        except Exception as e:
            logger.error(f"백업 파일 압축 해제 실패: {e}")
            return None
    
    def restore_database(self, restore_point: RestorePoint, 
                        target_path: Optional[str] = None) -> RestoreResult:
        """데이터베이스 복원"""
        start_time = datetime.now()
        
        safe_print(f"🔄 데이터베이스 복원 시작: {restore_point.backup_id}")
        safe_print(f"📅 백업 시점: {restore_point.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        safe_print(f"💾 백업 크기: {restore_point.size_mb:.1f}MB")
        
        try:
            # 1. 백업 파일 다운로드
            backup_file = self.download_backup_file(restore_point)
            if not backup_file:
                raise Exception("백업 파일 다운로드 실패")
            
            # 2. 압축 해제
            extracted_file = self.extract_backup_file(backup_file)
            if not extracted_file:
                raise Exception("백업 파일 압축 해제 실패")
            
            # 3. 복원 대상 경로 설정
            if not target_path:
                # 기본 데이터베이스 경로들 시도
                possible_paths = [
                    "python/baccarat_monitor_pwa_v3.db",
                    "python/baccarat_monitor_pwa_v2.db",
                    "../python/baccarat_monitor_pwa_v3.db"
                ]
                
                for path in possible_paths:
                    if Path(path).parent.exists():
                        target_path = path
                        break
                
                if not target_path:
                    target_path = "baccarat_monitor_restored.db"
            
            # 4. 기존 데이터베이스 백업 (안전을 위해)
            target_path_obj = Path(target_path)
            if target_path_obj.exists():
                backup_suffix = datetime.now().strftime("_backup_%Y%m%d_%H%M%S")
                backup_target = target_path_obj.with_name(f"{target_path_obj.stem}{backup_suffix}{target_path_obj.suffix}")
                shutil.copy2(target_path, backup_target)
                safe_print(f"🔒 기존 DB 백업: {backup_target.name}")
            
            # 5. 복원 실행
            target_path_obj.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(extracted_file, target_path)
            
            # 6. 복원 완료
            duration = (datetime.now() - start_time).total_seconds()
            restored_size = Path(target_path).stat().st_size / (1024 * 1024)
            
            result = RestoreResult(
                success=True,
                restore_point=restore_point,
                restored_path=target_path,
                duration_seconds=duration
            )
            
            self.restore_history.append(result)
            
            safe_print(f"✅ 데이터베이스 복원 완료!")
            safe_print(f"📁 복원 경로: {target_path}")
            safe_print(f"💾 복원 크기: {restored_size:.1f}MB")
            safe_print(f"⏱️ 소요 시간: {duration:.1f}초")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            result = RestoreResult(
                success=False,
                restore_point=restore_point,
                restored_path="",
                duration_seconds=duration,
                error_message=error_msg
            )
            
            self.restore_history.append(result)
            
            safe_print(f"❌ 데이터베이스 복원 실패: {error_msg}")
            logger.error(f"데이터베이스 복원 오류: {e}")
            
            return result
        
        finally:
            # 임시 파일 정리
            self.cleanup_temp_files()
    
    def restore_from_latest(self) -> RestoreResult:
        """최신 백업으로부터 복원"""
        restore_points = self.discover_restore_points()
        
        if not restore_points:
            return RestoreResult(
                success=False,
                restore_point=RestorePoint("", "", "", datetime.now(), 0, "", {}),
                restored_path="",
                duration_seconds=0,
                error_message="복원 가능한 백업이 없습니다"
            )
        
        latest_restore_point = restore_points[0]
        safe_print(f"📅 최신 백업으로 복원: {latest_restore_point.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.restore_database(latest_restore_point)
    
    def restore_from_date(self, target_date: datetime) -> RestoreResult:
        """특정 날짜에 가장 가까운 백업으로 복원"""
        restore_points = self.discover_restore_points()
        
        if not restore_points:
            return RestoreResult(
                success=False,
                restore_point=RestorePoint("", "", "", datetime.now(), 0, "", {}),
                restored_path="",
                duration_seconds=0,
                error_message="복원 가능한 백업이 없습니다"
            )
        
        # 목표 날짜에 가장 가까운 백업 찾기
        closest_restore_point = min(
            restore_points,
            key=lambda rp: abs((rp.timestamp - target_date).total_seconds())
        )
        
        time_diff = abs((closest_restore_point.timestamp - target_date).total_seconds() / 3600)  # 시간 단위
        safe_print(f"📅 목표 날짜: {target_date.strftime('%Y-%m-%d %H:%M:%S')}")
        safe_print(f"📅 선택된 백업: {closest_restore_point.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({time_diff:.1f}시간 차이)")
        
        return self.restore_database(closest_restore_point)
    
    def list_restore_points(self, limit: int = 10) -> List[Dict[str, Any]]:
        """복원 지점 목록을 사용자 친화적 형태로 반환"""
        restore_points = self.discover_restore_points()
        
        result = []
        for rp in restore_points[:limit]:
            result.append({
                "backup_id": rp.backup_id,
                "provider": rp.provider,
                "timestamp": rp.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "size_mb": round(rp.size_mb, 1),
                "backup_type": rp.backup_type,
                "age_hours": round((datetime.now() - rp.timestamp).total_seconds() / 3600, 1)
            })
        
        return result
    
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        try:
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    temp_file.unlink()
                elif temp_file.is_dir():
                    shutil.rmtree(temp_file)
            
            safe_print("🧹 임시 파일 정리 완료")
            
        except Exception as e:
            logger.warning(f"임시 파일 정리 중 오류: {e}")
    
    def get_restore_status(self) -> Dict[str, Any]:
        """복원 시스템 상태 정보"""
        restore_points = self.discover_restore_points()
        recent_restores = [
            r for r in self.restore_history 
            if r.restore_point.timestamp > datetime.now() - timedelta(days=1)
        ]
        
        return {
            "available_restore_points": len(restore_points),
            "latest_backup": restore_points[0].timestamp.isoformat() if restore_points else None,
            "oldest_backup": restore_points[-1].timestamp.isoformat() if restore_points else None,
            "total_backup_size_mb": sum(rp.size_mb for rp in restore_points),
            "recent_restores": len(recent_restores),
            "successful_restores": sum(1 for r in recent_restores if r.success),
            "temp_files_size_mb": sum(
                f.stat().st_size for f in self.temp_dir.glob("*") if f.is_file()
            ) / (1024 * 1024) if self.temp_dir.exists() else 0
        }


# 전역 인스턴스
_restore_system = None

def get_restore_system() -> BackupRestoreSystem:
    """복원 시스템 인스턴스 반환"""
    global _restore_system
    if _restore_system is None:
        _restore_system = BackupRestoreSystem()
    return _restore_system


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 백업 복원 시스템 테스트 ===")
    
    restore_system = get_restore_system()
    
    # 복원 지점 검색
    restore_points = restore_system.discover_restore_points()
    safe_print(f"🔍 복원 지점: {len(restore_points)}개")
    
    # 복원 지점 목록 출력
    points_list = restore_system.list_restore_points(5)
    for i, point in enumerate(points_list, 1):
        safe_print(f"  {i}. {point['timestamp']} ({point['provider']}, {point['size_mb']}MB, {point['age_hours']}h 전)")
    
    # 상태 정보
    status = restore_system.get_restore_status()
    safe_print(f"📊 복원 시스템 상태: {status}")
    
    # 최신 백업 복원 테스트 (실제로는 실행하지 않음)
    if restore_points and input("최신 백업으로 복원을 테스트하시겠습니까? (y/N): ").lower() == 'y':
        result = restore_system.restore_from_latest()
        if result.success:
            safe_print(f"✅ 복원 테스트 성공: {result.restored_path}")
        else:
            safe_print(f"❌ 복원 테스트 실패: {result.error_message}")
    
    safe_print("🏁 백업 복원 시스템 테스트 완료")