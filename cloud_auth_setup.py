#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
클라우드 인증 정보 설정 도구
대화형으로 AWS, GCP, Azure 인증 정보를 안전하게 설정
"""

import os
import json
import base64
import getpass
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import secrets

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

class CloudAuthSetup:
    """클라우드 인증 설정 도구"""
    
    def __init__(self):
        self.env_file = Path(".env")
        self.credentials = {}
        
        safe_print("🔐 클라우드 인증 설정 도구 시작")
    
    def interactive_setup(self):
        """대화형 인증 설정"""
        safe_print("=== 클라우드 백업 인증 설정 ===")
        safe_print("💡 Enter 키만 누르면 해당 서비스를 건너뜁니다")
        safe_print("")
        
        # AWS 설정
        self.setup_aws()
        
        # Google Cloud 설정
        self.setup_gcp()
        
        # Azure 설정
        self.setup_azure()
        
        # 백업 암호화 키 설정
        self.setup_encryption()
        
        # .env 파일 생성
        self.create_env_file()
        
        # 설정 테스트
        self.test_configurations()
    
    def auto_setup(self, config_dict: Dict[str, str] = None):
        """비대화형 자동 설정"""
        safe_print("🤖 자동 클라우드 인증 설정 시작")
        
        if config_dict:
            self.credentials.update(config_dict)
            safe_print(f"📋 {len(config_dict)}개 설정 항목 로드됨")
        else:
            # 기본 설정 적용
            self.apply_default_config()
        
        # .env 파일 생성
        self.create_env_file()
        
        # 자동 검증
        self.auto_validate_configurations()
        
        safe_print("✅ 자동 설정 완료")
        return True
    
    def apply_default_config(self):
        """기본 설정 적용"""
        # 백업 암호화 키 자동 생성
        encryption_key = secrets.token_urlsafe(32)[:32]  # 32자로 제한
        
        self.credentials.update({
            "BACKUP_ENCRYPTION_KEY": encryption_key,
            "BACKUP_ENABLED": "true",
            "SSL_CERT_EXPIRY_ALERT_DAYS": "30"
        })
        
        safe_print("🔑 백업 암호화 키 자동 생성됨")
        safe_print("💡 클라우드 설정은 나중에 추가할 수 있습니다")
    
    def setup_aws(self):
        """AWS 인증 설정"""
        safe_print("🔶 AWS S3 백업 설정")
        safe_print("AWS 콘솔 > IAM > 사용자 > 보안 자격 증명에서 확인 가능")
        
        access_key = input("AWS Access Key ID (Enter 키로 건너뜀): ").strip()
        if access_key:
            secret_key = getpass.getpass("AWS Secret Access Key: ").strip()
            region = input("AWS Region [ap-northeast-2]: ").strip() or "ap-northeast-2"
            bucket = input("S3 버킷명 [two-very-auto-backups]: ").strip() or "two-very-auto-backups"
            
            self.credentials.update({
                "AWS_ACCESS_KEY_ID": access_key,
                "AWS_SECRET_ACCESS_KEY": secret_key,
                "AWS_REGION": region,
                "AWS_BUCKET_NAME": bucket
            })
            
            # AWS 설정 검증
            if self.validate_aws_credentials():
                safe_print("✅ AWS 설정 검증 완료")
            else:
                safe_print("⚠️ AWS 설정을 확인해주세요")
        else:
            safe_print("⏭️ AWS 설정 건너뜀")
        safe_print("")
    
    def setup_gcp(self):
        """Google Cloud 설정"""
        safe_print("🔵 Google Cloud Storage 백업 설정")
        safe_print("GCP 콘솔 > IAM 및 관리자 > 서비스 계정에서 키 파일 다운로드")
        
        credentials_path = input("서비스 계정 키 파일 경로 (Enter 키로 건너뜀): ").strip()
        if credentials_path and Path(credentials_path).exists():
            project_id = input("GCP 프로젝트 ID: ").strip()
            bucket = input("GCS 버킷명 [two-very-auto-backups-gcp]: ").strip() or "two-very-auto-backups-gcp"
            
            self.credentials.update({
                "GOOGLE_APPLICATION_CREDENTIALS": str(Path(credentials_path).absolute()),
                "GCP_PROJECT_ID": project_id,
                "GCP_BUCKET_NAME": bucket
            })
            
            safe_print("✅ Google Cloud 설정 완료")
        else:
            safe_print("⏭️ Google Cloud 설정 건너뜀")
        safe_print("")
    
    def setup_azure(self):
        """Azure 설정"""
        safe_print("🔷 Azure Blob Storage 백업 설정")
        safe_print("Azure Portal > 스토리지 계정 > 액세스 키에서 확인 가능")
        
        account_name = input("Azure 스토리지 계정명 (Enter 키로 건너뜀): ").strip()
        if account_name:
            account_key = getpass.getpass("Azure 스토리지 계정 키: ").strip()
            container = input("Azure 컨테이너명 [two-very-auto-backups]: ").strip() or "two-very-auto-backups"
            
            self.credentials.update({
                "AZURE_STORAGE_ACCOUNT_NAME": account_name,
                "AZURE_STORAGE_ACCOUNT_KEY": account_key,
                "AZURE_CONTAINER_NAME": container
            })
            
            safe_print("✅ Azure 설정 완료")
        else:
            safe_print("⏭️ Azure 설정 건너뜀")
        safe_print("")
    
    def setup_encryption(self):
        """백업 암호화 키 설정"""
        safe_print("🔒 백업 암호화 키 설정")
        
        choice = input("새 암호화 키를 생성하시겠습니까? (Y/n): ").strip().lower()
        if choice != 'n':
            # 32바이트 (256비트) 키 생성
            encryption_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            self.credentials["BACKUP_ENCRYPTION_KEY"] = encryption_key
            safe_print("🔑 새 암호화 키 생성 완료")
        else:
            existing_key = getpass.getpass("기존 암호화 키를 입력하세요 (32자 이상): ").strip()
            if len(existing_key) >= 32:
                self.credentials["BACKUP_ENCRYPTION_KEY"] = existing_key
                safe_print("✅ 기존 암호화 키 설정 완료")
            else:
                safe_print("⚠️ 키가 너무 짧습니다. 새 키를 생성합니다.")
                encryption_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
                self.credentials["BACKUP_ENCRYPTION_KEY"] = encryption_key
        safe_print("")
    
    def validate_aws_credentials(self) -> bool:
        """AWS 인증 정보 검증"""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            session = boto3.Session(
                aws_access_key_id=self.credentials.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=self.credentials.get("AWS_SECRET_ACCESS_KEY"),
                region_name=self.credentials.get("AWS_REGION")
            )
            
            s3 = session.client('s3')
            
            # 버킷 목록 조회로 인증 테스트
            s3.list_buckets()
            return True
            
        except (ClientError, NoCredentialsError, ImportError) as e:
            safe_print(f"AWS 검증 오류: {e}")
            return False
        except Exception as e:
            safe_print(f"예상치 못한 오류: {e}")
            return False
    
    def create_env_file(self):
        """환경변수 파일 생성"""
        if not self.credentials:
            safe_print("⚠️ 설정된 인증 정보가 없습니다")
            return
        
        # 기존 .env 파일 백업
        if self.env_file.exists():
            backup_path = Path(f".env.backup_{int(datetime.now().timestamp())}")
            self.env_file.rename(backup_path)
            safe_print(f"📁 기존 .env 파일 백업: {backup_path}")
        
        # .env.example 파일 읽어서 템플릿으로 사용
        template_content = ""
        example_file = Path(".env.example")
        if example_file.exists():
            with open(example_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
        
        # 새 .env 파일 생성
        env_content = template_content
        
        # 설정된 값들로 치환
        for key, value in self.credentials.items():
            # 템플릿에서 해당 키 찾아 치환
            import re
            pattern = f"^{key}=.*$"
            replacement = f"{key}={value}"
            
            if re.search(pattern, env_content, re.MULTILINE):
                env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
            else:
                # 템플릿에 없는 키는 추가
                env_content += f"\n{key}={value}"
        
        # 파일 저장
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 파일 권한 설정 (보안)
        try:
            os.chmod(self.env_file, 0o600)  # 소유자만 읽기/쓰기
        except:
            pass  # Windows에서는 chmod가 제한적
        
        safe_print(f"✅ 환경변수 파일 생성: {self.env_file}")
        safe_print("🔒 파일 권한이 보안으로 설정됨")
    
    def test_configurations(self):
        """설정 테스트"""
        safe_print("🧪 설정 테스트 실행")
        
        try:
            # 보안 설정 매니저로 검증
            from cloud.secure_config_manager import get_secure_config_manager
            
            manager = get_secure_config_manager()
            validation = manager.validate_security_settings()
            
            if validation["valid"]:
                safe_print("✅ 모든 설정 검증 통과")
            else:
                safe_print("⚠️ 일부 설정에 문제가 있습니다:")
                for error in validation.get("errors", []):
                    safe_print(f"  ❌ {error}")
                for warning in validation.get("warnings", []):
                    safe_print(f"  ⚠️ {warning}")
            
            # 클라우드 설정 파일 업데이트
            manager.update_cloud_config()
            
        except Exception as e:
            safe_print(f"⚠️ 설정 테스트 중 오류: {e}")
    
    def auto_validate_configurations(self):
        """자동 설정 검증 (비대화형)"""
        safe_print("🔍 설정 자동 검증 시작...")
        
        validation_results = []
        
        try:
            # 환경변수 존재 여부 확인
            if self.env_file.exists():
                validation_results.append("✅ .env 파일 생성됨")
            else:
                validation_results.append("❌ .env 파일 생성 실패")
            
            # 암호화 키 확인
            if self.credentials.get("BACKUP_ENCRYPTION_KEY"):
                validation_results.append("✅ 백업 암호화 키 설정됨")
            else:
                validation_results.append("❌ 백업 암호화 키 없음")
            
            # 클라우드 설정 확인
            cloud_providers = []
            if self.credentials.get("AWS_ACCESS_KEY_ID"):
                cloud_providers.append("AWS")
            if self.credentials.get("GOOGLE_APPLICATION_CREDENTIALS"):
                cloud_providers.append("GCP")
            if self.credentials.get("AZURE_STORAGE_ACCOUNT_NAME"):
                cloud_providers.append("Azure")
            
            if cloud_providers:
                validation_results.append(f"✅ 클라우드 설정: {', '.join(cloud_providers)}")
            else:
                validation_results.append("💡 클라우드 설정 없음 (로컬 백업만 사용)")
            
            # 결과 출력
            for result in validation_results:
                safe_print(f"  {result}")
            
            return len([r for r in validation_results if r.startswith("✅")]) > 0
            
        except Exception as e:
            safe_print(f"⚠️ 자동 검증 중 오류: {e}")
            return False
    
    def create_quick_test_script(self):
        """빠른 테스트 스크립트 생성"""
        script_content = '''#!/usr/bin/env python3
"""클라우드 백업 빠른 테스트"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from cloud.backup_manager import get_backup_manager

