from app.services.similarity_service import (
    analyze,
    jd_resume_score,
)


def handle_skill_gap(data: dict) -> tuple[dict, int]:
    """
    POST /api/analysis/skill-gap
    Body: { jd_text, resume_text, resume_skills, experience_level? }
    Uses MiniLM semantic matching — no keyword matching.
    """
    jd_text          = data.get("jd_text", "").strip()
    resume_text      = data.get("resume_text", "").strip()
    resume_skills    = data.get("resume_skills", [])
    experience_level = data.get("experience_level", None)

    if not jd_text:
        return {"success": False, "error": "jd_text is required"}, 400
    if not resume_text:
        return {"success": False, "error": "resume_text is required"}, 400
    if not resume_skills or not isinstance(resume_skills, list):
        return {"success": False, "error": "resume_skills must be a non-empty list"}, 400

    try:
        result = analyze(jd_text, resume_text, resume_skills, experience_level)
        return {"success": True, "analysis": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_similarity(data: dict) -> tuple[dict, int]:
    """
    POST /api/analysis/similarity
    Body: { jd_text, resume_text }
    Quick overall semantic similarity score.
    """
    jd_text     = data.get("jd_text", "").strip()
    resume_text = data.get("resume_text", "").strip()

    if not jd_text or not resume_text:
        return {"success": False, "error": "jd_text and resume_text are required"}, 400

    try:
        result = jd_resume_score(jd_text, resume_text)
        return {"success": True, "similarity": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500
