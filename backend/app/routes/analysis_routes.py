from flask import Blueprint, request, jsonify
from app.controllers.analysis_controller import (
    handle_skill_gap,
    handle_similarity,
)

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/skill-gap", methods=["POST"])
def skill_gap():
    """
    POST /api/analysis/skill-gap
    Full semantic skill gap analysis (MiniLM powered).
    Body: { jd_text, resume_text, resume_skills, experience_level? }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_skill_gap(data)
    return jsonify(result), status


@analysis_bp.route("/similarity", methods=["POST"])
def similarity():
    """
    POST /api/analysis/similarity
    Quick JD vs resume semantic similarity score.
    Body: { jd_text, resume_text }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_similarity(data)
    return jsonify(result), status


@analysis_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Analysis service is up"}), 200
