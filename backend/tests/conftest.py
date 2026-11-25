import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

import io
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.database import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def make_pdf(text: str = "Sample resume content for testing purposes.") -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    y = 750
    for line in text.split("\n"):
        pdf.drawString(72, y, line)
        y -= 16
    pdf.save()
    return buffer.getvalue()


def make_empty_pdf() -> bytes:
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def settings_override(test_settings: Settings) -> Settings:
    return test_settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        max_upload_size_mb=5,
        llm_max_retries=1,
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-secret-key-for-testing-only",
        jwt_algorithm="HS256",
        access_token_expire_minutes=60,
    )


@pytest.fixture
def client(db_session, test_settings: Settings) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client


    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepass123",
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def auth_headers(registered_user: dict) -> dict[str, str]:
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
