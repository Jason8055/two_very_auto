#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - AWS S3 통합 모듈
S3 버킷 관리, 자동 백업, 복원 시스템
"""

import os
import json
import logging
from datetime import datetime, timedelta
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

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    AWS_AVAILABLE = True
    safe_print("✅ AWS boto3 라이브러리 사용 가능")
except ImportError:
    AWS_AVAILABLE = False
    safe_print("⚠️ AWS boto3 미설치. pip install boto3 실행 필요")


@dataclass
class S3Config:
    """S3 설정 클래스"""
    access_key_id: str
    secret_access_key: str
    region: str = 'ap-northeast-2'
    bucket_name: str = 'two-very-auto-backups'
    endpoint_url: Optional[str] = None
    
    
class S3BackupIntegration:
    """AWS S3 백업 통합 클래스"""
    
    def __init__(self, config: Optional[S3Config] = None):
        self.config = config or self.load_config()
        self.s3_client = None
        self.s3_resource = None
        
        if AWS_AVAILABLE:
            self.initialize_s3()
        
        safe_print("🔗 AWS S3 통합 모듈 초기화 완료")
    
    def load_config(self) -> S3Config:
        """S3 설정 로드"""
        config_file = Path("s3_config.json")
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                return S3Config(
                    access_key_id=config_data.get('access_key_id', ''),
                    secret_access_key=config_data.get('secret_access_key', ''),
                    region=config_data.get('region', 'ap-northeast-2'),
                    bucket_name=config_data.get('bucket_name', 'two-very-auto-backups'),
                    endpoint_url=config_data.get('endpoint_url')
                )
            except Exception as e:
                logger.error(f"S3 설정 로드 실패: {e}")
        
        # 환경 변수에서 설정 로드
        return S3Config(
            access_key_id=os.getenv('AWS_ACCESS_KEY_ID', ''),
            secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            region=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2'),
            bucket_name=os.getenv('TWO_AUTO_S3_BUCKET', 'two-very-auto-backups'),
            endpoint_url=os.getenv('AWS_ENDPOINT_URL')
        )
    
    def save_config(self, config: S3Config):
        """S3 설정 저장"""
        config_data = {
            "access_key_id": config.access_key_id,
            "secret_access_key": config.secret_access_key,
            "region": config.region,
            "bucket_name": config.bucket_name,
            "endpoint_url": config.endpoint_url
        }
        
        with open("s3_config.json", 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        safe_print("💾 S3 설정 저장 완료")
    
    def initialize_s3(self) -> bool:
        """S3 클라이언트 초기화"""
        if not AWS_AVAILABLE:
            return False
        
        try:
            # 세션 생성
            session = boto3.Session(
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name=self.config.region
            )
            
            # 클라이언트 및 리소스 생성
            self.s3_client = session.client(
                's3',
                endpoint_url=self.config.endpoint_url
            )
            
            self.s3_resource = session.resource(
                's3',
                endpoint_url=self.config.endpoint_url
            )
            
            # 연결 테스트
            self.s3_client.list_buckets()
            safe_print("✅ AWS S3 클라이언트 초기화 완료")
            
            # 버킷 생성/확인
            self.ensure_bucket_exists()
            
            return True
            
        except NoCredentialsError:
            safe_print("❌ AWS 자격 증명 없음")
            return False
        except ClientError as e:
            safe_print(f"❌ S3 초기화 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"S3 초기화 오류: {e}")
            return False
    
    def ensure_bucket_exists(self) -> bool:
        """S3 버킷 존재 확인 및 생성"""
        if not self.s3_client:
            return False
        
        try:
            # 버킷 존재 확인
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            safe_print(f"✅ S3 버킷 확인: {self.config.bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == '404':
                # 버킷이 없으므로 생성
                try:
                    if self.config.region == 'us-east-1':
                        # us-east-1은 LocationConstraint 불필요
                        self.s3_client.create_bucket(Bucket=self.config.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.config.bucket_name,
                            CreateBucketConfiguration={
                                'LocationConstraint': self.config.region
                            }
                        )
                    
                    # 버킷 정책 설정 (Private)
                    bucket_policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "DenyPublicAccess",
                                "Effect": "Deny",
                                "Principal": "*",
                                "Action": "s3:*",
                                "Resource": [
                                    f"arn:aws:s3:::{self.config.bucket_name}",
                                    f"arn:aws:s3:::{self.config.bucket_name}/*"
                                ],
                                "Condition": {
                                    "StringNotEquals": {
                                        "aws:PrincipalServiceName": ["s3.amazonaws.com"]
                                    }
                                }
                            }
                        ]
                    }
                    
                    # 버킷 암호화 설정
                    self.s3_client.put_bucket_encryption(
                        Bucket=self.config.bucket_name,
                        ServerSideEncryptionConfiguration={
                            'Rules': [
                                {
                                    'ApplyServerSideEncryptionByDefault': {
                                        'SSEAlgorithm': 'AES256'
                                    },
                                    'BucketKeyEnabled': True
                                }
                            ]
                        }
                    )
                    
                    # 수명 주기 정책 설정 (30일 후 자동 삭제)
                    lifecycle_config = {
                        'Rules': [
                            {
                                'ID': 'DeleteOldBackups',
                                'Status': 'Enabled',
                                'Expiration': {'Days': 30},
                                'Filter': {'Prefix': 'backups/'}
                            },
                            {
                                'ID': 'DeleteIncompleteUploads',
                                'Status': 'Enabled',
                                'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1}
                            }
                        ]
                    }
                    
                    self.s3_client.put_bucket_lifecycle_configuration(
                        Bucket=self.config.bucket_name,
                        LifecycleConfiguration=lifecycle_config
                    )
                    
                    safe_print(f"🎉 S3 버킷 생성 완료: {self.config.bucket_name}")
                    return True
                    
                except ClientError as create_error:
                    safe_print(f"❌ S3 버킷 생성 실패: {create_error}")
                    return False
            
            elif error_code == '403':
                safe_print(f"❌ S3 버킷 접근 권한 없음: {self.config.bucket_name}")
                return False
            
            else:
                safe_print(f"❌ S3 버킷 확인 실패: {e}")
                return False
    
    def upload_file(self, local_file_path: str, s3_key: Optional[str] = None,
                   metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """파일을 S3에 업로드"""
        if not self.s3_client:
            return {"success": False, "error": "S3 클라이언트 미초기화"}
        
        local_path = Path(local_file_path)
        if not local_path.exists():
            return {"success": False, "error": f"파일 없음: {local_file_path}"}
        
        # S3 키 자동 생성
        if not s3_key:
            timestamp = datetime.now().strftime("%Y/%m/%d")
            s3_key = f"backups/{timestamp}/{local_path.name}"
        
        try:
            # 파일 크기 확인
            file_size = local_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            # 메타데이터 설정
            extra_args = {
                'Metadata': {
                    'source-system': 'TwoVeryAuto',
                    'upload-timestamp': datetime.now().isoformat(),
                    'file-size-mb': str(round(size_mb, 2)),
                    **(metadata or {})
                }
            }
            
            # 큰 파일은 멀티파트 업로드
            if file_size > 100 * 1024 * 1024:  # 100MB 이상
                safe_print(f"📤 대용량 파일 멀티파트 업로드 시작: {size_mb:.1f}MB")
                
                # 진행률 콜백
                class ProgressCallback:
                    def __init__(self, total_size):
                        self.total_size = total_size
                        self.uploaded = 0
                        self.last_printed = 0
                    
                    def __call__(self, bytes_amount):
                        self.uploaded += bytes_amount
                        percent = (self.uploaded / self.total_size) * 100
                        
                        # 10%마다 출력
                        if percent - self.last_printed >= 10:
                            safe_print(f"📤 업로드 진행률: {percent:.0f}%")
                            self.last_printed = percent
                
                extra_args['Callback'] = ProgressCallback(file_size)
            
            # 파일 업로드
            self.s3_client.upload_file(
                str(local_path),
                self.config.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # 업로드된 파일 URL 생성
            file_url = f"s3://{self.config.bucket_name}/{s3_key}"
            
            safe_print(f"✅ S3 업로드 완료: {file_url}")
            
            return {
                "success": True,
                "s3_key": s3_key,
                "bucket": self.config.bucket_name,
                "url": file_url,
                "size_mb": size_mb
            }
            
        except ClientError as e:
            logger.error(f"S3 업로드 실패: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"파일 업로드 오류: {e}")
            return {"success": False, "error": str(e)}
    
    def download_file(self, s3_key: str, local_file_path: str) -> Dict[str, Any]:
        """S3에서 파일 다운로드"""
        if not self.s3_client:
            return {"success": False, "error": "S3 클라이언트 미초기화"}
        
        try:
            local_path = Path(local_file_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 다운로드
            self.s3_client.download_file(
                self.config.bucket_name,
                s3_key,
                str(local_path)
            )
            
            file_size = local_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            safe_print(f"✅ S3 다운로드 완료: {local_file_path} ({size_mb:.1f}MB)")
            
            return {
                "success": True,
                "local_path": str(local_path),
                "size_mb": size_mb
            }
            
        except ClientError as e:
            logger.error(f"S3 다운로드 실패: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"파일 다운로드 오류: {e}")
            return {"success": False, "error": str(e)}
    
    def list_backups(self, prefix: str = "backups/") -> List[Dict[str, Any]]:
        """백업 파일 목록 조회"""
        if not self.s3_client:
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            backups = []
            for obj in response.get('Contents', []):
                # 메타데이터 조회
                try:
                    metadata_response = self.s3_client.head_object(
                        Bucket=self.config.bucket_name,
                        Key=obj['Key']
                    )
                    metadata = metadata_response.get('Metadata', {})
                except:
                    metadata = {}
                
                backups.append({
                    "key": obj['Key'],
                    "size_mb": obj['Size'] / (1024 * 1024),
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag'].strip('"'),
                    "metadata": metadata
                })
            
            # 최신순 정렬
            backups.sort(key=lambda x: x['last_modified'], reverse=True)
            
            return backups
            
        except ClientError as e:
            logger.error(f"백업 목록 조회 실패: {e}")
            return []
    
    def delete_backup(self, s3_key: str) -> bool:
        """백업 파일 삭제"""
        if not self.s3_client:
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            
            safe_print(f"🗑️ S3 백업 삭제: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 백업 삭제 실패: {e}")
            return False
    
    def cleanup_old_backups(self, days: int = 30) -> int:
        """오래된 백업 파일 정리"""
        if not self.s3_client:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        backups = self.list_backups()
        
        deleted_count = 0
        for backup in backups:
            backup_date = datetime.fromisoformat(backup['last_modified'].replace('Z', '+00:00'))
            
            if backup_date.replace(tzinfo=None) < cutoff_date:
                if self.delete_backup(backup['key']):
                    deleted_count += 1
        
        safe_print(f"🧹 {deleted_count}개 오래된 S3 백업 삭제 완료")
        return deleted_count
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """백업 통계 정보"""
        if not self.s3_client:
            return {"error": "S3 클라이언트 미초기화"}
        
        backups = self.list_backups()
        
        total_size = sum(backup['size_mb'] for backup in backups)
        recent_backups = [
            b for b in backups 
            if datetime.fromisoformat(b['last_modified'].replace('Z', '+00:00')) > 
            datetime.now() - timedelta(days=7)
        ]
        
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "recent_backups_7d": len(recent_backups),
            "oldest_backup": backups[-1]['last_modified'] if backups else None,
            "newest_backup": backups[0]['last_modified'] if backups else None,
            "bucket_name": self.config.bucket_name,
            "region": self.config.region
        }


# 전역 인스턴스
_s3_integration = None

def get_s3_integration() -> S3BackupIntegration:
    """S3 통합 인스턴스 반환"""
    global _s3_integration
    if _s3_integration is None:
        _s3_integration = S3BackupIntegration()
    return _s3_integration


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== AWS S3 통합 테스트 ===")
    
    s3 = get_s3_integration()
    
    if AWS_AVAILABLE and s3.s3_client:
        # 통계 정보 조회
        stats = s3.get_backup_statistics()
        safe_print(f"📊 S3 백업 통계: {stats}")
        
        # 백업 목록 조회
        backups = s3.list_backups()
        safe_print(f"📋 백업 파일 수: {len(backups)}")
        
        if backups:
            safe_print(f"📅 최근 백업: {backups[0]['last_modified']}")
            safe_print(f"💾 총 크기: {sum(b['size_mb'] for b in backups):.1f}MB")
    
    else:
        safe_print("❌ S3 기능 사용 불가 (설정 확인 필요)")
    
    safe_print("🏁 AWS S3 통합 테스트 완료")