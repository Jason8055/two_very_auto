#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
백업 건전성 점검 및 정기 복원 테스트 시스템
자동으로 백업 파일의 무결성을 확인하고 복원 테스트를 수행
"""

import os
import json
import sqlite3
import hashlib
import shutil
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncio

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 클라우드 백업 모듈
from cloud.backup_manager import get_backup_manager
from cloud.restore_system import get_restore_system

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

class BackupHealthChecker:
    """백업 건전성 점검기"""
    
    def __init__(self):
        self.backup_manager = get_backup_manager()
        self.restore_system = get_restore_system()
        self.test_results = []
        self.temp_dir = Path(tempfile.gettempdir()) / "backup_health_tests"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 설정 로드
        self.config = self.load_health_check_config()
        
        safe_print("🏥 백업 건전성 점검기 초기화")
    
    def load_health_check_config(self) -> Dict[str, Any]:
        """건전성 점검 설정 로드"""
        config_path = Path("backup_health_config.json")
        
        default_config = {
            "enabled": True,
            "test_interval_days": 7,
            "max_test_duration_minutes": 30,
            "tests": {
                "file_integrity": True,
                "database_structure": True,
                "data_completeness": True,
                "restore_functionality": True,
                "performance_benchmark": True
            },
            "thresholds": {
                "max_restore_time_minutes": 5,
                "min_data_records": 100,
                "max_file_size_diff_percent": 5
            },
            "notifications": {
                "success": False,
                "warning": True,
                "failure": True,
                "report_email": None
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값과 병합
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
            else:
                config = default_config
                self.save_health_check_config(config)
                
            return config
        except Exception as e:
            logger.error(f"건전성 점검 설정 로드 오류: {e}")
            return default_config
    
    def save_health_check_config(self, config: Dict[str, Any]):
        """건전성 점검 설정 저장"""
        config_path = Path("backup_health_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"건전성 점검 설정 저장 오류: {e}")
    
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """종합 건전성 점검 실행"""
        safe_print("🔍 종합 백업 건전성 점검 시작")
        
        start_time = datetime.now()
        health_report = {
            "timestamp": start_time.isoformat(),
            "test_results": {},
            "overall_status": "unknown",
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        try:
            # 1. 백업 파일 발견 및 목록화
            safe_print("📁 백업 파일 검색 중...")
            restore_points = self.restore_system.discover_restore_points()
            
            if not restore_points:
                health_report["overall_status"] = "critical"
                health_report["errors"].append("복원 가능한 백업이 없습니다")
                return health_report
            
            safe_print(f"✅ {len(restore_points)}개 백업 발견")
            
            # 2. 최신 백업들에 대해 테스트 수행
            recent_backups = restore_points[:3]  # 최신 3개
            
            for i, backup in enumerate(recent_backups):
                safe_print(f"🧪 백업 테스트 {i+1}/{len(recent_backups)}: {backup.backup_id}")
                
                test_result = await self.test_single_backup(backup)
                health_report["test_results"][backup.backup_id] = test_result
                
                # 결과 분석
                if not test_result["success"]:
                    health_report["errors"].extend(test_result.get("errors", []))
                elif test_result.get("warnings"):
                    health_report["warnings"].extend(test_result.get("warnings", []))
            
            # 3. 전반적 상태 평가
            health_report["overall_status"] = self._evaluate_overall_health(health_report)
            
            # 4. 권장사항 생성
            health_report["recommendations"] = self._generate_recommendations(health_report)
            
            duration = datetime.now() - start_time
            safe_print(f"✅ 건전성 점검 완료 ({duration.total_seconds():.1f}초)")
            
        except Exception as e:
            logger.error(f"건전성 점검 오류: {e}")
            health_report["overall_status"] = "error"
            health_report["errors"].append(f"점검 중 오류: {str(e)}")
        
        # 결과 저장
        self._save_health_report(health_report)
        
        return health_report
    
    async def test_single_backup(self, restore_point) -> Dict[str, Any]:
        """단일 백업 파일 테스트"""
        test_result = {
            "backup_id": restore_point.backup_id,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "tests_passed": [],
            "tests_failed": [],
            "warnings": [],
            "errors": [],
            "metrics": {}
        }
        
        try:
            # 테스트 1: 파일 무결성 확인
            if self.config["tests"]["file_integrity"]:
                integrity_result = await self._test_file_integrity(restore_point)
                if integrity_result["success"]:
                    test_result["tests_passed"].append("file_integrity")
                    test_result["metrics"]["file_size_mb"] = integrity_result["size_mb"]
                else:
                    test_result["tests_failed"].append("file_integrity")
                    test_result["errors"].extend(integrity_result["errors"])
            
            # 테스트 2: 복원 기능 테스트
            if self.config["tests"]["restore_functionality"]:
                restore_result = await self._test_restore_functionality(restore_point)
                if restore_result["success"]:
                    test_result["tests_passed"].append("restore_functionality")
                    test_result["metrics"]["restore_time_seconds"] = restore_result["duration"]
                else:
                    test_result["tests_failed"].append("restore_functionality")
                    test_result["errors"].extend(restore_result["errors"])
            
            # 테스트 3: 데이터베이스 구조 확인
            if self.config["tests"]["database_structure"]:
                structure_result = await self._test_database_structure(restore_point)
                if structure_result["success"]:
                    test_result["tests_passed"].append("database_structure")
                    test_result["metrics"]["table_count"] = structure_result["table_count"]
                else:
                    test_result["tests_failed"].append("database_structure")
                    test_result["errors"].extend(structure_result["errors"])
            
            # 테스트 4: 데이터 완전성 확인
            if self.config["tests"]["data_completeness"]:
                completeness_result = await self._test_data_completeness(restore_point)
                if completeness_result["success"]:
                    test_result["tests_passed"].append("data_completeness")
                    test_result["metrics"]["record_count"] = completeness_result["record_count"]
                else:
                    test_result["tests_failed"].append("data_completeness")
                    test_result["errors"].extend(completeness_result["errors"])
            
            # 전체 성공 여부 결정
            test_result["success"] = len(test_result["tests_failed"]) == 0
            
        except Exception as e:
            test_result["success"] = False
            test_result["errors"].append(f"테스트 실행 오류: {str(e)}")
        
        return test_result
    
    async def _test_file_integrity(self, restore_point) -> Dict[str, Any]:
        """파일 무결성 테스트"""
        result = {"success": False, "errors": [], "size_mb": 0}
        
        try:
            # 백업 파일 다운로드
            local_file = self.restore_system.download_backup_file(restore_point)
            
            if not local_file or not Path(local_file).exists():
                result["errors"].append("백업 파일 다운로드 실패")
                return result
            
            file_path = Path(local_file)
            file_size = file_path.stat().st_size
            result["size_mb"] = file_size / (1024 * 1024)
            
            # 파일 크기 검증
            expected_min_size = 1024  # 최소 1KB
            if file_size < expected_min_size:
                result["errors"].append(f"파일 크기가 너무 작습니다: {file_size} bytes")
                return result
            
            # 파일 해시 계산
            sha256_hash = self._calculate_file_hash(file_path)
            result["file_hash"] = sha256_hash
            
            result["success"] = True
            
        except Exception as e:
            result["errors"].append(f"파일 무결성 테스트 오류: {str(e)}")
        
        return result
    
    async def _test_restore_functionality(self, restore_point) -> Dict[str, Any]:
        """복원 기능 테스트"""
        result = {"success": False, "errors": [], "duration": 0}
        
        try:
            start_time = datetime.now()
            
            # 임시 위치에 복원
            test_db_path = self.temp_dir / f"test_restore_{restore_point.backup_id}.db"
            
            restore_result = self.restore_system.restore_database(
                restore_point, 
                str(test_db_path)
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            result["duration"] = duration
            
            if restore_result.success:
                # 복원된 파일 확인
                if test_db_path.exists():
                    result["success"] = True
                    
                    # 임시 파일 정리
                    test_db_path.unlink(missing_ok=True)
                else:
                    result["errors"].append("복원된 파일이 생성되지 않음")
            else:
                result["errors"].append(f"복원 실패: {restore_result.error_message}")
            
        except Exception as e:
            result["errors"].append(f"복원 기능 테스트 오류: {str(e)}")
        
        return result
    
    async def _test_database_structure(self, restore_point) -> Dict[str, Any]:
        """데이터베이스 구조 테스트"""
        result = {"success": False, "errors": [], "table_count": 0}
        
        try:
            # 임시 복원
            test_db_path = self.temp_dir / f"test_structure_{restore_point.backup_id}.db"
            
            restore_result = self.restore_system.restore_database(
                restore_point,
                str(test_db_path)
            )
            
            if not restore_result.success:
                result["errors"].append("데이터베이스 복원 실패")
                return result
            
            # SQLite 데이터베이스 구조 확인
            with sqlite3.connect(test_db_path) as conn:
                cursor = conn.cursor()
                
                # 테이블 목록 확인
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                result["table_count"] = len(tables)
                
                # 필수 테이블 확인
                required_tables = ["games"]
                existing_tables = [table[0] for table in tables]
                
                missing_tables = []
                for required_table in required_tables:
                    if required_table not in existing_tables:
                        missing_tables.append(required_table)
                
                if missing_tables:
                    result["errors"].append(f"필수 테이블 누락: {missing_tables}")
                else:
                    result["success"] = True
            
            # 임시 파일 정리
            test_db_path.unlink(missing_ok=True)
            
        except Exception as e:
            result["errors"].append(f"데이터베이스 구조 테스트 오류: {str(e)}")
        
        return result
    
    async def _test_data_completeness(self, restore_point) -> Dict[str, Any]:
        """데이터 완전성 테스트"""
        result = {"success": False, "errors": [], "record_count": 0}
        
        try:
            # 임시 복원
            test_db_path = self.temp_dir / f"test_data_{restore_point.backup_id}.db"
            
            restore_result = self.restore_system.restore_database(
                restore_point,
                str(test_db_path)
            )
            
            if not restore_result.success:
                result["errors"].append("데이터베이스 복원 실패")
                return result
            
            # 데이터 레코드 수 확인
            with sqlite3.connect(test_db_path) as conn:
                cursor = conn.cursor()
                
                # games 테이블 레코드 수
                cursor.execute("SELECT COUNT(*) FROM games")
                record_count = cursor.fetchone()[0]
                
                result["record_count"] = record_count
                
                # 최소 레코드 수 확인
                min_records = self.config["thresholds"]["min_data_records"]
                if record_count < min_records:
                    result["errors"].append(f"데이터가 너무 적습니다: {record_count} < {min_records}")
                else:
                    result["success"] = True
            
            # 임시 파일 정리
            test_db_path.unlink(missing_ok=True)
            
        except Exception as e:
            result["errors"].append(f"데이터 완전성 테스트 오류: {str(e)}")
        
        return result
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """파일 SHA256 해시 계산"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def _evaluate_overall_health(self, health_report: Dict[str, Any]) -> str:
        """전반적 건전성 상태 평가"""
        if health_report["errors"]:
            return "critical"
        
        test_results = health_report["test_results"]
        if not test_results:
            return "unknown"
        
        total_tests = len(test_results)
        successful_tests = sum(1 for result in test_results.values() if result["success"])
        
        success_rate = successful_tests / total_tests
        
        if success_rate >= 0.8:
            return "healthy" if not health_report["warnings"] else "good"
        elif success_rate >= 0.6:
            return "warning"
        else:
            return "critical"
    
    def _generate_recommendations(self, health_report: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        overall_status = health_report["overall_status"]
        
        if overall_status == "critical":
            recommendations.extend([
                "즉시 백업 시스템을 점검하세요",
                "새로운 백업을 수행하세요",
                "백업 저장소의 용량과 권한을 확인하세요"
            ])
        elif overall_status == "warning":
            recommendations.extend([
                "백업 설정을 검토하세요",
                "정기적인 백업 모니터링을 강화하세요"
            ])
        elif overall_status in ["healthy", "good"]:
            recommendations.extend([
                "현재 백업 시스템이 정상 작동 중입니다",
                "정기 점검 일정을 유지하세요"
            ])
        
        # 경고가 있는 경우
        if health_report["warnings"]:
            recommendations.append("경고 사항들을 검토하고 개선하세요")
        
        return recommendations
    
    def _save_health_report(self, health_report: Dict[str, Any]):
        """건전성 리포트 저장"""
        reports_dir = Path("backup_health_reports")
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"health_report_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(health_report, f, ensure_ascii=False, indent=2)
            
            safe_print(f"📊 건전성 리포트 저장: {report_file}")
            
        except Exception as e:
            logger.error(f"건전성 리포트 저장 오류: {e}")
    
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            safe_print("🧹 임시 파일 정리 완료")
        except Exception as e:
            logger.error(f"임시 파일 정리 오류: {e}")

async def main():
    """메인 실행 함수"""
    checker = BackupHealthChecker()
    
    try:
        # 종합 건전성 점검 실행
        health_report = await checker.run_comprehensive_health_check()
        
        # 결과 요약
        safe_print("=" * 60)
        safe_print("📋 백업 건전성 점검 결과")
        safe_print("=" * 60)
        safe_print(f"🏥 전반적 상태: {health_report['overall_status'].upper()}")
        safe_print(f"📊 테스트 완료: {len(health_report['test_results'])}개")
        safe_print(f"⚠️ 경고: {len(health_report['warnings'])}개")
        safe_print(f"❌ 오류: {len(health_report['errors'])}개")
        
        if health_report["warnings"]:
            safe_print("\n⚠️ 경고 사항:")
            for warning in health_report["warnings"]:
                safe_print(f"  - {warning}")
        
        if health_report["errors"]:
            safe_print("\n❌ 오류 사항:")
            for error in health_report["errors"]:
                safe_print(f"  - {error}")
        
        safe_print("\n💡 권장사항:")
        for recommendation in health_report["recommendations"]:
            safe_print(f"  - {recommendation}")
        
    except Exception as e:
        safe_print(f"❌ 건전성 점검 실행 오류: {e}")
    
    finally:
        # 정리
        checker.cleanup_temp_files()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())