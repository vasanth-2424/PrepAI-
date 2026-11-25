import io
import json
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from tests.conftest import make_pdf
from app.models.resume import ResumeAnalysis
from app.services.resume_analyzer import ResumeAnalyzer
from app.utils.exceptions import AppException


SAMPLE_ANALYSIS_JSON = {
    "name": "Vasanth A",
    "skills": ["Python", "Java", "SQL", "React"],
    "projects": ["Email Spam Detection System", "Placement Data Analysis"],
    "education": ["B.Tech Computer Science"],
    "experience": ["Software Intern at Example Corp"],
    "certifications": [],
}


def test_analyze_resume_success(settings_override: Settings) -> None:
    analyzer = ResumeAnalyzer(settings_override)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(SAMPLE_ANALYSIS_JSON)))]

    with patch.object(analyzer._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyzer.analyze("Vasanth A resume with Python and React skills.")

    assert result.name == "Vasanth A"
    assert "Python" in result.skills
    assert len(result.projects) == 2


def test_analyze_resume_missing_sections(settings_override: Settings) -> None:
    analyzer = ResumeAnalyzer(settings_override)
    sparse_json = {
        "name": "",
        "skills": ["Python"],
        "projects": [],
        "education": [],
        "experience": [],
        "certifications": [],
    }
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(sparse_json)))]

    with patch.object(analyzer._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = analyzer.analyze("Skills: Python")

    assert result.name == ""
    assert result.skills == ["Python"]
    assert result.projects == []


def test_analyze_resume_llm_failure(settings_override: Settings) -> None:
    analyzer = ResumeAnalyzer(settings_override)

    with patch.object(analyzer._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")
        mock_get_client.return_value = mock_client

        with pytest.raises(AppException) as exc:
            analyzer.analyze("Some resume text")
        assert exc.value.status_code == 502


def test_analyze_resume_invalid_llm_json(settings_override: Settings) -> None:
    analyzer = ResumeAnalyzer(settings_override)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="not-json"))]

    with patch.object(analyzer._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with pytest.raises(AppException) as exc:
            analyzer.analyze("Some resume text")
        assert exc.value.status_code == 502


def test_analyze_endpoint(client, auth_headers: dict[str, str]) -> None:
    pdf_bytes = io.BytesIO(
        make_pdf("Vasanth A\nPython Developer\nSkills: Python, SQL")
    )
    upload_response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers,
    )
    assert upload_response.status_code == 200
    resume_id = upload_response.json()["resume_id"]

    with patch("app.routers.resume.ResumeAnalyzer") as MockAnalyzer:
        instance = MockAnalyzer.return_value
        instance.analyze.return_value = ResumeAnalysis(**SAMPLE_ANALYSIS_JSON)

        response = client.post(
            "/api/v1/resume/analyze",
            json={"resume_id": resume_id, "text": "Vasanth A Python developer resume"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["skills"]
