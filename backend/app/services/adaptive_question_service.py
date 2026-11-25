"""Adaptive Question Generation & Help Service (Fresher-First & Conversational)."""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Set

from pydantic import BaseModel, Field

from app.config import Settings
from app.db.models.session_answer import SessionAnswer
from app.models.questions import InterviewQuestion
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


ADAPTIVE_QUESTION_PROMPT = """You are an expert technical interviewer conducting a realistic, conversational fresher placement interview for a candidate seeking an entry-level software engineering role.

Your goal is to conduct a natural interview conversation using short, practical, resume-grounded questions.

CORE PRINCIPLES:
1. "Ask what a real interviewer is likely to ask a fresher, not what a difficult technical exam could ask."
2. KEEP QUESTIONS SHORT: Questions MUST be concise (1 sentence, ~8–25 words, maximum ~35 words).
3. ONE MAIN IDEA PER QUESTION: Test ONE concept at a time. Do NOT combine multiple tasks or sub-questions into a single turn.
4. LISTEN TO THE CANDIDATE: Use details, technologies, or projects mentioned in the candidate's last answer to ask a natural follow-up question.

Rules:
1. FRESHER-FIRST CONVERSATIONAL REALISM:
   - Ask clear, conversational questions grounded in technical fundamentals, resume skills, and resume projects.
   - You may use short conversational transitions where appropriate (e.g. "That's good. Tell me about...", "Okay, you mentioned Python...", "Let's talk about your project.").
   - STRICT PROHIBITION ON OVERLY COMPLEX EXAM QUESTIONS: Do NOT ask specification calculations, obscure framework edge cases, complex dynamic programming space/time proofs, or multi-part questions.
   - RESUME EVIDENCE RULE: Ask technical questions ONLY about technologies explicitly listed in candidate skills, projects, or introduced by candidate in their answers.

2. ADAPTIVE DIFFICULTY & GRADUAL SCALING:
   - WEAK ANSWER (score < 5.0/10):
     * Lock to the EXACT SAME topic/concept ('{last_topic}').
     * Ask a short, simple, fundamental question helping the candidate recover.
     * Set difficulty to "Beginner".
   - SINGLE STRONG ANSWER (score >= 8.0/10):
     * Stay locked on '{last_topic}'. Ask a short, practical, slightly deeper follow-up.
     * Scale difficulty GRADUALLY. Do NOT jump to advanced exam questions.
     * Set difficulty to "Intermediate".
   - REPEATED STRONG ANSWERS (2+ consecutive turns >= 8.0/10):
     * Stay locked on '{last_topic}' and ask a deeper practical question (design choices or common trade-offs).
     * Set difficulty to "Intermediate" or "Advanced".
   - MEDIUM ANSWER (5.0 - 7.9/10):
     * Ask a short, practical follow-up on '{last_topic}' or make a natural transition.
     * Set difficulty to "Intermediate" or "Beginner".

3. PROJECT GROUNDING:
   - When discussing a project, stay focused on that specific project (goal, candidate's role, technology choices, challenges, solution). Do NOT invent unlisted projects or features.

4. DIVERSITY & NON-REPETITION:
   - Do NOT repeat any previously asked question.

5. OUTPUT FORMAT:
   Return valid JSON matching this schema:
   {{
     "category": "<string topic matching the locked/current topic>",
     "difficulty": "<Beginner | Intermediate | Advanced>",
     "question": "<short string interview question>",
     "question_type": "<technical | project | problem_solving | hr>"
   }}"""


PROJECT_DEEP_DIVE_PROMPT = """You are an expert technical interviewer conducting a realistic Project Deep Dive interview for a fresher.

The candidate has listed the following projects on their resume:
{projects_text}

Your goal is to question the candidate about their ACTUAL projects in a short, conversational, fresher-friendly manner.

Rules:
1. Grounding: All questions MUST directly reference one of the candidate's listed projects. Do NOT invent unlisted projects or features.
2. Progression across turns:
   - Turn 1: "Can you explain your project briefly?" or "What was the main goal of your project?"
   - Turn 2: "What was your specific role in the project?"
   - Turn 3: "Why did you choose this technology for the project?"
   - Turn 4: "What was one challenge you faced and how did you solve it?"
   - Turn 5+: "What is one thing you would improve in your project?"
3. Keep questions SHORT (1 sentence, under 30 words) and conversational.
4. Listen to what the candidate explained and ask a natural follow-up.
5. OUTPUT FORMAT:
   Return valid JSON matching this schema:
   {{
     "category": "Project Deep Dive",
     "difficulty": "<Beginner | Intermediate | Advanced>",
     "question": "<short string interview question>",
     "question_type": "project"
   }}"""


