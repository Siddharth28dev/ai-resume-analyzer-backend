from app.services.question_service import generate_interview_questions
from app.services.evaluation_service import evaluate_answer, evaluate_multiple_answers


def handle_generate_questions(data: dict) -> tuple[dict, int]:
    job_role           = data.get("job_role", "").strip()
    resume_text        = data.get("resume_text", "").strip()
    skill_gaps         = data.get("skill_gaps", [])
    matched_skills     = data.get("matched_skills", [])
    experience_level   = data.get("experience_level", "fresher")
    questions_per_type = int(data.get("questions_per_type", 3))

    if not job_role:
        return {"success": False, "error": "job_role is required"}, 400
    if not resume_text:
        return {"success": False, "error": "resume_text is required"}, 400

    try:
        result = generate_interview_questions(
            job_role=job_role,
            resume_text=resume_text,
            skill_gaps=skill_gaps,
            matched_skills=matched_skills,
            experience_level=experience_level,
            questions_per_type=questions_per_type,
        )
        return {"success": True, "data": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_evaluate_answer(data: dict) -> tuple[dict, int]:
    """Evaluate a single candidate answer."""
    question         = data.get("question", "").strip()
    candidate_answer = data.get("candidate_answer", "").strip()
    question_type    = data.get("question_type", "technical")
    skill            = data.get("skill", "")
    job_role         = data.get("job_role", "")

    if not question:
        return {"success": False, "error": "question is required"}, 400
    if not candidate_answer:
        return {"success": False, "error": "candidate_answer is required"}, 400

    try:
        result = evaluate_answer(
            question=question,
            candidate_answer=candidate_answer,
            question_type=question_type,
            skill=skill,
            job_role=job_role,
        )
        return {"success": True, "evaluation": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_evaluate_multiple(data: dict) -> tuple[dict, int]:
    """Evaluate multiple answers at once."""
    answers = data.get("answers", [])

    if not answers or not isinstance(answers, list):
        return {"success": False, "error": "answers must be a non-empty list"}, 400

    try:
        result = evaluate_multiple_answers(answers)
        return {"success": True, "evaluation": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500