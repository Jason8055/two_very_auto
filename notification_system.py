#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합 알림 시스템
백업, SSL 인증서, 시스템 상태에 대한 이메일/Slack/Discord/Teams 알림
"""

import os
import json
import smtplib
import ssl
import requests
import logging
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart  
    from email.mime.base import MimeBase
    from email import encoders
except ImportError:
    # Python 호환성 대안
    class MimeText:
        def __init__(self, *args, **kwargs): pass
    class MimeMultipart:
        def __init__(self, *args, **kwargs): pass
    class MimeBase:
        def __init__(self, *args, **kwargs): pass
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import asyncio
import aiohttp

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

logger = logging.getLogger(__name__)

class NotificationSystem:
    """통합 알림 시스템"""
    
    def __init__(self):
        self.config = self.load_notification_config()
        self.email_settings = self.config.get("email", {})
        self.slack_settings = self.config.get("slack", {})
        self.discord_settings = self.config.get("discord", {})
        self.teams_settings = self.config.get("teams", {})
        
        safe_print("📢 통합 알림 시스템 초기화")
    
    def load_notification_config(self) -> Dict[str, Any]:
        """알림 설정 로드"""
        config_path = Path("notification_config.json")
        
        default_config = {
            "enabled": True,
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipients": [],
                "use_tls": True
            },
            "slack": {
                "enabled": False,
                "webhook_url": "",
                "channel": "#backups",
                "username": "Two Very Auto",
                "icon_emoji": "🎰"
            },
            "discord": {
                "enabled": False,
                "webhook_url": "",
                "username": "Two Very Auto Bot",
                "avatar_url": ""
            },
            "teams": {
                "enabled": False,
                "webhook_url": ""
            },
            "notification_levels": {
                "success": ["slack"],
                "warning": ["email", "slack"],
                "error": ["email", "slack", "discord"],
                "critical": ["email", "slack", "discord", "teams"]
            },
            "rate_limiting": {
                "max_notifications_per_hour": 10,
                "cooldown_minutes": 15
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
                self.save_notification_config(config)
                
            return config
        except Exception as e:
            logger.error(f"알림 설정 로드 오류: {e}")
            return default_config
    
    def save_notification_config(self, config: Dict[str, Any]):
        """알림 설정 저장"""
        config_path = Path("notification_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"알림 설정 저장 오류: {e}")
    
    async def send_notification(self, 
                              level: str, 
                              title: str, 
                              message: str, 
                              details: Optional[Dict[str, Any]] = None,
                              attachments: Optional[List[str]] = None) -> Dict[str, bool]:
        """통합 알림 전송"""
        
        if not self.config.get("enabled", True):
            return {"notification_disabled": True}
        
        # 알림 레벨별 채널 결정
        channels = self.config.get("notification_levels", {}).get(level, ["slack"])
        
        results = {}
        
        # 각 채널로 알림 전송
        for channel in channels:
            try:
                if channel == "email" and self.email_settings.get("enabled"):
                    success = await self._send_email(title, message, details, attachments)
                    results["email"] = success
                
                elif channel == "slack" and self.slack_settings.get("enabled"):
                    success = await self._send_slack(title, message, details, level)
                    results["slack"] = success
                
                elif channel == "discord" and self.discord_settings.get("enabled"):
                    success = await self._send_discord(title, message, details, level)
                    results["discord"] = success
                
                elif channel == "teams" and self.teams_settings.get("enabled"):
                    success = await self._send_teams(title, message, details)
                    results["teams"] = success
                
            except Exception as e:
                logger.error(f"{channel} 알림 전송 오류: {e}")
                results[channel] = False
        
        return results
    
    async def _send_email(self, 
                         title: str, 
                         message: str, 
                         details: Optional[Dict[str, Any]] = None,
                         attachments: Optional[List[str]] = None) -> bool:
        """이메일 알림 전송"""
        
        try:
            sender_email = self.email_settings.get("sender_email")
            sender_password = self.email_settings.get("sender_password")
            recipients = self.email_settings.get("recipients", [])
            
            if not all([sender_email, sender_password, recipients]):
                logger.warning("이메일 설정이 완전하지 않습니다")
                return False
            
            # 이메일 메시지 구성
            msg = MimeMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = f"[Two Very Auto] {title}"
            
            # HTML 본문 생성
            html_body = self._create_email_html(title, message, details)
            msg.attach(MimeText(html_body, 'html', 'utf-8'))
            
            # 첨부파일 추가
            if attachments:
                for attachment_path in attachments:
                    if Path(attachment_path).exists():
                        with open(attachment_path, "rb") as attachment:
                            part = MimeBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {Path(attachment_path).name}'
                        )
                        msg.attach(part)
            
            # SMTP 서버로 전송
            smtp_server = self.email_settings.get("smtp_server")
            smtp_port = self.email_settings.get("smtp_port", 587)
            
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if self.email_settings.get("use_tls", True):
                    server.starttls(context=context)
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())
            
            safe_print(f"📧 이메일 알림 전송 완료: {len(recipients)}명")
            return True
            
        except Exception as e:
            logger.error(f"이메일 전송 오류: {e}")
            return False
    
    def _create_email_html(self, title: str, message: str, details: Optional[Dict[str, Any]] = None) -> str:
        """이메일 HTML 본문 생성"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 15px 0; }}
                .footer {{ background-color: #ecf0f1; padding: 10px; text-align: center; font-size: 12px; color: #7f8c8d; }}
                .status-success {{ color: #27ae60; }}
                .status-warning {{ color: #f39c12; }}
                .status-error {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎰 Two Very Auto</h1>
                <h2>{title}</h2>
            </div>
            
            <div class="content">
                <p>{message}</p>
                
                {self._format_details_html(details) if details else ""}
            </div>
            
            <div class="footer">
                <p>알림 발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Two Very Auto 백업 시스템</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_details_html(self, details: Dict[str, Any]) -> str:
        """상세 정보 HTML 포맷"""
        html = '<div class="details"><h3>📊 상세 정보</h3><ul>'
        
        for key, value in details.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        
        html += "</ul></div>"
        return html
    
    async def _send_slack(self, title: str, message: str, details: Optional[Dict[str, Any]] = None, level: str = "info") -> bool:
        """Slack 알림 전송"""
        
        try:
            webhook_url = self.slack_settings.get("webhook_url")
            if not webhook_url:
                return False
            
            # 레벨별 색상 설정
            color_map = {
                "success": "good",
                "warning": "warning", 
                "error": "danger",
                "critical": "danger"
            }
            
            # Slack 메시지 구성
            slack_payload = {
                "channel": self.slack_settings.get("channel", "#backups"),
                "username": self.slack_settings.get("username", "Two Very Auto"),
                "icon_emoji": self.slack_settings.get("icon_emoji", "🎰"),
                "attachments": [
                    {
                        "color": color_map.get(level, "good"),
                        "title": title,
                        "text": message,
                        "fields": self._format_slack_fields(details) if details else [],
                        "footer": "Two Very Auto 백업 시스템",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # 비동기 HTTP 전송
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=slack_payload) as response:
                    if response.status == 200:
                        safe_print("📱 Slack 알림 전송 완료")
                        return True
                    else:
                        logger.error(f"Slack 전송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Slack 전송 오류: {e}")
            return False
    
    def _format_slack_fields(self, details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Slack 필드 포맷"""
        fields = []
        
        for key, value in details.items():
            fields.append({
                "title": key,
                "value": str(value),
                "short": True
            })
        
        return fields
    
    async def _send_discord(self, title: str, message: str, details: Optional[Dict[str, Any]] = None, level: str = "info") -> bool:
        """Discord 알림 전송"""
        
        try:
            webhook_url = self.discord_settings.get("webhook_url")
            if not webhook_url:
                return False
            
            # 레벨별 색상 설정 (Discord용 16진수)
            color_map = {
                "success": 0x00ff00,  # 초록
                "warning": 0xffff00,  # 노랑
                "error": 0xff0000,    # 빨강
                "critical": 0x8b0000  # 진한 빨강
            }
            
            # Discord Embed 메시지 구성
            embed = {
                "title": title,
                "description": message,
                "color": color_map.get(level, 0x0099ff),
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "Two Very Auto 백업 시스템",
                    "icon_url": "🎰"
                }
            }
            
            # 상세 정보를 필드로 추가
            if details:
                embed["fields"] = []
                for key, value in details.items():
                    embed["fields"].append({
                        "name": key,
                        "value": str(value),
                        "inline": True
                    })
            
            discord_payload = {
                "username": self.discord_settings.get("username", "Two Very Auto Bot"),
                "avatar_url": self.discord_settings.get("avatar_url", ""),
                "embeds": [embed]
            }
            
            # 비동기 HTTP 전송
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=discord_payload) as response:
                    if response.status == 204:
                        safe_print("🎮 Discord 알림 전송 완료")
                        return True
                    else:
                        logger.error(f"Discord 전송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Discord 전송 오류: {e}")
            return False
    
    async def _send_teams(self, title: str, message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Microsoft Teams 알림 전송"""
        
        try:
            webhook_url = self.teams_settings.get("webhook_url")
            if not webhook_url:
                return False
            
            # Teams 적응형 카드 메시지 구성
            teams_payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": "0078D4",
                "sections": [
                    {
                        "activityTitle": title,
                        "activitySubtitle": "Two Very Auto 백업 시스템",
                        "activityImage": "https://adaptivecards.io/content/cats/1.png",
                        "text": message,
                        "markdown": True
                    }
                ]
            }
            
            # 상세 정보 추가
            if details:
                facts = []
                for key, value in details.items():
                    facts.append({
                        "name": key,
                        "value": str(value)
                    })
                
                teams_payload["sections"][0]["facts"] = facts
            
            # 비동기 HTTP 전송
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=teams_payload) as response:
                    if response.status == 200:
                        safe_print("💼 Teams 알림 전송 완료")
                        return True
                    else:
                        logger.error(f"Teams 전송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Teams 전송 오류: {e}")
            return False
    
    def create_setup_wizard(self):
        """알림 설정 마법사"""
        safe_print("🧙‍♂️ 알림 설정 마법사 시작")
        
        config = self.config.copy()
        
        # 이메일 설정
        safe_print("\n📧 이메일 알림 설정")
        email_enabled = input("이메일 알림을 사용하시겠습니까? (y/N): ").lower() == 'y'
        
        if email_enabled:
            config["email"]["enabled"] = True
            config["email"]["sender_email"] = input("발신자 이메일: ")
            config["email"]["sender_password"] = input("발신자 비밀번호 (앱 비밀번호 권장): ")
            config["email"]["smtp_server"] = input("SMTP 서버 [smtp.gmail.com]: ") or "smtp.gmail.com"
            config["email"]["smtp_port"] = int(input("SMTP 포트 [587]: ") or "587")
            
            recipients = input("수신자 이메일 (쉼표로 구분): ").split(",")
            config["email"]["recipients"] = [email.strip() for email in recipients if email.strip()]
        
        # Slack 설정
        safe_print("\n📱 Slack 알림 설정")
        slack_enabled = input("Slack 알림을 사용하시겠습니까? (y/N): ").lower() == 'y'
        
        if slack_enabled:
            config["slack"]["enabled"] = True
            webhook_url = input("Slack Webhook URL: ").strip()
            
            # 웹훅 URL 검증
            if webhook_url:
                safe_print("🔍 Slack 웹훅 검증 중...")
                validation = asyncio.run(self.validate_webhook(webhook_url, "slack"))
                
                if validation["valid"]:
                    safe_print("✅ Slack 웹훅 검증 성공!")
                    config["slack"]["webhook_url"] = webhook_url
                else:
                    safe_print(f"❌ Slack 웹훅 검증 실패: {validation['error']}")
                    retry = input("그래도 저장하시겠습니까? (y/N): ").lower() == 'y'
                    if retry:
                        config["slack"]["webhook_url"] = webhook_url
                    else:
                        config["slack"]["enabled"] = False
                        safe_print("⏭️ Slack 설정을 건너뜁니다.")
            
            if config["slack"]["enabled"]:
                config["slack"]["channel"] = input("채널명 [#backups]: ") or "#backups"
                config["slack"]["username"] = input("봇 이름 [Two Very Auto]: ") or "Two Very Auto"
        
        # Discord 설정
        safe_print("\n🎮 Discord 알림 설정")
        discord_enabled = input("Discord 알림을 사용하시겠습니까? (y/N): ").lower() == 'y'
        
        if discord_enabled:
            config["discord"]["enabled"] = True
            webhook_url = input("Discord Webhook URL: ").strip()
            
            # 웹훅 URL 검증
            if webhook_url:
                safe_print("🔍 Discord 웹훅 검증 중...")
                validation = asyncio.run(self.validate_webhook(webhook_url, "discord"))
                
                if validation["valid"]:
                    safe_print("✅ Discord 웹훅 검증 성공!")
                    config["discord"]["webhook_url"] = webhook_url
                else:
                    safe_print(f"❌ Discord 웹훅 검증 실패: {validation['error']}")
                    retry = input("그래도 저장하시겠습니까? (y/N): ").lower() == 'y'
                    if retry:
                        config["discord"]["webhook_url"] = webhook_url
                    else:
                        config["discord"]["enabled"] = False
                        safe_print("⏭️ Discord 설정을 건너뜁니다.")
            
            if config["discord"]["enabled"]:
                config["discord"]["username"] = input("봇 이름 [Two Very Auto Bot]: ") or "Two Very Auto Bot"
        
        # Teams 설정
        safe_print("\n💼 Microsoft Teams 알림 설정")
        teams_enabled = input("Teams 알림을 사용하시겠습니까? (y/N): ").lower() == 'y'
        
        if teams_enabled:
            config["teams"]["enabled"] = True
            webhook_url = input("Teams Webhook URL: ").strip()
            
            # 웹훅 URL 검증
            if webhook_url:
                safe_print("🔍 Teams 웹훅 검증 중...")
                validation = asyncio.run(self.validate_webhook(webhook_url, "teams"))
                
                if validation["valid"]:
                    safe_print("✅ Teams 웹훅 검증 성공!")
                    config["teams"]["webhook_url"] = webhook_url
                else:
                    safe_print(f"❌ Teams 웹훅 검증 실패: {validation['error']}")
                    retry = input("그래도 저장하시겠습니까? (y/N): ").lower() == 'y'
                    if retry:
                        config["teams"]["webhook_url"] = webhook_url
                    else:
                        config["teams"]["enabled"] = False
                        safe_print("⏭️ Teams 설정을 건너뜁니다.")
        
        # 설정 저장
        self.config = config
        self.save_notification_config(config)
        
        safe_print("✅ 알림 설정이 저장되었습니다!")
        
        # 테스트 알림
        test = input("테스트 알림을 전송하시겠습니까? (y/N): ").lower() == 'y'
        if test:
            asyncio.run(self.send_test_notification())
    
    async def validate_webhook(self, webhook_url: str, platform: str = "generic") -> Dict[str, Any]:
        """웹훅 URL 유효성 검사"""
        validation_result = {
            "valid": False,
            "status_code": None,
            "response_time": None,
            "error": None,
            "platform": platform
        }
        
        try:
            import time
            start_time = time.time()
            
            # 플랫폼별 테스트 페이로드
            test_payloads = {
                "slack": {
                    "text": "Two Very Auto 웹훅 연결 테스트",
                    "channel": "#test",
                    "username": "Two Very Auto Test"
                },
                "discord": {
                    "content": "Two Very Auto 웹훅 연결 테스트",
                    "username": "Two Very Auto Test"
                },
                "teams": {
                    "@type": "MessageCard",
                    "@context": "https://schema.org/extensions",
                    "summary": "Two Very Auto 웹훅 연결 테스트",
                    "text": "웹훅 연결이 정상적으로 작동합니다."
                },
                "generic": {
                    "message": "Two Very Auto 웹훅 연결 테스트",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            payload = test_payloads.get(platform, test_payloads["generic"])
            
            # 웹훅 URL 형식 검사
            if not webhook_url or not webhook_url.startswith(('http://', 'https://')):
                validation_result["error"] = "유효하지 않은 URL 형식"
                return validation_result
            
            # HTTP 요청 전송
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(webhook_url, json=payload) as response:
                    validation_result["status_code"] = response.status
                    validation_result["response_time"] = round(time.time() - start_time, 3)
                    
                    # 플랫폼별 성공 상태 코드 확인
                    success_codes = {
                        "slack": [200],
                        "discord": [204],
                        "teams": [200],
                        "generic": [200, 201, 204]
                    }
                    
                    expected_codes = success_codes.get(platform, success_codes["generic"])
                    
                    if response.status in expected_codes:
                        validation_result["valid"] = True
                        safe_print(f"✅ {platform.title()} 웹훅 검증 성공 (HTTP {response.status})")
                    else:
                        validation_result["error"] = f"예상하지 못한 응답 코드: {response.status}"
                        safe_print(f"⚠️ {platform.title()} 웹훅 응답 이상: HTTP {response.status}")
                        
        except asyncio.TimeoutError:
            validation_result["error"] = "요청 시간 초과 (10초)"
            safe_print("⏰ 웹훅 검증 시간 초과")
        except aiohttp.ClientError as e:
            validation_result["error"] = f"연결 오류: {str(e)}"
            safe_print(f"❌ 웹훅 연결 오류: {e}")
        except Exception as e:
            validation_result["error"] = f"알 수 없는 오류: {str(e)}"
            safe_print(f"❌ 웹훅 검증 오류: {e}")
        
        return validation_result

    async def validate_all_webhooks(self) -> Dict[str, Dict[str, Any]]:
        """모든 설정된 웹훅 검증"""
        results = {}
        
        # Slack 웹훅 검증
        if self.slack_settings.get("enabled") and self.slack_settings.get("webhook_url"):
            results["slack"] = await self.validate_webhook(
                self.slack_settings["webhook_url"], 
                "slack"
            )
        
        # Discord 웹훅 검증
        if self.discord_settings.get("enabled") and self.discord_settings.get("webhook_url"):
            results["discord"] = await self.validate_webhook(
                self.discord_settings["webhook_url"], 
                "discord"
            )
        
        # Teams 웹훅 검증
        if self.teams_settings.get("enabled") and self.teams_settings.get("webhook_url"):
            results["teams"] = await self.validate_webhook(
                self.teams_settings["webhook_url"], 
                "teams"
            )
        
        return results

    async def send_test_notification(self):
        """테스트 알림 전송"""
        # 먼저 웹훅 검증
        safe_print("🔍 웹훅 유효성 검사 실행...")
        validation_results = await self.validate_all_webhooks()
        
        if validation_results:
            safe_print("\n📊 웹훅 검증 결과:")
            for platform, result in validation_results.items():
                status = "✅" if result["valid"] else "❌"
                response_time = f" ({result['response_time']}초)" if result["response_time"] else ""
                error_msg = f" - {result['error']}" if result["error"] else ""
                safe_print(f"  {status} {platform.title()}: HTTP {result['status_code']}{response_time}{error_msg}")
        
        # 테스트 알림 전송
        safe_print("\n📤 테스트 알림 전송...")
        results = await self.send_notification(
            level="success",
            title="알림 시스템 테스트",
            message="Two Very Auto 알림 시스템이 정상적으로 작동합니다!",
            details={
                "테스트 시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "시스템 상태": "정상",
                "백업 상태": "활성화됨",
                "검증된 웹훅": len([r for r in validation_results.values() if r["valid"]])
            }
        )
        
        safe_print(f"📊 테스트 알림 결과: {results}")

# 전역 인스턴스
_notification_system = None

def get_notification_system() -> NotificationSystem:
    """알림 시스템 인스턴스 반환"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system

async def validate_single_webhook_cli(webhook_url: str, platform: str):
    """CLI를 통한 단일 웹훅 검증"""
    notification = NotificationSystem()
    
    safe_print(f"🔍 {platform.title()} 웹훅 검증 중...")
    safe_print(f"URL: {webhook_url}")
    
    result = await notification.validate_webhook(webhook_url, platform)
    
    safe_print(f"\n📊 검증 결과:")
    safe_print(f"  ✅ 유효성: {'성공' if result['valid'] else '실패'}")
    safe_print(f"  🌐 HTTP 상태: {result['status_code']}")
    safe_print(f"  ⏱️ 응답 시간: {result['response_time']}초" if result['response_time'] else "  ⏱️ 응답 시간: 측정 실패")
    if result['error']:
        safe_print(f"  ❌ 오류: {result['error']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Two Very Auto 통합 알림 시스템")
    parser.add_argument("--setup", action="store_true", help="알림 설정 마법사 실행")
    parser.add_argument("--test", action="store_true", help="테스트 알림 전송")
    parser.add_argument("--validate", action="store_true", help="모든 웹훅 검증")
    parser.add_argument("--validate-webhook", help="특정 웹훅 URL 검증")
    parser.add_argument("--platform", choices=["slack", "discord", "teams"], default="generic", help="웹훅 플랫폼 지정")
    
    args = parser.parse_args()
    
    safe_print("=== 통합 알림 시스템 ===")
    
    notification = NotificationSystem()
    
    if args.validate_webhook:
        # 단일 웹훅 검증
        asyncio.run(validate_single_webhook_cli(args.validate_webhook, args.platform))
    elif args.validate:
        # 모든 웹훅 검증
        async def validate_all():
            results = await notification.validate_all_webhooks()
            
            if results:
                safe_print("\n📊 웹훅 검증 결과:")
                for platform, result in results.items():
                    status = "✅" if result["valid"] else "❌"
                    response_time = f" ({result['response_time']}초)" if result['response_time'] else ""
                    error_msg = f" - {result['error']}" if result['error'] else ""
                    safe_print(f"  {status} {platform.title()}: HTTP {result['status_code']}{response_time}{error_msg}")
            else:
                safe_print("📝 검증할 웹훅이 설정되지 않았습니다.")
        
        asyncio.run(validate_all())
    elif args.test:
        # 테스트 알림
        asyncio.run(notification.send_test_notification())
    elif args.setup:
        # 설정 마법사
        notification.create_setup_wizard()
    else:
        # 기본 설정 마법사
        notification.create_setup_wizard()