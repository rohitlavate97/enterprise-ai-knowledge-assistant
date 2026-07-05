# Milestone 3: Authentication (JWT, OAuth2, RBAC)

## Goal
Implement a secure, robust authentication system utilizing JSON Web Tokens (JWT), OAuth2 password flows, and Role-Based Access Control (RBAC).

## Status
- [x] Configure JWT token encoding, decoding, validation, and token rotation security utilities
- [x] Define User roles and permission levels (RBAC definitions)
- [x] Create Pydantic schemas for User registration, login, token responses, and profiles
- [x] Implement Security Dependency Injection utilities (`get_current_user`, `check_permissions`)
- [x] Create OAuth2 FastAPI auth endpoints (register, login, token refresh)
- [x] Write tests verifying password hashing, token validation, and RBAC protection

## Key Technical Decisions & Justifications
- **JWT + OAuth2 Password Flow:** Standard secure industry approach for FastAPI backends, integrating easily with standard auth libraries and Streamlit clients.
- **Direct bcrypt Library Hashing:** Bypassed the unmaintained `passlib` library in favor of utilizing the modern `bcrypt` library directly. This avoids deprecation warnings in Python 3.12+ and prevents runtime crashes caused by the 72-byte password check in `passlib`'s startup tests when run alongside modern `bcrypt` versions.
- **In-Memory Repository Mocking:** Implemented in-memory repository abstractions to allow the API routing and security layers to be fully testable and operational prior to relational database setup in Milestone 4.

## Completed Tasks Record
* *Commit 6 (Actual):* Setup core security utilities, DTO schemas, mock repository layers, and FastAPI routes for JWT authentication and RBAC.
* *Commit 7 (Actual):* Add comprehensive unit/integration tests covering registration, login, refresh, and role-based endpoint protection.
