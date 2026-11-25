"""Tests for Adaptive Interview, Help System, and Final Evaluation Report (Stage 3)."""

from unittest.mock import MagicMock, patch

from app.models.questions import InterviewQuestion
from app.schemas.interview import FinalReport, HelpResponse


def test_create_adaptive_session(client, auth_headers):
    """Test creating an adaptive session without pre-generated questions."""
    response = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "adaptive"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "adaptive"
    assert "session_id" in data
    assert data["questions"] == []


def test_get_help_endpoint(client, auth_headers):
    """Test requesting real-time help during a question."""
    sess_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "adaptive"},
        headers=auth_headers,
    )
    session_id = sess_res.json()["session_id"]

    expected_penalties = {
        "small_hint": 0.5,
        "explain_concept": 1.0,
        "show_approach": 1.5,
        "suggested_answer": 3.0,
    }

    with patch("app.routers.interview.AdaptiveQuestionService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_instance.generate_help.return_value = "Help content for candidate."
        mock_service_cls.return_value = mock_instance

        for help_type, penalty in expected_penalties.items():
            help_res = client.post(
                f"/api/v1/interview/sessions/{session_id}/help",
                json={
                    "question_text": "Describe a difficult project challenge.",
                    "question_category": "Behavioral",
                    "question_type": "hr",
                    "help_type": help_type,
                },
                headers=auth_headers,
            )

            assert help_res.status_code == 200
            data = help_res.json()
            assert data["help_type"] == help_type
            assert data["content"] == "Help content for candidate."
            assert data["penalty"] == penalty


def test_submit_answer_with_help_penalty(client, auth_headers):
    """Test answer evaluation applies assistance penalties correctly and clamps score at 0."""
    # Create session with 1 initial question
    questions = [
        {
            "category": "Python",
            "difficulty": "Intermediate",
            "question": "What is GIL in Python?",
            "question_type": "technical",
        }
    ]
    sess_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "standard", "questions": questions},
        headers=auth_headers,
    )
    session_id = sess_res.json()["session_id"]

    with patch("app.routers.interview.AnswerEvaluator") as mock_eval_cls:
        mock_eval = MagicMock()
        # Raw score 8.0
        mock_eval.evaluate.return_value = MagicMock(
            score=8.0,
            technical_accuracy="Accurate definition of GIL.",
            clarity="Clear description.",
            completeness="Complete.",
            feedback="Good answer.",
            suggested_answer="GIL is global interpreter lock.",
        )
        mock_eval_cls.return_value = mock_eval

        # Submit answer using small_hint (-0.5) and show_approach (-1.5) => Total Penalty 2.0
        sub_res = client.post(
            f"/api/v1/interview/sessions/{session_id}/answers",
            json={
                "question_text": "What is GIL in Python?",
                "question_category": "Python",
                "question_difficulty": "Intermediate",
                "question_type": "technical",
                "answer_text": "The GIL locks execution to one thread.",
                "assistance_used": ["small_hint", "show_approach"],
            },
            headers=auth_headers,
        )

        assert sub_res.status_code == 200
        data = sub_res.json()
        assert data["raw_score"] == 8.0
        assert data["total_penalty"] == 2.0
        assert data["adjusted_score"] == 6.0
        assert data["score"] == 6.0
        assert data["assistance_used"] == ["small_hint", "show_approach"]


