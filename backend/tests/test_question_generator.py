import json
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.models.questions import LLMQuestionsPayload
from app.models.resume import ResumeAnalysis
from app.services.question_generator import QuestionGenerator
from app.utils.exceptions import AppException


def _sample_questions_payload() -> dict:
    questions = [
        {
            "category": "Introduction",
            "difficulty": "Beginner",
            "question": "Tell me about yourself.",
            "question_type": "hr",
        },
        {
            "category": "Education",
            "difficulty": "Beginner",
            "question": "Can you tell me about your education and what you're currently studying?",
            "question_type": "hr",
        },
        {
            "category": "Technical Skills",
            "difficulty": "Beginner",
            "question": "Which technical skills or programming languages are you most comfortable using?",
            "question_type": "hr",
        },
        {
            "category": "Python",
            "difficulty": "Beginner",
            "question": "What is the difference between a list and a tuple in Python?",
            "question_type": "technical",
        },
        {
            "category": "Email Spam Detection",
            "difficulty": "Beginner",
            "question": "Can you explain your Email Spam Detection project and your role in it?",
            "question_type": "project",
        },
        {
            "category": "Email Spam Detection",
            "difficulty": "Intermediate",
            "question": "What algorithms did you use in your project?",
            "question_type": "project",
        },
        {
            "category": "Python",
            "difficulty": "Intermediate",
            "question": "How do you manage exceptions in Python?",
            "question_type": "technical",
        },
        {
            "category": "Problem Solving",
            "difficulty": "Intermediate",
            "question": "How do you debug failing code?",
            "question_type": "problem_solving",
        },
        {
            "category": "Python",
            "difficulty": "Intermediate",
            "question": "What are decorators in Python?",
            "question_type": "technical",
        },
        {
            "category": "Behavioral",
            "difficulty": "Beginner",
            "question": "Where do you see yourself in 3 years?",
            "question_type": "hr",
        },
    ]
    return {"questions": questions}


SAMPLE_ANALYSIS = ResumeAnalysis(
    name="Vasanth A",
    skills=["Python", "SQL", "React"],
    projects=["Email Spam Detection System"],
    education=[],
    experience=[],
    certifications=[],
)


def test_generate_questions_success(settings_override: Settings) -> None:
    generator = QuestionGenerator(settings_override)
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_sample_questions_payload())))
    ]

    with patch.object(generator._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generator.generate(SAMPLE_ANALYSIS)

    assert len(result.questions) == 10
    assert sum(1 for q in result.questions if q.question_type == "hr") >= 2


def test_generate_questions_invalid_distribution(settings_override: Settings) -> None:
    # 0 HR questions should trigger validation failure and fallback to safe fresher questions
    bad_payload = _sample_questions_payload()
    for q in bad_payload["questions"]:
        q["question_type"] = "technical"

    generator = QuestionGenerator(settings_override)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(bad_payload)))]

    with patch.object(generator._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generator.generate(SAMPLE_ANALYSIS)

    # Fallback produces 10 questions starting with "Tell me about yourself."
    assert len(result.questions) == 10
    assert result.questions[0].question == "Tell me about yourself."


def test_generate_questions_llm_failure(settings_override: Settings) -> None:
    generator = QuestionGenerator(settings_override)

    with patch.object(generator._llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("timeout")
        mock_get_client.return_value = mock_client

        result = generator.generate(SAMPLE_ANALYSIS)

    assert len(result.questions) == 10
    assert result.questions[0].question == "Tell me about yourself."


def test_questions_endpoint(client, auth_headers: dict[str, str]) -> None:
    with patch("app.routers.questions.QuestionGenerator") as MockGenerator:
        instance = MockGenerator.return_value
        instance.generate.return_value = LLMQuestionsPayload.model_validate(
            _sample_questions_payload()
        )

        response = client.post(
            "/api/v1/questions/generate",
            json={"analysis": SAMPLE_ANALYSIS.model_dump()},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert len(response.json()["questions"]) == 10
