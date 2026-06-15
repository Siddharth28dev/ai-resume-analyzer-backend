import re
from app.utils.constants import SECTION_HEADERS


def clean_text(text: str) -> str:
    """Remove noise from raw extracted text."""
    # Collapse multiple spaces / tabs
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines into two
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def normalize_text(text: str) -> str:
    """Lowercase + strip punctuation for skill matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s\.\+\#]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_email(text: str) -> str | None:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w{2,}", text)
    return match.group(0).lower() if match else None


def extract_phone(text: str) -> str | None:
    # Matches Indian (+91) and general formats
    match = re.search(
        r"(\+91[\s\-]?)?[6-9]\d{9}|(\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}",
        text,
    )
    return match.group(0).strip() if match else None


def extract_linkedin(text: str) -> str | None:
    match = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    return match.group(0).lower() if match else None


def extract_github(text: str) -> str | None:
    match = re.search(r"github\.com/[\w\-]+", text, re.IGNORECASE)
    return match.group(0).lower() if match else None


def split_into_sections(text: str) -> dict:
    """
    Heuristically split resume text into labelled sections.
    Returns a dict like: { "education": "...", "skills": "...", ... }
    """
    sections = {key: "" for key in SECTION_HEADERS}
    sections["other"] = ""

    lines = text.splitlines()
    current_section = "other"

    for line in lines:
        lower = line.lower().strip()
        matched = False
        for section, keywords in SECTION_HEADERS.items():
            if any(kw in lower for kw in keywords) and len(lower) < 50:
                current_section = section
                matched = True
                break
        if not matched:
            sections[current_section] += line + "\n"

    return {k: v.strip() for k, v in sections.items()}
