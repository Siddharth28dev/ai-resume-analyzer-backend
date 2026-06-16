from flask import Blueprint, request, jsonify
from app.controllers.feedback_controller import (
    handle_generate_feedback,
    handle_generate_todo,
    handle_delete_user_data,
)

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/generate", methods=["POST"])
def generate_feedback():
    """
    POST /api/feedback/generate
    Synthesize feedback from all 3 sources.
    Body: {
        resume_data:    parsed resume output,
        skill_gap_data: similarity service output,
        interview_data: evaluation service output (optional),
        job_role:       string
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_generate_feedback(data)
    return jsonify(result), status


@feedback_bp.route("/todo", methods=["POST"])
def generate_todo():
    """
    POST /api/feedback/todo
    Generate prioritized to-do list.
    Body: {
        resume_feedback:    feedback section output,
        skill_gap_data:     similarity service output,
        interview_feedback: interview section output,
        job_role:           string
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_generate_todo(data)
    return jsonify(result), status


@feedback_bp.route("/delete-account", methods=["DELETE"])
def delete_user_data():
    """
    DELETE /api/feedback/delete-account
    Paper: "Candidates retain ownership of their information
            and can request deletion at any time."
    Body: { user_id: int }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_delete_user_data(data)
    return jsonify(result), status


@feedback_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Feedback service is up"}), 200
