from app.services.feedback_service import generate_feedback
from app.services.todo_service     import generate_todo_list


def handle_generate_feedback(data: dict) -> tuple[dict, int]:
    """
    Synthesize complete feedback report from 3 sources.
    """
    resume_data    = data.get("resume_data",    {})
    skill_gap_data = data.get("skill_gap_data", {})
    interview_data = data.get("interview_data", {})
    job_role       = data.get("job_role", "")

    if not resume_data:
        return {"success": False, "error": "resume_data is required"}, 400
    if not skill_gap_data:
        return {"success": False, "error": "skill_gap_data is required"}, 400

    try:
        feedback = generate_feedback(
            resume_data    = resume_data,
            skill_gap_data = skill_gap_data,
            interview_data = interview_data,
        )

        # Auto-generate todo list along with feedback
        todos = generate_todo_list(
            resume_feedback    = feedback["resume_section"],
            skill_gap_data     = skill_gap_data,
            interview_feedback = feedback["interview_section"],
            job_role           = job_role,
        )

        return {
            "success":  True,
            "feedback": feedback,
            "todo_list": todos,
            "todo_count": len(todos),
        }, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_generate_todo(data: dict) -> tuple[dict, int]:
    """
    Generate to-do list independently.
    """
    resume_feedback    = data.get("resume_feedback",    {})
    skill_gap_data     = data.get("skill_gap_data",     {})
    interview_feedback = data.get("interview_feedback", {})
    job_role           = data.get("job_role", "")

    if not skill_gap_data:
        return {"success": False, "error": "skill_gap_data is required"}, 400

    try:
        todos = generate_todo_list(
            resume_feedback    = resume_feedback,
            skill_gap_data     = skill_gap_data,
            interview_feedback = interview_feedback,
            job_role           = job_role,
        )
        return {
            "success":    True,
            "todo_list":  todos,
            "todo_count": len(todos),
        }, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_delete_user_data(data: dict) -> tuple[dict, int]:
    """
    Paper: "Candidates retain ownership of their information
            and can request deletion at any time."
    Deletes all data associated with a user_id.
    Note: Requires DB session — connect to your DB in production.
    """
    user_id = data.get("user_id")

    if not user_id:
        return {"success": False, "error": "user_id is required"}, 400

    try:
        # Import here to avoid circular imports
        from app.extensions import db
        from app.models     import User

        user = db.session.get(User, user_id)
        if not user:
            return {"success": False, "error": f"User {user_id} not found"}, 404

        # Cascade delete handles all related records:
        # resumes → resume_skills, skill_gaps, interview_sessions
        # interview_sessions → questions → responses → evaluations
        # interview_sessions → feedback_reports → todo_items
        db.session.delete(user)
        db.session.commit()

        return {
            "success": True,
            "message": f"All data for user {user_id} has been permanently deleted.",
        }, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500
