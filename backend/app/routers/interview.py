"""FastAPI router for mock interview sessions (Stage 2 & Stage 3 Adaptive)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.models.user import User
from app.deps import get_current_user
from app.schemas.interview import (
    EvaluationResponse,
    HelpRequest,
    HelpResponse,
    NextQuestionRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionQuestionOut,
    SessionResultResponse,
    SessionStatusResponse,
    SubmitAnswerRequest,
)
from app.services.adaptive_question_service import AdaptiveQuestionService
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_service import HELP_PENALTIES, InterviewService

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/sessions", response_model=SessionCreateResponse)
def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionCreateResponse:
    """Create a new mock interview session."""
    mode = payload.mode or "standard"
    service = InterviewService(db)
    session, question_outs = service.create_session(
        user_id=current_user.id,
        questions=payload.questions,
        mode=mode,
    )
    return SessionCreateResponse(
        session_id=session.id,
        mode=session.mode,
        questions=question_outs,
    )


@router.get("/sessions/{session_id}", response_model=SessionStatusResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionStatusResponse:
    """Get session metadata and question list for the authenticated user."""
    service = InterviewService(db)
    session = service.get_session(session_id, current_user.id)

    answered_questions = [
        SessionQuestionOut(
            index=i,
            category=a.question_category,
            difficulty=a.question_difficulty,
            question=a.question_text,
            question_type=a.question_type,
        )
        for i, a in enumerate(session.answers)
    ]

    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        mode=session.mode or "standard",
        created_at=session.created_at,
        completed_at=session.completed_at,
        questions=answered_questions,
    )


@router.post("/sessions/{session_id}/answers", response_model=EvaluationResponse)
def submit_answer(
    session_id: int,
    payload: SubmitAnswerRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationResponse:
    """Submit and AI-evaluate one answer with assistance penalties."""
    evaluator = AnswerEvaluator(settings)
    evaluation = evaluator.evaluate(
        question=payload.question_text,
        answer=payload.answer_text,
        question_type=payload.question_type,
    )

    service = InterviewService(db)
    saved, raw_score, adjusted_score, total_penalty = service.save_answer(
        session_id=session_id,
        user_id=current_user.id,
        question_text=payload.question_text,
        question_category=payload.question_category,
        question_difficulty=payload.question_difficulty,
        question_type=payload.question_type,
        answer_text=payload.answer_text,
        evaluation=evaluation,
        assistance_used=payload.assistance_used,
    )

    return EvaluationResponse(
        answer_id=saved.id,
        score=adjusted_score,
        raw_score=raw_score,
        adjusted_score=adjusted_score,
        total_penalty=total_penalty,
        technical_accuracy=evaluation.technical_accuracy,
        clarity=evaluation.clarity,
        completeness=evaluation.completeness,
        feedback=evaluation.feedback,
        suggested_answer=evaluation.suggested_answer,
        assistance_used=payload.assistance_used,
    )


@router.post("/sessions/{session_id}/help", response_model=HelpResponse)
def get_interview_help(
    session_id: int,
    payload: HelpRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HelpResponse:
    """Request real-time assistance (hint/concept/approach/suggested answer) for a question."""
    service = InterviewService(db)
    service.get_session(session_id, current_user.id)

    adaptive_service = AdaptiveQuestionService(settings)
    content = adaptive_service.generate_help(
        question_text=payload.question_text,
        question_category=payload.question_category,
        question_type=payload.question_type,
        help_type=payload.help_type,
    )
    penalty = HELP_PENALTIES.get(payload.help_type, 0.0)

    return HelpResponse(
        help_type=payload.help_type,
        content=content,
        penalty=penalty,
    )


@router.post("/sessions/{session_id}/next-question", response_model=SessionQuestionOut)
def generate_next_question(
    session_id: int,
    payload: NextQuestionRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionQuestionOut:
    """Dynamically generate the next question for adaptive/project deep-dive sessions."""
    service = InterviewService(db)
    session = service.get_session(session_id, current_user.id)

    adaptive_service = AdaptiveQuestionService(settings)
    question = adaptive_service.generate_next_question(
        mode=session.mode,
        previous_answers=session.answers,
        projects=payload.projects,
        skills=payload.skills,
        current_index=payload.current_index,
    )

    return SessionQuestionOut(
        index=payload.current_index,
        category=question.category,
        difficulty=question.difficulty,
        question=question.question,
        question_type=question.question_type,
    )


@router.get("/sessions/{session_id}/results", response_model=SessionResultResponse)
def get_results(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResultResponse:
    """Return all evaluated answers and final comprehensive evaluation report."""
    return InterviewService(db).get_results(session_id, current_user.id)


@router.post("/sessions/{session_id}/complete", response_model=SessionStatusResponse)
def complete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionStatusResponse:
    """Mark a session as completed and synthesize final AI report."""
    service = InterviewService(db)
    session, _ = service.complete_session(session_id, current_user.id)

    answered = [
        SessionQuestionOut(
            index=i,
            category=a.question_category,
            difficulty=a.question_difficulty,
            question=a.question_text,
            question_type=a.question_type,
        )
        for i, a in enumerate(session.answers)
    ]

    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        mode=session.mode or "standard",
        created_at=session.created_at,
        completed_at=session.completed_at,
        questions=answered,
    )
