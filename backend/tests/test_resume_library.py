"""Tests for Resume Library, Multi-Resume persistence, and New Interview isolation."""

import io
from unittest.mock import MagicMock, patch

from app.models.resume import ResumeAnalysis
from tests.conftest import make_pdf


def test_list_resumes_empty(client, auth_headers):
    """Test that a user with no uploaded resumes gets an empty list."""
    res = client.get("/api/v1/resume", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_resumes_multiple_and_active(client, auth_headers):
    """Test uploading multiple resumes keeps both in the library and allows listing."""
    # Upload first resume
    pdf1 = make_pdf("Candidate Resume Version 1 with Python and React skills.")
    res1 = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume_v1.pdf", io.BytesIO(pdf1), "application/pdf")},
        headers=auth_headers,
    )
    assert res1.status_code == 200
    r1_id = res1.json()["resume_id"]

    # Upload second resume
    pdf2 = make_pdf("Candidate Resume Version 2 with FastAPI and SQL skills.")
    res2 = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume_v2.pdf", io.BytesIO(pdf2), "application/pdf")},
        headers=auth_headers,
    )
    assert res2.status_code == 200
    r2_id = res2.json()["resume_id"]

    # Analyze second resume
    with patch("app.routers.resume.ResumeAnalyzer") as MockAnalyzer:
        mock_instance = MagicMock()
        mock_instance.analyze.return_value = ResumeAnalysis(
            name="Alice",
            skills=["Python", "FastAPI"],
            projects=["Backend API"],
        )
        MockAnalyzer.return_value = mock_instance

        analyze_res = client.post(
            "/api/v1/resume/analyze",
            json={"resume_id": r2_id, "text": "Sample text"},
            headers=auth_headers,
        )
        assert analyze_res.status_code == 200

    # Fetch resume library
    lib_res = client.get("/api/v1/resume", headers=auth_headers)
    assert lib_res.status_code == 200
    library = lib_res.json()
    assert len(library) == 2

    filenames = [r["filename"] for r in library]
    assert "resume_v1.pdf" in filenames
    assert "resume_v2.pdf" in filenames

    # Verify second resume has analyzed skills & projects
    r2_data = next(r for r in library if r["id"] == r2_id)
    assert r2_data["skills"] == ["Python", "FastAPI"]
    assert r2_data["projects"] == ["Backend API"]


def test_new_interview_session_isolation(client, auth_headers):
    """Test that creating a new interview session resets session state and does not carry previous answers/scores."""
    questions = [
        {
            "category": "Python",
            "difficulty": "Intermediate",
            "question": "What is a Python decorator?",
            "question_type": "technical",
        }
    ]

    # Create Session 1
    sess1_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "standard", "questions": questions},
        headers=auth_headers,
    )
    assert sess1_res.status_code == 200
    sess1_id = sess1_res.json()["session_id"]

    # Submit answer to Session 1
    with patch("app.routers.interview.AnswerEvaluator") as MockEval:
        mock_eval = MagicMock()
        mock_eval.evaluate.return_value = MagicMock(
            score=9.0,
            technical_accuracy="Accurate definition",
            clarity="Very clear",
            completeness="Complete",
            feedback="Great job",
            suggested_answer="A decorator wraps a function",
        )
        MockEval.return_value = mock_eval

        ans1_res = client.post(
            f"/api/v1/interview/sessions/{sess1_id}/answers",
            json={
                "question_text": "What is a Python decorator?",
                "question_category": "Python",
                "question_difficulty": "Intermediate",
                "question_type": "technical",
                "answer_text": "A decorator takes a function and extends its behavior.",
                "assistance_used": [],
            },
            headers=auth_headers,
        )
        assert ans1_res.status_code == 200
        assert ans1_res.json()["score"] == 9.0

    # Create Session 2 (New Interview) using existing resume's questions
    sess2_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "adaptive", "questions": questions},
        headers=auth_headers,
    )
    assert sess2_res.status_code == 200
    sess2_id = sess2_res.json()["session_id"]
    assert sess2_id != sess1_id

    # Verify Session 2 status has 0 answered questions and clean status
    status2 = client.get(f"/api/v1/interview/sessions/{sess2_id}", headers=auth_headers)
    assert status2.status_code == 200
    assert status2.json()["questions"] == []

    # Verify Session 1 results still exist and were not corrupted
    results1 = client.get(f"/api/v1/interview/sessions/{sess1_id}/results", headers=auth_headers)
    assert results1.status_code == 200
    assert len(results1.json()["answers"]) == 1
    assert results1.json()["answers"][0]["score"] == 9.0


def test_resume_remains_available_after_interview(client, auth_headers):
    """Test that resume and its analysis remain available in DB after completing an interview."""
    pdf = make_pdf("Master Resume content with software development skills.")
    up_res = client.post(
        "/api/v1/resume/upload",
        files={"file": ("master_resume.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_headers,
    )
    resume_id = up_res.json()["resume_id"]

    # Check resume is in library
    lib_before = client.get("/api/v1/resume", headers=auth_headers).json()
    assert any(r["id"] == resume_id for r in lib_before)

    # Start session
    sess_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "adaptive"},
        headers=auth_headers,
    )
    assert sess_res.status_code == 200

    # Check resume is STILL in library
    lib_after = client.get("/api/v1/resume", headers=auth_headers).json()
    assert any(r["id"] == resume_id for r in lib_after)


