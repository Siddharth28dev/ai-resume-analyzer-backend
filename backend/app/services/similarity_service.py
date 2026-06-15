"""
similarity_service.py
─────────────────────
Logic based on research paper:
  "AI-Based Resume Analyzer and Interview Simulator"

Flow:
  1. User uploads resume → parser_service extracts skills
  2. User pastes Job Description
  3. THIS SERVICE:
     a) Extracts required skills FROM the JD using MiniLM
     b) Computes semantic similarity: resume skills vs JD skills
     c) Returns match score + matched skills + missing skills + recommendations
"""

import json
import os
import re
import torch
from sentence_transformers import SentenceTransformer, util


# ── Model singleton ───────────────────────────────────────────────────────────

_model = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is not None:
        return _model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[MiniLM] Loading all-MiniLM-L6-v2 on {device}...")
    _model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    print(f"[MiniLM] Ready on {device}")
    return _model


# ── Job dataset singleton (only for job title lookup) ────────────────────────

_job_data = None

def _load_dataset():
    global _job_data
    if _job_data is not None:
        return
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "job_dataset.json")
    )
    with open(path, "r", encoding="utf-8") as f:
        _job_data = json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def analyze(
    jd_text: str,
    resume_text: str,
    resume_skills: list,
    experience_level: str = None,
) -> dict:
    """
    Core analysis as per research paper:

    Step 1: Extract skills required from JD text
    Step 2: Compute overall JD ↔ Resume semantic similarity
    Step 3: Match resume skills against JD-required skills semantically
    Step 4: Identify matched skills, missing skills, match score
    Step 5: Generate recommendations for missing skills
    """
    model = _get_model()

    # ── Step 1: Extract required skills from JD ───────────────────────────────
    jd_skills = _extract_skills_from_jd(jd_text, model)

    # ── Step 2: Overall semantic similarity (JD text vs Resume text) ─────────
    jd_emb     = model.encode(jd_text,     convert_to_tensor=True)
    resume_emb = model.encode(resume_text, convert_to_tensor=True)
    overall_sim = round(float(util.cos_sim(jd_emb, resume_emb)[0][0]) * 100, 1)

    # ── Step 3 & 4: Semantic skill matching ───────────────────────────────────
    match_result = _match_skills(resume_skills, jd_skills, model)

    # ── Step 5: Combined score ────────────────────────────────────────────────
    combined = round((overall_sim + match_result["skill_score"]) / 2, 1)

    # ── Step 6: Recommendations ───────────────────────────────────────────────
    recommendations = _build_recommendations(match_result["missing_skills"])

    return {
        "scores": {
            "overall_similarity": overall_sim,
            "skill_match_score":  match_result["skill_score"],
            "combined_score":     combined,
            "rating":             _rating(combined),
            "interpretation":     _interpretation(combined),
        },
        "jd_required_skills": sorted(jd_skills),
        "matched_skills":     match_result["matched"],
        "missing_skills":     match_result["missing_skills"],
        "semantic_pairs":     match_result["pairs"],
        "recommendations":    recommendations,
        "total_required":     len(jd_skills),
        "total_matched":      len(match_result["matched"]),
        "total_missing":      len(match_result["missing_skills"]),
    }


def jd_resume_score(jd_text: str, resume_text: str) -> dict:
    """Quick overall semantic similarity score."""
    model      = _get_model()
    jd_emb     = model.encode(jd_text,     convert_to_tensor=True)
    resume_emb = model.encode(resume_text, convert_to_tensor=True)
    score      = round(float(util.cos_sim(jd_emb, resume_emb)[0][0]) * 100, 1)
    return {
        "similarity_score": score,
        "rating":           _rating(score),
        "interpretation":   _interpretation(score),
    }


def get_all_job_titles() -> list:
    _load_dataset()
    seen, result = set(), []
    for e in _job_data:
        key = f"{e.get('Title','')}|{e.get('ExperienceLevel','')}"
        if key not in seen:
            seen.add(key)
            result.append({
                "title":            e.get("Title", ""),
                "experience_level": e.get("ExperienceLevel", ""),
                "years":            e.get("YearsOfExperience", ""),
            })
    return sorted(result, key=lambda x: x["title"])


