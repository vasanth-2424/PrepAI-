"""Tests for the mock interview session API (Stage 2)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.answer_evaluator import EvaluationPayload

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

SAMPLE_QUESTIONS = [
    {
        "category": "Python",
        "difficulty": "Intermediate",
        "question": "Explain Python's GIL.",
        "question_type": "technical",
    },
    {
        "category": "Project",
        "difficulty": "Beginner",
        "question": "Describe a project you are proud of.",
        "question_type": "project",
    },
]

MOCK_EVALUATION = EvaluationPayload(
    score=8.0,
    technical_accuracy="The answer was technically accurate.",
    clarity="The answer was clear and well-structured.",
    completeness="The answer covered most important aspects.",
    feedback="Good answer. Consider adding more examples.",
    suggested_answer="A model answer would cover X, Y, and Z in detail.",
)


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------


def test_create_session_success(client, auth_headers):
    response = client.post(
        "/api/v1/interview/sessions",
        json={"questions": SAMPLE_QUESTIONS},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert isinstance(data["session_id"], int)
    assert len(data["questions"]) == len(SAMPLE_QUESTIONS)
    assert data["questions"][0]["index"] == 0
    assert data["questions"][0]["question"] == SAMPLE_QUESTIONS[0]["question"]


def test_create_session_requires_auth(client):
    response = client.post(
        "/api/v1/interview/sessions",
        json={"questions": SAMPLE_QUESTIONS},
    )
    assert response.status_code == 403


def test_create_session_empty_questions_rejected(client, auth_headers):
    response = client.post(
        "/api/v1/interview/sessions",
        json={"questions": []},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Session retrieval
# ---------------------------------------------------------------------------


def test_get_session_not_found(client, auth_headers):
    response = client.get("/api/v1/interview/sessions/99999", headers=auth_headers)
    assert response.status_code == 404


def test_get_session_requires_auth(client):
    response = client.get("/api/v1/interview/sessions/1")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Answer submission + evaluation
# ---------------------------------------------------------------------------


@patch("app.routers.interview.AnswerEvaluator")
def test_submit_answer_success(mock_evaluator_cls, client, auth_headers):
    """Create a session then submit one answer with a mocked evaluator."""
    mock_instance = MagicMock()
    mock_instance.evaluate.return_value = MOCK_EVALUATION
    mock_evaluator_cls.return_value = mock_instance

    # Create session first
    create_resp = client.post(
        "/api/v1/interview/sessions",
        json={"questions": SAMPLE_QUESTIONS},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    # Submit an answer
    answer_resp = client.post(
        f"/api/v1/interview/sessions/{session_id}/answers",
        json={
            "question_text": SAMPLE_QUESTIONS[0]["question"],
            "question_category": SAMPLE_QUESTIONS[0]["category"],
            "question_difficulty": SAMPLE_QUESTIONS[0]["difficulty"],
            "question_type": SAMPLE_QUESTIONS[0]["question_type"],
            "answer_text": "The GIL is a mutex that protects Python objects.",
        },
        headers=auth_headers,
    )
    assert answer_resp.status_code == 200
    data = answer_resp.json()
    assert data["score"] == 8.0
    assert "feedback" in data
    assert "suggested_answer" in data
    assert "technical_accuracy" in data
    assert "clarity" in data
    assert "completeness" in data
    assert "answer_id" in data


@patch("app.routers.interview.AnswerEvaluator")
def test_submit_answer_to_wrong_session(mock_evaluator_cls, client, auth_headers):
    """Submitting to a non-existent session returns 404."""
    mock_instance = MagicMock()
    mock_instance.evaluate.return_value = MOCK_EVALUATION
    mock_evaluator_cls.return_value = mock_instance

    response = client.post(
        "/api/v1/interview/sessions/99999/answers",
        json={
            "question_text": "Some question?",
            "answer_text": "Some answer.",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_submit_empty_answer_rejected(client, auth_headers):
    """Empty answer_text must fail validation."""
    # Create session first
    create_resp = client.post(
        "/api/v1/interview/sessions",
        json={"questions": SAMPLE_QUESTIONS},
        headers=auth_headers,
    )
    session_id = create_resp.json()["session_id"]

    response = client.post(
        f"/api/v1/interview/sessions/{session_id}/answers",
        json={
            "question_text": "What is Python?",
            "answer_text": "",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@patch("app.routers.interview.AnswerEvaluator")
def test_get_results(mock_evaluator_cls, client, auth_headers):
    """After submitting answers, results endpoint returns them all."""
    mock_instance = MagicMock()
    mock_instance.evaluate.return_value = MOCK_EVALUATION
    mock_evaluator_cls.return_value = mock_instance

    # Create session
    session_id = client.post(
        "/api/v1/interview/sessions",
        json={"questions": SAMPLE_QUESTIONS},
        headers=auth_headers,
    ).json()["session_id"]

    # Submit 2 answers
    for q in SAMPLE_QUESTIONS:
        client.post(
            f"/api/v1/interview/sessions/{session_id}/answers",
            json={
                "question_text": q["question"],
                "question_category": q["category"],
                "question_difficulty": q["difficulty"],
                "question_type": q["question_type"],
                "answer_text": "Sample answer for testing.",
            },
            headers=auth_headers,
        )

    results_resp = client.get(
        f"/api/v1/interview/sessions/{session_id}/results",
        headers=auth_headers,
    )
    assert results_resp.status_code == 200
    data = results_resp.json()
    assert data["session_id"] == session_id
    assert data["total_questions"] == 2
    assert data["average_score"] == 8.0
    assert len(data["answers"]) == 2


# ---------------------------------------------------------------------------
# Session completion
# ---------------------------------------------------------------------------


def test_complete_session(client, auth_headers):
    """Mark a session completed and verify status changes."""
    session_id = client.post(
        "/api/v1/interview/sessions",
        json={"questions": SAMPLE_QUESTIONS},
        headers=auth_headers,
    ).json()["session_id"]

    complete_resp = client.post(
        f"/api/v1/interview/sessions/{session_id}/complete",
        headers=auth_headers,
    )
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


def test_complete_wrong_session(client, auth_headers):
    response = client.post(
        "/api/v1/interview/sessions/99999/complete",
        headers=auth_headers,
    )
    assert response.status_code == 404