HELP_PROMPT = """You are an interview mentor providing real-time assistance during a technical mock interview.

Question: {question_text}
Question Type: {question_type}
Category: {question_category}
Help Type Requested: {help_type}

Instructions based on Help Type:
- "small_hint": Provide a 1-2 sentence subtle hint guiding the candidate's thinking WITHOUT giving away the complete answer.
- "explain_concept": Provide a 2-3 sentence clear explanation of the core technical concept/term behind the question.
- "show_approach": Provide 2-3 bullet points framing how to structure an ideal response (e.g. STAR method or logical steps).
- "suggested_answer": Provide a 3-5 sentence complete model answer demonstrating how a top candidate would respond.

Return valid JSON with key "content":
{{
  "content": "<string response>"
}}"""


class HelpPayload(BaseModel):
    content: str = Field(..., min_length=1)


# Comprehensive tech families dictionary for cross-tech switch detection
TECH_FAMILIES = {
    "css": ["css", "box model", "flexbox", "grid", "responsive layout", "box-sizing", "media queries", "css selectors"],
    "html": ["html", "dom", "semantic html"],
    "react": ["react", "usestate", "useeffect", "usecontext", "usereducer", "usememo", "usecallback", "virtual dom", "jsx", "props", "state management", "reusable component"],
    "vue": ["vue", "vuex", "composition api"],
    "angular": ["angular", "rxjs", "ngmodule"],
    "typescript": ["typescript", "generics", "generic type", "type annotation", "interface", "prop types"],
    "javascript": ["javascript", "event loop", "closure", "closures", "promises", "async/await", "hoisting", "prototypal"],
    "express": ["express", "express.js", "node", "node.js", "get endpoint", "post endpoint", "put endpoint", "delete endpoint", "rest", "rest api", "middleware", "routing"],
    "python": ["python", "gil", "list comprehension", "decorators", "asyncio", "dunder"],
    "java": ["java", "jvm", "spring", "spring boot", "garbage collection"],
    "cpp": ["c++", "pointers", "raii", "stl", "templates"],
    "go": ["go", "golang", "goroutine", "channels"],
    "sql": ["sql", "postgres", "postgresql", "mysql", "indexing", "b-tree", "joins", "sqlalchemy", "acid", "transactions"],
    "mongodb": ["mongodb", "nosql", "aggregation pipeline", "mongoose"],
    "redis": ["redis", "caching", "pub/sub"],
    "docker": ["docker", "container", "dockerfile", "docker-compose"],
    "kubernetes": ["kubernetes", "k8s", "pod", "deployment"],
    "ml": ["machine learning", "classification model", "spam detection", "tf-idf", "random forest", "scikit-learn", "pandas", "numpy", "neural network"],
}


def _extract_specific_concepts(q_text: str, cat: str) -> list[str]:
    """Extract specific technical concepts or phrases from question text and category."""
    text_to_search = f"{cat} {q_text}"
    text_lower = text_to_search.lower()

    found = []

    concept_phrases = [
        ("css box model", "CSS box model"),
        ("flexbox", "Flexbox"),
        ("grid", "CSS Grid"),
        ("responsive layout", "responsive layout"),
        ("usestate", "useState"),
        ("useeffect", "useEffect"),
        ("usecontext", "useContext"),
        ("usereducer", "useReducer"),
        ("usememo", "useMemo"),
        ("usecallback", "useCallback"),
        ("virtual dom", "Virtual DOM"),
        ("props", "React props"),
        ("state management", "state management"),
        ("reusable button", "reusable button component"),
        ("reusable component", "reusable components"),
        ("generic type", "generics"),
        ("generics", "generics"),
        ("rest api", "REST API"),
        ("get endpoint", "GET endpoint"),
        ("post endpoint", "POST endpoint"),
        ("express.js", "Express.js"),
        ("express", "Express.js"),
        ("b-tree", "B-Tree indexing"),
        ("indexing", "indexing"),
        ("sql joins", "SQL joins"),
        ("join", "SQL joins"),
        ("gil", "Python GIL"),
        ("event loop", "event loop"),
        ("closure", "closures"),
        ("closures", "closures"),
    ]

    for kw, label in concept_phrases:
        if kw in text_lower and label not in found:
            found.append(label)

    code_terms = re.findall(r'`([^`]+)`|\b(use[A-Z][a-zA-Z0-9]+)\b', q_text)
    for match in code_terms:
        term = match[0] or match[1]
        if term and term.lower() not in [f.lower() for f in found]:
            found.append(term)

    return found