def test_submit_answer_clamped_penalty(client, auth_headers):
    """Test score penalty never goes below 0."""
    questions = [
        {
            "category": "Databases",
            "difficulty": "Beginner",
            "question": "What is SQL?",
            "question_type": "technical",
        }
    ]
    sess_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "standard", "questions": questions},
        headers=auth_headers,
    )
    session_id = sess_res.json()["session_id"]

    with patch("app.routers.interview.AnswerEvaluator") as mock_eval_cls:
        mock_eval = MagicMock()
        # Raw score 2.0
        mock_eval.evaluate.return_value = MagicMock(
            score=2.0,
            technical_accuracy="Basic.",
            clarity="Vague.",
            completeness="Incomplete.",
            feedback="Needs work.",
            suggested_answer="SQL is structured query language.",
        )
        mock_eval_cls.return_value = mock_eval

        # Penalty = -3.0 (suggested_answer) => 2.0 - 3.0 = -1.0 => clamped to 0.0
        sub_res = client.post(
            f"/api/v1/interview/sessions/{session_id}/answers",
            json={
                "question_text": "What is SQL?",
                "question_category": "Databases",
                "question_difficulty": "Beginner",
                "question_type": "technical",
                "answer_text": "Database query language.",
                "assistance_used": ["suggested_answer"],
            },
            headers=auth_headers,
        )

        assert sub_res.status_code == 200
        data = sub_res.json()
        assert data["raw_score"] == 2.0
        assert data["total_penalty"] == 3.0
        assert data["adjusted_score"] == 0.0
        assert data["score"] == 0.0


def test_next_question_endpoint(client, auth_headers):
    """Test generating dynamic next question for project deep-dive."""
    sess_res = client.post(
        "/api/v1/interview/sessions",
        json={"mode": "project_deep_dive"},
        headers=auth_headers,
    )
    session_id = sess_res.json()["session_id"]

    with patch("app.routers.interview.AdaptiveQuestionService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_instance.generate_next_question.return_value = InterviewQuestion(
            category="Project Deep Dive",
            difficulty="Intermediate",
            question="How did you handle model latency in your Spam Detector project?",
            question_type="project",
        )
        mock_service_cls.return_value = mock_instance

        next_res = client.post(
            f"/api/v1/interview/sessions/{session_id}/next-question",
            json={
                "current_index": 1,
                "projects": ["Email Spam Detection System"],
                "skills": ["Python", "Machine Learning"],
            },
            headers=auth_headers,
        )

        assert next_res.status_code == 200
        data = next_res.json()
        assert data["index"] == 1
        assert data["category"] == "Project Deep Dive"
        assert "Spam Detector" in data["question"]


def test_adaptive_weak_answer():
    """TEST 1 — WEAK ANSWER: Score < 5 stays on topic, Beginner difficulty, easier question."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="How did you implement the classification model for Email Spam Detection?",
        question_category="Email Spam Detection",
        question_difficulty="Intermediate",
        question_type="project",
        answer_text="I just used some code online.",
        raw_score=3.0,
        score=3.0,
        technical_accuracy="Vague and incomplete.",
        feedback="Lacks basic technical detail.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="Email Spam Detection",
            difficulty="Beginner",
            question="What is the basic purpose of an email spam detection system?",
            question_type="project",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Email Spam Detection", "Placement Data Analysis"],
            skills=["Python", "Scikit-Learn"],
            current_index=6,
        )

        assert res.category == "Email Spam Detection"
        assert res.difficulty == "Beginner"
        call_kwargs = mock_complete.call_args.kwargs
        assert "WEAKER" in call_kwargs["user_prompt"]
        assert "Email Spam Detection" in call_kwargs["user_prompt"]
        assert "Placement Data Analysis" not in call_kwargs["user_prompt"].split("PREVIOUS TOPIC:\n")[1].split("\n\n")[0]


def test_adaptive_strong_answer():
    """TEST 2 — STRONG ANSWER: Score >= 8 stays on topic, Intermediate/Advanced difficulty, deeper question."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="Explain how the React Virtual DOM works.",
        question_category="React Virtual DOM",
        question_difficulty="Intermediate",
        question_type="technical",
        answer_text="Virtual DOM is an in-memory representation of real DOM elements. React uses diffing to compute minimal updates.",
        raw_score=8.5,
        score=8.5,
        technical_accuracy="Clear and precise explanation.",
        feedback="Excellent answer.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="React Virtual DOM",
            difficulty="Advanced",
            question="How does Fiber architecture improve rendering performance during diffing?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Dashboard App"],
            skills=["React", "TypeScript"],
            current_index=6,
        )

        assert res.category == "React Virtual DOM"
        assert res.difficulty in ["Intermediate", "Advanced"]
        call_kwargs = mock_complete.call_args.kwargs
        assert "DEEPER" in call_kwargs["user_prompt"]
        assert "React Virtual DOM" in call_kwargs["user_prompt"]


