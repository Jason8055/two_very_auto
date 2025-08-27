#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패킷 데이터 아카이빙 매니저
대용량 패킷 데이터의 자동 압축, 아카이빙, 관리 시스템
"""

import os
import zipfile
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
from dataclasses import dataclass, asdict
import threading
import time


@dataclass
class ArchiveMetadata:
    """아카이브 메타데이터"""
    original_path: str
    archive_path: str
    original_size: int
    compressed_size: int
    file_count: int
    created_at: str
    compression_ratio: float


class PacketArchiveManager:
    """패킷 데이터 아카이빙 매니저"""
    
    def __init__(self, 
                 packet_root: str = "F:/two very auto 25.08.23/packet",
                 archive_root: str = "F:/two very auto 25.08.23/archives",
                 retention_days: int = 30):
        self.packet_root = Path(packet_root)
        self.archive_root = Path(archive_root)
        self.retention_days = retention_days
        self.metadata_file = self.archive_root / "archive_metadata.json"
        
        # 아카이브 디렉토리 생성
        self.archive_root.mkdir(exist_ok=True)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 메타데이터 로드
        self.metadata: List[ArchiveMetadata] = self._load_metadata()
    
    def _load_metadata(self) -> List[ArchiveMetadata]:
        """메타데이터 파일 로드"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return [ArchiveMetadata(**item) for item in data]
        except Exception as e:
            self.logger.error(f"메타데이터 로드 실패: {e}")
        return []
    
    def _save_metadata(self):
        """메타데이터 파일 저장"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(meta) for meta in self.metadata], f, 
                         indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"메타데이터 저장 실패: {e}")
    
    def get_archivable_directories(self) -> List[Tuple[Path, int]]:
        """아카이빙 가능한 디렉토리 목록 반환"""
        archivable = []
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        try:
            for date_dir in self.packet_root.iterdir():
                if date_dir.is_dir() and date_dir.name.startswith('2025'):
                    try:
                        # 디렉토리명에서 날짜 추출 (YYYYMMDD)
                        dir_date = datetime.strptime(date_dir.name, '%Y%m%d')
                        if dir_date < cutoff_date:
                            file_count = len(list(date_dir.glob('*.txt')))
                            archivable.append((date_dir, file_count))
                    except ValueError:
                        continue
        except Exception as e:
            self.logger.error(f"디렉토리 스캔 실패: {e}")
        
        return archivable
    
    def calculate_directory_size(self, directory: Path) -> int:
        """디렉토리 크기 계산"""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.error(f"크기 계산 실패 {directory}: {e}")
        return total_size
    
    def create_archive(self, source_dir: Path) -> Optional[ArchiveMetadata]:
        """단일 디렉토리 아카이빙"""
        try:
            # 원본 정보 수집
            original_size = self.calculate_directory_size(source_dir)
            file_count = len(list(source_dir.glob('*.txt')))
            
            if file_count == 0:
                self.logger.info(f"빈 디렉토리 건너뛰기: {source_dir}")
                return None
            
            # 아카이브 파일 경로
            archive_name = f"{source_dir.name}_packet_data.zip"
            archive_path = self.archive_root / archive_name
            
            self.logger.info(f"아카이빙 시작: {source_dir} -> {archive_path}")
            
            # ZIP 압축
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, 
                               compresslevel=9) as zipf:
                for txt_file in source_dir.glob('*.txt'):
                    # 아카이브 내 경로 = 날짜/파일명
                    arcname = f"{source_dir.name}/{txt_file.name}"
                    zipf.write(txt_file, arcname)
            
            # 압축 후 크기
            compressed_size = archive_path.stat().st_size
            compression_ratio = compressed_size / original_size if original_size > 0 else 0
            
            # 메타데이터 생성
            metadata = ArchiveMetadata(
                original_path=str(source_dir),
                archive_path=str(archive_path),
                original_size=original_size,
                compressed_size=compressed_size,
                file_count=file_count,
                created_at=datetime.now().isoformat(),
                compression_ratio=compression_ratio
            )
            
            self.logger.info(
                f"아카이빙 완료: {file_count}개 파일, "
                f"압축률 {compression_ratio:.2%}, "
                f"{original_size//1024}KB -> {compressed_size//1024}KB"
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"아카이빙 실패 {source_dir}: {e}")
            return None
    
    def archive_old_data(self, dry_run: bool = False) -> Dict:
        """오래된 데이터 자동 아카이빙"""
        archivable_dirs = self.get_archivable_directories()
        results = {
            'total_dirs': len(archivable_dirs),
            'archived': [],
            'failed': [],
            'total_original_size': 0,
            'total_compressed_size': 0,
            'space_saved': 0
        }
        
        if not archivable_dirs:
            self.logger.info("아카이빙할 디렉토리가 없습니다.")
            return results
        
        self.logger.info(f"{len(archivable_dirs)}개 디렉토리 아카이빙 시작")
        
        for dir_path, file_count in archivable_dirs:
            if dry_run:
                size = self.calculate_directory_size(dir_path)
                results['total_original_size'] += size
                self.logger.info(f"[DRY-RUN] {dir_path.name}: {file_count}개 파일, {size//1024}KB")
                continue
            
            # 실제 아카이빙
            metadata = self.create_archive(dir_path)
            if metadata:
                self.metadata.append(metadata)
                results['archived'].append(metadata.original_path)
                results['total_original_size'] += metadata.original_size
                results['total_compressed_size'] += metadata.compressed_size
                
                # 원본 디렉토리 삭제
                try:
                    shutil.rmtree(dir_path)
                    self.logger.info(f"원본 디렉토리 삭제: {dir_path}")
                except Exception as e:
                    self.logger.error(f"원본 삭제 실패 {dir_path}: {e}")
            else:
                results['failed'].append(str(dir_path))
        
        # 메타데이터 저장
        if not dry_run and results['archived']:
            self._save_metadata()
        
        # 통계 계산
        results['space_saved'] = results['total_original_size'] - results['total_compressed_size']
        compression_ratio = (results['total_compressed_size'] / results['total_original_size'] 
                           if results['total_original_size'] > 0 else 0)
        
        self.logger.info(
            f"아카이빙 완료: {len(results['archived'])}개 성공, "
            f"{len(results['failed'])}개 실패, "
            f"압축률: {compression_ratio:.2%}, "
            f"절약 공간: {results['space_saved']//1024//1024}MB"
        )
        
        return results
    
    def extract_archive(self, date_str: str, extract_to: Optional[str] = None) -> bool:
        """아카이브 추출"""
        try:
            archive_name = f"{date_str}_packet_data.zip"
            archive_path = self.archive_root / archive_name
            
            if not archive_path.exists():
                self.logger.error(f"아카이브 없음: {archive_path}")
                return False
            
            extract_path = Path(extract_to) if extract_to else self.packet_root
            
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_path)
            
            self.logger.info(f"아카이브 추출 완료: {archive_path} -> {extract_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"아카이브 추출 실패: {e}")
            return False
    
    def get_archive_info(self) -> List[Dict]:
        """아카이브 정보 조회"""
        info = []
        for meta in self.metadata:
            info.append({
                'date': Path(meta.original_path).name,
                'files': meta.file_count,
                'original_size_mb': meta.original_size // 1024 // 1024,
                'compressed_size_mb': meta.compressed_size // 1024 // 1024,
                'compression_ratio': f"{meta.compression_ratio:.2%}",
                'created_at': meta.created_at,
                'space_saved_mb': (meta.original_size - meta.compressed_size) // 1024 // 1024
            })
        return info
    
    def start_auto_archiving(self, interval_hours: int = 24):
        """자동 아카이빙 백그라운드 작업 시작"""
        def archive_worker():
            while True:
                try:
                    self.logger.info("정기 아카이빙 작업 시작")
                    results = self.archive_old_data()
                    if results['archived']:
                        self.logger.info(f"정기 아카이빙: {len(results['archived'])}개 처리")
                except Exception as e:
                    self.logger.error(f"정기 아카이빙 오류: {e}")
                
                # 다음 실행까지 대기
                time.sleep(interval_hours * 3600)
        
        worker_thread = threading.Thread(target=archive_worker, daemon=True)
        worker_thread.start()
        self.logger.info(f"자동 아카이빙 시작 (간격: {interval_hours}시간)")


def main():
    """CLI 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='패킷 데이터 아카이빙 매니저')
    parser.add_argument('--action', choices=['scan', 'archive', 'info', 'extract'], 
                       default='scan', help='실행할 작업')
    parser.add_argument('--dry-run', action='store_true', help='실제 실행하지 않고 시뮬레이션')
    parser.add_argument('--date', help='추출할 날짜 (YYYYMMDD)')
    parser.add_argument('--retention-days', type=int, default=30, help='보관 기간 (일)')
    
    args = parser.parse_args()
    
    manager = PacketArchiveManager(retention_days=args.retention_days)
    
    if args.action == 'scan':
        dirs = manager.get_archivable_directories()
        print(f"\n아카이빙 가능한 디렉토리: {len(dirs)}개")
        for dir_path, file_count in dirs:
            size = manager.calculate_directory_size(dir_path)
            print(f"  {dir_path.name}: {file_count}개 파일, {size//1024//1024}MB")
    
    elif args.action == 'archive':
        results = manager.archive_old_data(dry_run=args.dry_run)
        print(f"\n아카이빙 결과:")
        print(f"  처리 대상: {results['total_dirs']}개")
        print(f"  성공: {len(results['archived'])}개")
        print(f"  실패: {len(results['failed'])}개")
        print(f"  절약 공간: {results['space_saved']//1024//1024}MB")
    
    elif args.action == 'info':
        info = manager.get_archive_info()
        print(f"\n아카이브 정보: {len(info)}개")
        for item in info:
            print(f"  {item['date']}: {item['files']}개 파일, "
                  f"{item['original_size_mb']}MB -> {item['compressed_size_mb']}MB "
                  f"({item['compression_ratio']})")
    
    elif args.action == 'extract' and args.date:
        success = manager.extract_archive(args.date)
        print(f"추출 {'성공' if success else '실패'}: {args.date}")


if __name__ == "__main__":
    main()