def test_resume_crud_create(client, auth_headers):
    """TEST 5 — CREATE: Authenticated user uploads a resume, creating record with user ownership."""
    pdf = make_pdf("Backend Engineer Resume with Python, Django, PostgreSQL.")
    res = client.post(
        "/api/v1/resume/upload",
        files={"file": ("backend_dev.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "resume_id" in data
    assert data["character_count"] > 0


def test_resume_crud_read(client, auth_headers):
    """TEST 6 — READ: Authenticated user requests resume list, returning only their resumes."""
    pdf = make_pdf("Frontend Engineer Resume with React, Vue, CSS.")
    client.post(
        "/api/v1/resume/upload",
        files={"file": ("frontend_dev.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_headers,
    )

    res = client.get("/api/v1/resume", headers=auth_headers)
    assert res.status_code == 200
    library = res.json()
    assert len(library) >= 1
    assert any(r["filename"] == "frontend_dev.pdf" for r in library)


def test_resume_crud_read_ownership(client, auth_headers):
    """TEST 7 — READ OWNERSHIP: Attempting to read another user's resume is rejected with 404."""
    register_res = client.post(
        "/api/v1/auth/register",
        json={"name": "Bob Other", "email": "bob@example.com", "password": "password123"},
    )
    bob_token = register_res.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    pdf = make_pdf("Bob's Private Resume with software engineering skills and project experience.")
    bob_up = client.post(
        "/api/v1/resume/upload",
        files={"file": ("bobs_secret_resume.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=bob_headers,
    )
    assert bob_up.status_code == 200
    bob_resume_id = bob_up.json()["resume_id"]

    res = client.get(f"/api/v1/resume/{bob_resume_id}", headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Resume not found"


def test_resume_crud_update(client, auth_headers):
    """TEST 8 — UPDATE: User updates their own resume filename, leaving unrelated fields unchanged."""
    pdf = make_pdf("ML Engineer Resume with PyTorch, Scikit-Learn, and Python experience.")
    up = client.post(
        "/api/v1/resume/upload",
        files={"file": ("draft_ml_resume.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_headers,
    )
    assert up.status_code == 200
    resume_id = up.json()["resume_id"]

    patch_res = client.patch(
        f"/api/v1/resume/{resume_id}",
        json={"filename": "Final_ML_Engineer_Resume.pdf"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["id"] == resume_id
    assert data["filename"] == "Final_ML_Engineer_Resume.pdf"

    detail = client.get(f"/api/v1/resume/{resume_id}", headers=auth_headers).json()
    assert detail["filename"] == "Final_ML_Engineer_Resume.pdf"


def test_resume_crud_update_ownership(client, auth_headers):
    """TEST 9 — UPDATE OWNERSHIP: User attempting to update another user's resume is rejected."""
    register_res = client.post(
        "/api/v1/auth/register",
        json={"name": "Charlie User", "email": "charlie@example.com", "password": "password123"},
    )
    charlie_token = register_res.json()["access_token"]
    charlie_headers = {"Authorization": f"Bearer {charlie_token}"}

    pdf = make_pdf("Charlie's Resume with software development experience and projects.")
    charlie_up = client.post(
        "/api/v1/resume/upload",
        files={"file": ("charlie_resume.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=charlie_headers,
    )
    assert charlie_up.status_code == 200
    charlie_resume_id = charlie_up.json()["resume_id"]

    patch_res = client.patch(
        f"/api/v1/resume/{charlie_resume_id}",
        json={"filename": "Hacked_Filename.pdf"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 404


def test_resume_crud_delete(client, auth_headers):
    """TEST 10 — DELETE: User deletes their own resume, removing it from database."""
    pdf = make_pdf("Temp Resume to Delete with software engineering skills.")
    up = client.post(
        "/api/v1/resume/upload",
        files={"file": ("temp_resume.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_headers,
    )
    assert up.status_code == 200
    resume_id = up.json()["resume_id"]

    del_res = client.delete(f"/api/v1/resume/{resume_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["resume_id"] == resume_id

    get_res = client.get(f"/api/v1/resume/{resume_id}", headers=auth_headers)
    assert get_res.status_code == 404


def test_resume_crud_delete_ownership(client, auth_headers):
    """TEST 11 — DELETE OWNERSHIP: User attempting to delete another user's resume is rejected."""
    register_res = client.post(
        "/api/v1/auth/register",
        json={"name": "David User", "email": "david@example.com", "password": "password123"},
    )
    david_token = register_res.json()["access_token"]
    david_headers = {"Authorization": f"Bearer {david_token}"}

    pdf = make_pdf("David's Resume with software development and database experience.")
    david_up = client.post(
        "/api/v1/resume/upload",
        files={"file": ("david_resume.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=david_headers,
    )
    assert david_up.status_code == 200
    david_resume_id = david_up.json()["resume_id"]

    del_res = client.delete(f"/api/v1/resume/{david_resume_id}", headers=auth_headers)
    assert del_res.status_code == 404

    david_get = client.get(f"/api/v1/resume/{david_resume_id}", headers=david_headers)
    assert david_get.status_code == 200
    assert david_get.json()["filename"] == "david_resume.pdf"