def test_adaptive_medium_answer():
    """TEST 3 — MEDIUM ANSWER: Score 5-7 allows normal progression."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What are HTTP status codes in REST APIs?",
        question_category="REST API",
        question_difficulty="Beginner",
        question_type="technical",
        answer_text="200 means ok, 404 is not found, 500 is server error.",
        raw_score=7.0,
        score=7.0,
        technical_accuracy="Correct basic codes.",
        feedback="Good basic answer.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="REST API",
            difficulty="Intermediate",
            question="How do HTTP verbs like PUT and PATCH differ when updating API resources?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Backend API"],
            skills=["REST API"],
            current_index=6,
        )

        assert res.category == "REST API"
        call_kwargs = mock_complete.call_args.kwargs
        assert "MEDIUM" in call_kwargs["user_prompt"]


def test_adaptive_project_weak_answer():
    """TEST 4 — PROJECT WEAK ANSWER: Must not switch to another project on weak answer."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What features did you extract for your Email Spam Detection project?",
        question_category="Project",
        question_difficulty="Intermediate",
        question_type="project",
        answer_text="I used text features.",
        raw_score=3.0,
        score=3.0,
        technical_accuracy="Too generic.",
        feedback="Did not explain TF-IDF or tokenization.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="Email Spam Detection",
            difficulty="Beginner",
            question="What is spam in an email and how do simple word counts help identify it?",
            question_type="project",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Email Spam Detection", "Placement Data Analysis"],
            skills=["Python", "Pandas"],
            current_index=6,
        )

        assert "Email Spam Detection" in res.category or res.category == "Email Spam Detection"
        assert res.difficulty == "Beginner"
        call_kwargs = mock_complete.call_args.kwargs
        assert "WEAKER" in call_kwargs["user_prompt"]
        assert "Email Spam Detection" in call_kwargs["user_prompt"]