def _resolve_specific_topic(
    ans: SessionAnswer | None, projects: list[str], skills: list[str]
) -> str:
    """Resolve specific topic or project name from question category, text, and resume profile."""
    if not ans:
        return "General Software Engineering"

    cat = (ans.question_category or "").strip()
    q_text = (ans.question_text or "").strip()

    # 1. Match against candidate projects
    for p in projects:
        if p and (p.lower() in q_text.lower() or p.lower() in cat.lower()):
            concepts = _extract_specific_concepts(q_text, cat)
            if concepts:
                return f"{p} ({concepts[0]})"
            return p

    # 2. Extract specific concepts from question text & category
    concepts = _extract_specific_concepts(q_text, cat)

    generic_categories = {
        "project",
        "project deep dive",
        "technical",
        "hr",
        "behavioral",
        "general",
        "problem solving",
        "programming",
        "frontend",
        "backend",
    }

    if concepts:
        concept_str = " / ".join(concepts[:2])
        if cat and cat.lower() not in generic_categories:
            if cat.lower() not in concept_str.lower():
                return f"{cat} ({concept_str})"
            return cat
        return concept_str

    if cat and cat.lower() not in generic_categories:
        return cat

    matched_skills = [s for s in skills if s and s.lower() in q_text.lower()]
    if matched_skills:
        return " + ".join(matched_skills[:2])

    return q_text[:50] if q_text else "Technical Engineering"


def _get_tech_families(text: str) -> set[str]:
    """Find all technology families present in the given text."""
    text_lower = text.lower()
    families = set()
    for fam_name, keywords in TECH_FAMILIES.items():
        for kw in keywords:
            if kw in text_lower:
                families.add(fam_name)
                break
    return families


def _is_off_topic_on_weak_answer(
    question: InterviewQuestion,
    last_topic: str,
    last_question: str,
    skills: list[str],
    projects: list[str],
) -> bool:
    """Check generically if generated question inappropriately switched topics after a weak answer."""
    gen_text = f"{question.category} {question.question}".lower()
    last_full = f"{last_topic} {last_question}".lower()

    # 1. Check for project switches
    for proj in projects:
        if proj and proj.lower() in gen_text and proj.lower() not in last_full:
            logger.warning(
                "Rejected LLM question on weak answer due to project jump to '%s': %s",
                proj, question.question
            )
            return True

    # 2. Tech Family switch check
    prev_families = _get_tech_families(last_full)
    gen_families = _get_tech_families(gen_text)

    if prev_families:
        unrelated_switches = gen_families - prev_families
        if unrelated_switches:
            logger.warning(
                "Rejected LLM question on weak answer due to tech family switch from %s to %s: %s",
                prev_families, unrelated_switches, question.question
            )
            return True

    # 3. Check token / keyword overlap
    stop_words = {
        "explain", "create", "describe", "how", "what", "would", "using", "technical",
        "engineering", "question", "type", "category", "purpose", "concept", "handling",
        "implementation", "basic", "simple", "main", "with", "and", "the", "for", "you",
        "your", "can", "does", "that", "this", "from", "into", "returns", "set", "up"
    }
    raw_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', last_full)) - stop_words
    if raw_tokens:
        has_overlap = any(tok in gen_text for tok in raw_tokens)
        if not has_overlap and not (prev_families and gen_families and prev_families.intersection(gen_families)):
            logger.warning(
                "Rejected LLM question on weak answer due to lack of token/family overlap (tokens: %s): %s",
                raw_tokens, question.question
            )
            return True

    # 4. Check for jumps to unrelated candidate skills
    for other_skill in skills:
        if other_skill and other_skill.lower() not in last_full:
            if other_skill.lower() in gen_text:
                logger.warning(
                    "Rejected LLM question on weak answer because it jumped to candidate skill '%s': %s",
                    other_skill, question.question
                )
                return True

    return False


