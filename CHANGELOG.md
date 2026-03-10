# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD workflow with test, lint, and security scanning
- Dependabot configuration for automated dependency updates
- CodeQL security analysis workflow
- Pre-commit hooks configuration for code quality
- Multi-stage Dockerfile for optimized production builds
- .dockerignore file for faster Docker builds
- Bandit security scanning configuration
- Python 3.13 support classification

### Changed
- Updated Next.js from 14.0.4 to 14.2.35 (security patch for CVE-2025-66478)
- Consolidated linting to Ruff-only (removed Black dependency)
- Updated Ruff configuration with modern rule sets
- Updated FastAPI dependency to >=0.115.0
- Modernized pyproject.toml with explicit version constraints
- Enhanced mypy configuration with stricter type checking

### Security
- Fixed critical RCE vulnerability in Next.js (CVE-2025-66478)
- Added SHA-pinned GitHub Actions for supply chain security
- Added Gitleaks for secret detection in pre-commit
- Added dependency review action for PR security scanning

### Removed
- Removed Black formatter (replaced by Ruff format)

## [0.1.0] - 2024-12-25

### Added
- Initial release of Geospatial AI Co-Scientist
- Multi-agent architecture with LangGraph orchestration
- 8 specialized agents (Generation, Reflection, Ranking, etc.)
- FastAPI REST API with WebSocket support
- CLI interface with Typer
- Docker and docker-compose configuration
- Comprehensive test suite with pytest
- Next.js frontend with Orbital Command design
- LangSmith tracing integration
- ChromaDB and FAISS vector store support

[Unreleased]: https://github.com/georeason-labs/geospatial-co-scientist/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/georeason-labs/geospatial-co-scientist/releases/tag/v0.1.0
