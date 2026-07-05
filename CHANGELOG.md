# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Created initial project configuration files (`pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`).
- Set up directory structure for tracking milestones under the `milestones/` directory.
- Configured and verified local Python virtual environment with all core dependencies.
- Added basic repository package structure (`app/`, `tests/`) and initialized a baseline FastAPI health endpoint.
- Configured local code styling, formatting (Ruff), strict type validation (MyPy), and async testing (Pytest) suites.
- Added environment variable configuration template (`.env.example`) and comprehensive developer setup guide in `README.md`.
- Configured local infrastructure skeleton (`docker-compose.yml`) containing MySQL 8.4, Redis 7, RabbitMQ 3, and Qdrant 1.10.
- Established frontend module structure (`frontend/`) and a baseline Streamlit thin client interface (`app.py`).
- Integrated pre-commit configuration (`.pre-commit-config.yaml`) with Ruff formatting/linting and MyPy type check hooks.
- Configured a baseline Github Actions CI workflow (`.github/workflows/ci.yml`) to run automated checks (Ruff, MyPy, Pytest) on branch pushes and pull requests.