def test_adaptive_regression_react_typescript_weak_answer():
    """REGRESSION TEST: Weak answer (2.3/10) on React+TypeScript reusable button component MUST NOT jump to Express.js/GET endpoint."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="How do you build a reusable Button component in React using TypeScript with props for label and onClick?",
        question_category="React Component Design",
        question_difficulty="Intermediate",
        question_type="technical",
        answer_text="I don't know props or typescript syntax for buttons.",
        raw_score=2.3,
        score=2.3,
        technical_accuracy="Failed to define React props interface or onClick handler.",
        feedback="Incomplete answer lacking basic React component knowledge.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="React + TypeScript",
            difficulty="Beginner",
            question="What is the basic purpose of props in a React Button component?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["E-Commerce UI", "User Management API"],
            skills=["React", "TypeScript", "Express.js", "Node.js", "PostgreSQL"],
            current_index=6,
        )

        # 1. Assert difficulty for weak-answer follow-up is Beginner
        assert res.difficulty == "Beginner"

        # 2. Assert generated question and category remain related to React/TypeScript button component
        assert any(
            kw in res.question.lower() or kw in res.category.lower()
            for kw in ["react", "typescript", "button", "props", "component"]
        )

        # 3. Assert generated question does NOT jump to Express.js, REST API, Node.js, GET endpoints, or database APIs
        forbidden_terms = ["express", "express.js", "node", "node.js", "rest", "get endpoint", "database", "json list"]
        for term in forbidden_terms:
            assert term not in res.question.lower(), f"Generated question incorrectly jumped to '{term}': {res.question}"
            assert term not in res.category.lower(), f"Generated category incorrectly jumped to '{term}': {res.category}"

        # 4. Assert user prompt passed to LLM explicitly locked topic to React + TypeScript and prohibited Express/Node jumps
        call_kwargs = mock_complete.call_args.kwargs
        assert "WEAKER" in call_kwargs["user_prompt"]
        assert "React" in call_kwargs["user_prompt"]
        assert "STRICT PROHIBITION" in call_kwargs["user_prompt"]


def test_adaptive_regression_react_usestate_weak_answer():
    """REGRESSION TEST: Weak answer (2.7/10) on React useState MUST NOT jump to TypeScript generics or Express/REST APIs."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="Can you explain how state is managed within a functional React component and demonstrate updating state with the useState hook?",
        question_category="React State Management",
        question_difficulty="Intermediate",
        question_type="technical",
        answer_text="State is stored in variables. I don't remember useState syntax.",
        raw_score=2.7,
        score=2.7,
        technical_accuracy="Vague answer missing useState syntax and functional component state lifecycle.",
        feedback="Weak response lacking basic React useState understanding.",
    )

    # 1. Test fallback rejection when LLM attempts to output the exact observed failure (TypeScript generics)
    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="TypeScript",
            difficulty="Advanced",
            question="How would you define a reusable generic type for a function that takes an array of items and returns a promise of the same array type?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["E-Commerce Frontend"],
            skills=["React", "TypeScript", "Express.js", "Node.js", "PostgreSQL"],
            current_index=6,
        )

        # Assert difficulty is Beginner
        assert res.difficulty == "Beginner"

        # Assert question remains related to React/useState/state management
        assert any(
            kw in res.question.lower() or kw in res.category.lower()
            for kw in ["react", "usestate", "state"]
        )

        # Assert question does NOT contain unrelated topics from failure report
        forbidden_terms = [
            "typescript generics",
            "promise generic",
            "generic type",
            "express",
            "express.js",
            "node",
            "node.js",
            "rest api",
            "get endpoint",
            "database",
        ]
        for term in forbidden_terms:
            assert term not in res.question.lower(), f"Question jumped to forbidden term '{term}': {res.question}"
            assert term not in res.category.lower(), f"Category jumped to forbidden term '{term}': {res.category}"

    # 2. Test prompt directive when LLM returns valid on-topic question
    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="React State Management",
            difficulty="Beginner",
            question="What is the basic purpose of the useState hook in a React component?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["E-Commerce Frontend"],
            skills=["React", "TypeScript", "Express.js"],
            current_index=6,
        )

        assert res.difficulty == "Beginner"
        assert "react" in res.question.lower() or "usestate" in res.question.lower() or "state" in res.question.lower()

        call_kwargs = mock_complete.call_args.kwargs
        assert "WEAKER" in call_kwargs["user_prompt"]
        assert "React" in call_kwargs["user_prompt"]
        assert "STRICT PROHIBITION" in call_kwargs["user_prompt"]


