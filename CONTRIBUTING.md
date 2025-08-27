# Contributing to Two Very Auto Casino System

Thank you for your interest in contributing to Two Very Auto! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct:
- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Docker (for containerized development)
- Node.js 18+ (for frontend development)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Jason8055/two_very_auto.git
   cd two_very_auto
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev,test]"
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   pre-commit install --hook-type commit-msg
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

5. **Run tests**
   ```bash
   pytest
   ```

## Development Workflow

### Branch Naming Convention
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Message Format
We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semi colons, etc)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add user authentication endpoint
fix(monitoring): resolve WebSocket connection timeout
docs: update installation instructions
```

### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards below
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks**
   ```bash
   # Run all pre-commit hooks
   pre-commit run --all-files
   
   # Run tests
   pytest
   
   # Run type checking
   mypy python/
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request through GitHub.

## Coding Standards

### Python Code Style
- Follow PEP 8 with line length of 88 characters
- Use Black for code formatting
- Use Ruff for linting
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes

**Example:**
```python
from typing import Optional
import asyncio

async def process_packet_data(
    packet_data: bytes, 
    table_id: Optional[str] = None
) -> dict[str, any]:
    """
    Process raw packet data and extract game information.
    
    Args:
        packet_data: Raw packet bytes from network capture
        table_id: Optional table identifier for filtering
        
    Returns:
        Dictionary containing processed game data
        
    Raises:
        PacketDecodeError: If packet format is invalid
    """
    # Implementation here
    pass
```

### Testing Standards
- Minimum 80% code coverage for new code
- Write unit tests for all public functions
- Write integration tests for API endpoints
- Use pytest fixtures for test setup
- Mock external dependencies in tests

**Test file structure:**
```
tests/
├── unit/
│   ├── test_packet_decoder.py
│   └── test_ai_engine.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_websocket_connection.py
└── conftest.py
```

### Documentation Standards
- Update README.md for major changes
- Add docstrings to all public functions and classes
- Update API documentation for endpoint changes
- Include examples in documentation

## Architecture Guidelines

### Project Structure
```
two_very_auto/
├── python/                 # Main Python application
│   ├── fastapi_app/       # FastAPI web service
│   ├── models/            # Data models and ML models
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── docker/                # Docker configuration
├── deployment/            # Deployment scripts
├── monitoring/            # Monitoring and metrics
└── docs/                  # Documentation
```

### API Design Principles
- Use RESTful conventions
- Version APIs using URL path (`/api/v1/`)
- Return consistent error formats
- Use appropriate HTTP status codes
- Implement rate limiting
- Add comprehensive logging

### Database Guidelines
- Use migrations for schema changes
- Add database indexes for performance
- Use database constraints for data integrity
- Implement proper connection pooling

### Security Guidelines
- Never commit secrets or credentials
- Use environment variables for configuration
- Implement proper input validation
- Add authentication and authorization
- Log security-relevant events
- Use HTTPS in production

## Issue Reporting

### Bug Reports
Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs. actual behavior
- Environment information (OS, Python version, etc.)
- Log files or error messages

### Feature Requests
Include:
- Clear description of the desired feature
- Use case or problem it solves
- Proposed solution or implementation ideas
- Any relevant examples or mockups

## Performance Guidelines

- Profile code changes that may impact performance
- Use appropriate data structures and algorithms
- Implement caching where appropriate
- Monitor memory usage
- Use async/await for I/O operations
- Consider database query optimization

## Security Considerations

- Follow OWASP security guidelines
- Review code changes for security implications
- Use static analysis tools (bandit, semgrep)
- Validate and sanitize all inputs
- Implement proper error handling
- Use secure communication protocols

## Getting Help

- Check existing [Issues](https://github.com/Jason8055/two_very_auto/issues)
- Read the [Documentation](https://github.com/Jason8055/two_very_auto/wiki)
- Ask questions in discussions
- Contact maintainers for complex issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.