import io

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.resume_parser import ResumeParser
from app.utils.exceptions import AppException
from tests.conftest import make_empty_pdf, make_pdf


@pytest.fixture
def parser() -> ResumeParser:
    return ResumeParser(Settings(max_upload_size_mb=5))


def test_valid_pdf_extraction(parser: ResumeParser) -> None:
    pdf_bytes = make_pdf("Vasanth A\nSkills: Python, Java, SQL, React")
    result = parser.parse_upload(
        filename="resume.pdf",
        content_type="application/pdf",
        data=pdf_bytes,
    )
    assert result.page_count >= 1
    assert result.character_count >= 30
    assert "Python" in result.text or len(result.text) >= 30


def test_invalid_file_type(parser: ResumeParser) -> None:
    with pytest.raises(AppException) as exc:
        parser.parse_upload(
            filename="resume.txt",
            content_type="text/plain",
            data=b"not a pdf",
        )
    assert exc.value.status_code == 400


def test_empty_file(parser: ResumeParser) -> None:
    with pytest.raises(AppException) as exc:
        parser.parse_upload(filename="resume.pdf", content_type="application/pdf", data=b"")
    assert "empty" in exc.value.message.lower()


def test_corrupted_pdf(parser: ResumeParser) -> None:
    with pytest.raises(AppException) as exc:
        parser.parse_upload(
            filename="resume.pdf",
            content_type="application/pdf",
            data=b"%PDF-corrupted-content",
        )
    assert exc.value.status_code == 400


def test_image_only_pdf(parser: ResumeParser) -> None:
    pdf_bytes = make_empty_pdf()
    with pytest.raises(AppException) as exc:
        parser.parse_upload(
            filename="resume.pdf",
            content_type="application/pdf",
            data=pdf_bytes,
        )
    assert exc.value.status_code == 422
    assert "OCR" in exc.value.message


def test_upload_endpoint_valid_pdf(client: TestClient, auth_headers: dict[str, str]) -> None:
    pdf_bytes = make_pdf("Vasanth A\nPython Developer\nSkills: Python, SQL")
    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "text" in body
    assert "resume_id" in body
    assert body["page_count"] >= 1


def test_upload_endpoint_invalid_type(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_upload_endpoint_requires_auth(client: TestClient) -> None:
    pdf_bytes = make_pdf("Vasanth A\nPython Developer")
    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 403
