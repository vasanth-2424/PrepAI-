from datetime import datetime

from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    resume_id: int = Field(..., description="Database ID of the saved resume")
    text: str = Field(..., description="Combined extracted text from all PDF pages")
    page_count: int = Field(..., ge=1)
    character_count: int = Field(..., ge=1)


class ResumeAnalyzeRequest(BaseModel):
    resume_id: int = Field(..., ge=1)
    text: str = Field(..., min_length=1, max_length=100_000)


class ResumeUpdateRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)


class ResumeAnalysis(BaseModel):
    name: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ResumeAnalyzeResponse(BaseModel):
    analysis: ResumeAnalysis


class ResumeDetailResponse(BaseModel):
    id: int
    filename: str
    extracted_text: str
    uploaded_at: datetime
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}
