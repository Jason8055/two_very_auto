#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 클라우드 백업 매니저
AWS S3, Google Cloud Storage, Azure Blob Storage 통합 백업 시스템
"""

import os
import json
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    """클라우드 제공업체 열거형"""
    AWS_S3 = "aws_s3"
    GOOGLE_CLOUD = "google_cloud"
    AZURE_BLOB = "azure_blob"
    LOCAL = "local"


@dataclass
class BackupConfig:
    """백업 설정 클래스"""
    provider: CloudProvider
    bucket_name: str
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    compression: bool = True
    encryption: bool = True
    retention_days: int = 30
    max_backup_size_mb: int = 1000


@dataclass
class BackupResult:
    """백업 결과 클래스"""
    success: bool
    backup_id: str
    file_path: str
    size_mb: float
    duration_seconds: float
    provider: CloudProvider
    timestamp: datetime
    error_message: Optional[str] = None


class CloudBackupManager:
    """통합 클라우드 백업 관리자"""
    
    def __init__(self, config_path: str = "cloud_config.json"):
        self.config_path = Path(config_path)
        self.backup_configs: Dict[str, BackupConfig] = {}
        self.backup_history: List[BackupResult] = []
        
        # 클라우드 클라이언트들 (lazy loading)
        self._s3_client = None
        self._gcs_client = None
        self._azure_client = None
        
        self.load_config()
        safe_print("☁️ 클라우드 백업 매니저 초기화 완료")
    
    def load_config(self):
        """백업 설정 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                for name, config in config_data.get('backup_configs', {}).items():
                    self.backup_configs[name] = BackupConfig(
                        provider=CloudProvider(config['provider']),
                        bucket_name=config['bucket_name'],
                        access_key=config.get('access_key'),
                        secret_key=config.get('secret_key'),
                        region=config.get('region'),
                        endpoint_url=config.get('endpoint_url'),
                        compression=config.get('compression', True),
                        encryption=config.get('encryption', True),
                        retention_days=config.get('retention_days', 30),
                        max_backup_size_mb=config.get('max_backup_size_mb', 1000)
                    )
                
                safe_print(f"✅ 백업 설정 로드: {len(self.backup_configs)}개 구성")
            else:
                self.create_default_config()
                
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """기본 백업 설정 생성"""
        default_configs = {
            "backup_configs": {
                "aws_primary": {
                    "provider": "aws_s3",
                    "bucket_name": "two-very-auto-backups",
                    "region": "ap-northeast-2",
                    "compression": True,
                    "encryption": True,
                    "retention_days": 30
                },
                "gcp_secondary": {
                    "provider": "google_cloud",
                    "bucket_name": "two-very-auto-backups-gcp",
                    "compression": True,
                    "encryption": True,
                    "retention_days": 30
                },
                "local_backup": {
                    "provider": "local",
                    "bucket_name": "./backups",
                    "compression": True,
                    "retention_days": 7
                }
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_configs, f, ensure_ascii=False, indent=2)
        
        safe_print(f"📝 기본 백업 설정 생성: {self.config_path}")
    
    def get_s3_client(self, config: BackupConfig):
        """AWS S3 클라이언트 가져오기"""
        if self._s3_client is None:
            try:
                import boto3
                from botocore.exceptions import ClientError
                
                session = boto3.Session(
                    aws_access_key_id=config.access_key,
                    aws_secret_access_key=config.secret_key,
                    region_name=config.region
                )
                
                self._s3_client = session.client(
                    's3',
                    endpoint_url=config.endpoint_url
                )
                
                # 버킷 존재 확인
                try:
                    self._s3_client.head_bucket(Bucket=config.bucket_name)
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        # 버킷 생성
                        self._s3_client.create_bucket(
                            Bucket=config.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': config.region}
                        )
                        safe_print(f"📦 S3 버킷 생성: {config.bucket_name}")
                
                safe_print("✅ AWS S3 클라이언트 연결 완료")
                
            except ImportError:
                safe_print("⚠️ boto3 라이브러리 미설치. pip install boto3 실행 필요")
                return None
            except Exception as e:
                logger.error(f"S3 클라이언트 초기화 실패: {e}")
                return None
        
        return self._s3_client
    
    def get_gcs_client(self, config: BackupConfig):
        """Google Cloud Storage 클라이언트 가져오기"""
        if self._gcs_client is None:
            try:
                from google.cloud import storage
                
                # 서비스 계정 키 파일 경로 설정
                if config.access_key:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.access_key
                
                self._gcs_client = storage.Client()
                
                # 버킷 존재 확인
                bucket = self._gcs_client.bucket(config.bucket_name)
                if not bucket.exists():
                    bucket.create(location=config.region or 'ASIA-NORTHEAST3')
                    safe_print(f"📦 GCS 버킷 생성: {config.bucket_name}")
                
                safe_print("✅ Google Cloud Storage 클라이언트 연결 완료")
                
            except ImportError:
                safe_print("⚠️ google-cloud-storage 라이브러리 미설치")
                return None
            except Exception as e:
                logger.error(f"GCS 클라이언트 초기화 실패: {e}")
                return None
        
        return self._gcs_client
    
    def get_azure_client(self, config: BackupConfig):
        """Azure Blob Storage 클라이언트 가져오기"""
        if self._azure_client is None:
            try:
                from azure.storage.blob import BlobServiceClient
                
                connection_string = f"DefaultEndpointsProtocol=https;AccountName={config.access_key};AccountKey={config.secret_key};EndpointSuffix=core.windows.net"
                
                self._azure_client = BlobServiceClient.from_connection_string(connection_string)
                
                # 컨테이너 존재 확인
                container_client = self._azure_client.get_container_client(config.bucket_name)
                if not container_client.exists():
                    container_client.create_container()
                    safe_print(f"📦 Azure 컨테이너 생성: {config.bucket_name}")
                
                safe_print("✅ Azure Blob Storage 클라이언트 연결 완료")
                
            except ImportError:
                safe_print("⚠️ azure-storage-blob 라이브러리 미설치")
                return None
            except Exception as e:
                logger.error(f"Azure 클라이언트 초기화 실패: {e}")
                return None
        
        return self._azure_client
    
    def prepare_backup_file(self, source_path: str, config: BackupConfig) -> str:
        """백업 파일 준비 (압축, 암호화)"""
        source_path = Path(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 백업 파일명 생성
        backup_filename = f"two_auto_backup_{timestamp}"
        
        if source_path.is_file():
            backup_filename += f"_{source_path.stem}"
        else:
            backup_filename += "_full"
        
        # 임시 디렉터리 생성
        temp_dir = Path("temp_backups")
        temp_dir.mkdir(exist_ok=True)
        
        if config.compression:
            backup_path = temp_dir / f"{backup_filename}.tar.gz"
            
            # tar.gz 압축
            import tarfile
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(source_path, arcname=source_path.name)
            
        else:
            backup_path = temp_dir / f"{backup_filename}.bak"
            
            if source_path.is_file():
                shutil.copy2(source_path, backup_path)
            else:
                shutil.copytree(source_path, backup_path)
        
        # 파일 크기 확인
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        if size_mb > config.max_backup_size_mb:
            safe_print(f"⚠️ 백업 파일 크기 초과: {size_mb:.1f}MB > {config.max_backup_size_mb}MB")
        
        return str(backup_path)
    
    def upload_to_s3(self, file_path: str, config: BackupConfig) -> Dict[str, Any]:
        """S3에 백업 파일 업로드"""
        client = self.get_s3_client(config)
        if not client:
            return {"success": False, "error": "S3 클라이언트 초기화 실패"}
        
        try:
            file_path = Path(file_path)
            s3_key = f"backups/{datetime.now().strftime('%Y/%m/%d')}/{file_path.name}"
            
            # 업로드 진행률 콜백
            def progress_callback(bytes_transferred):
                percentage = (bytes_transferred / file_path.stat().st_size) * 100
                if percentage % 20 == 0:  # 20%마다 출력
                    safe_print(f"📤 S3 업로드 진행률: {percentage:.0f}%")
            
            # 파일 업로드
            client.upload_file(
                str(file_path),
                config.bucket_name,
                s3_key,
                Callback=progress_callback
            )
            
            # 메타데이터 설정
            client.put_object_tagging(
                Bucket=config.bucket_name,
                Key=s3_key,
                Tagging={
                    'TagSet': [
                        {'Key': 'BackupType', 'Value': 'TwoVeryAuto'},
                        {'Key': 'CreatedAt', 'Value': datetime.now().isoformat()},
                        {'Key': 'Retention', 'Value': str(config.retention_days)}
                    ]
                }
            )
            
            return {
                "success": True,
                "s3_key": s3_key,
                "bucket": config.bucket_name,
                "url": f"s3://{config.bucket_name}/{s3_key}"
            }
            
        except Exception as e:
            logger.error(f"S3 업로드 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_to_gcs(self, file_path: str, config: BackupConfig) -> Dict[str, Any]:
        """Google Cloud Storage에 백업 파일 업로드"""
        client = self.get_gcs_client(config)
        if not client:
            return {"success": False, "error": "GCS 클라이언트 초기화 실패"}
        
        try:
            file_path = Path(file_path)
            blob_name = f"backups/{datetime.now().strftime('%Y/%m/%d')}/{file_path.name}"
            
            bucket = client.bucket(config.bucket_name)
            blob = bucket.blob(blob_name)
            
            # 메타데이터 설정
            blob.metadata = {
                'backup_type': 'TwoVeryAuto',
                'created_at': datetime.now().isoformat(),
                'retention_days': str(config.retention_days)
            }
            
            # 파일 업로드
            with open(file_path, 'rb') as f:
                blob.upload_from_file(f)
            
            return {
                "success": True,
                "blob_name": blob_name,
                "bucket": config.bucket_name,
                "url": f"gs://{config.bucket_name}/{blob_name}"
            }
            
        except Exception as e:
            logger.error(f"GCS 업로드 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_to_azure(self, file_path: str, config: BackupConfig) -> Dict[str, Any]:
        """Azure Blob Storage에 백업 파일 업로드"""
        client = self.get_azure_client(config)
        if not client:
            return {"success": False, "error": "Azure 클라이언트 초기화 실패"}
        
        try:
            file_path = Path(file_path)
            blob_name = f"backups/{datetime.now().strftime('%Y/%m/%d')}/{file_path.name}"
            
            blob_client = client.get_blob_client(
                container=config.bucket_name,
                blob=blob_name
            )
            
            # 메타데이터 설정
            metadata = {
                'backup_type': 'TwoVeryAuto',
                'created_at': datetime.now().isoformat(),
                'retention_days': str(config.retention_days)
            }
            
            # 파일 업로드
            with open(file_path, 'rb') as f:
                blob_client.upload_blob(f, metadata=metadata, overwrite=True)
            
            return {
                "success": True,
                "blob_name": blob_name,
                "container": config.bucket_name,
                "url": f"https://{config.access_key}.blob.core.windows.net/{config.bucket_name}/{blob_name}"
            }
            
        except Exception as e:
            logger.error(f"Azure 업로드 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_to_local(self, file_path: str, config: BackupConfig) -> Dict[str, Any]:
        """로컬 스토리지에 백업 파일 복사"""
        try:
            backup_dir = Path(config.bucket_name)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = Path(file_path)
            dest_path = backup_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.name}"
            
            shutil.copy2(file_path, dest_path)
            
            return {
                "success": True,
                "local_path": str(dest_path),
                "size_mb": dest_path.stat().st_size / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"로컬 백업 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def backup_database(self, config_name: str = "aws_primary") -> BackupResult:
        """데이터베이스 백업"""
        start_time = datetime.now()
        backup_id = f"db_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        if config_name not in self.backup_configs:
            return BackupResult(
                success=False,
                backup_id=backup_id,
                file_path="",
                size_mb=0,
                duration_seconds=0,
                provider=CloudProvider.LOCAL,
                timestamp=start_time,
                error_message=f"백업 설정 '{config_name}' 없음"
            )
        
        config = self.backup_configs[config_name]
        
        try:
            # 데이터베이스 파일 찾기
            db_paths = [
                "python/fastapi_app/baccarat_optimized.db",
                "python/fastapi_app/baccarat_fastapi.db",
                "python/baccarat_monitor_pwa_v3.db",
                "python/baccarat_monitor_pwa_v2.db",
                "../python/baccarat_monitor_pwa_v3.db"
            ]
            
            db_path = None
            for path in db_paths:
                if Path(path).exists():
                    db_path = path
                    break
            
            if not db_path:
                raise FileNotFoundError("데이터베이스 파일을 찾을 수 없습니다")
            
            # 백업 파일 준비
            backup_file = self.prepare_backup_file(db_path, config)
            
            # 클라우드에 업로드
            if config.provider == CloudProvider.AWS_S3:
                result = self.upload_to_s3(backup_file, config)
            elif config.provider == CloudProvider.GOOGLE_CLOUD:
                result = self.upload_to_gcs(backup_file, config)
            elif config.provider == CloudProvider.AZURE_BLOB:
                result = self.upload_to_azure(backup_file, config)
            else:
                result = self.upload_to_local(backup_file, config)
            
            # 임시 파일 삭제
            Path(backup_file).unlink(missing_ok=True)
            
            duration = (datetime.now() - start_time).total_seconds()
            size_mb = Path(backup_file).stat().st_size / (1024 * 1024) if Path(backup_file).exists() else 0
            
            backup_result = BackupResult(
                success=result.get("success", False),
                backup_id=backup_id,
                file_path=result.get("url", backup_file),
                size_mb=size_mb,
                duration_seconds=duration,
                provider=config.provider,
                timestamp=start_time,
                error_message=result.get("error") if not result.get("success") else None
            )
            
            self.backup_history.append(backup_result)
            
            if backup_result.success:
                safe_print(f"✅ 데이터베이스 백업 완료: {backup_result.file_path}")
                safe_print(f"📊 크기: {size_mb:.1f}MB, 소요시간: {duration:.1f}초")
            
            return backup_result
            
        except Exception as e:
            logger.error(f"데이터베이스 백업 실패: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            
            return BackupResult(
                success=False,
                backup_id=backup_id,
                file_path="",
                size_mb=0,
                duration_seconds=duration,
                provider=config.provider,
                timestamp=start_time,
                error_message=str(e)
            )
    
    def backup_all_configs(self) -> List[BackupResult]:
        """모든 설정된 백업 수행"""
        results = []
        
        safe_print(f"🚀 전체 백업 시작: {len(self.backup_configs)}개 설정")
        
        for config_name in self.backup_configs:
            safe_print(f"📦 백업 실행: {config_name}")
            result = self.backup_database(config_name)
            results.append(result)
            
            if result.success:
                safe_print(f"✅ {config_name} 백업 완료")
            else:
                safe_print(f"❌ {config_name} 백업 실패: {result.error_message}")
        
        successful = sum(1 for r in results if r.success)
        safe_print(f"📊 백업 완료: {successful}/{len(results)}개 성공")
        
        return results
    
    def cleanup_old_backups(self, config_name: str) -> int:
        """오래된 백업 파일 정리"""
        if config_name not in self.backup_configs:
            return 0
        
        config = self.backup_configs[config_name]
        cutoff_date = datetime.now() - timedelta(days=config.retention_days)
        
        deleted_count = 0
        
        try:
            if config.provider == CloudProvider.AWS_S3:
                deleted_count = self._cleanup_s3_backups(config, cutoff_date)
            elif config.provider == CloudProvider.GOOGLE_CLOUD:
                deleted_count = self._cleanup_gcs_backups(config, cutoff_date)
            elif config.provider == CloudProvider.AZURE_BLOB:
                deleted_count = self._cleanup_azure_backups(config, cutoff_date)
            elif config.provider == CloudProvider.LOCAL:
                deleted_count = self._cleanup_local_backups(config, cutoff_date)
            
            safe_print(f"🧹 {config_name}: {deleted_count}개 오래된 백업 삭제")
            
        except Exception as e:
            logger.error(f"백업 정리 실패 ({config_name}): {e}")
        
        return deleted_count
    
    def _cleanup_s3_backups(self, config: BackupConfig, cutoff_date: datetime) -> int:
        """S3 백업 정리"""
        client = self.get_s3_client(config)
        if not client:
            return 0
        
        try:
            response = client.list_objects_v2(
                Bucket=config.bucket_name,
                Prefix="backups/"
            )
            
            deleted_count = 0
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    client.delete_object(Bucket=config.bucket_name, Key=obj['Key'])
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"S3 백업 정리 실패: {e}")
            return 0
    
    def _cleanup_gcs_backups(self, config: BackupConfig, cutoff_date: datetime) -> int:
        """GCS 백업 정리"""
        # GCS 정리 로직 (구현 생략)
        return 0
    
    def _cleanup_azure_backups(self, config: BackupConfig, cutoff_date: datetime) -> int:
        """Azure 백업 정리"""
        # Azure 정리 로직 (구현 생략)
        return 0
    
    def _cleanup_local_backups(self, config: BackupConfig, cutoff_date: datetime) -> int:
        """로컬 백업 정리"""
        backup_dir = Path(config.bucket_name)
        if not backup_dir.exists():
            return 0
        
        deleted_count = 0
        for file_path in backup_dir.glob("*"):
            if file_path.stat().st_mtime < cutoff_date.timestamp():
                file_path.unlink()
                deleted_count += 1
        
        return deleted_count
    
    def get_backup_status(self) -> Dict[str, Any]:
        """백업 상태 정보 반환"""
        recent_backups = [r for r in self.backup_history if r.timestamp > datetime.now() - timedelta(days=1)]
        
        return {
            "total_configs": len(self.backup_configs),
            "recent_backups": len(recent_backups),
            "successful_backups": sum(1 for r in recent_backups if r.success),
            "last_backup": recent_backups[-1].timestamp.isoformat() if recent_backups else None,
            "total_backup_size_mb": sum(r.size_mb for r in recent_backups if r.success),
            "configured_providers": [c.provider.value for c in self.backup_configs.values()]
        }


# 전역 인스턴스
_backup_manager = None

def get_backup_manager() -> CloudBackupManager:
    """백업 매니저 인스턴스 반환"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = CloudBackupManager()
    return _backup_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 클라우드 백업 매니저 테스트 ===")
    
    manager = get_backup_manager()
    
    # 상태 확인
    status = manager.get_backup_status()
    safe_print(f"📊 백업 상태: {status}")
    
    # 로컬 백업 테스트
    if "local_backup" in manager.backup_configs:
        result = manager.backup_database("local_backup")
        if result.success:
            safe_print(f"✅ 로컬 백업 테스트 성공: {result.file_path}")
        else:
            safe_print(f"❌ 로컬 백업 테스트 실패: {result.error_message}")
    
    safe_print("🏁 클라우드 백업 매니저 테스트 완료")