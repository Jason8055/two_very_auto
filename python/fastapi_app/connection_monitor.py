#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
연결 안정성 모니터링 스크립트
Connection Stability Monitor
"""

import asyncio
import aiohttp
import time
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionMonitor:
    def __init__(self):
        self.servers = [
            {"name": "Simple Server", "url": "http://127.0.0.1:8005/health"},
            {"name": "Main Server", "url": "http://127.0.0.1:8006/health"},
            {"name": "System Status", "url": "http://127.0.0.1:8006/system-status"}
        ]
        self.stats = {
            "total_checks": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "response_times": [],
            "last_failure": None,
            "uptime_start": datetime.now()
        }
        
    async def check_server(self, session, server):
        """개별 서버 연결 확인"""
        try:
            start_time = time.time()
            
            async with session.get(server["url"], timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status == 200:
                    data = await response.json()
                    
                    self.stats["successful_connections"] += 1
                    self.stats["response_times"].append(response_time)
                    
                    # 최근 100개의 응답 시간만 유지
                    if len(self.stats["response_times"]) > 100:
                        self.stats["response_times"] = self.stats["response_times"][-100:]
                    
                    logger.info(f"✅ {server['name']}: {response.status} ({response_time:.1f}ms)")
                    return True, response_time, data
                else:
                    logger.warning(f"⚠️ {server['name']}: HTTP {response.status}")
                    self.stats["failed_connections"] += 1
                    return False, response_time, None
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ {server['name']}: 연결 타임아웃 (5초)")
            self.stats["failed_connections"] += 1
            self.stats["last_failure"] = datetime.now()
            return False, 5000, None
            
        except Exception as e:
            logger.error(f"❌ {server['name']}: 연결 실패 - {str(e)}")
            self.stats["failed_connections"] += 1
            self.stats["last_failure"] = datetime.now()
            return False, 0, None
    
    async def monitor_connections(self, interval=10, duration=300):
        """연결 모니터링 실행"""
        logger.info(f"🔍 연결 모니터링 시작 - {duration}초 동안 {interval}초 간격으로 확인")
        
        end_time = time.time() + duration
        
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                check_start = datetime.now()
                logger.info(f"\n📊 연결 상태 확인 - {check_start.strftime('%H:%M:%S')}")
                
                # 모든 서버 동시 확인
                tasks = []
                for server in self.servers:
                    task = self.check_server(session, server)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                self.stats["total_checks"] += len(self.servers)
                
                # 결과 분석
                successful = sum(1 for success, _, _ in results if success)
                avg_response_time = sum(rt for _, rt, _ in results if rt > 0) / len(results) if results else 0
                
                # 통계 출력
                success_rate = (self.stats["successful_connections"] / self.stats["total_checks"] * 100) if self.stats["total_checks"] > 0 else 0
                avg_historical = sum(self.stats["response_times"]) / len(self.stats["response_times"]) if self.stats["response_times"] else 0
                
                print(f"""
🔗 연결 상태 요약:
   현재 세션: {successful}/{len(self.servers)} 성공 (평균 {avg_response_time:.1f}ms)
   전체 통계: {self.stats['successful_connections']}/{self.stats['total_checks']} ({success_rate:.1f}% 성공률)
   평균 응답시간: {avg_historical:.1f}ms
   마지막 실패: {self.stats['last_failure'].strftime('%H:%M:%S') if self.stats['last_failure'] else '없음'}
   가동시간: {datetime.now() - self.stats['uptime_start']}
                """)
                
                # 연결 실패가 있으면 경고
                if successful < len(self.servers):
                    logger.warning(f"🚨 {len(self.servers) - successful}개 서버에서 연결 문제 발생!")
                
                # 대기
                await asyncio.sleep(interval)
        
        # 최종 보고서
        self.generate_report()
    
    def generate_report(self):
        """모니터링 보고서 생성"""
        total_time = datetime.now() - self.stats["uptime_start"]
        success_rate = (self.stats["successful_connections"] / self.stats["total_checks"] * 100) if self.stats["total_checks"] > 0 else 0
        avg_response_time = sum(self.stats["response_times"]) / len(self.stats["response_times"]) if self.stats["response_times"] else 0
        
        report = f"""
{'=' * 60}
📊 연결 안정성 모니터링 보고서
{'=' * 60}
모니터링 기간: {total_time}
총 확인 횟수: {self.stats['total_checks']}
성공적인 연결: {self.stats['successful_connections']}
실패한 연결: {self.stats['failed_connections']}
전체 성공률: {success_rate:.2f}%
평균 응답시간: {avg_response_time:.1f}ms
최대 응답시간: {max(self.stats['response_times']) if self.stats['response_times'] else 0:.1f}ms
최소 응답시간: {min(self.stats['response_times']) if self.stats['response_times'] else 0:.1f}ms
마지막 실패: {self.stats['last_failure'].strftime('%Y-%m-%d %H:%M:%S') if self.stats['last_failure'] else '없음'}

🎯 권장 사항:
{'- 연결이 안정적입니다.' if success_rate > 95 else '- 연결 불안정성이 감지되었습니다. 서버 또는 네트워크 확인 필요.'}
{'- 응답 시간이 양호합니다.' if avg_response_time < 100 else '- 응답 시간이 느립니다. 성능 최적화 검토 필요.'}
{'=' * 60}
        """
        
        print(report)
        logger.info("📄 모니터링 보고서 생성 완료")

async def main():
    """메인 모니터링 실행"""
    monitor = ConnectionMonitor()
    
    # 5분 동안 10초 간격으로 모니터링
    await monitor.monitor_connections(interval=10, duration=300)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 모니터링 중단됨")
    except Exception as e:
        print(f"❌ 모니터링 오류: {e}")