def _is_overly_complex_question(question: InterviewQuestion) -> bool:
    """Check if generated question is overly complex, exam-like, multi-part, or excessively long for a fresher."""
    q_text = question.question.strip()
    q_lower = q_text.lower()

    # 1. Reject questions exceeding word count limit (~38 words) for conversational TTS readability
    words = q_text.split()
    if len(words) > 38:
        logger.warning(
            "Rejected LLM question because it exceeds 38 words (%d words): %s",
            len(words), question.question
        )
        return True

    # 2. Reject multi-part questions combining multiple independent tasks into one prompt
    multi_task_patterns = [
        r'\b(what is|explain|describe)\b.*\band how\b.*\band (why|what|how)\b',
        r'\b(how|what|why)\b.*\band in what\b',
        r'\b(how|what|why)\b.*\band also\b',
        r'\b(explain|describe)\b.*\band compare\b.*\band\b',
    ]
    for pattern in multi_task_patterns:
        if re.search(pattern, q_lower):
            logger.warning(
                "Rejected LLM question because it combines multiple independent tasks: %s",
                question.question
            )
            return True

    # 3. Exam-style & specification-level phrases to reject
    complex_phrases = [
        "calculate step-by-step",
        "calculate the final rendered width",
        "according to the flexbox specification",
        "according to the css specification",
        "browser rendering pipeline step-by-step",
        "formal space complexity proof",
        "optimized dynamic programming approach",
        "recurrence relation for dynamic programming",
        "time and space complexity of the optimized dynamic programming",
        "step-by-step pixel calculation",
        "discuss all edge cases",
        "considering both",
        "explain the complete internal mechanism",
        "analyze multiple trade-offs",
        "under high scale",
        "provide a concrete example and discuss",
        "provide a detailed derivation",
    ]

    for phrase in complex_phrases:
        if phrase in q_lower:
            logger.warning(
                "Rejected LLM question because it contains overly complex exam-style phrasing: %s",
                question.question
            )
            return True

    return False


def _is_unsupported_resume_skill_jump(
    question: InterviewQuestion,
    skills: list[str],
    projects: list[str],
    previous_answers: list[SessionAnswer],
) -> bool:
    """Check if generated question asks about a major tech framework not supported by resume or previous turns."""
    if not skills and not projects:
        return False

    gen_text = f"{question.category} {question.question}".lower()

    major_techs = {
        "react", "vue", "angular", "svelte", "express", "django", "flask",
        "fastapi", "spring", "docker", "kubernetes", "aws", "postgresql",
        "mongodb", "redis", "graphql", "tensorflow", "pytorch"
    }

    history_text = " ".join(
        f"{a.question_text} {a.answer_text}" for a in previous_answers
    ).lower()
    allowed_context = f"{' '.join(skills)} {' '.join(projects)} {history_text}".lower()

    for tech in major_techs:
        if tech in gen_text and tech not in allowed_context:
            logger.warning(
                "Rejected LLM question because it introduced ungrounded technology '%s' not present in resume or previous turns: %s",
                tech, question.question
            )
            return True

    return False


