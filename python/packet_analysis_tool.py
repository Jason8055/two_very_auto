#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
패킷 분석 도구
실제 패킷 파일에서 암호화된 카드 데이터를 분석
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from korean_encoding_fix import setup_korean_encoding, safe_print
from encoded_card_decoder import EncodedCardDecoder

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PacketAnalysisTool:
    """패킷 분석 도구"""
    
    def __init__(self, packet_dir: str = "F:\\two very auto 25.08.23\\packet"):
        """
        패킷 분석 도구 초기화
        
        Args:
            packet_dir: 패킷 파일 디렉토리 경로
        """
        self.packet_dir = Path(packet_dir)
        self.decoder = EncodedCardDecoder()
        self.analysis_results = []
        
        logger.info(f"[Packet Analysis] Initialized with directory: {packet_dir}")
    
    def analyze_packet_files(self, max_files: int = 5) -> Dict[str, Any]:
        """
        패킷 파일들을 분석
        
        Args:
            max_files: 분석할 최대 파일 수
            
        Returns:
            분석 결과
        """
        try:
            safe_print(f"📁 패킷 파일 분석 시작: {self.packet_dir}")
            
            # 패킷 파일 찾기
            packet_files = []
            for date_dir in self.packet_dir.iterdir():
                if date_dir.is_dir():
                    for file_path in date_dir.glob("*.txt"):
                        packet_files.append(file_path)
                        if len(packet_files) >= max_files:
                            break
                    if len(packet_files) >= max_files:
                        break
            
            safe_print(f"🔍 발견된 패킷 파일: {len(packet_files)}개")
            
            analysis_summary = {
                'total_files_analyzed': 0,
                'total_encoded_strings': 0,
                'unique_patterns': set(),
                'decoding_attempts': [],
                'pattern_analysis': {},
                'best_candidates': []
            }
            
            # 각 파일 분석
            for file_path in packet_files[:max_files]:
                try:
                    file_result = self.analyze_single_file(file_path)
                    if file_result:
                        analysis_summary['total_files_analyzed'] += 1
                        analysis_summary['total_encoded_strings'] += len(file_result.get('encoded_samples', []))
                        
                        # 패턴 수집
                        for sample in file_result.get('encoded_samples', []):
                            if 'encoded_history' in sample:
                                analysis_summary['unique_patterns'].add(sample['encoded_history'][:20])
                        
                        # 최고 후보 추가
                        if file_result.get('best_decoding_candidate'):
                            analysis_summary['best_candidates'].append({
                                'file': str(file_path),
                                'candidate': file_result['best_decoding_candidate']
                            })
                
                except Exception as e:
                    safe_print(f"❌ 파일 분석 실패 {file_path}: {e}")
                    continue
            
            # 패턴 분석 수행
            analysis_summary['pattern_analysis'] = self._analyze_collected_patterns(
                analysis_summary['unique_patterns']
            )
            
            # set을 list로 변환 (JSON 직렬화 위해)
            analysis_summary['unique_patterns'] = list(analysis_summary['unique_patterns'])
            
            return analysis_summary
            
        except Exception as e:
            logger.error(f"패킷 파일 분석 실패: {e}")
            return {'error': str(e)}
    
    def analyze_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """단일 패킷 파일 분석"""
        try:
            safe_print(f"📄 파일 분석 중: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # JSON 패킷들 추출
            json_packets = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('{"id":') and 'baccarat.encodedShoeState' in line:
                    try:
                        packet_data = json.loads(line)
                        json_packets.append(packet_data)
                    except json.JSONDecodeError:
                        continue
            
            if not json_packets:
                return None
            
            safe_print(f"  📊 JSON 패킷 발견: {len(json_packets)}개")
            
            # 인코딩된 히스토리 샘플 수집
            encoded_samples = []
            
            for packet in json_packets[:10]:  # 최대 10개만 분석
                args = packet.get('args', {})
                encoded_history = args.get('history', '')
                history_v2 = args.get('history_v2', [])
                
                if encoded_history and history_v2:
                    # 디코딩 분석 수행
                    decode_result = self.decoder.analyze_with_context(encoded_history, history_v2)
                    
                    encoded_samples.append({
                        'encoded_history': encoded_history,
                        'history_v2_count': len(history_v2),
                        'decode_result': decode_result,
                        'timestamp': packet.get('time', 0)
                    })
            
            # 최고 디코딩 후보 선택
            best_candidate = self._select_best_candidate(encoded_samples)
            
            return {
                'file_path': str(file_path),
                'total_packets': len(json_packets),
                'encoded_samples': encoded_samples,
                'best_decoding_candidate': best_candidate
            }
            
        except Exception as e:
            logger.error(f"단일 파일 분석 실패 {file_path}: {e}")
            return None
    
    def _select_best_candidate(self, encoded_samples: List[Dict]) -> Optional[Dict[str, Any]]:
        """최고 디코딩 후보 선택"""
        try:
            best_candidate = None
            best_score = 0
            
            for sample in encoded_samples:
                decode_result = sample.get('decode_result', {})
                
                # 점수 계산
                score = 0
                
                # 디코딩 시도 성공 수
                attempts = decode_result.get('decode_result', {}).get('decoded_attempts', [])
                score += len(attempts) * 10
                
                # 권장사항 수 (좋은 신호)
                recommendations = decode_result.get('recommendations', [])
                score += len(recommendations) * 5
                
                # 패턴 매칭 품질
                context_analysis = decode_result.get('context_analysis', {})
                pattern_matching = context_analysis.get('pattern_matching', [])
                
                for pattern in pattern_matching:
                    correlation = pattern.get('possible_correlation', {})
                    if correlation.get('direct_player') or correlation.get('direct_banker'):
                        score += 20
                    if correlation.get('offset_correlations'):
                        score += len(correlation['offset_correlations']) * 5
                
                # 최고 점수 업데이트
                if score > best_score:
                    best_score = score
                    best_candidate = {
                        'sample': sample,
                        'score': score,
                        'reasons': self._get_selection_reasons(decode_result)
                    }
            
            return best_candidate
            
        except Exception as e:
            logger.error(f"최고 후보 선택 실패: {e}")
            return None
    
    def _get_selection_reasons(self, decode_result: Dict) -> List[str]:
        """선택 이유 생성"""
        reasons = []
        
        try:
            # 디코딩 시도 결과
            attempts = decode_result.get('decode_result', {}).get('decoded_attempts', [])
            if attempts:
                reasons.append(f"{len(attempts)}개의 디코딩 방법이 성공")
            
            # 상관관계 발견
            context_analysis = decode_result.get('context_analysis', {})
            pattern_matching = context_analysis.get('pattern_matching', [])
            
            correlations_found = 0
            for pattern in pattern_matching:
                correlation = pattern.get('possible_correlation', {})
                if correlation.get('direct_player') or correlation.get('direct_banker'):
                    correlations_found += 1
            
            if correlations_found > 0:
                reasons.append(f"{correlations_found}개의 직접적 상관관계 발견")
            
            # 권장사항
            recommendations = decode_result.get('recommendations', [])
            if recommendations:
                reasons.extend(recommendations[:2])  # 상위 2개만
            
            return reasons
            
        except Exception as e:
            return [f"분석 중 오류: {e}"]
    
    def _analyze_collected_patterns(self, unique_patterns: set) -> Dict[str, Any]:
        """수집된 패턴들 분석"""
        try:
            pattern_analysis = {
                'total_unique_patterns': len(unique_patterns),
                'common_characters': {},
                'common_prefixes': [],
                'common_suffixes': [],
                'length_distribution': {},
                'character_frequency': {}
            }
            
            patterns_list = list(unique_patterns)
            
            if not patterns_list:
                return pattern_analysis
            
            # 문자 빈도 분석
            all_chars = ''.join(patterns_list)
            for char in set(all_chars):
                pattern_analysis['character_frequency'][char] = all_chars.count(char)
            
            # 길이 분포
            for pattern in patterns_list:
                length = len(pattern)
                pattern_analysis['length_distribution'][length] = \
                    pattern_analysis['length_distribution'].get(length, 0) + 1
            
            # 공통 접두사/접미사 찾기
            if len(patterns_list) > 1:
                # 공통 접두사
                for length in range(1, min(10, min(len(p) for p in patterns_list))):
                    prefixes = set(p[:length] for p in patterns_list)
                    if len(prefixes) < len(patterns_list) // 2:  # 절반 이상이 공통
                        pattern_analysis['common_prefixes'].extend(list(prefixes))
                
                # 공통 접미사
                for length in range(1, min(10, min(len(p) for p in patterns_list))):
                    suffixes = set(p[-length:] for p in patterns_list)
                    if len(suffixes) < len(patterns_list) // 2:
                        pattern_analysis['common_suffixes'].extend(list(suffixes))
            
            return pattern_analysis
            
        except Exception as e:
            logger.error(f"패턴 분석 실패: {e}")
            return {'error': str(e)}
    
    def generate_decoding_report(self, analysis_results: Dict[str, Any]) -> str:
        """디코딩 분석 보고서 생성"""
        try:
            report_lines = [
                "🔍 바카라 패킷 암호화 카드 디코딩 분석 보고서",
                "=" * 60,
                "",
                f"📊 분석 개요:",
                f"  - 분석된 파일 수: {analysis_results.get('total_files_analyzed', 0)}개",
                f"  - 발견된 인코딩 문자열: {analysis_results.get('total_encoded_strings', 0)}개",
                f"  - 고유 패턴 수: {len(analysis_results.get('unique_patterns', []))}개",
                "",
                "🎯 주요 발견사항:",
            ]
            
            # 최고 후보들 분석
            best_candidates = analysis_results.get('best_candidates', [])
            if best_candidates:
                report_lines.extend([
                    f"  - {len(best_candidates)}개의 유력한 디코딩 후보 발견",
                    ""
                ])
                
                for i, candidate in enumerate(best_candidates[:3], 1):
                    sample = candidate.get('candidate', {}).get('sample', {})
                    score = candidate.get('candidate', {}).get('score', 0)
                    reasons = candidate.get('candidate', {}).get('reasons', [])
                    
                    report_lines.extend([
                        f"📋 후보 #{i} (점수: {score}):",
                        f"  - 파일: {Path(candidate.get('file', '')).name}",
                        f"  - 인코딩 길이: {len(sample.get('encoded_history', ''))}",
                        f"  - 게임 수: {sample.get('history_v2_count', 0)}",
                        f"  - 선택 이유: {', '.join(reasons[:2])}",
                        ""
                    ])
            
            # 패턴 분석 결과
            pattern_analysis = analysis_results.get('pattern_analysis', {})
            if pattern_analysis:
                report_lines.extend([
                    "🔍 패턴 분석:",
                    f"  - 총 고유 패턴: {pattern_analysis.get('total_unique_patterns', 0)}개",
                    f"  - 길이 분포: {pattern_analysis.get('length_distribution', {})}",
                    ""
                ])
                
                # 가장 빈번한 문자들
                char_freq = pattern_analysis.get('character_frequency', {})
                if char_freq:
                    top_chars = sorted(char_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                    report_lines.extend([
                        "📈 빈도 높은 문자들:",
                        f"  {', '.join(f'{char}({count})' for char, count in top_chars)}",
                        ""
                    ])
            
            # 권장사항
            report_lines.extend([
                "💡 권장 사항:",
                "  1. 최고 점수 후보의 디코딩 방법을 우선 적용",
                "  2. 직접적 상관관계가 발견된 패턴을 중심으로 분석",
                "  3. Evolution Gaming의 표준 인코딩 방식 조사",
                "  4. 더 많은 샘플로 패턴 검증",
                "",
                "🔧 다음 단계:",
                "  - 발견된 패턴을 packet_decoder.py에 통합",
                "  - 실시간 디코딩 시스템에 적용",
                "  - 정확도 검증 및 개선"
            ])
            
            return '\n'.join(report_lines)
            
        except Exception as e:
            return f"보고서 생성 실패: {e}"


def main():
    """메인 실행 함수"""
    safe_print("🚀 패킷 분석 도구 실행")
    
    try:
        # 분석 도구 생성
        analyzer = PacketAnalysisTool()
        
        # 패킷 파일들 분석
        safe_print("📁 패킷 파일 분석 중...")
        analysis_results = analyzer.analyze_packet_files(max_files=3)
        
        # 보고서 생성
        report = analyzer.generate_decoding_report(analysis_results)
        safe_print("\n" + report)
        
        # 보고서 파일로 저장
        report_path = Path("packet_decoding_analysis_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        safe_print(f"\n📄 보고서 저장: {report_path}")
        
        return analysis_results
        
    except Exception as e:
        safe_print(f"❌ 분석 실패: {e}")
        return None


if __name__ == '__main__':
    main()