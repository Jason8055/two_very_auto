#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTPS/SSL 인증서 자동 설정 도구
Let's Encrypt 인증서 자동 발급 및 갱신, 자체 서명 인증서 생성
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import socket
import ssl
import requests

# 로컬 모듈
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

class SSLAutoSetup:
    """SSL 인증서 자동 설정"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.absolute()
        self.ssl_dir = self.project_dir / "ssl_certificates"
        self.ssl_dir.mkdir(exist_ok=True)
        
        self.config = self.load_ssl_config()
        
        safe_print("🔐 SSL 자동 설정 도구 초기화")
    
    def load_ssl_config(self) -> Dict[str, Any]:
        """SSL 설정 로드"""
        config_path = self.project_dir / "ssl_config.json"
        
        default_config = {
            "domains": [],
            "email": "",
            "cert_type": "letsencrypt",  # letsencrypt, self_signed
            "auto_renewal": True,
            "renewal_days_before": 30,
            "webroot_path": str(self.project_dir / "webroot"),
            "certificates": {}
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값 병합
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                return config
            except Exception as e:
                safe_print(f"⚠️ SSL 설정 로드 오류: {e}")
        
        # 기본 설정 저장
        self.save_ssl_config(default_config)
        return default_config
    
    def save_ssl_config(self, config: Dict[str, Any]):
        """SSL 설정 저장"""
        config_path = self.project_dir / "ssl_config.json"
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            safe_print(f"❌ SSL 설정 저장 오류: {e}")
    
    def check_domain_availability(self, domain: str) -> bool:
        """도메인 접근 가능성 확인"""
        try:
            socket.gethostbyname(domain)
            return True
        except socket.gaierror:
            return False
    
    def check_port_open(self, domain: str, port: int = 80) -> bool:
        """포트 개방 상태 확인"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((domain, port))
                return result == 0
        except:
            return False
    
    def generate_self_signed_certificate(self, domain: str = "localhost") -> Tuple[bool, str]:
        """자체 서명 인증서 생성"""
        safe_print(f"🔒 자체 서명 인증서 생성 중: {domain}")
        
        try:
            # OpenSSL이 설치되어 있는지 확인
            subprocess.run(['openssl', 'version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return self._generate_python_certificate(domain)
        
        cert_path = self.ssl_dir / f"{domain}.crt"
        key_path = self.ssl_dir / f"{domain}.key"
        
        # OpenSSL 명령어로 인증서 생성
        openssl_cmd = [
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
            '-keyout', str(key_path),
            '-out', str(cert_path),
            '-days', '365',
            '-nodes',
            '-subj', f'/C=KR/ST=Seoul/L=Seoul/O=TwoVeryAuto/OU=IT/CN={domain}'
        ]
        
        try:
            result = subprocess.run(openssl_cmd, capture_output=True, text=True, check=True)
            safe_print(f"✅ 자체 서명 인증서 생성 완료")
            
            # 설정 업데이트
            self.config["certificates"][domain] = {
                "type": "self_signed",
                "cert_path": str(cert_path),
                "key_path": str(key_path),
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=365)).isoformat()
            }
            self.save_ssl_config(self.config)
            
            return True, f"인증서: {cert_path}, 키: {key_path}"
            
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ OpenSSL 인증서 생성 실패: {e}")
            return self._generate_python_certificate(domain)
    
    def _generate_python_certificate(self, domain: str) -> Tuple[bool, str]:
        """Python을 사용한 인증서 생성 (OpenSSL 대안)"""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            
            # 개인키 생성
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # 인증서 정보 설정
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "KR"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Seoul"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Seoul"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Two Very Auto"),
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
            ])
            
            # 인증서 생성
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(domain),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # 파일 저장
            cert_path = self.ssl_dir / f"{domain}.crt"
            key_path = self.ssl_dir / f"{domain}.key"
            
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            safe_print(f"✅ Python으로 자체 서명 인증서 생성 완료")
            
            # 설정 업데이트
            self.config["certificates"][domain] = {
                "type": "self_signed",
                "cert_path": str(cert_path),
                "key_path": str(key_path),
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=365)).isoformat()
            }
            self.save_ssl_config(self.config)
            
            return True, f"인증서: {cert_path}, 키: {key_path}"
            
        except ImportError:
            safe_print("❌ cryptography 라이브러리가 설치되지 않음")
            safe_print("설치 명령: pip install cryptography")
            return False, "cryptography 라이브러리 필요"
        except Exception as e:
            safe_print(f"❌ Python 인증서 생성 실패: {e}")
            return False, str(e)
    
    def setup_letsencrypt(self, domain: str, email: str) -> Tuple[bool, str]:
        """Let's Encrypt 인증서 설정"""
        safe_print(f"🌐 Let's Encrypt 인증서 설정: {domain}")
        
        # 도메인 및 포트 확인
        if not self.check_domain_availability(domain):
            return False, f"도메인 {domain}에 접근할 수 없습니다"
        
        if not self.check_port_open(domain, 80):
            safe_print("⚠️ 포트 80이 열려있지 않아 HTTP 챌린지가 실패할 수 있습니다")
        
        # certbot 설치 확인
        try:
            subprocess.run(['certbot', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False, "certbot이 설치되지 않음. 설치 명령: pip install certbot"
        
        # webroot 디렉토리 생성
        webroot_path = Path(self.config["webroot_path"])
        webroot_path.mkdir(parents=True, exist_ok=True)
        
        # certbot 명령어 실행
        certbot_cmd = [
            'certbot', 'certonly',
            '--webroot',
            '-w', str(webroot_path),
            '-d', domain,
            '--email', email,
            '--agree-tos',
            '--non-interactive'
        ]
        
        try:
            result = subprocess.run(certbot_cmd, capture_output=True, text=True, check=True)
            safe_print("✅ Let's Encrypt 인증서 발급 완료")
            
            # 인증서 경로 (일반적인 Let's Encrypt 경로)
            cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
            key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
            
            # Windows의 경우 다른 경로
            if os.name == 'nt':
                cert_path = f"C:/Certbot/live/{domain}/fullchain.pem"
                key_path = f"C:/Certbot/live/{domain}/privkey.pem"
            
            # 설정 업데이트
            self.config["certificates"][domain] = {
                "type": "letsencrypt",
                "cert_path": cert_path,
                "key_path": key_path,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=90)).isoformat(),
                "email": email
            }
            self.save_ssl_config(self.config)
            
            return True, f"인증서: {cert_path}"
            
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ Let's Encrypt 인증서 발급 실패")
            safe_print(f"오류 출력: {e.stderr}")
            return False, f"certbot 실행 실패: {e.stderr}"
    
    def check_certificate_expiry(self, domain: str) -> Optional[datetime]:
        """인증서 만료일 확인"""
        cert_info = self.config["certificates"].get(domain)
        if not cert_info:
            return None
        
        cert_path = cert_info.get("cert_path")
        if not cert_path or not Path(cert_path).exists():
            return None
        
        try:
            # 인증서 파일에서 만료일 확인
            with open(cert_path, 'rb') as cert_file:
                cert_data = cert_file.read()
                cert = ssl.PEM_cert_to_DER_cert(cert_data.decode())
                cert_ssl = ssl.DER_cert_to_PEM_cert(cert)
                
                # OpenSSL로 만료일 확인
                openssl_cmd = ['openssl', 'x509', '-enddate', '-noout']
                result = subprocess.run(
                    openssl_cmd, 
                    input=cert_ssl, 
                    text=True, 
                    capture_output=True
                )
                
                if result.returncode == 0:
                    # notAfter=Dec 30 23:59:59 2024 GMT 형식 파싱
                    date_str = result.stdout.strip().replace('notAfter=', '')
                    return datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                    
        except Exception as e:
            safe_print(f"❌ 인증서 만료일 확인 오류: {e}")
        
        # 설정 파일의 만료일 사용 (fallback)
        try:
            return datetime.fromisoformat(cert_info["expires_at"])
        except:
            return None
    
    def check_renewal_needed(self) -> List[str]:
        """갱신이 필요한 인증서 목록"""
        renewal_needed = []
        renewal_threshold = datetime.now() + timedelta(days=self.config["renewal_days_before"])
        
        for domain, cert_info in self.config["certificates"].items():
            expiry_date = self.check_certificate_expiry(domain)
            if expiry_date and expiry_date < renewal_threshold:
                renewal_needed.append(domain)
        
        return renewal_needed
    
    def renew_certificate(self, domain: str) -> Tuple[bool, str]:
        """인증서 갱신"""
        cert_info = self.config["certificates"].get(domain)
        if not cert_info:
            return False, f"도메인 {domain} 인증서 정보를 찾을 수 없음"
        
        cert_type = cert_info.get("type", "self_signed")
        
        if cert_type == "letsencrypt":
            return self._renew_letsencrypt(domain)
        elif cert_type == "self_signed":
            return self.generate_self_signed_certificate(domain)
        else:
            return False, f"알 수 없는 인증서 타입: {cert_type}"
    
    def _renew_letsencrypt(self, domain: str) -> Tuple[bool, str]:
        """Let's Encrypt 인증서 갱신"""
        try:
            renewal_cmd = ['certbot', 'renew', '--quiet']
            result = subprocess.run(renewal_cmd, capture_output=True, text=True, check=True)
            
            # 설정에서 만료일 업데이트
            self.config["certificates"][domain]["expires_at"] = (
                datetime.now() + timedelta(days=90)
            ).isoformat()
            self.save_ssl_config(self.config)
            
            safe_print(f"✅ {domain} Let's Encrypt 인증서 갱신 완료")
            return True, "갱신 완료"
            
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ Let's Encrypt 갱신 실패: {e}")
            return False, f"갱신 실패: {e}"
    
    def create_nginx_ssl_config(self, domain: str, port: int = 443) -> str:
        """Nginx SSL 설정 생성"""
        cert_info = self.config["certificates"].get(domain)
        if not cert_info:
            return ""
        
        nginx_config = f"""
# SSL configuration for {domain}
server {{
    listen {port} ssl http2;
    server_name {domain};
    
    ssl_certificate {cert_info['cert_path']};
    ssl_certificate_key {cert_info['key_path']};
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 5m;
    
    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Your application configuration here
    location / {{
        proxy_pass http://127.0.0.1:8000;  # Two Very Auto dashboard
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}

# HTTP to HTTPS redirect
server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}
"""
        
        config_path = self.ssl_dir / f"nginx_{domain}.conf"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(nginx_config)
        
        safe_print(f"📝 Nginx 설정 파일 생성: {config_path}")
        return str(config_path)
    
    def interactive_setup(self):
        """대화형 SSL 설정"""
        safe_print("=== SSL 인증서 자동 설정 ===")
        
        # 인증서 타입 선택
        safe_print("\n인증서 타입을 선택하세요:")
        safe_print("1. 자체 서명 인증서 (개발용)")
        safe_print("2. Let's Encrypt (실제 도메인 필요)")
        
        choice = input("선택 (1-2): ").strip()
        
        if choice == "1":
            domain = input("도메인 또는 호스트명 [localhost]: ").strip() or "localhost"
            success, message = self.generate_self_signed_certificate(domain)
            
            if success:
                safe_print(f"✅ 자체 서명 인증서 생성 완료")
                safe_print(f"📁 {message}")
                
                # Nginx 설정 생성
                if input("Nginx 설정 파일을 생성하시겠습니까? (y/N): ").lower() == 'y':
                    self.create_nginx_ssl_config(domain)
            else:
                safe_print(f"❌ 인증서 생성 실패: {message}")
        
        elif choice == "2":
            domain = input("도메인명: ").strip()
            email = input("이메일 주소: ").strip()
            
            if not domain or not email:
                safe_print("❌ 도메인과 이메일을 모두 입력해야 합니다")
                return
            
            success, message = self.setup_letsencrypt(domain, email)
            
            if success:
                safe_print(f"✅ Let's Encrypt 인증서 발급 완료")
                safe_print(f"📁 {message}")
                
                # 자동 갱신 설정
                self.config["auto_renewal"] = True
                self.config["email"] = email
                if domain not in self.config["domains"]:
                    self.config["domains"].append(domain)
                self.save_ssl_config(self.config)
                
                # Nginx 설정 생성
                if input("Nginx 설정 파일을 생성하시겠습니까? (y/N): ").lower() == 'y':
                    self.create_nginx_ssl_config(domain)
            else:
                safe_print(f"❌ Let's Encrypt 인증서 발급 실패: {message}")
        
        else:
            safe_print("잘못된 선택입니다")
    
    def auto_renewal_check(self):
        """자동 갱신 확인 및 실행"""
        if not self.config.get("auto_renewal", True):
            return
        
        renewal_needed = self.check_renewal_needed()
        
        if renewal_needed:
            safe_print(f"🔄 {len(renewal_needed)}개 인증서 갱신 필요")
            
            for domain in renewal_needed:
                safe_print(f"📝 {domain} 인증서 갱신 중...")
                success, message = self.renew_certificate(domain)
                
                if success:
                    safe_print(f"✅ {domain} 갱신 완료")
                else:
                    safe_print(f"❌ {domain} 갱신 실패: {message}")
        else:
            safe_print("✅ 모든 인증서가 최신 상태입니다")
    
    def get_ssl_status(self) -> Dict[str, Any]:
        """SSL 상태 정보"""
        status = {
            "total_certificates": len(self.config["certificates"]),
            "certificates": [],
            "renewal_needed": self.check_renewal_needed(),
            "auto_renewal": self.config.get("auto_renewal", False)
        }
        
        for domain, cert_info in self.config["certificates"].items():
            expiry_date = self.check_certificate_expiry(domain)
            
            cert_status = {
                "domain": domain,
                "type": cert_info.get("type", "unknown"),
                "created_at": cert_info.get("created_at", ""),
                "expires_at": expiry_date.isoformat() if expiry_date else "unknown",
                "days_until_expiry": (expiry_date - datetime.now()).days if expiry_date else None,
                "cert_path": cert_info.get("cert_path", ""),
                "key_path": cert_info.get("key_path", "")
            }
            
            status["certificates"].append(cert_status)
        
        return status

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SSL 인증서 자동 설정 도구")
    parser.add_argument("--setup", action="store_true", help="대화형 SSL 설정")
    parser.add_argument("--status", action="store_true", help="SSL 상태 확인")
    parser.add_argument("--check-renewal", action="store_true", help="갱신 필요 인증서 확인")
    parser.add_argument("--auto-renew", action="store_true", help="자동 갱신 실행")
    parser.add_argument("--generate-self", metavar="DOMAIN", help="자체 서명 인증서 생성")
    parser.add_argument("--letsencrypt", nargs=2, metavar=("DOMAIN", "EMAIL"), help="Let's Encrypt 인증서 발급")
    parser.add_argument("--nginx-config", metavar="DOMAIN", help="Nginx 설정 파일 생성")
    
    args = parser.parse_args()
    
    ssl_setup = SSLAutoSetup()
    
    if args.setup:
        ssl_setup.interactive_setup()
    elif args.status:
        status = ssl_setup.get_ssl_status()
        safe_print("📊 SSL 인증서 상태:")
        safe_print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.check_renewal:
        renewal_needed = ssl_setup.check_renewal_needed()
        if renewal_needed:
            safe_print(f"🔄 갱신 필요한 인증서: {', '.join(renewal_needed)}")
        else:
            safe_print("✅ 모든 인증서가 최신 상태입니다")
    elif args.auto_renew:
        ssl_setup.auto_renewal_check()
    elif args.generate_self:
        success, message = ssl_setup.generate_self_signed_certificate(args.generate_self)
        if success:
            safe_print(f"✅ 자체 서명 인증서 생성 완료: {message}")
        else:
            safe_print(f"❌ 생성 실패: {message}")
    elif args.letsencrypt:
        domain, email = args.letsencrypt
        success, message = ssl_setup.setup_letsencrypt(domain, email)
        if success:
            safe_print(f"✅ Let's Encrypt 인증서 발급 완료: {message}")
        else:
            safe_print(f"❌ 발급 실패: {message}")
    elif args.nginx_config:
        config_path = ssl_setup.create_nginx_ssl_config(args.nginx_config)
        if config_path:
            safe_print(f"📝 Nginx 설정 생성: {config_path}")
    else:
        safe_print("=== SSL 인증서 자동 설정 도구 ===")
        safe_print("사용법:")
        safe_print("  --setup              : 대화형 설정")
        safe_print("  --status             : 상태 확인")
        safe_print("  --generate-self HOST : 자체 서명 인증서")
        safe_print("  --auto-renew         : 자동 갱신")