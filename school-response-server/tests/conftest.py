"""
tests/conftest.py
=================
Pytest fixtures: in-memory SQLite engine, test client, seeded test data.
"""
from __future__ import annotations

import os

# ── Must be set BEFORE importing app modules that load settings ───────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-never-use-in-production")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

# Clear cached settings so the test env vars are picked up
try:
    from app.core.config import get_settings
    get_settings.cache_clear()
except Exception:
    pass

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import (
    CardStatus, QuestionSetStatus, QuizSessionStatus,
    SchoolStatus, StudentStatus, UserRole,
)
from app.models.school import AcademicYear, Class, School, Section
from app.models.user import Teacher, User
from app.models.student import Student
from app.models.card import Card, StudentCard
from app.models.quiz import Question, QuestionSet, QuizSession

# ── Use in-memory SQLite for tests ────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionFactory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh session and rollback after each test."""
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_db(db: AsyncSession):
    """Override the app's get_db dependency with the test session."""
    async def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client(override_db) -> AsyncGenerator[AsyncClient, None]:
    # Reset the SlowAPI in-memory rate limit counters before each test
    # so repeated login calls across tests don't accumulate to 10/min.
    try:
        from app.core.rate_limit import limiter
        limiter.reset()
    except Exception:
        try:
            # SlowAPI >= 0.1.9: limiter._storage.reset()
            from app.core.rate_limit import limiter
            limiter._storage.reset()
        except Exception:
            pass

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Seed helpers ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def school_a(db: AsyncSession) -> School:
    s = School(school_code="SCHOOL-A", name="School Alpha",
                status=SchoolStatus.ACTIVE)
    db.add(s)
    await db.flush()
    return s


@pytest_asyncio.fixture
async def school_b(db: AsyncSession) -> School:
    s = School(school_code="SCHOOL-B", name="School Beta",
                status=SchoolStatus.ACTIVE)
    db.add(s)
    await db.flush()
    return s


@pytest_asyncio.fixture
async def admin_user_a(db: AsyncSession, school_a: School) -> User:
    u = User(
        school_id=school_a.id,
        username="admin_a",
        email="admin@schoola.test",
        password_hash=hash_password("Password@1"),
        role=UserRole.SCHOOL_ADMIN,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def teacher_user_a(db: AsyncSession, school_a: School) -> User:
    u = User(
        school_id=school_a.id,
        username="teacher_a",
        email="teacher@schoola.test",
        password_hash=hash_password("Password@1"),
        role=UserRole.TEACHER,
    )
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def super_admin(db: AsyncSession) -> User:
    u = User(
        school_id=None,
        username="superadmin",
        email="super@platform.test",
        password_hash=hash_password("SuperPass@1"),
        role=UserRole.SUPER_ADMIN,
    )
    db.add(u)
    await db.flush()
    return u


async def get_token(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]