def test_adaptive_regression_css_weak_answer_cannot_jump_to_react_typescript():
    """REGRESSION TEST: Weak answer (2.7/10) on CSS box model / Flexbox / Grid MUST NOT jump to React/TypeScript."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="Explain the CSS box model and how you would create a responsive layout using Flexbox or Grid.",
        question_category="Frontend / CSS",
        question_difficulty="Intermediate",
        question_type="technical",
        answer_text="The box model is about the size of an element. Flexbox and Grid are used to make websites responsive.",
        raw_score=2.7,
        score=2.7,
        technical_accuracy="Very weak and superficial answer omitting box-sizing, padding, margin, border, flex container, and grid layout concepts.",
        feedback="Lacks basic technical understanding of CSS box model properties and layout mechanics.",
    )

    # 1. Test fallback rejection when LLM generates off-topic React + TypeScript question
    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="React / TypeScript",
            difficulty="Intermediate",
            question="What are the benefits of using TypeScript with React, and how do you define prop types for a functional component?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["E-Commerce UI", "Portfolio Site"],
            skills=["CSS", "HTML", "React", "TypeScript", "Express.js"],
            current_index=6,
        )

        # Result MUST be rejected as off-topic and use topic-locked fallback
        assert res.difficulty == "Beginner"
        assert any(
            kw in res.question.lower() or kw in res.category.lower()
            for kw in ["css", "box model", "flexbox", "grid", "layout", "margin", "padding"]
        )

        # Result MUST NOT switch to React or TypeScript
        assert "react" not in res.question.lower()
        assert "typescript" not in res.question.lower()
        assert "express" not in res.question.lower()

    # 2. Test valid on-topic LLM response
    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="CSS Box Model",
            difficulty="Beginner",
            question="What are the four main parts of the CSS box model?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["E-Commerce UI"],
            skills=["CSS", "React", "TypeScript"],
            current_index=6,
        )

        assert res.difficulty == "Beginner"
        assert "box model" in res.question.lower() or "css" in res.question.lower()


def test_adaptive_regression_express_weak_answer():
    """REGRESSION TEST: Weak answer (2.5/10) on Express GET endpoint MUST NOT jump to React props."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="Describe how you would set up a simple GET endpoint using Express.js that returns a JSON list of users.",
        question_category="Express.js",
        question_difficulty="Intermediate",
        question_type="technical",
        answer_text="You write app.get and send data.",
        raw_score=2.5,
        score=2.5,
        technical_accuracy="Superficial explanation missing req/res params, app.get syntax, and res.json call.",
        feedback="Lacks fundamental Express endpoint routing details.",
    )

    # 1. Test fallback rejection when LLM outputs React props question
    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="React",
            difficulty="Beginner",
            question="How do you pass props in a React functional component?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Backend API", "React Dashboard"],
            skills=["Express.js", "Node.js", "React", "TypeScript"],
            current_index=6,
        )

        assert res.difficulty == "Beginner"
        assert any(
            kw in res.question.lower() or kw in res.category.lower()
            for kw in ["express", "get", "endpoint", "http", "api", "routing"]
        )
        assert "react" not in res.question.lower()
        assert "props" not in res.question.lower()


def test_adaptive_single_strong_answer_gradual_scaling():
    """FRESHER-FIRST TEST: Single strong answer (8.5/10) MUST scale difficulty gradually (Intermediate) without jumping to Advanced exam questions."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What is the CSS box model?",
        question_category="CSS",
        question_difficulty="Beginner",
        question_type="technical",
        answer_text="The CSS box model consists of content, padding, border, and margin surrounding every element.",
        raw_score=8.5,
        score=8.5,
        technical_accuracy="Accurate definition of all four box model components.",
        feedback="Great answer.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="CSS",
            difficulty="Intermediate",
            question="What is the difference between content-box and border-box sizing in CSS?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Portfolio Site"],
            skills=["CSS", "HTML"],
            current_index=6,
        )

        assert res.difficulty == "Intermediate"
        call_kwargs = mock_complete.call_args.kwargs
        assert "SINGLE_STRONG" in call_kwargs["user_prompt"]
        assert "Intermediate" in call_kwargs["user_prompt"]


def test_adaptive_repeated_strong_answers_scaling():
    """FRESHER-FIRST TEST: Repeated strong answers (2+ consecutive >= 8.0) allow deeper technical follow-up."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    ans1 = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What is the CSS box model?",
        question_category="CSS",
        question_difficulty="Beginner",
        question_type="technical",
        answer_text="Content, padding, border, and margin.",
        raw_score=8.5,
        score=8.5,
        technical_accuracy="Accurate.",
        feedback="Good.",
    )
    ans2 = SessionAnswer(
        id=2,
        session_id=1,
        question_text="What is the difference between content-box and border-box in CSS?",
        question_category="CSS",
        question_difficulty="Intermediate",
        question_type="technical",
        answer_text="Border-box includes padding and border in the element's total width and height, whereas content-box adds them on top.",
        raw_score=9.0,
        score=9.0,
        technical_accuracy="Excellent precise explanation.",
        feedback="Outstanding answer.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        mock_complete.return_value = InterviewQuestion(
            category="CSS Layout",
            difficulty="Intermediate",
            question="When would you choose CSS Grid over Flexbox for a complex web application layout?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[ans1, ans2],
            projects=["Portfolio Site"],
            skills=["CSS", "HTML"],
            current_index=6,
        )

        assert res.difficulty in ["Intermediate", "Advanced"]
        call_kwargs = mock_complete.call_args.kwargs
        assert "REPEATED_STRONG" in call_kwargs["user_prompt"]


