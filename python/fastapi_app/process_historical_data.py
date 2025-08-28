#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
과거 패킷 데이터 처리 스크립트
독립적으로 실행하여 패킷 폴더의 모든 과거 데이터를 데이터베이스에 저장
"""

import asyncio
import logging
import sys
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.append(str(Path(__file__).parent))

from services.historical_data_processor import HistoricalDataProcessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('historical_data_processing.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 과거 패킷 데이터 처리 시작")
        
        # 처리기 생성
        processor = HistoricalDataProcessor()
        
        # 초기화
        await processor.initialize()
        
        # 모든 과거 데이터 처리
        await processor.process_all_historical_data()
        
        logger.info("✅ 과거 패킷 데이터 처리 완료")
        
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자가 처리를 중단했습니다")
    except Exception as e:
        logger.error(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        try:
            await processor.close()
        except:
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Two Very Auto - 과거 데이터 처리")
    print("=" * 60)
    print("패킷 폴더의 모든 과거 파일을 분석하여 데이터베이스에 저장합니다.")
    print("처리 시간은 데이터 양에 따라 몇 분에서 몇 시간이 걸릴 수 있습니다.")
    print("Ctrl+C로 언제든 중단할 수 있습니다.")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        sys.exit(1)