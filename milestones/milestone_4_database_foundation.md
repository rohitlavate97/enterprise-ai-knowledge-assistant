# Milestone 4: Database Foundation (MySQL + Alembic + Seed Data)

## Goal
Establish the relational database infrastructure by configuring SQLAlchemy async engine and sessionmaker, setting up Alembic migrations, mapping relational models with audit tracking fields, writing seeding utilities, and wiring the repository layer to perform real database operations.

## Status
- [ ] Setup async database connection engine and session factory (`app/core/database.py`)
- [ ] Define SQLAlchemy base metadata class and auditing mixins (`app/models/base.py`)
- [ ] Create user relational model (`app/models/user.py`)
- [ ] Configure Alembic migrations pipeline (`alembic.ini`, `migrations/env.py`)
- [ ] Generate initial Alembic migration script for the user table
- [ ] Implement database seeding command for initial setup (e.g., default administrator)
- [ ] Migrate the `UserRepository` to run async queries using SQLAlchemy sessions
- [ ] Update pytest fixtures to handle transactional database state during testing

## Key Technical Decisions & Justifications
- **SQLAlchemy 2.0 Async:** Enables clean, modern, type-safe, and asynchronous queries using `asyncio` and `aiomysql` dialect for MySQL 8.4 compatibility.
- **Alembic migrations:** Strict version control for relational schema modifications, ensuring zero manual schema edits in any environment.
- **Auditing Mixin:** Automatically logs `created_at` and `updated_at` time stamps on all relational tables, adhering to corporate audit standards.

## Completed Tasks Record
* *Commit 7 (Planned):* Initialize database session manager, base models, and user model.
* *Commit 8 (Planned):* Configure Alembic and generate initial migrations.
* *Commit 9 (Planned):* Update repositories and pytest fixtures to integrate database support.