def test_adaptive_resume_grounding_rejects_unlisted_skills():
    """RESUME GROUNDING TEST: Must reject questions introducing major ungrounded tech (React) when not present in resume or history."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What is the difference between a list and a tuple in Python?",
        question_category="Python",
        question_difficulty="Beginner",
        question_type="technical",
        answer_text="Lists are mutable and tuples are immutable.",
        raw_score=7.5,
        score=7.5,
        technical_accuracy="Correct distinction.",
        feedback="Good answer.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        # LLM attempts to generate ungrounded React hooks question for candidate with only Python/Java/HTML/CSS
        mock_complete.return_value = InterviewQuestion(
            category="React",
            difficulty="Intermediate",
            question="Can you explain how React hooks work under the hood?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Placement Data Analysis"],
            skills=["Python", "Java", "HTML", "CSS"],
            current_index=6,
        )

        # React question MUST be rejected as ungrounded and fallback used
        assert "react" not in res.question.lower()
        assert "react" not in res.category.lower()


def test_adaptive_overly_complex_question_rejection():
    """OVERLY COMPLEX QUESTION TEST: Must reject specification-exam style questions and fallback to practical fresher questions."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What is CSS Flexbox?",
        question_category="CSS",
        question_difficulty="Beginner",
        question_type="technical",
        answer_text="Flexbox is used for layout.",
        raw_score=7.0,
        score=7.0,
        technical_accuracy="Basic idea.",
        feedback="Good start.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        # LLM outputs an overly complex specification exam question
        mock_complete.return_value = InterviewQuestion(
            category="CSS",
            difficulty="Advanced",
            question="Calculate step-by-step how the browser determines the final rendered width of each Flexbox item according to the Flexbox specification given a container of 800px.",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Portfolio"],
            skills=["CSS", "HTML"],
            current_index=6,
        )

        # Exam question MUST be rejected
        assert "calculate step-by-step" not in res.question.lower()
        assert res.difficulty == "Intermediate"


