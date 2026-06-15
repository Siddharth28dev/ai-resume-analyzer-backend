from flask import Blueprint, request, jsonify
from app.controllers.resume_controller import (
    handle_resume_upload,
    handle_get_parsed_text,
)
from app.schemas.resume_schema import ResumeUploadSchema
from marshmallow import ValidationError

resume_bp = Blueprint("resume", __name__)
upload_schema = ResumeUploadSchema()


@resume_bp.route("/upload", methods=["POST"])
def upload_resume():
    """
    POST /api/resume/upload
    Form-data:
        file     : resume file  (pdf | docx | txt)
        job_role : string       (optional)

    Returns parsed resume JSON.
    """
    # Validate form fields
    try:
        form_data = upload_schema.load(request.form)
    except ValidationError as err:
        return jsonify({"success": False, "errors": err.messages}), 400

    file     = request.files.get("file")
    job_role = form_data.get("job_role")

    result, status = handle_resume_upload(file, job_role)
    return jsonify(result), status


@resume_bp.route("/extract-text", methods=["POST"])
def extract_text():
    """
    POST /api/resume/extract-text
    Returns only the cleaned raw text (debug endpoint).
    """
    file     = request.files.get("file")
    job_role = request.form.get("job_role")
    result, status = handle_get_parsed_text(file, job_role)
    return jsonify(result), status


@resume_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Resume service is up"}), 200
