"""Pydantic schemas for the mock interview flow (Stage 2 & Stage 3 Adaptive)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.questions import InterviewQuestion

HelpType = Literal["small_hint", "explain_concept", "show_approach", "suggested_answer"]


# ---------------------------------------------------------------------------
# Session creation & status
# ---------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    """Payload to create a new interview session."""

    mode: Optional[str] = "standard"  # "standard", "adaptive", "project_deep_dive"
    questions: Optional[List[InterviewQuestion]] = Field(default=None)

    @model_validator(mode="after")
    def validate_questions_for_mode(self) -> SessionCreateRequest:
        if (self.mode or "standard") == "standard":
            if not self.questions or len(self.questions) == 0:
                raise ValueError("Standard interview session requires at least 1 question.")
        return self


class SessionQuestionOut(BaseModel):
    """A question as returned inside a session response."""

    index: int  # 0-based position in the session
    category: str
    difficulty: str
    question: str
    question_type: str


class SessionCreateResponse(BaseModel):
    session_id: int
    mode: str
    questions: List[SessionQuestionOut]


class SessionStatusResponse(BaseModel):
    session_id: int
    status: str
    mode: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    questions: List[SessionQuestionOut]


# ---------------------------------------------------------------------------
# Answer submission, evaluation, and Help system
# ---------------------------------------------------------------------------


class SubmitAnswerRequest(BaseModel):
    """Payload to submit and evaluate one answer."""

    question_text: str = Field(..., min_length=1)
    question_category: str = Field(default="")
    question_difficulty: str = Field(default="")
    question_type: str = Field(default="")
    answer_text: str = Field(..., min_length=1)
    assistance_used: List[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Returned immediately after an answer is evaluated."""

    answer_id: int
    score: float
    raw_score: float
    adjusted_score: float
    total_penalty: float
    technical_accuracy: str
    clarity: str
    completeness: str
    feedback: str
    suggested_answer: str
    assistance_used: List[str] = Field(default_factory=list)


class HelpRequest(BaseModel):
    """Payload to request assistance during an interview question."""

    question_text: str = Field(..., min_length=1)
    question_category: str = Field(default="")
    question_difficulty: str = Field(default="")
    question_type: str = Field(default="")
    help_type: HelpType


class HelpResponse(BaseModel):
    """Response containing assistance hint and penalty warning."""

    help_type: str
    content: str
    penalty: float


# ---------------------------------------------------------------------------
# Dynamic next question request
# ---------------------------------------------------------------------------


class NextQuestionRequest(BaseModel):
    """Payload to request dynamically generated next question."""

    current_index: int
    projects: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Session results & Comprehensive Final Report
# ---------------------------------------------------------------------------


class DimensionScore(BaseModel):
    dimension: str
    score: float
    details: str


class FinalReport(BaseModel):
    overall_score: float
    independent_score: float
    independent_ratio: float  # Percentage 0-100%
    dimensions: List[DimensionScore]
    strengths: List[str]
    weaknesses: List[str]
    mentor_feedback: str
    recommended_improvements: List[str]
    next_topics_to_practice: List[str]


class AnswerResult(BaseModel):
    """One evaluated answer inside a session results response."""

    answer_id: int
    question_text: str
    question_category: str
    question_difficulty: str
    question_type: str
    answer_text: str
    score: Optional[float] = None
    raw_score: Optional[float] = None
    adjusted_score: Optional[float] = None
    assistance_used: List[str] = Field(default_factory=list)
    technical_accuracy: Optional[str] = None
    clarity: Optional[str] = None
    completeness: Optional[str] = None
    feedback: Optional[str] = None
    suggested_answer: Optional[str] = None


class SessionResultResponse(BaseModel):
    session_id: int
    status: str
    mode: str
    total_questions: int
    average_score: Optional[float] = None
    answers: List[AnswerResult]
    final_report: Optional[FinalReport] = None