def test_adaptive_multi_part_question_rejection():
    """MULTI-PART TASK TEST: Must reject questions combining multiple independent tasks into a single turn."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What is CSS Flexbox?",
        question_category="CSS",
        question_difficulty="Beginner",
        question_type="technical",
        answer_text="It is used for layout.",
        raw_score=7.0,
        score=7.0,
        technical_accuracy="Basic idea.",
        feedback="Good start.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        # LLM outputs a multi-part question combining 3 independent tasks
        mock_complete.return_value = InterviewQuestion(
            category="CSS",
            difficulty="Intermediate",
            question="What is Flexbox, and how does flex-grow work, and why would you choose Flexbox over Grid?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Portfolio"],
            skills=["CSS", "HTML"],
            current_index=6,
        )

        # Multi-part combined task question MUST be rejected
        assert "and how does flex-grow work" not in res.question.lower()
        assert len(res.question.split()) <= 20


def test_adaptive_candidate_introduced_skill_becomes_valid_context():
    """CANDIDATE-INTRODUCED SKILL TEST: If candidate mentions a technology in their answer, it becomes valid context."""
    from app.config import Settings
    from app.db.models.session_answer import SessionAnswer
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)

    prev_answer = SessionAnswer(
        id=1,
        session_id=1,
        question_text="What technologies did you use in your project?",
        question_category="Projects",
        question_difficulty="Beginner",
        question_type="project",
        answer_text="I used Python for backend and PostgreSQL for the database.",
        raw_score=8.0,
        score=8.0,
        technical_accuracy="Clear technology list.",
        feedback="Good answer.",
    )

    with patch.object(service._llm, "complete_json") as mock_complete:
        # Candidate introduced PostgreSQL in answer, so PostgreSQL question should be ALLOWED
        mock_complete.return_value = InterviewQuestion(
            category="PostgreSQL",
            difficulty="Intermediate",
            question="Why did you choose PostgreSQL over other databases for your project?",
            question_type="technical",
        )

        res = service.generate_next_question(
            mode="adaptive",
            previous_answers=[prev_answer],
            projects=["Placement Prediction"],
            skills=["Python", "HTML", "CSS"],  # PostgreSQL not in resume skills, but in candidate's answer
            current_index=6,
        )

        # PostgreSQL question should be accepted because candidate explicitly introduced it in their answer
        assert "postgresql" in res.question.lower() or "postgresql" in res.category.lower()


def test_adaptive_short_fallback_questions():
    """SHORT FALLBACK TEST: Fallback questions must be short, clear, 1-sentence questions."""
    from app.services.adaptive_question_service import _generate_safe_fallback

    # Weak answer fallback
    fb1 = _generate_safe_fallback("CSS box model", "What is CSS box model?", 3.0, [])
    assert len(fb1.question.split()) <= 15
    assert fb1.difficulty == "Beginner"

    # Single strong answer fallback
    fb2 = _generate_safe_fallback("React useState", "What is useState?", 8.5, [], consecutive_strong_count=1)
    assert len(fb2.question.split()) <= 20
    assert fb2.difficulty == "Intermediate"


def test_fresher_first_initial_interview_flow_sequence():
    """TEST INITIAL FLOW: Verify Q1 Intro -> Q2 Education -> Q3 Skills -> Q4 Basic Tech -> Q5 Project -> Q6 Follow-up."""
    from app.config import Settings
    from app.services.adaptive_question_service import AdaptiveQuestionService

    settings = Settings()
    service = AdaptiveQuestionService(settings)
    projects = ["Placement Data Analysis"]
    skills = ["Python", "Java", "HTML", "CSS", "React"]

    # 1. Turn 0 (Q1): Introduction
    q1 = service.generate_next_question(
        mode="standard",
        previous_answers=[],
        projects=projects,
        skills=skills,
        current_index=0,
    )
    assert q1.question_type == "hr"
    assert "tell me about yourself" in q1.question.lower() or "introduce" in q1.question.lower()

    # 2. Turn 1 (Q2): Education
    q2 = service.generate_next_question(
        mode="standard",
        previous_answers=[],
        projects=projects,
        skills=skills,
        current_index=1,
    )
    assert q2.question_type == "hr"
    assert "education" in q2.question.lower() or "studying" in q2.question.lower()

    # 3. Turn 2 (Q3): Skills
    q3 = service.generate_next_question(
        mode="standard",
        previous_answers=[],
        projects=projects,
        skills=skills,
        current_index=2,
    )
    assert "skill" in q3.question.lower() or "language" in q3.question.lower() or "technology" in q3.question.lower()

    # 4. Turn 3 (Q4): Basic Technical Fundamental
    q4 = service.generate_next_question(
        mode="standard",
        previous_answers=[],
        projects=projects,
        skills=skills,
        current_index=3,
    )
    assert q4.question_type == "technical"
    assert q4.difficulty == "Beginner"
    # Must NOT start with advanced React hooks / useState / TypeScript generics / performance / internals
    forbidden_initial = ["usestate", "generics", "rendering pipeline", "flex-basis", "scalability", "trade-offs"]
    for term in forbidden_initial:
        assert term not in q4.question.lower()

    # 5. Turn 4 (Q5): Project Question
    q5 = service.generate_next_question(
        mode="standard",
        previous_answers=[],
        projects=projects,
        skills=skills,
        current_index=4,
    )
    assert q5.question_type == "project"
    assert "project" in q5.question.lower() or "placement data analysis" in q5.question.lower()

    # 6. Turn 5 (Q6): Practical Follow-up
    q6 = service.generate_next_question(
        mode="standard",
        previous_answers=[],
        projects=projects,
        skills=skills,
        current_index=5,
    )
    assert q6.difficulty in ["Beginner", "Intermediate"]
    assert len(q6.question.split()) <= 35








