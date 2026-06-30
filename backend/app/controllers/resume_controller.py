from flask import current_app
from app.utils.file_handler import allowed_file, save_upload, extract_text_from_file
from app.utils.text_cleaner import clean_text
from app.services.parser_service import parse_resume
from app.schemas.resume_schema import ParsedResumeSchema


def handle_resume_upload(file, job_role: str | None) -> tuple[dict, int]:
    if not file or file.filename == "":
        return {"success": False, "error": "No file provided"}, 400

    if not allowed_file(file.filename):
        return {"success": False, "error": "Invalid file type. Allowed: pdf, docx, txt"}, 400

    try:
        upload_info = save_upload(file, current_app.config["UPLOAD_FOLDER"])
    except Exception as e:
        return {"success": False, "error": f"File save failed: {str(e)}"}, 500

    try:
        raw_text = extract_text_from_file(
            upload_info["filepath"], upload_info["extension"]
        )
    except Exception as e:
        return {"success": False, "error": f"Text extraction failed: {str(e)}"}, 422

    if not raw_text.strip():
        return {"success": False, "error": "Could not extract text from file"}, 422

    try:
        parsed = parse_resume(raw_text)
    except Exception as e:
        return {"success": False, "error": f"NLP parsing failed: {str(e)}"}, 500

    schema     = ParsedResumeSchema()
    serialized = schema.dump(parsed)

    return {
        "success":    True,
        "file_info": {
            "original_name": upload_info["original_name"],
            "extension":     upload_info["extension"],
        },
        "job_role":    job_role,
        "parsed_data": serialized,
        "parsed_text": raw_text,   # ← FIXED: was raw_text, frontend expects parsed_text
        "skills":      serialized.get("skills", {}),       # ← direct access for frontend
        "experience":  serialized.get("experience", {}),   # ← direct access for frontend
    }, 200


def handle_get_parsed_text(file, job_role: str | None) -> tuple[dict, int]:
    if not file or file.filename == "":
        return {"success": False, "error": "No file provided"}, 400

    if not allowed_file(file.filename):
        return {"success": False, "error": "Invalid file type"}, 400

    try:
        upload_info = save_upload(file, current_app.config["UPLOAD_FOLDER"])
        raw_text    = extract_text_from_file(
            upload_info["filepath"], upload_info["extension"]
        )
        cleaned     = clean_text(raw_text)
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

    return {"success": True, "raw_text": cleaned}, 200