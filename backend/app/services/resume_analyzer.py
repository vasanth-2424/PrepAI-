from pydantic import BaseModel

from app.config import Settings
from app.models.resume import ResumeAnalysis
from app.services.llm_client import LLMClient

SYSTEM_PROMPT = """You are a resume analysis assistant for an interview preparation platform.

Extract structured information from the resume text provided by the user.

Rules:
- Only extract information that is explicitly present in the resume text.
- Do NOT invent, guess, or infer missing information.
- If a field is not found, use an empty string for name or an empty list for list fields.
- Skills should be individual technologies, tools, or competencies mentioned in the resume.
- Projects should be project titles or short project names mentioned in the resume.
- Education entries should be concise (degree, institution, or both if available).
- Experience entries should be concise role/company summaries from the resume.
- Certifications should be certification names only if explicitly listed.

Return valid JSON matching this schema:
{
  "name": "string",
  "skills": ["string"],
  "projects": ["string"],
  "education": ["string"],
  "experience": ["string"],
  "certifications": ["string"]
}"""


class ResumeAnalyzer:
    """Analyzes extracted resume text using an LLM."""

    def __init__(self, settings: Settings):
        self._llm = LLMClient(settings)

    def analyze(self, text: str) -> ResumeAnalysis:
        sanitized = text.strip()
        user_prompt = f"Analyze the following resume text and extract structured information:\n\n{sanitized}"

        class AnalysisPayload(BaseModel):
            name: str = ""
            skills: list[str] = []
            projects: list[str] = []
            education: list[str] = []
            experience: list[str] = []
            certifications: list[str] = []

        payload = self._llm.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=AnalysisPayload,
        )

        return ResumeAnalysis(
            name=payload.name.strip(),
            skills=_clean_list(payload.skills),
            projects=_clean_list(payload.projects),
            education=_clean_list(payload.education),
            experience=_clean_list(payload.experience),
            certifications=_clean_list(payload.certifications),
        )


def _clean_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items:
        value = item.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned
