from sqlalchemy.orm import Session

from app.db.models.interview_question import InterviewQuestion
from app.db.models.project import Project
from app.db.models.resume import Resume
from app.db.models.skill import Skill
from app.models.questions import InterviewQuestion as InterviewQuestionSchema
from app.models.resume import ResumeAnalysis
from app.utils.exceptions import AppException


class ResumeStorageService:
    """Persists resumes, analysis results, and generated interview questions."""

    def __init__(self, db: Session):
        self._db = db

    def create_resume(self, *, user_id: int, filename: str, extracted_text: str) -> Resume:
        resume = Resume(
            user_id=user_id,
            filename=filename,
            extracted_text=extracted_text,
        )
        self._db.add(resume)
        self._db.commit()
        self._db.refresh(resume)
        return resume

    def get_resume_for_user(self, resume_id: int, user_id: int) -> Resume:
        resume = self._db.get(Resume, resume_id)
        if resume is None or resume.user_id != user_id:
            raise AppException("Resume not found", status_code=404)
        return resume

    def list_resumes_for_user(self, user_id: int) -> list[Resume]:
        return (
            self._db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.uploaded_at.desc())
            .all()
        )

    def update_resume_filename(self, resume_id: int, user_id: int, filename: str) -> Resume:
        resume = self.get_resume_for_user(resume_id, user_id)
        resume.filename = filename
        self._db.commit()
        self._db.refresh(resume)
        return resume

    def delete_resume_for_user(self, resume_id: int, user_id: int) -> None:
        resume = self.get_resume_for_user(resume_id, user_id)
        self._db.delete(resume)
        self._db.commit()

    def save_analysis(self, resume: Resume, analysis: ResumeAnalysis) -> None:
        for skill in list(resume.skills):
            self._db.delete(skill)
        for project in list(resume.projects):
            self._db.delete(project)

        for skill_name in analysis.skills:
            self._db.add(Skill(resume_id=resume.id, skill_name=skill_name))
        for project_name in analysis.projects:
            self._db.add(Project(resume_id=resume.id, project_name=project_name))

        self._db.commit()
        self._db.refresh(resume)

    def save_interview_questions(
        self,
        user_id: int,
        questions: list[InterviewQuestionSchema],
    ) -> None:
        for question in questions:
            self._db.add(
                InterviewQuestion(
                    user_id=user_id,
                    category=question.category,
                    difficulty=question.difficulty,
                    question=question.question,
                )
            )
        self._db.commit()
