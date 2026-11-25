from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.resume import ResumeAnalysis

QuestionDifficulty = Literal["Beginner", "Intermediate", "Advanced"]
QuestionType = Literal["technical", "project", "problem_solving", "hr"]


class InterviewQuestion(BaseModel):
    category: str = Field(..., min_length=1)
    difficulty: QuestionDifficulty
    question: str = Field(..., min_length=1)
    question_type: QuestionType


class QuestionsGenerateRequest(BaseModel):
    analysis: ResumeAnalysis


class QuestionsGenerateResponse(BaseModel):
    questions: list[InterviewQuestion]

    @field_validator("questions")
    @classmethod
    def validate_question_count(cls, questions: list[InterviewQuestion]) -> list[InterviewQuestion]:
        if len(questions) != 10:
            raise ValueError(f"Expected exactly 10 questions, got {len(questions)}")
        return questions


class LLMQuestionsPayload(BaseModel):
    """Schema used to validate raw LLM JSON output."""

    questions: list[InterviewQuestion]

    @field_validator("questions")
    @classmethod
    def validate_distribution(cls, questions: list[InterviewQuestion]) -> list[InterviewQuestion]:
        if len(questions) != 10:
            raise ValueError(f"Expected exactly 10 questions, got {len(questions)}")

        type_counts = {
            "technical": 0,
            "project": 0,
            "problem_solving": 0,
            "hr": 0,
        }
        for q in questions:
            if q.question_type in type_counts:
                type_counts[q.question_type] += 1

        if type_counts["hr"] < 2:
            raise ValueError(
                f"Fresher sequence requires at least 2 HR questions (Intro, Education), got {type_counts['hr']}"
            )
        if type_counts["technical"] < 2:
            raise ValueError(
                f"Fresher sequence requires at least 2 technical questions, got {type_counts['technical']}"
            )
        if type_counts["project"] < 1:
            raise ValueError(
                f"Fresher sequence requires at least 1 project question, got {type_counts['project']}"
            )

        return questions
