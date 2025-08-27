#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
데이터 품질 검증 및 정리 스크립트
배치 처리된 데이터의 품질을 검증하고 문제가 있는 데이터를 정리
"""

import sqlite3
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
from collections import defaultdict, Counter

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidator:
    """데이터 품질 검증 및 정리 클래스"""
    
    def __init__(self, db_path: str = "F:/two very auto 25.08.23/python/fastapi_app/baccarat_data.db"):
        """
        데이터 검증기 초기화
        
        Args:
            db_path: 데이터베이스 경로
        """
        self.db_path = Path(db_path)
        self.validation_report = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'issues': defaultdict(int),
            'corrections': defaultdict(int),
            'recommendations': []
        }
        
        logger.info(f"[Data Validator] 초기화 완료 - DB: {self.db_path}")
    
    async def run_validation(self) -> Dict[str, Any]:
        """전체 데이터 검증 실행"""
        try:
            logger.info("🔍 데이터 품질 검증 시작")
            
            # 1. 기본 통계 수집
            await self._collect_basic_stats()
            
            # 2. 데이터 무결성 검증
            await self._validate_data_integrity()
            
            # 3. 페어 데이터 검증
            await self._validate_pair_data()
            
            # 4. 중복 데이터 검증
            await self._validate_duplicates()
            
            # 5. 카드 데이터 검증
            await self._validate_card_data()
            
            # 6. 시간 데이터 검증
            await self._validate_time_data()
            
            # 7. 데이터 정리 수행
            await self._cleanup_invalid_data()
            
            # 8. 인덱스 최적화
            await self._optimize_indexes()
            
            # 9. 검증 결과 요약
            self._generate_recommendations()
            
            logger.info("✅ 데이터 품질 검증 완료")
            return self.validation_report
            
        except Exception as e:
            logger.error(f"데이터 검증 실패: {e}")
            raise
    
    async def _collect_basic_stats(self):
        """기본 통계 수집"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 전체 레코드 수
            cursor.execute("SELECT COUNT(*) FROM baccarat_games")
            self.validation_report['total_records'] = cursor.fetchone()[0]
            
            # 테이블별 통계
            cursor.execute('''
                SELECT 
                    table_name,
                    COUNT(*) as record_count,
                    COUNT(CASE WHEN has_any_pair = 1 THEN 1 END) as pair_count,
                    MIN(game_time) as earliest_game,
                    MAX(game_time) as latest_game
                FROM baccarat_games 
                GROUP BY table_name
                ORDER BY record_count DESC
            ''')
            
            table_stats = cursor.fetchall()
            self.validation_report['table_stats'] = [
                {
                    'table_name': row[0],
                    'record_count': row[1],
                    'pair_count': row[2],
                    'pair_rate': round(row[2] / row[1] * 100, 2) if row[1] > 0 else 0,
                    'earliest_game': row[3],
                    'latest_game': row[4]
                }
                for row in table_stats
            ]
            
            conn.close()
            logger.info(f"📊 총 레코드: {self.validation_report['total_records']:,}개")
            
        except Exception as e:
            logger.error(f"기본 통계 수집 실패: {e}")
            raise
    
    async def _validate_data_integrity(self):
        """데이터 무결성 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 필수 필드 누락 검증
            required_fields = [
                ('table_name', 'table_name IS NULL OR table_name = ""'),
                ('game_time', 'game_time IS NULL OR game_time = ""'),
                ('player_cards', 'player_cards IS NULL OR player_cards = ""'),
                ('banker_cards', 'banker_cards IS NULL OR banker_cards = ""')
            ]
            
            for field_name, condition in required_fields:
                cursor.execute(f"SELECT COUNT(*) FROM baccarat_games WHERE {condition}")
                missing_count = cursor.fetchone()[0]
                
                if missing_count > 0:
                    self.validation_report['issues'][f'missing_{field_name}'] = missing_count
                    logger.warning(f"❌ {field_name} 누락: {missing_count}개")
            
            # 점수 범위 검증 (바카라는 0-9)
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE player_score < 0 OR player_score > 9 
                OR banker_score < 0 OR banker_score > 9
            ''')
            
            invalid_scores = cursor.fetchone()[0]
            if invalid_scores > 0:
                self.validation_report['issues']['invalid_scores'] = invalid_scores
                logger.warning(f"❌ 잘못된 점수: {invalid_scores}개")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"데이터 무결성 검증 실패: {e}")
            raise
    
    async def _validate_pair_data(self):
        """페어 데이터 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 페어 플래그 일치성 검증
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE (has_player_pair = 1 OR has_banker_pair = 1) 
                AND has_any_pair = 0
            ''')
            
            inconsistent_pairs = cursor.fetchone()[0]
            if inconsistent_pairs > 0:
                self.validation_report['issues']['inconsistent_pair_flags'] = inconsistent_pairs
                logger.warning(f"❌ 페어 플래그 불일치: {inconsistent_pairs}개")
            
            # 페어 타입과 플래그 불일치 검증
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE pair_type = 'PLAYER_PAIR' AND has_player_pair = 0
            ''')
            
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE pair_type = 'BANKER_PAIR' AND has_banker_pair = 0
            ''')
            
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE pair_type = 'BOTH_PAIR' 
                AND (has_player_pair = 0 OR has_banker_pair = 0)
            ''')
            
            type_flag_mismatches = sum([cursor.fetchone()[0] for _ in range(3)])
            if type_flag_mismatches > 0:
                self.validation_report['issues']['pair_type_flag_mismatch'] = type_flag_mismatches
                logger.warning(f"❌ 페어 타입-플래그 불일치: {type_flag_mismatches}개")
            
            # 페어 카드 검증
            cursor.execute('''
                SELECT id, pair_cards FROM baccarat_games 
                WHERE has_any_pair = 1 AND pair_cards IS NOT NULL
                LIMIT 1000
            ''')
            
            pair_card_issues = 0
            for row in cursor.fetchall():
                game_id, pair_cards_json = row
                try:
                    pair_cards = json.loads(pair_cards_json)
                    if not isinstance(pair_cards, list) or len(pair_cards) == 0:
                        pair_card_issues += 1
                except (json.JSONDecodeError, TypeError):
                    pair_card_issues += 1
            
            if pair_card_issues > 0:
                self.validation_report['issues']['invalid_pair_cards'] = pair_card_issues
                logger.warning(f"❌ 잘못된 페어 카드: {pair_card_issues}개")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"페어 데이터 검증 실패: {e}")
            raise
    
    async def _validate_duplicates(self):
        """중복 데이터 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 완전 중복 검증
            cursor.execute('''
                SELECT table_name, game_time, player_cards, banker_cards, COUNT(*) as dup_count
                FROM baccarat_games 
                GROUP BY table_name, game_time, player_cards, banker_cards
                HAVING COUNT(*) > 1
            ''')
            
            duplicates = cursor.fetchall()
            duplicate_count = sum(row[4] - 1 for row in duplicates)  # 중복된 개수만 카운트
            
            if duplicate_count > 0:
                self.validation_report['issues']['complete_duplicates'] = duplicate_count
                logger.warning(f"❌ 완전 중복 데이터: {duplicate_count}개")
                
                # 중복 데이터 상세 정보
                self.validation_report['duplicate_details'] = [
                    {
                        'table_name': row[0],
                        'game_time': row[1],
                        'duplicate_count': row[4]
                    }
                    for row in duplicates[:10]  # 상위 10개만
                ]
            
            # 유사 중복 (같은 시간, 다른 카드) 검증
            cursor.execute('''
                SELECT table_name, game_time, COUNT(*) as similar_count
                FROM baccarat_games 
                GROUP BY table_name, game_time
                HAVING COUNT(*) > 1
            ''')
            
            similar_duplicates = cursor.fetchall()
            similar_count = len(similar_duplicates)
            
            if similar_count > 0:
                self.validation_report['issues']['similar_duplicates'] = similar_count
                logger.info(f"ℹ️ 같은 시간 다른 데이터: {similar_count}개")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"중복 데이터 검증 실패: {e}")
            raise
    
    async def _validate_card_data(self):
        """카드 데이터 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 카드 JSON 파싱 오류 검증
            cursor.execute('SELECT id, player_cards, banker_cards FROM baccarat_games LIMIT 1000')
            
            card_parsing_errors = 0
            invalid_card_format = 0
            
            for row in cursor.fetchall():
                game_id, player_cards_json, banker_cards_json = row
                
                # 플레이어 카드 검증
                try:
                    player_cards = json.loads(player_cards_json)
                    if not isinstance(player_cards, list):
                        card_parsing_errors += 1
                    elif len(player_cards) < 2 or len(player_cards) > 3:
                        invalid_card_format += 1
                    else:
                        # 카드 형식 검증 (예: "AH", "KS")
                        for card in player_cards:
                            if not isinstance(card, str) or len(card) < 2:
                                invalid_card_format += 1
                                break
                except (json.JSONDecodeError, TypeError):
                    card_parsing_errors += 1
                
                # 뱅커 카드 검증
                try:
                    banker_cards = json.loads(banker_cards_json)
                    if not isinstance(banker_cards, list):
                        card_parsing_errors += 1
                    elif len(banker_cards) < 2 or len(banker_cards) > 3:
                        invalid_card_format += 1
                    else:
                        for card in banker_cards:
                            if not isinstance(card, str) or len(card) < 2:
                                invalid_card_format += 1
                                break
                except (json.JSONDecodeError, TypeError):
                    card_parsing_errors += 1
            
            if card_parsing_errors > 0:
                self.validation_report['issues']['card_parsing_errors'] = card_parsing_errors
                logger.warning(f"❌ 카드 JSON 파싱 오류: {card_parsing_errors}개")
            
            if invalid_card_format > 0:
                self.validation_report['issues']['invalid_card_format'] = invalid_card_format
                logger.warning(f"❌ 잘못된 카드 형식: {invalid_card_format}개")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"카드 데이터 검증 실패: {e}")
            raise
    
    async def _validate_time_data(self):
        """시간 데이터 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 시간 형식 검증
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE game_time IS NOT NULL 
                AND game_time NOT LIKE '____-__-__T__:__:__%'
            ''')
            
            invalid_time_format = cursor.fetchone()[0]
            if invalid_time_format > 0:
                self.validation_report['issues']['invalid_time_format'] = invalid_time_format
                logger.warning(f"❌ 잘못된 시간 형식: {invalid_time_format}개")
            
            # 미래 시간 검증
            future_time = datetime.now() + timedelta(hours=1)
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE game_time > ?
            ''', (future_time.isoformat(),))
            
            future_games = cursor.fetchone()[0]
            if future_games > 0:
                self.validation_report['issues']['future_games'] = future_games
                logger.warning(f"❌ 미래 시간 데이터: {future_games}개")
            
            # 너무 오래된 데이터 검증 (1년 이상)
            old_time = datetime.now() - timedelta(days=365)
            cursor.execute('''
                SELECT COUNT(*) FROM baccarat_games 
                WHERE game_time < ?
            ''', (old_time.isoformat(),))
            
            old_games = cursor.fetchone()[0]
            if old_games > 0:
                self.validation_report['issues']['very_old_games'] = old_games
                logger.info(f"ℹ️ 1년 이상 된 데이터: {old_games}개")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"시간 데이터 검증 실패: {e}")
            raise
    
    async def _cleanup_invalid_data(self):
        """잘못된 데이터 정리"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cleaned_count = 0
            
            # 1. 완전 중복 데이터 제거 (가장 최근 것만 남김)
            cursor.execute('''
                DELETE FROM baccarat_games 
                WHERE id NOT IN (
                    SELECT MAX(id) 
                    FROM baccarat_games 
                    GROUP BY table_name, game_time, player_cards, banker_cards
                )
            ''')
            
            duplicate_removed = cursor.rowcount
            cleaned_count += duplicate_removed
            self.validation_report['corrections']['duplicates_removed'] = duplicate_removed
            
            if duplicate_removed > 0:
                logger.info(f"🧹 중복 데이터 정리: {duplicate_removed}개")
            
            # 2. 페어 플래그 수정
            cursor.execute('''
                UPDATE baccarat_games 
                SET has_any_pair = 1 
                WHERE (has_player_pair = 1 OR has_banker_pair = 1) 
                AND has_any_pair = 0
            ''')
            
            pair_flags_fixed = cursor.rowcount
            cleaned_count += pair_flags_fixed
            self.validation_report['corrections']['pair_flags_fixed'] = pair_flags_fixed
            
            if pair_flags_fixed > 0:
                logger.info(f"🔧 페어 플래그 수정: {pair_flags_fixed}개")
            
            # 3. 잘못된 점수 수정 (점수는 0-9 범위로 제한)
            cursor.execute('''
                UPDATE baccarat_games 
                SET player_score = player_score % 10 
                WHERE player_score > 9
            ''')
            
            cursor.execute('''
                UPDATE baccarat_games 
                SET banker_score = banker_score % 10 
                WHERE banker_score > 9
            ''')
            
            cursor.execute('''
                UPDATE baccarat_games 
                SET player_score = 0 
                WHERE player_score < 0
            ''')
            
            cursor.execute('''
                UPDATE baccarat_games 
                SET banker_score = 0 
                WHERE banker_score < 0
            ''')
            
            score_corrections = cursor.rowcount
            cleaned_count += score_corrections
            self.validation_report['corrections']['scores_corrected'] = score_corrections
            
            if score_corrections > 0:
                logger.info(f"🔧 점수 수정: {score_corrections}개")
            
            conn.commit()
            conn.close()
            
            self.validation_report['valid_records'] = (
                self.validation_report['total_records'] - 
                sum(self.validation_report['issues'].values()) + 
                cleaned_count
            )
            
            logger.info(f"✅ 총 정리된 데이터: {cleaned_count}개")
            
        except Exception as e:
            logger.error(f"데이터 정리 실패: {e}")
            raise
    
    async def _optimize_indexes(self):
        """인덱스 최적화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기존 인덱스 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            existing_indexes = [row[0] for row in cursor.fetchall()]
            
            # 권장 인덱스 생성
            recommended_indexes = [
                ("idx_table_game_time", "CREATE INDEX IF NOT EXISTS idx_table_game_time ON baccarat_games(table_name, game_time)"),
                ("idx_pairs_only", "CREATE INDEX IF NOT EXISTS idx_pairs_only ON baccarat_games(has_any_pair) WHERE has_any_pair = 1"),
                ("idx_source_date_hour", "CREATE INDEX IF NOT EXISTS idx_source_date_hour ON baccarat_games(source_date, source_hour)"),
                ("idx_pair_type", "CREATE INDEX IF NOT EXISTS idx_pair_type ON baccarat_games(pair_type) WHERE pair_type IS NOT NULL"),
                ("idx_game_time_desc", "CREATE INDEX IF NOT EXISTS idx_game_time_desc ON baccarat_games(game_time DESC)")
            ]
            
            indexes_created = 0
            for index_name, create_sql in recommended_indexes:
                if index_name not in existing_indexes:
                    cursor.execute(create_sql)
                    indexes_created += 1
                    logger.info(f"📈 인덱스 생성: {index_name}")
            
            # 데이터베이스 통계 업데이트
            cursor.execute("ANALYZE")
            
            # VACUUM으로 데이터베이스 최적화
            cursor.execute("VACUUM")
            
            conn.close()
            
            self.validation_report['corrections']['indexes_created'] = indexes_created
            logger.info(f"✅ 인덱스 최적화 완료: {indexes_created}개 생성")
            
        except Exception as e:
            logger.error(f"인덱스 최적화 실패: {e}")
            raise
    
    def _generate_recommendations(self):
        """권장사항 생성"""
        recommendations = []
        
        # 데이터 품질 평가
        total_issues = sum(self.validation_report['issues'].values())
        quality_score = max(0, 100 - (total_issues / max(self.validation_report['total_records'], 1) * 100))
        
        self.validation_report['quality_score'] = round(quality_score, 2)
        
        if quality_score >= 95:
            recommendations.append("✅ 데이터 품질이 매우 우수합니다.")
        elif quality_score >= 90:
            recommendations.append("🟡 데이터 품질이 양호합니다. 약간의 정리가 필요합니다.")
        elif quality_score >= 80:
            recommendations.append("🟠 데이터 품질에 문제가 있습니다. 정기적인 정리가 필요합니다.")
        else:
            recommendations.append("🔴 데이터 품질이 나쁩니다. 즉시 정리 작업이 필요합니다.")
        
        # 구체적 권장사항
        if self.validation_report['issues'].get('complete_duplicates', 0) > 0:
            recommendations.append("중복 데이터 정리를 정기적으로 실행하세요.")
        
        if self.validation_report['issues'].get('invalid_scores', 0) > 0:
            recommendations.append("점수 데이터 검증 로직을 강화하세요.")
        
        if self.validation_report['issues'].get('inconsistent_pair_flags', 0) > 0:
            recommendations.append("페어 플래그 일관성 검사를 추가하세요.")
        
        # 성능 권장사항
        if self.validation_report['total_records'] > 100000:
            recommendations.append("대용량 데이터를 위한 파티셔닝을 고려하세요.")
        
        if not recommendations:
            recommendations.append("현재 데이터 상태가 양호합니다.")
        
        self.validation_report['recommendations'] = recommendations
    
    def print_summary(self):
        """검증 결과 요약 출력"""
        report = self.validation_report
        
        print("=" * 60)
        print("📊 데이터 품질 검증 결과 요약")
        print("=" * 60)
        print(f"총 레코드: {report['total_records']:,}개")
        print(f"유효 레코드: {report['valid_records']:,}개")
        print(f"품질 점수: {report['quality_score']}점")
        print()
        
        if report['issues']:
            print("⚠️  발견된 문제:")
            for issue, count in report['issues'].items():
                print(f"  - {issue}: {count:,}개")
            print()
        
        if report['corrections']:
            print("🔧 수행된 정리:")
            for correction, count in report['corrections'].items():
                print(f"  - {correction}: {count:,}개")
            print()
        
        if report['table_stats']:
            print("📈 테이블별 통계 (상위 5개):")
            for table in report['table_stats'][:5]:
                print(f"  - {table['table_name']}: {table['record_count']:,}개 레코드, "
                      f"{table['pair_count']:,}개 페어 ({table['pair_rate']:.2f}%)")
            print()
        
        print("💡 권장사항:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
        
        print("=" * 60)

async def main():
    """메인 실행 함수"""
    try:
        # 데이터 검증기 생성
        validator = DataValidator()
        
        # 전체 검증 실행
        report = await validator.run_validation()
        
        # 결과 출력
        validator.print_summary()
        
    except Exception as e:
        logger.error(f"실행 오류: {e}")

if __name__ == "__main__":
    # asyncio로 실행
    asyncio.run(main())