def _generate_safe_fallback(
    last_topic: str,
    last_question: str,
    last_score: float | None,
    projects: list[str],
    skills: list[str] | None = None,
    current_index: int = 0,
    question_type: str = "technical",
    consecutive_strong_count: int = 0,
    mode: str = "standard",
) -> InterviewQuestion:
    """Generate a clean, deterministic, short, fresher-friendly fallback question."""
    if mode != "project_deep_dive" and current_index < 6 and last_score is None:
        if current_index == 0:
            return InterviewQuestion(
                category="Introduction",
                difficulty="Beginner",
                question="Tell me about yourself.",
                question_type="hr",
            )
        elif current_index == 1:
            return InterviewQuestion(
                category="Education",
                difficulty="Beginner",
                question="Can you tell me about your education and what you're currently studying?",
                question_type="hr",
            )
        elif current_index == 2:
            return InterviewQuestion(
                category="Technical Skills",
                difficulty="Beginner",
                question="Which technical skills or programming languages are you most comfortable using?",
                question_type="hr",
            )
        elif current_index == 3:
            skills_lower = [s.lower() for s in (skills or [])]
            if any("python" in s for s in skills_lower):
                q_text = "What is the difference between a list and a tuple in Python?"
                cat = "Python"
            elif any("java" in s for s in skills_lower if "javascript" not in s):
                q_text = "What is the difference between == and equals() in Java?"
                cat = "Java"
            elif any("html" in s for s in skills_lower):
                q_text = "What is the difference between block-level and inline elements in HTML?"
                cat = "HTML"
            elif any("css" in s for s in skills_lower):
                q_text = "What is the CSS box model?"
                cat = "CSS"
            elif any("sql" in s for s in skills_lower):
                q_text = "What is the difference between WHERE and HAVING in SQL?"
                cat = "SQL"
            else:
                q_text = "What is the difference between a list and a tuple in Python?"
                cat = "Programming Fundamentals"
            return InterviewQuestion(
                category=cat,
                difficulty="Beginner",
                question=q_text,
                question_type="technical",
            )
        elif current_index == 4:
            proj_name = projects[0] if projects else "main project"
            return InterviewQuestion(
                category=proj_name,
                difficulty="Beginner",
                question=f"Can you explain your {proj_name} project and your role in it?",
                question_type="project",
            )
        elif current_index == 5:
            proj_name = projects[0] if projects else "main project"
            return InterviewQuestion(
                category=proj_name,
                difficulty="Beginner",
                question=f"What was one key technology choice or challenge in your {proj_name} project?",
                question_type="project",
            )

    is_project = any(p.lower() in last_topic.lower() or p.lower() in last_question.lower() for p in projects)
    q_type = "project" if is_project else question_type

    if last_score is not None and last_score < 5.0:
        if is_project:
            fallback_q = f"What was the main goal of your {last_topic} project?"
        elif "usestate" in last_topic.lower() or "state" in last_topic.lower():
            fallback_q = "What is the useState hook used for in React?"
        elif "props" in last_topic.lower():
            fallback_q = "What are props in a React component?"
        elif "virtual dom" in last_topic.lower():
            fallback_q = "What is the Virtual DOM in React?"
        elif "box model" in last_topic.lower() or "css" in last_topic.lower():
            fallback_q = "What is the CSS box model?"
        elif "get" in last_topic.lower() or "endpoint" in last_topic.lower() or "express" in last_topic.lower():
            fallback_q = "What is a GET request used for in Express?"
        else:
            fallback_q = f"What is {last_topic} used for?"

        return InterviewQuestion(
            category=last_topic,
            difficulty="Beginner",
            question=fallback_q,
            question_type=q_type,
        )

    if last_score is not None and last_score >= 8.0:
        if is_project:
            fallback_q = f"What was one technical challenge you faced in your {last_topic} project?"
        else:
            fallback_q = f"Can you give a simple example of how you used {last_topic}?"

        return InterviewQuestion(
            category=last_topic,
            difficulty="Intermediate",
            question=fallback_q,
            question_type=q_type,
        )

    if is_project:
        fallback_q = f"What technologies did you use in your {last_topic} project?"
    else:
        fallback_q = f"How would you use {last_topic} in a project?"

    return InterviewQuestion(
        category=last_topic,
        difficulty="Intermediate",
        question=fallback_q,
        question_type=q_type,
    )


