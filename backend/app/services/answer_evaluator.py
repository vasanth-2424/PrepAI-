"""AI-powered answer evaluator for the mock interview (Stage 2)."""

import json
import logging

from pydantic import BaseModel, Field, field_validator

from app.config import Settings
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical interviewer evaluating a candidate's interview answer.

Given the interview question and the candidate's answer, provide a structured evaluation.

Evaluation criteria:
- score: A float between 0 and 10 (e.g. 7.5) reflecting overall quality.
- technical_accuracy: One concise sentence assessing factual/technical correctness.
- clarity: One concise sentence assessing how clear and well-structured the answer is.
- completeness: One concise sentence assessing whether all important aspects were covered.
- feedback: 2-4 sentences of actionable, constructive feedback to help the candidate improve.
- suggested_answer: A model answer that demonstrates what an ideal response would look like (3-6 sentences).

Rules:
- Be objective and fair. Score 0 for completely wrong/blank, 10 for exceptional.
- feedback and suggested_answer must be specific to the question and answer provided.
- Do NOT penalise for minor grammatical issues — focus on substance.
- For HR/behavioral questions, evaluate based on structure, self-awareness, and relevance.

Return valid JSON matching this exact schema:
{
  "score": <float 0-10>,
  "technical_accuracy": "<string>",
  "clarity": "<string>",
  "completeness": "<string>",
  "feedback": "<string>",
  "suggested_answer": "<string>"
}"""


class EvaluationPayload(BaseModel):
    """Schema for raw LLM evaluation output."""

    score: float = Field(..., ge=0, le=10)
    technical_accuracy: str = Field(..., min_length=1)
    clarity: str = Field(..., min_length=1)
    completeness: str = Field(..., min_length=1)
    feedback: str = Field(..., min_length=1)
    suggested_answer: str = Field(..., min_length=1)

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return round(max(0.0, min(10.0, v)), 1)


class AnswerEvaluator:
    """Evaluates a candidate's answer to an interview question using an LLM."""

    def __init__(self, settings: Settings):
        self._llm = LLMClient(settings)

    def evaluate(self, question: str, answer: str, question_type: str = "") -> EvaluationPayload:
        """Evaluate the candidate's answer and return structured feedback."""
        context = f"Question Type: {question_type}\n" if question_type else ""
        user_prompt = (
            f"{context}"
            f"Interview Question:\n{question}\n\n"
            f"Candidate's Answer:\n{answer if answer.strip() else '[No answer provided]'}"
        )

        return self._llm.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=EvaluationPayload,
        )