def test_all_backups():
    """모든 백업 설정 테스트"""
    print("=== 클라우드 백업 테스트 ===")
    
    manager = get_backup_manager()
    configs = list(manager.backup_configs.keys())
    
    for config_name in configs:
        print(f"\\n📦 {config_name} 백업 테스트...")
        try:
            result = manager.backup_database(config_name)
            
            if result.success:
                print(f"✅ 성공: {result.size_mb:.1f}MB, {result.duration_seconds:.1f}초")
            else:
                print(f"❌ 실패: {result.error_message}")
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_all_backups()
'''
        
        script_path = Path("test_cloud_backups.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        safe_print(f"📝 테스트 스크립트 생성: {script_path}")
        return str(script_path)

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    # CLI 인자 파싱
    parser = argparse.ArgumentParser(description="Two Very Auto 클라우드 인증 설정")
    parser.add_argument("--auto", action="store_true", help="자동 설정 모드 (비대화형)")
    parser.add_argument("--aws-key", help="AWS Access Key ID")
    parser.add_argument("--aws-secret", help="AWS Secret Access Key")
    parser.add_argument("--aws-region", default="ap-northeast-2", help="AWS Region")
    parser.add_argument("--aws-bucket", default="two-very-auto-backups", help="AWS S3 Bucket")
    
    args = parser.parse_args()
    
    setup = CloudAuthSetup()
    
    try:
        if args.auto:
            # 자동 설정 모드
            config_dict = {}
            
            if args.aws_key and args.aws_secret:
                config_dict.update({
                    "AWS_ACCESS_KEY_ID": args.aws_key,
                    "AWS_SECRET_ACCESS_KEY": args.aws_secret,
                    "AWS_REGION": args.aws_region,
                    "AWS_BUCKET_NAME": args.aws_bucket
                })
                safe_print("🔶 AWS 설정이 CLI 인자로 제공됨")
            
            success = setup.auto_setup(config_dict if config_dict else None)
            
            if success:
                safe_print("🎉 자동 설정 완료!")
            else:
                safe_print("❌ 자동 설정 실패")
                sys.exit(1)
        else:
            # 대화형 설정 실행
            setup.interactive_setup()
        
        # 빠른 테스트 스크립트 생성
        test_script = setup.create_quick_test_script()
        
        safe_print("🎉 클라우드 인증 설정 완료!")
        safe_print("")
        safe_print("다음 단계:")
        safe_print("1. 설정 확인: python cloud/secure_config_manager.py")
        safe_print(f"2. 백업 테스트: python {test_script}")
        safe_print("3. 자동 스케줄러 시작: python backup_scheduler.py")
        
    except KeyboardInterrupt:
        safe_print("\\n⏹️ 사용자에 의한 중단")
    except Exception as e:
        safe_print(f"\\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()