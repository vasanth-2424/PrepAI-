from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.deps import get_current_user
from app.db.models.user import User
from app.models.resume import (
    ResumeAnalyzeRequest,
    ResumeAnalyzeResponse,
    ResumeDetailResponse,
    ResumeUpdateRequest,
    ResumeUploadResponse,
)
from app.services.resume_analyzer import ResumeAnalyzer
from app.services.resume_parser import ResumeParser
from app.services.resume_storage_service import ResumeStorageService
from app.utils.exceptions import AppException

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeUploadResponse:
    """Upload a PDF resume, extract text, and persist it for the current user."""
    if file.filename is None and file.content_type is None:
        raise AppException("No file was provided.", status_code=400)

    data = await file.read()
    parser = ResumeParser(settings)
    parsed = parser.parse_upload(
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )

    storage = ResumeStorageService(db)
    resume = storage.create_resume(
        user_id=current_user.id,
        filename=file.filename or "resume.pdf",
        extracted_text=parsed.text,
    )

    return ResumeUploadResponse(
        resume_id=resume.id,
        text=parsed.text,
        page_count=parsed.page_count,
        character_count=parsed.character_count,
    )


@router.get("", response_model=list[ResumeDetailResponse])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResumeDetailResponse]:
    """List all resumes uploaded by the authenticated user."""
    resumes = ResumeStorageService(db).list_resumes_for_user(current_user.id)
    return [
        ResumeDetailResponse(
            id=r.id,
            filename=r.filename,
            extracted_text=r.extracted_text,
            uploaded_at=r.uploaded_at,
            skills=[s.skill_name for s in r.skills],
            projects=[p.project_name for p in r.projects],
        )
        for r in resumes
    ]


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeDetailResponse:
    """Return a resume owned by the authenticated user."""
    resume = ResumeStorageService(db).get_resume_for_user(resume_id, current_user.id)
    return ResumeDetailResponse(
        id=resume.id,
        filename=resume.filename,
        extracted_text=resume.extracted_text,
        uploaded_at=resume.uploaded_at,
        skills=[skill.skill_name for skill in resume.skills],
        projects=[project.project_name for project in resume.projects],
    )


@router.post("/analyze", response_model=ResumeAnalyzeResponse)
async def analyze_resume(
    payload: ResumeAnalyzeRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeAnalyzeResponse:
    """Analyze extracted resume text and persist skills/projects for the resume."""
    storage = ResumeStorageService(db)
    resume = storage.get_resume_for_user(payload.resume_id, current_user.id)

    analyzer = ResumeAnalyzer(settings)
    analysis = analyzer.analyze(payload.text)
    storage.save_analysis(resume, analysis)

    return ResumeAnalyzeResponse(analysis=analysis)


@router.patch("/{resume_id}", response_model=ResumeDetailResponse)
def update_resume(
    resume_id: int,
    payload: ResumeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeDetailResponse:
    """Update metadata (filename) for a resume owned by the authenticated user."""
    service = ResumeStorageService(db)
    resume = service.update_resume_filename(resume_id, current_user.id, payload.filename)
    return ResumeDetailResponse(
        id=resume.id,
        filename=resume.filename,
        extracted_text=resume.extracted_text,
        uploaded_at=resume.uploaded_at,
        skills=[skill.skill_name for skill in resume.skills],
        projects=[project.project_name for project in resume.projects],
    )


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a resume owned by the authenticated user."""
    service = ResumeStorageService(db)
    service.delete_resume_for_user(resume_id, current_user.id)
    return {"message": "Resume deleted successfully", "resume_id": resume_id}
