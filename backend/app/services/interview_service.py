"""Interview session persistence service (Stage 2 & Stage 3 Adaptive)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.interview_session import InterviewSession
from app.db.models.session_answer import SessionAnswer
from app.models.questions import InterviewQuestion as InterviewQuestionSchema
from app.schemas.interview import (
    AnswerResult,
    FinalReport,
    SessionQuestionOut,
    SessionResultResponse,
    SessionStatusResponse,
)
from app.services.answer_evaluator import EvaluationPayload
from app.services.final_evaluator import FinalEvaluator
from app.utils.exceptions import AppException

HELP_PENALTIES = {
    "small_hint": 0.5,
    "explain_concept": 1.0,
    "show_approach": 1.5,
    "suggested_answer": 3.0,
}


class InterviewService:
    """Manages interview session creation, answer storage, help tracking, and results retrieval."""

    def __init__(self, db: Session):
        self._db = db

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        user_id: int,
        questions: Optional[list[InterviewQuestionSchema]] = None,
        mode: str = "standard",
    ) -> tuple[InterviewSession, list[SessionQuestionOut]]:
        """Create a new in-progress session; returns the ORM object + ordered question list."""
        questions_list = questions or []
        session = InterviewSession(user_id=user_id, status="in_progress", mode=mode)
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)

        question_outs = [
            SessionQuestionOut(
                index=i,
                category=q.category,
                difficulty=q.difficulty,
                question=q.question,
                question_type=q.question_type,
            )
            for i, q in enumerate(questions_list)
        ]
        return session, question_outs

    def get_session(self, session_id: int, user_id: int) -> InterviewSession:
        """Fetch session and assert ownership."""
        session = self._db.get(InterviewSession, session_id)
        if session is None or session.user_id != user_id:
            raise AppException("Interview session not found", status_code=404)
        return session

    def complete_session(self, session_id: int, user_id: int) -> tuple[InterviewSession, Optional[FinalReport]]:
        """Mark the session as completed and generate final AI report."""
        session = self.get_session(session_id, user_id)
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)

        # Generate final comprehensive evaluation report
        final_report_obj = None
        try:
            evaluator = FinalEvaluator(get_settings())
            final_report_obj = evaluator.evaluate_session(session.answers, session.mode)
            session.final_report = json.dumps(final_report_obj.model_dump())
        except Exception as err:
            # Fallback if LLM fails during final synthesis
            print(f"Warning: Failed to generate final report: {err}")

        self._db.commit()
        self._db.refresh(session)
        return session, final_report_obj

    # ------------------------------------------------------------------
    # Answer + evaluation persistence
    # ------------------------------------------------------------------

    def save_answer(
        self,
        *,
        session_id: int,
        user_id: int,
        question_text: str,
        question_category: str,
        question_difficulty: str,
        question_type: str,
        answer_text: str,
        evaluation: EvaluationPayload,
        assistance_used: Optional[list[str]] = None,
    ) -> tuple[SessionAnswer, float, float, float]:
        """Persist one evaluated answer for the session, applying help penalties."""
        self.get_session(session_id, user_id)

        used_help = assistance_used or []
        raw_score = evaluation.score

        # Calculate exact penalty
        total_penalty = sum(HELP_PENALTIES.get(h, 0.0) for h in used_help)
        adjusted_score = round(max(0.0, raw_score - total_penalty), 1)

        row = SessionAnswer(
            session_id=session_id,
            question_text=question_text,
            question_category=question_category,
            question_difficulty=question_difficulty,
            question_type=question_type,
            answer_text=answer_text,
            assistance_used=json.dumps(used_help),
            raw_score=raw_score,
            adjusted_score=adjusted_score,
            score=adjusted_score,  # Store adjusted score as primary score
            technical_accuracy=evaluation.technical_accuracy,
            clarity=evaluation.clarity,
            completeness=evaluation.completeness,
            feedback=evaluation.feedback,
            suggested_answer=evaluation.suggested_answer,
            evaluated_at=datetime.now(timezone.utc),
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)

        return row, raw_score, adjusted_score, total_penalty

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def get_results(self, session_id: int, user_id: int) -> SessionResultResponse:
        """Return all evaluated answers and final report for a session."""
        session = self.get_session(session_id, user_id)

        answers = []
        for a in session.answers:
            help_list = json.loads(a.assistance_used) if a.assistance_used else []
            answers.append(
                AnswerResult(
                    answer_id=a.id,
                    question_text=a.question_text,
                    question_category=a.question_category,
                    question_difficulty=a.question_difficulty,
                    question_type=a.question_type,
                    answer_text=a.answer_text,
                    score=a.score,
                    raw_score=a.raw_score if a.raw_score is not None else a.score,
                    adjusted_score=a.adjusted_score if a.adjusted_score is not None else a.score,
                    assistance_used=help_list,
                    technical_accuracy=a.technical_accuracy,
                    clarity=a.clarity,
                    completeness=a.completeness,
                    feedback=a.feedback,
                    suggested_answer=a.suggested_answer,
                )
            )

        scored = [a.score for a in answers if a.score is not None]
        avg = round(sum(scored) / len(scored), 1) if scored else None

        final_report_data = None
        if session.final_report:
            try:
                final_report_data = FinalReport(**json.loads(session.final_report))
            except Exception:
                pass

        return SessionResultResponse(
            session_id=session.id,
            status=session.status,
            mode=session.mode or "standard",
            total_questions=len(answers),
            average_score=avg,
            answers=answers,
            final_report=final_report_data,
        )
