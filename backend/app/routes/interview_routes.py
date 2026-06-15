from flask import Blueprint, request, jsonify
from app.controllers.interview_controller import (
    handle_generate_questions,
    handle_evaluate_answer,
    handle_evaluate_multiple,
)

interview_bp = Blueprint("interview", __name__)


@interview_bp.route("/generate-questions", methods=["POST"])
def generate_questions():
    """
    POST /api/interview/generate-questions
    Body: { job_role, resume_text, skill_gaps, matched_skills,
            experience_level?, questions_per_type? }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_generate_questions(data)
    return jsonify(result), status


@interview_bp.route("/evaluate", methods=["POST"])
def evaluate():
    """
    POST /api/interview/evaluate
    Evaluate a single answer.
    Body: { question, candidate_answer, question_type, skill, job_role }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_evaluate_answer(data)
    return jsonify(result), status


@interview_bp.route("/evaluate-all", methods=["POST"])
def evaluate_all():
    """
    POST /api/interview/evaluate-all
    Evaluate all answers at once.
    Body: { answers: [ { question, candidate_answer, question_type, skill, job_role } ] }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_evaluate_multiple(data)
    return jsonify(result), status


@interview_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Interview service is up"}), 200