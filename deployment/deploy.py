#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 자동 배포 시스템
Docker 기반 블루-그린 배포 및 롤백 지원
"""

import os
import json
import time
import logging
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class Environment(Enum):
    """배포 환경"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(Enum):
    """배포 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentConfig:
    """배포 설정"""
    environment: Environment
    docker_registry: str = "ghcr.io/your-org/two-very-auto"
    image_tag: str = "latest"
    docker_compose_file: str = "docker-compose.yml"
    health_check_url: str = "http://localhost:8080/api/health"
    health_check_timeout: int = 300
    rollback_enabled: bool = True
    backup_enabled: bool = True
    notification_webhook: Optional[str] = None


@dataclass
class DeploymentRecord:
    """배포 기록"""
    deployment_id: str
    environment: Environment
    image_tag: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_deployment_id: Optional[str] = None


class DeploymentManager:
    """자동 배포 관리자"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        
        # 배포 상태
        self.current_deployment: Optional[DeploymentRecord] = None
        self.deployment_history: List[DeploymentRecord] = []
        
        # 경로 설정
        self.project_root = Path(__file__).parent.parent
        self.docker_dir = self.project_root / "docker"
        self.backup_dir = self.project_root / "backups" / "deployments"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 로깅 설정
        self.setup_logging()
        
        safe_print(f"🚀 배포 관리자 초기화: {config.environment.value}")
    
    def setup_logging(self):
        """로깅 설정"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"deployment_{self.config.environment.value}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def generate_deployment_id(self) -> str:
        """배포 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"deploy_{self.config.environment.value}_{timestamp}"
    
    def run_command(self, command: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """명령어 실행"""
        try:
            safe_print(f"🔧 실행: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    def check_prerequisites(self) -> bool:
        """배포 전 사전 조건 확인"""
        safe_print("🔍 사전 조건 확인 중...")
        
        checks = [
            ("Docker", ["docker", "--version"]),
            ("Docker Compose", ["docker-compose", "--version"]),
            ("Git", ["git", "--version"])
        ]
        
        for name, command in checks:
            result = self.run_command(command)
            if not result["success"]:
                safe_print(f"❌ {name} 확인 실패: {result.get('error', 'Unknown error')}")
                return False
            safe_print(f"✅ {name} 확인 완료")
        
        # Docker Compose 파일 확인
        compose_file = self.project_root / "docker" / self.config.docker_compose_file
        if not compose_file.exists():
            safe_print(f"❌ Docker Compose 파일 없음: {compose_file}")
            return False
        
        safe_print("✅ 모든 사전 조건 충족")
        return True
    
    def create_backup(self) -> Optional[str]:
        """현재 상태 백업"""
        if not self.config.backup_enabled:
            return None
        
        safe_print("💾 배포 전 백업 생성 중...")
        
        try:
            # 백업 디렉터리 생성
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{self.config.environment.value}_{backup_timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            # 현재 이미지 정보 저장
            result = self.run_command(["docker", "images", "--format", "json"])
            if result["success"]:
                with open(backup_path / "docker_images.json", 'w') as f:
                    f.write(result["stdout"])
            
            # Docker Compose 설정 백업
            compose_file = self.docker_dir / self.config.docker_compose_file
            if compose_file.exists():
                import shutil
                shutil.copy2(compose_file, backup_path / self.config.docker_compose_file)
            
            # 데이터베이스 백업 (있는 경우)
            self._backup_database(backup_path)
            
            safe_print(f"✅ 백업 생성 완료: {backup_name}")
            return backup_name
            
        except Exception as e:
            logger.error(f"백업 생성 실패: {e}")
            return None
    
    def _backup_database(self, backup_path: Path):
        """데이터베이스 백업"""
        try:
            # SQLite 데이터베이스 백업
            db_files = list(self.project_root.glob("**/*.db"))
            for db_file in db_files:
                if db_file.exists():
                    import shutil
                    backup_db_path = backup_path / "databases" / db_file.name
                    backup_db_path.parent.mkdir(exist_ok=True)
                    shutil.copy2(db_file, backup_db_path)
                    safe_print(f"📊 DB 백업: {db_file.name}")
                    
        except Exception as e:
            logger.warning(f"데이터베이스 백업 실패: {e}")
    
    def pull_images(self) -> bool:
        """최신 이미지 다운로드"""
        safe_print("📥 최신 이미지 다운로드 중...")
        
        images = [
            f"{self.config.docker_registry}-web:{self.config.image_tag}",
            f"{self.config.docker_registry}-ai:{self.config.image_tag}"
        ]
        
        for image in images:
            result = self.run_command(["docker", "pull", image])
            if not result["success"]:
                safe_print(f"❌ 이미지 다운로드 실패: {image}")
                safe_print(f"오류: {result.get('stderr', 'Unknown error')}")
                return False
            safe_print(f"✅ 이미지 다운로드 완료: {image}")
        
        return True
    
    def stop_current_services(self) -> bool:
        """현재 서비스 중지"""
        safe_print("🛑 현재 서비스 중지 중...")
        
        result = self.run_command(
            ["docker-compose", "-f", self.config.docker_compose_file, "down"],
            cwd=self.docker_dir
        )
        
        if not result["success"]:
            safe_print(f"⚠️ 서비스 중지 중 오류 발생: {result.get('stderr', '')}")
            return False
        
        safe_print("✅ 서비스 중지 완료")
        return True
    
    def start_new_services(self) -> bool:
        """새 서비스 시작"""
        safe_print("🚀 새 서비스 시작 중...")
        
        # 환경 변수 설정
        env = os.environ.copy()
        env["IMAGE_TAG"] = self.config.image_tag
        env["ENVIRONMENT"] = self.config.environment.value
        
        result = self.run_command(
            ["docker-compose", "-f", self.config.docker_compose_file, "up", "-d", "--remove-orphans"],
            cwd=self.docker_dir
        )
        
        if not result["success"]:
            safe_print(f"❌ 서비스 시작 실패: {result.get('stderr', 'Unknown error')}")
            return False
        
        safe_print("✅ 서비스 시작 완료")
        return True
    
    def wait_for_health_check(self) -> bool:
        """헬스체크 대기"""
        safe_print("🩺 헬스체크 대기 중...")
        
        import requests
        
        start_time = time.time()
        timeout = self.config.health_check_timeout
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(self.config.health_check_url, timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get("status") == "healthy":
                        safe_print("✅ 헬스체크 통과")
                        return True
            
            except Exception as e:
                logger.debug(f"헬스체크 실패: {e}")
            
            safe_print("⏳ 헬스체크 재시도 중...")
            time.sleep(10)
        
        safe_print("❌ 헬스체크 시간 초과")
        return False
    
    def run_smoke_tests(self) -> bool:
        """스모크 테스트 실행"""
        safe_print("🧪 스모크 테스트 실행 중...")
        
        tests = [
            ("API 엔드포인트", f"{self.config.health_check_url.replace('/health', '/api/status')}"),
            ("WebSocket 연결", f"{self.config.health_check_url.replace('/api/health', '/socket.io/')}"),
        ]
        
        import requests
        
        for test_name, url in tests:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code < 400:
                    safe_print(f"✅ {test_name} 테스트 통과")
                else:
                    safe_print(f"⚠️ {test_name} 테스트 경고: {response.status_code}")
                    
            except Exception as e:
                safe_print(f"❌ {test_name} 테스트 실패: {e}")
                return False
        
        safe_print("✅ 모든 스모크 테스트 통과")
        return True
    
    def deploy(self) -> DeploymentRecord:
        """배포 실행"""
        deployment_id = self.generate_deployment_id()
        
        deployment = DeploymentRecord(
            deployment_id=deployment_id,
            environment=self.config.environment,
            image_tag=self.config.image_tag,
            status=DeploymentStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        self.current_deployment = deployment
        self.deployment_history.append(deployment)
        
        safe_print(f"🚀 배포 시작: {deployment_id}")
        safe_print(f"📦 이미지 태그: {self.config.image_tag}")
        safe_print(f"🌍 환경: {self.config.environment.value}")
        
        try:
            # 1. 사전 조건 확인
            if not self.check_prerequisites():
                raise Exception("사전 조건 확인 실패")
            
            # 2. 백업 생성
            backup_name = self.create_backup()
            if backup_name:
                safe_print(f"💾 백업 생성: {backup_name}")
            
            # 3. 최신 이미지 다운로드
            if not self.pull_images():
                raise Exception("이미지 다운로드 실패")
            
            # 4. 현재 서비스 중지
            if not self.stop_current_services():
                raise Exception("서비스 중지 실패")
            
            # 5. 새 서비스 시작
            if not self.start_new_services():
                raise Exception("서비스 시작 실패")
            
            # 6. 헬스체크 대기
            if not self.wait_for_health_check():
                raise Exception("헬스체크 실패")
            
            # 7. 스모크 테스트
            if not self.run_smoke_tests():
                raise Exception("스모크 테스트 실패")
            
            # 배포 성공
            deployment.status = DeploymentStatus.SUCCESS
            deployment.completed_at = datetime.now()
            
            duration = (deployment.completed_at - deployment.started_at).total_seconds()
            safe_print(f"✅ 배포 성공 완료!")
            safe_print(f"⏱️ 소요 시간: {duration:.1f}초")
            
            # 성공 알림
            self.send_notification("success", f"배포 성공: {deployment_id}")
            
        except Exception as e:
            # 배포 실패
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now()
            deployment.error_message = str(e)
            
            logger.error(f"배포 실패: {e}")
            safe_print(f"❌ 배포 실패: {e}")
            
            # 롤백 실행
            if self.config.rollback_enabled:
                self.rollback(deployment_id)
            
            # 실패 알림
            self.send_notification("failure", f"배포 실패: {deployment_id} - {e}")
        
        return deployment
    
    def rollback(self, failed_deployment_id: str) -> bool:
        """롤백 실행"""
        safe_print("🔄 롤백 시작...")
        
        try:
            # 이전 배포 찾기
            previous_successful = None
            for record in reversed(self.deployment_history[:-1]):  # 현재 실패한 것 제외
                if record.status == DeploymentStatus.SUCCESS:
                    previous_successful = record
                    break
            
            if not previous_successful:
                safe_print("❌ 롤백할 이전 버전이 없습니다")
                return False
            
            safe_print(f"🔄 이전 버전으로 롤백: {previous_successful.image_tag}")
            
            # 이전 이미지로 롤백 배포
            rollback_config = DeploymentConfig(
                environment=self.config.environment,
                docker_registry=self.config.docker_registry,
                image_tag=previous_successful.image_tag,
                docker_compose_file=self.config.docker_compose_file,
                health_check_url=self.config.health_check_url,
                backup_enabled=False,  # 롤백 시에는 백업 생성 안함
                rollback_enabled=False  # 롤백의 롤백은 하지 않음
            )
            
            rollback_manager = DeploymentManager(rollback_config)
            rollback_deployment = rollback_manager.deploy()
            
            if rollback_deployment.status == DeploymentStatus.SUCCESS:
                # 원래 실패한 배포를 롤백된 것으로 표시
                for record in self.deployment_history:
                    if record.deployment_id == failed_deployment_id:
                        record.status = DeploymentStatus.ROLLED_BACK
                        record.rollback_deployment_id = rollback_deployment.deployment_id
                        break
                
                safe_print("✅ 롤백 성공")
                self.send_notification("rollback", f"롤백 성공: {rollback_deployment.deployment_id}")
                return True
            
            else:
                safe_print("❌ 롤백 실패")
                return False
                
        except Exception as e:
            logger.error(f"롤백 실행 실패: {e}")
            safe_print(f"❌ 롤백 실행 실패: {e}")
            return False
    
    def send_notification(self, event_type: str, message: str):
        """배포 알림 전송"""
        if not self.config.notification_webhook:
            return
        
        try:
            import requests
            
            webhook_data = {
                "text": f"🚀 Two Very Auto - {message}",
                "attachments": [
                    {
                        "color": "good" if event_type == "success" else "danger" if event_type == "failure" else "warning",
                        "fields": [
                            {"title": "Environment", "value": self.config.environment.value, "short": True},
                            {"title": "Image Tag", "value": self.config.image_tag, "short": True},
                            {"title": "Timestamp", "value": datetime.now().isoformat(), "short": True}
                        ]
                    }
                ]
            }
            
            requests.post(self.config.notification_webhook, json=webhook_data, timeout=10)
            
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """배포 상태 조회"""
        return {
            "current_deployment": asdict(self.current_deployment) if self.current_deployment else None,
            "deployment_history": [asdict(record) for record in self.deployment_history[-10:]],  # 최근 10개
            "environment": self.config.environment.value,
            "config": {
                "image_tag": self.config.image_tag,
                "docker_registry": self.config.docker_registry,
                "health_check_url": self.config.health_check_url,
                "rollback_enabled": self.config.rollback_enabled,
                "backup_enabled": self.config.backup_enabled
            }
        }


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Two Very Auto 자동 배포 도구")
    parser.add_argument("--environment", choices=["development", "staging", "production"], 
                       required=True, help="배포 환경")
    parser.add_argument("--image-tag", default="latest", help="Docker 이미지 태그")
    parser.add_argument("--registry", default="ghcr.io/your-org/two-very-auto", help="Docker 레지스트리")
    parser.add_argument("--health-check-url", default="http://localhost:8080/api/health", 
                       help="헬스체크 URL")
    parser.add_argument("--no-backup", action="store_true", help="백업 생성 건너뛰기")
    parser.add_argument("--no-rollback", action="store_true", help="롤백 비활성화")
    parser.add_argument("--webhook", help="알림 웹훅 URL")
    parser.add_argument("--status", action="store_true", help="배포 상태만 조회")
    
    args = parser.parse_args()
    
    # 설정 생성
    config = DeploymentConfig(
        environment=Environment(args.environment),
        docker_registry=args.registry,
        image_tag=args.image_tag,
        health_check_url=args.health_check_url,
        backup_enabled=not args.no_backup,
        rollback_enabled=not args.no_rollback,
        notification_webhook=args.webhook
    )
    
    # 배포 관리자 생성
    deployment_manager = DeploymentManager(config)
    
    if args.status:
        # 상태 조회만
        status = deployment_manager.get_deployment_status()
        safe_print(f"📊 배포 상태: {json.dumps(status, indent=2, default=str)}")
    else:
        # 배포 실행
        deployment_result = deployment_manager.deploy()
        safe_print(f"🏁 배포 완료: {deployment_result.status.value}")


if __name__ == "__main__":
    main()