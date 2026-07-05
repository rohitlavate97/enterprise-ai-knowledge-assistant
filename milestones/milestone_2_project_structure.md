# Milestone 2: Project Structure

## Goal
Establish the complete directory layout, configure the Docker Compose skeleton for local external services, set up pre-commit hooks for automated code quality checks, and create a baseline CI pipeline configuration.

## Status
- [ ] Initialize frontend directory structure (`frontend/`) and basic Streamlit entrypoint
- [ ] Configure `docker-compose.yml` for local infrastructure (MySQL 8.4, Redis, RabbitMQ, Qdrant)
- [ ] Create pre-commit configuration (`.pre-commit-config.yaml`) with Ruff, MyPy, and file validators
- [ ] Add Github Actions CI workflow configuration (`.github/workflows/ci.yml`)
- [ ] Verify local development stack setup and services startup

## Key Technical Decisions & Justifications
- **Docker Compose:** Essential for unified local orchestration of MySQL, Redis, RabbitMQ, and Qdrant, mirroring the target production environment variables closely.
- **Pre-commit Hooks:** Automates running linters (Ruff) and type checkers (MyPy) on every git commit, ensuring no syntax, style, or typing regressions make it to the repository.

## Completed Tasks Record
* *Commit 4 (Planned):* Setup Docker Compose skeleton and frontend structure.
* *Commit 5 (Planned):* Configure pre-commit hooks and CI workflow files.
