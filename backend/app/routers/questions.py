from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.deps import get_current_user
from app.db.models.user import User
from app.models.questions import QuestionsGenerateRequest, QuestionsGenerateResponse
from app.services.question_generator import QuestionGenerator
from app.services.resume_storage_service import ResumeStorageService

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("/generate", response_model=QuestionsGenerateResponse)
async def generate_questions(
    payload: QuestionsGenerateRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionsGenerateResponse:
    """Generate personalized interview questions and persist them for the user."""
    generator = QuestionGenerator(settings)
    result = generator.generate(payload.analysis)

    ResumeStorageService(db).save_interview_questions(current_user.id, result.questions)

    return QuestionsGenerateResponse(questions=result.questions)
