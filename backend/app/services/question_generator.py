import json
import logging

from app.config import Settings
from app.models.questions import InterviewQuestion, LLMQuestionsPayload
from app.models.resume import ResumeAnalysis
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical interviewer conducting a realistic fresher placement interview.

Given structured resume information, generate exactly 10 interview questions tailored to the candidate.

Requirements:
- Questions MUST follow a realistic, fresher-first interview progression:
  1. Question 1 (HR/Introduction): "Tell me about yourself." (question_type: "hr")
  2. Question 2 (HR/Education): "Can you tell me about your education and what you're currently studying?" (question_type: "hr")
  3. Question 3 (HR/Technical Skills): "Which technical skills or programming languages are you most comfortable using?" (question_type: "hr")
  4. Question 4 (Technical/Basic Fundamental): ONE simple, basic fundamental question on a primary skill listed in the resume (e.g., Python, Java, HTML, CSS, SQL). Do NOT ask about advanced frameworks or complex internals! (question_type: "technical")
  5. Question 5 (Project): "Can you explain your [Project Name] project and your role in it?" (grounded in an actual listed project, question_type: "project").
  6. Question 6 (Project/Technical Follow-up): A simple practical follow-up question on the project or technology (question_type: "project" or "technical").
  7. Questions 7-10: Additional simple technical fundamentals, practical problem-solving, or behavioral questions grounded in the resume (question_type: "technical", "problem_solving", or "hr").

- Expected Types Distribution across the 10 questions:
  - 3 to 4 "hr" questions (including Introduction, Education, Skills)
  - 3 to 4 "technical" questions
  - 2 to 3 "project" questions
  - 1 to 2 "problem_solving" questions

- Rules:
  - Difficulty MUST be "Beginner" or "Intermediate" only.
  - Do NOT start with advanced React hooks, TypeScript generics, browser rendering internals, architecture, optimization, or complex algorithms!
  - Questions MUST be grounded in technologies and projects actually present in the resume.
  - Questions MUST be short (1 sentence, ~8-25 words).

Return valid JSON matching this schema:
{
  "questions": [
    {
      "category": "string",
      "difficulty": "Beginner" | "Intermediate",
      "question": "string",
      "question_type": "technical" | "project" | "problem_solving" | "hr"
    }
  ]
}"""


def _generate_fallback_questions(analysis: ResumeAnalysis) -> LLMQuestionsPayload:
    """Generate a deterministic, fresher-friendly set of 10 initial questions grounded in resume analysis."""
    skills = analysis.skills or ["Programming Fundamentals"]
    projects = analysis.projects or ["Software Engineering Project"]

    skills_lower = [s.lower() for s in skills]
    if any("python" in s for s in skills_lower):
        tech_q = "What is the difference between a list and a tuple in Python?"
        tech_cat = "Python"
    elif any("java" in s for s in skills_lower if "javascript" not in s):
        tech_q = "What is the difference between == and equals() in Java?"
        tech_cat = "Java"
    elif any("html" in s for s in skills_lower):
        tech_q = "What is the difference between block-level and inline elements in HTML?"
        tech_cat = "HTML"
    elif any("css" in s for s in skills_lower):
        tech_q = "What is the CSS box model?"
        tech_cat = "CSS"
    elif any("sql" in s for s in skills_lower):
        tech_q = "What is the difference between WHERE and HAVING in SQL?"
        tech_cat = "SQL"
    else:
        tech_q = f"What are the core principles of programming in {skills[0]}?"
        tech_cat = skills[0]

    main_proj = projects[0]

    fallback_list = [
        InterviewQuestion(
            category="Introduction",
            difficulty="Beginner",
            question="Tell me about yourself.",
            question_type="hr",
        ),
        InterviewQuestion(
            category="Education",
            difficulty="Beginner",
            question="Can you tell me about your education and what you're currently studying?",
            question_type="hr",
        ),
        InterviewQuestion(
            category="Technical Skills",
            difficulty="Beginner",
            question="Which technical skills or programming languages are you most comfortable using?",
            question_type="hr",
        ),
        InterviewQuestion(
            category=tech_cat,
            difficulty="Beginner",
            question=tech_q,
            question_type="technical",
        ),
        InterviewQuestion(
            category=main_proj,
            difficulty="Beginner",
            question=f"Can you explain your {main_proj} project and your role in it?",
            question_type="project",
        ),
        InterviewQuestion(
            category=main_proj,
            difficulty="Beginner",
            question=f"What was one key technology choice or challenge in your {main_proj} project?",
            question_type="project",
        ),
        InterviewQuestion(
            category=tech_cat,
            difficulty="Intermediate",
            question=f"How would you handle error handling or data validation in {tech_cat}?",
            question_type="technical",
        ),
        InterviewQuestion(
            category="Problem Solving",
            difficulty="Intermediate",
            question="How do you approach debugging when a program produces an unexpected result?",
            question_type="problem_solving",
        ),
        InterviewQuestion(
            category=main_proj,
            difficulty="Intermediate",
            question=f"What is one improvement or feature you would add to your {main_proj} project?",
            question_type="project",
        ),
        InterviewQuestion(
            category="Behavioral",
            difficulty="Beginner",
            question="Where do you see yourself developing your technical skills over the next few years?",
            question_type="hr",
        ),
    ]
    return LLMQuestionsPayload(questions=fallback_list)


class QuestionGenerator:
    """Generates personalized interview questions from resume analysis."""

    def __init__(self, settings: Settings):
        self._llm = LLMClient(settings)

    def generate(self, analysis: ResumeAnalysis) -> LLMQuestionsPayload:
        user_prompt = (
            "Generate personalized interview questions for this candidate:\n\n"
            f"{json.dumps(analysis.model_dump(), indent=2)}"
        )

        try:
            return self._llm.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=LLMQuestionsPayload,
            )
        except Exception as exc:
            logger.warning("LLM question generation failed: %s. Using safe fresher-first fallback questions.", exc)
            return _generate_fallback_questions(analysis)