# ══════════════════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# Common technical skills vocabulary for JD extraction
TECH_SKILLS_VOCAB = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "golang",
    "kotlin", "swift", "ruby", "php", "bash", "shell", "r", "scala", "dart",
    # Web
    "html", "css", "react", "angular", "vue", "nextjs", "nodejs", "express",
    "tailwind", "bootstrap", "sass", "webpack", "vite", "jquery",
    # Backend
    "flask", "django", "fastapi", "spring", "laravel", "asp.net", "rails",
    # Databases
    "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
    "dynamodb", "elasticsearch", "firebase", "sql", "nosql",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "github",
    "linux", "ci/cd", "jenkins", "terraform", "ansible", "nginx",
    # ML/AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "transformers", "hugging face", "llm", "bert",
    # Concepts
    "rest api", "graphql", "microservices", "agile", "scrum",
    "oop", "data structures", "algorithms", "system design",
    "unit testing", "devops", "cloud computing",
    # Soft skills
    "communication", "teamwork", "problem solving", "leadership",
]


def _extract_skills_from_jd(jd_text: str, model) -> list:
    """
    Extract required skills from JD by:
    1. Encoding each skill in TECH_SKILLS_VOCAB
    2. Computing similarity with JD text sentences
    3. Keeping skills that are semantically present in the JD

    This is phrase-vs-phrase comparison (JD sentences vs skill names).
    """
    # Split JD into sentences/lines for better matching
    jd_sentences = [s.strip() for s in re.split(r'[\n.•\-\*]+', jd_text) if len(s.strip()) > 5]
    if not jd_sentences:
        jd_sentences = [jd_text]

    # Encode JD sentences and skill vocab
    jd_embs    = model.encode(jd_sentences,      convert_to_tensor=True, batch_size=64)
    skill_embs = model.encode(TECH_SKILLS_VOCAB, convert_to_tensor=True, batch_size=64)

    # For each skill, find max similarity across all JD sentences
    sim_matrix = util.cos_sim(skill_embs, jd_embs)  # (n_skills × n_sentences)

    extracted = []
    for i, skill in enumerate(TECH_SKILLS_VOCAB):
        max_score = float(sim_matrix[i].max())
        if max_score >= 0.50:   # skill is meaningfully present in JD
            extracted.append(skill)

    return extracted


def _match_skills(
    resume_skills: list,
    jd_skills: list,
    model,
    threshold: float = 0.60,
) -> dict:
    """
    Semantically match resume skills vs JD required skills.
    For each JD skill, find the best matching resume skill.
    If similarity >= threshold → matched, else → missing.
    """
    if not jd_skills:
        return {
            "matched": resume_skills, "missing_skills": [],
            "pairs": [], "skill_score": 100.0
        }
    if not resume_skills:
        return {
            "matched": [], "missing_skills": jd_skills,
            "pairs": [], "skill_score": 0.0
        }

    res_embs   = model.encode(resume_skills, convert_to_tensor=True)
    jd_embs    = model.encode(jd_skills,     convert_to_tensor=True)
    sim_matrix = util.cos_sim(jd_embs, res_embs)  # (n_jd × n_resume)

    matched, missing, pairs = [], [], []

    for i, jd_skill in enumerate(jd_skills):
        best_score     = float(sim_matrix[i].max())
        best_res_idx   = int(sim_matrix[i].argmax())
        best_res_skill = resume_skills[best_res_idx]

        if best_score >= threshold:
            matched.append(jd_skill)
            pairs.append({
                "required":     jd_skill,
                "matched_with": best_res_skill,
                "score":        round(best_score * 100, 1),
                "type":         "exact" if jd_skill == best_res_skill else "semantic",
            })
        else:
            missing.append(jd_skill)

    skill_score = round(len(matched) / len(jd_skills) * 100, 1)

    return {
        "matched":       sorted(matched),
        "missing_skills": sorted(missing),
        "pairs":         sorted(pairs, key=lambda x: -x["score"]),
        "skill_score":   skill_score,
    }


def _build_recommendations(missing_skills: list) -> list:
    resource_map = {
        "python":           ("https://docs.python.org/3/tutorial/",                   "Official Python Tutorial"),
        "java":             ("https://dev.java/learn/",                                "Oracle Java Tutorials"),
        "javascript":       ("https://javascript.info",                                "Modern JavaScript Tutorial"),
        "typescript":       ("https://www.typescriptlang.org/docs/",                  "TypeScript Docs"),
        "react":            ("https://react.dev/learn",                                "React Official Docs"),
        "nodejs":           ("https://nodejs.org/en/learn",                            "Node.js Docs"),
        "express":          ("https://expressjs.com",                                  "Express.js Guide"),
        "flask":            ("https://flask.palletsprojects.com/tutorial/",            "Flask Tutorial"),
        "django":           ("https://docs.djangoproject.com/intro/tutorial01/",      "Django Tutorial"),
        "fastapi":          ("https://fastapi.tiangolo.com/tutorial/",                "FastAPI Tutorial"),
        "postgresql":       ("https://www.postgresql.org/docs/current/tutorial.html", "PostgreSQL Tutorial"),
        "mongodb":          ("https://learn.mongodb.com",                              "MongoDB University (Free)"),
        "mysql":            ("https://dev.mysql.com/doc/refman/8.0/en/tutorial.html", "MySQL Tutorial"),
        "docker":           ("https://docs.docker.com/get-started/",                  "Docker Getting Started"),
        "kubernetes":       ("https://kubernetes.io/docs/tutorials/",                 "Kubernetes Tutorials"),
        "aws":              ("https://aws.amazon.com/training/",                       "AWS Training (Free)"),
        "git":              ("https://git-scm.com/book/en/v2",                         "Pro Git Book (Free)"),
        "machine learning": ("https://www.coursera.org/learn/machine-learning",        "Andrew Ng ML Course"),
        "deep learning":    ("https://www.deeplearning.ai",                            "DeepLearning.AI"),
        "nlp":              ("https://huggingface.co/learn/nlp-course/",              "HuggingFace NLP Course"),
        "tensorflow":       ("https://www.tensorflow.org/tutorials",                  "TensorFlow Tutorials"),
        "pytorch":          ("https://pytorch.org/tutorials/",                         "PyTorch Tutorials"),
        "linux":            ("https://linuxjourney.com",                               "Linux Journey (Free)"),
        "rest api":         ("https://restfulapi.net",                                 "RESTful API Tutorial"),
        "agile":            ("https://www.atlassian.com/agile",                        "Atlassian Agile Guide"),
        "sql":              ("https://sqlzoo.net",                                      "SQLZoo (Free)"),
        "c++":              ("https://cplusplus.com/doc/tutorial/",                    "cplusplus.com Tutorial"),
    }
    recs = []
    for skill in missing_skills:
        url, note = resource_map.get(skill, (
            f"https://www.google.com/search?q=learn+{skill.replace(' ', '+')}+tutorial",
            "Search for tutorials and courses"
        ))
        recs.append({
            "skill":    skill,
            "resource": url,
            "note":     note,
        })
    return recs


def _rating(score: float) -> str:
    if score >= 80: return "Excellent"
    if score >= 65: return "Good"
    if score >= 50: return "Fair"
    if score >= 35: return "Weak"
    return "Poor"


def _interpretation(score: float) -> str:
    if score >= 80: return "Excellent match! Your profile aligns very well with this role."
    if score >= 65: return "Good match. Minor improvements could strengthen your profile."
    if score >= 50: return "Moderate match. Consider tailoring your resume to the job description."
    if score >= 35: return "Weak match. Significant skill gaps exist for this role."
    return "Poor match. This role requires a very different skill set."