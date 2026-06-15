import os
import uuid
import pdfplumber
import docx
from werkzeug.utils import secure_filename
from app.utils.constants import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_upload(file, upload_folder: str) -> dict:
    """
    Saves an uploaded FileStorage object to disk.
    Returns { filename, filepath, extension }.
    """
    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, unique_name)
    file.save(filepath)
    return {
        "original_name": original_name,
        "saved_name": unique_name,
        "filepath": filepath,
        "extension": ext,
    }


def extract_text_from_file(filepath: str, extension: str) -> str:
    """
    Extract raw text from PDF, DOCX, or TXT.
    Raises ValueError for unsupported formats.
    """
    if extension == "pdf":
        return _extract_pdf(filepath)
    elif extension == "docx":
        return _extract_docx(filepath)
    elif extension == "txt":
        return _extract_txt(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {extension}")


# ── private helpers ────────────────────────────────────────────────────────────

def _extract_pdf(filepath: str) -> str:
    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx(filepath: str) -> str:
    doc = docx.Document(filepath)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def _extract_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
