"""AI Mentor Final Evaluator Service."""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import Settings
from app.db.models.session_answer import SessionAnswer
from app.schemas.interview import DimensionScore, FinalReport
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

FINAL_REPORT_PROMPT = """You are an AI Mentor analyzing a candidate's complete technical mock interview performance.

Based on all questions asked, candidate answers, assistance used, and evaluation feedback across the interview session, synthesize a comprehensive Final Performance Report.

Required JSON Structure:
{
  "dimensions": [
    {"dimension": "Technical Knowledge", "score": <float 0-10>, "details": "<1 sentence assessment>"},
    {"dimension": "Communication & Clarity", "score": <float 0-10>, "details": "<1 sentence assessment>"},
    {"dimension": "Problem Solving", "score": <float 0-10>, "details": "<1 sentence assessment>"},
    {"dimension": "Project Knowledge", "score": <float 0-10>, "details": "<1 sentence assessment>"},
    {"dimension": "Independent Answering", "score": <float 0-10>, "details": "<1 sentence assessment>"}
  ],
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "mentor_feedback": "<3-5 sentence encouraging, constructive overall summary narrative>",
  "recommended_improvements": ["<actionable tip 1>", "<actionable tip 2>", "<actionable tip 3>"],
  "next_topics_to_practice": ["<topic 1>", "<topic 2>", "<topic 3>"]
}"""


class LLMFinalReportPayload(BaseModel):
    dimensions: List[DimensionScore]
    strengths: List[str]
    weaknesses: List[str]
    mentor_feedback: str
    recommended_improvements: List[str]
    next_topics_to_practice: List[str]


class FinalEvaluator:
    """Synthesizes final comprehensive interview report and learning roadmap."""

    def __init__(self, settings: Settings):
        self._llm = LLMClient(settings)

    def evaluate_session(self, answers: list[SessionAnswer], mode: str) -> FinalReport:
        """Synthesize final report from session answers."""
        if not answers:
            return FinalReport(
                overall_score=0.0,
                independent_score=0.0,
                independent_ratio=0.0,
                dimensions=[
                    DimensionScore(dimension="Technical Knowledge", score=0.0, details="No questions answered."),
                    DimensionScore(dimension="Communication & Clarity", score=0.0, details="No questions answered."),
                    DimensionScore(dimension="Problem Solving", score=0.0, details="No questions answered."),
                    DimensionScore(dimension="Project Knowledge", score=0.0, details="No questions answered."),
                    DimensionScore(dimension="Independent Answering", score=0.0, details="No questions answered."),
                ],
                strengths=["Started interview session."],
                weaknesses=["No answers submitted."],
                mentor_feedback="Session ended early without submitted answers.",
                recommended_improvements=["Complete at least 3-5 interview questions to receive detailed feedback."],
                next_topics_to_practice=["General Interview Prep"],
            )

        # Calculate exact scores & assistance math
        adjusted_scores = []
        independent_scores = []
        assisted_count = 0

        for a in answers:
            score_val = a.adjusted_score if a.adjusted_score is not None else (a.score if a.score is not None else 0.0)
            adjusted_scores.append(score_val)

            # Check help usage
            help_list = json.loads(a.assistance_used) if a.assistance_used else []
            if help_list:
                assisted_count += 1
            else:
                independent_scores.append(score_val)

        overall_avg = round(sum(adjusted_scores) / len(adjusted_scores), 1) if adjusted_scores else 0.0
        independent_avg = round(sum(independent_scores) / len(independent_scores), 1) if independent_scores else overall_avg
        independent_ratio = round(((len(answers) - assisted_count) / len(answers)) * 100, 1)

        # Build LLM context
        turns_summary = []
        for i, a in enumerate(answers):
            help_list = json.loads(a.assistance_used) if a.assistance_used else []
            help_str = f"Help Used: {', '.join(help_list)}" if help_list else "No help used"
            turns_summary.append(
                f"Turn {i+1} [{a.question_type}]: {a.question_text}\n"
                f"Candidate Answer: {a.answer_text}\n"
                f"Score: {a.score or 0.0}/10 (Adjusted: {a.adjusted_score or 0.0}/10) | {help_str}\n"
                f"Feedback: {a.feedback or 'N/A'}"
            )

        user_prompt = (
            f"Interview Mode: {mode}\n"
            f"Total Questions Answered: {len(answers)}\n"
            f"Overall Score: {overall_avg}/10\n"
            f"Independent Answering Ratio: {independent_ratio}%\n\n"
            f"Session Turn History:\n" + "\n\n".join(turns_summary)
        )

        llm_res = self._llm.complete_json(
            system_prompt=FINAL_REPORT_PROMPT,
            user_prompt=user_prompt,
            response_model=LLMFinalReportPayload,
        )

        return FinalReport(
            overall_score=overall_avg,
            independent_score=independent_avg,
            independent_ratio=independent_ratio,
            dimensions=llm_res.dimensions,
            strengths=llm_res.strengths,
            weaknesses=llm_res.weaknesses,
            mentor_feedback=llm_res.mentor_feedback,
            recommended_improvements=llm_res.recommended_improvements,
            next_topics_to_practice=llm_res.next_topics_to_practice,
        )