class AdaptiveQuestionService:
    """Service generating dynamic questions and contextual help for interviews."""

    def __init__(self, settings: Settings):
        self._llm = LLMClient(settings)

    def generate_next_question(
        self,
        *,
        mode: str,
        previous_answers: list[SessionAnswer],
        projects: list[str],
        skills: list[str],
        current_index: int,
    ) -> InterviewQuestion:
        """Generate next dynamic question based on candidate trajectory and interview mode."""
        history_summary = []
        last_ans = previous_answers[-1] if previous_answers else None
        last_topic = _resolve_specific_topic(last_ans, projects, skills)
        last_score = last_ans.score if last_ans and last_ans.score is not None else None
        last_question = last_ans.question_text if last_ans else ""
        last_accuracy = last_ans.technical_accuracy if last_ans else None
        last_ans_text = last_ans.answer_text if last_ans else ""

        # Calculate consecutive strong answers count
        consecutive_strong_count = 0
        for ans in reversed(previous_answers):
            if ans.score is not None and ans.score >= 8.0:
                consecutive_strong_count += 1
            else:
                break

        for i, ans in enumerate(previous_answers):
            score_str = f"Score: {ans.score:.1f}/10" if ans.score is not None else "Skipped"
            history_summary.append(
                f"- Q{i+1} [{ans.question_type} / {ans.question_category} / {ans.question_difficulty}]: {ans.question_text}\n"
                f"  Candidate Answer: {ans.answer_text[:200]}\n"
                f"  {score_str} | Technical Accuracy: {ans.technical_accuracy or 'N/A'} | Feedback: {ans.feedback or 'N/A'}"
            )

        history_text = "\n".join(history_summary) if history_summary else "No previous turns yet."
        projects_text = ", ".join(projects) if projects else "General Software Engineering Projects"
        skills_text = ", ".join(skills) if skills else "General Software Development"

        if mode != "project_deep_dive" and current_index < 6:
            if current_index == 0:
                direction_label = "INITIAL_Q1_INTRO"
                directive = (
                    "INITIAL FRESHER INTERVIEW PHASE - Turn 1 (Q1: Introduction).\n"
                    "Generate a warm, standard fresher self-introduction question.\n"
                    "Preferred: 'Tell me about yourself.'\n"
                    "Set category to 'Introduction', difficulty to 'Beginner', question_type to 'hr'."
                )
            elif current_index == 1:
                direction_label = "INITIAL_Q2_EDUCATION"
                directive = (
                    "INITIAL FRESHER INTERVIEW PHASE - Turn 2 (Q2: Education / Academic Background).\n"
                    "Ask about the candidate's education and what they are currently studying.\n"
                    "Example: 'Can you tell me about your education and what you're currently studying?'\n"
                    "Set category to 'Education', difficulty to 'Beginner', question_type to 'hr'."
                )
            elif current_index == 2:
                direction_label = "INITIAL_Q3_SKILLS"
                directive = (
                    f"INITIAL FRESHER INTERVIEW PHASE - Turn 3 (Q3: Technical Skills).\n"
                    f"Ask which technical skills or programming languages the candidate is most comfortable using, referencing candidate skills ({skills_text}).\n"
                    f"Example: 'Which technical skills or programming languages are you most comfortable using?'\n"
                    f"Set category to 'Technical Skills', difficulty to 'Beginner', question_type to 'hr'."
                )
            elif current_index == 3:
                direction_label = "INITIAL_Q4_BASIC_TECHNICAL"
                directive = (
                    f"INITIAL FRESHER INTERVIEW PHASE - Turn 4 (Q4: Basic Technical Fundamental).\n"
                    f"Ask ONE simple, basic technical fundamental question about a skill listed in candidate's resume ({skills_text}).\n"
                    f"Examples based on resume skills:\n"
                    f"- Python: 'What is the difference between a list and a tuple in Python?'\n"
                    f"- Java: 'What is the difference between == and equals() in Java?'\n"
                    f"- HTML: 'What is the difference between block-level and inline elements in HTML?'\n"
                    f"- CSS: 'What is the CSS box model?'\n"
                    f"- SQL: 'What is the difference between WHERE and HAVING in SQL?'\n"
                    f"STRICT PROHIBITION: Do NOT ask about advanced React hooks (useState, useEffect), TypeScript generics, browser rendering internals, architecture, or optimization.\n"
                    f"Set category matching the skill, difficulty to 'Beginner', question_type to 'technical'."
                )
            elif current_index == 4:
                direction_label = "INITIAL_Q5_PROJECT"
                directive = (
                    f"INITIAL FRESHER INTERVIEW PHASE - Turn 5 (Q5: Resume Project).\n"
                    f"Ask the candidate to explain one project listed in their resume ({projects_text}) and their role in it.\n"
                    f"Example: 'Can you explain your project and your role in it?'\n"
                    f"Set category matching the project name, difficulty to 'Beginner', question_type to 'project'."
                )
            else:
                direction_label = "INITIAL_Q6_PRACTICAL_FOLLOWUP"
                directive = (
                    f"INITIAL FRESHER INTERVIEW PHASE - Turn 6 (Q6: Practical Follow-up).\n"
                    f"Ask a simple, practical follow-up question based on the candidate's previous answer about their project or skills.\n"
                    f"Keep it concise (1 sentence, under 25 words).\n"
                    f"Set category to match the topic, difficulty to 'Beginner' or 'Intermediate', question_type to 'project' or 'technical'."
                )
        elif last_ans and last_score is not None:
            if last_score < 5.0:
                direction_label = "WEAKER"
                directive = (
                    f"PREVIOUS ANSWER EVALUATION: WEAK (Score: {last_score:.1f}/10 < 5.0)\n"
                    f"LOCKED TOPIC / CONCEPT: '{last_topic}'\n"
                    f"AUTHORITATIVE TOPIC ANCHOR (PREVIOUS QUESTION): '{last_question}'\n"
                    f"CANDIDATE'S LAST ANSWER: '{last_ans_text[:150]}'\n"
                    f"MANDATORY REQUIREMENT: The candidate gave a WEAK answer ({last_score:.1f}/10).\n"
                    f"1. You MUST stay STRICTLY LOCKED on the EXACT SAME specific topic ('{last_topic}').\n"
                    f"2. Generate a SHORT, simple, fundamental follow-up question testing basic concepts of '{last_topic}'.\n"
                    f"3. Keep question concise (1 sentence, under 25 words).\n"
                    f"4. STRICT PROHIBITION: You are STRICTLY FORBIDDEN from switching to another technology, framework, language, backend API, database, or candidate resume skill.\n"
                    f"5. Set category to '{last_topic}' and difficulty to 'Beginner'."
                )
            elif last_score >= 8.0:
                if consecutive_strong_count >= 2:
                    direction_label = "REPEATED_STRONG_DEEPER"
                    directive = (
                        f"PREVIOUS ANSWER EVALUATION: REPEATED STRONG ({consecutive_strong_count} consecutive answers >= 8.0/10, latest: {last_score:.1f}/10)\n"
                        f"Previous Topic / Project: '{last_topic}'\n"
                        f"Previous Question: '{last_question}'\n"
                        f"CANDIDATE'S LAST ANSWER: '{last_ans_text[:150]}'\n"
                        f"MANDATORY REQUIREMENT: The candidate demonstrated repeatedly strong performance.\n"
                        f"1. Stay locked on '{last_topic}' or make a logical, natural progression.\n"
                        f"2. Generate a SHORT, deeper technical follow-up question (probing architecture, design choices, or common trade-offs).\n"
                        f"3. Keep question practical, concise (1 sentence, under 30 words), and realistic for a fresher interview.\n"
                        f"4. Set category to '{last_topic}' and difficulty to 'Intermediate' or 'Advanced'."
                    )
                else:
                    direction_label = "SINGLE_STRONG_DEEPER"
                    directive = (
                        f"PREVIOUS ANSWER EVALUATION: SINGLE STRONG (Score: {last_score:.1f}/10 >= 8.0)\n"
                        f"Previous Topic / Project: '{last_topic}'\n"
                        f"Previous Question: '{last_question}'\n"
                        f"CANDIDATE'S LAST ANSWER: '{last_ans_text[:150]}'\n"
                        f"MANDATORY REQUIREMENT: The candidate gave a single strong answer ({last_score:.1f}/10).\n"
                        f"1. Scale difficulty GRADUALLY. Do NOT jump to an expert exam question.\n"
                        f"2. Stay locked on '{last_topic}' and ask a SHORT, practical, slightly deeper follow-up (e.g. common use cases or practical differences).\n"
                        f"3. Keep question concise (1 sentence, under 25 words).\n"
                        f"4. Set category to '{last_topic}' and difficulty to 'Intermediate'."
                    )
            else:
                direction_label = "MEDIUM"
                directive = (
                    f"PREVIOUS ANSWER EVALUATION: MEDIUM (Score: {last_score:.1f}/10)\n"
                    f"Previous Topic / Project: '{last_topic}'\n"
                    f"Previous Question: '{last_question}'\n"
                    f"CANDIDATE'S LAST ANSWER: '{last_ans_text[:150]}'\n"
                    f"REQUIREMENT: Ask a SHORT, practical follow-up question addressing missing details on '{last_topic}' or make a natural transition. Keep under 25 words. Set difficulty to 'Intermediate' or 'Beginner'."
                )
        else:
            direction_label = "INITIAL"
            directive = (
                f"First question in adaptive interview mode (Turn #{current_index + 1}). "
                f"Ask a friendly, short, realistic fresher introduction or foundational technical question grounded in candidate's resume skills ({skills_text}) or projects ({projects_text}). "
                f"Example: 'Tell me about yourself and your technical background' or 'Which programming language are you most comfortable with?'"
            )

        if mode == "project_deep_dive":
            system_prompt = PROJECT_DEEP_DIVE_PROMPT.format(projects_text=projects_text)
        else:
            system_prompt = ADAPTIVE_QUESTION_PROMPT

        user_prompt = (
            f"PREVIOUS QUESTION:\n{last_question or 'N/A'}\n\n"
            f"PREVIOUS TOPIC:\n{last_topic}\n\n"
            f"PREVIOUS DIFFICULTY:\n{last_ans.question_difficulty if last_ans else 'N/A'}\n\n"
            f"CANDIDATE ANSWER:\n{last_ans_text if last_ans else 'N/A'}\n\n"
            f"SCORE:\n{f'{last_score:.1f}/10' if last_score is not None else 'N/A'}\n\n"
            f"EVALUATION:\n{last_ans.feedback if last_ans else 'N/A'}\n\n"
            f"CANDIDATE SKILLS:\n{skills_text}\n\n"
            f"CANDIDATE PROJECTS:\n{projects_text}\n\n"
            f"ADAPTIVE DIRECTION:\n{direction_label}\n\n"
            f"DETAILED DIRECTIVE:\n{directive}\n\n"
            f"PREVIOUS TURN HISTORY:\n{history_text}\n\n"
            f"Generate Question #{current_index + 1} adaptively."
        )

        try:
            res = self._llm.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=InterviewQuestion,
            )

            # 1. Post-generation validation for weak answers: reject off-topic jumps
            if last_score is not None and last_score < 5.0 and current_index >= 6:
                if _is_off_topic_on_weak_answer(res, last_topic, last_question, skills, projects):
                    raise ValueError(f"LLM generated off-topic question on weak answer: {res.question}")

            # 2. Reject questions introducing ungrounded skills not present in resume or previous turns
            if _is_unsupported_resume_skill_jump(res, skills, projects, previous_answers):
                raise ValueError(f"LLM generated question with ungrounded technology: {res.question}")

            # 3. Reject overly complex specification-exam style questions or multi-part questions
            if _is_overly_complex_question(res):
                raise ValueError(f"LLM generated overly complex exam-style question: {res.question}")

            return res
        except Exception as exc:
            logger.error("LLM adaptive question generation failed or rejected: %s. Using safe topic-locked fallback.", exc)
            return _generate_safe_fallback(
                last_topic=last_topic,
                last_question=last_question,
                last_score=last_score,
                projects=projects,
                skills=skills,
                current_index=current_index,
                question_type=last_ans.question_type if last_ans else "technical",
                consecutive_strong_count=consecutive_strong_count,
                mode=mode,
            )

    def generate_help(
        self,
        *,
        question_text: str,
        question_category: str,
        question_type: str,
        help_type: str,
    ) -> str:
        """Generate targeted hint, concept explanation, or approach outline."""
        system_prompt = HELP_PROMPT.format(
            question_text=question_text,
            question_category=question_category or "General",
            question_type=question_type or "technical",
            help_type=help_type,
        )
        user_prompt = f"Provide help for request type '{help_type}' on question: '{question_text}'."

        res = self._llm.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=HelpPayload,
        )
        return res.content
