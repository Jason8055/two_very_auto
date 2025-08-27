# Security Policy

## Supported Versions

We actively support and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.5.x   | :white_check_mark: |
| 2.4.x   | :white_check_mark: |
| < 2.4   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in Two Very Auto Casino System, please follow these steps:

### 1. DO NOT create a public issue

Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.

### 2. Send a private security report

- **Email**: security@two-very-auto.local (or create a GitHub private vulnerability report)
- **Subject**: [SECURITY] Brief description of the vulnerability
- **Include**:
  - Description of the vulnerability
  - Steps to reproduce the issue
  - Potential impact and attack scenarios
  - Any suggested fixes or mitigations

### 3. Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Progress Updates**: Every week until resolved
- **Resolution**: Target within 90 days (varies by severity)

## Security Best Practices

### For Users
- Always use the latest supported version
- Never expose database credentials or API keys in configuration files
- Use secure WebSocket connections (WSS) in production
- Implement proper network segmentation for packet monitoring
- Regularly update dependencies using Dependabot alerts

### For Contributors
- Follow secure coding practices
- Never commit secrets, API keys, or credentials
- Use environment variables for sensitive configuration
- Run security scans before submitting pull requests
- Review dependencies for known vulnerabilities

## Security Features

- **Authentication**: Multi-factor authentication support
- **Data Encryption**: AES-256 encryption for sensitive data
- **Network Security**: TLS/SSL encryption for all communications
- **Access Control**: Role-based access control (RBAC)
- **Audit Logging**: Comprehensive audit trails for all operations
- **Data Validation**: Input validation and sanitization

## Security Architecture

### Packet Monitoring Security
- Encrypted packet capture and storage
- Secure real-time data transmission via WebSocket
- Access-controlled packet analysis endpoints

### Database Security
- Encrypted database connections
- Regular security backups
- Access logging and monitoring

### API Security
- Rate limiting and throttling
- Request validation and sanitization
- JWT token-based authentication
- CORS policy enforcement

## Compliance

This system is designed with security best practices in mind, but users are responsible for:
- Ensuring compliance with local gaming and data protection laws
- Implementing additional security measures as required
- Regular security assessments and penetration testing

## Contact

For non-security related issues, please use GitHub issues.
For security-related concerns, contact: security@two-very-auto.local