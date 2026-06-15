"""
question_service.py
────────────────────
Phase 3A — Dynamic Interview Question Generation

Final decision after extensive testing:
  flan-t5-base is NOT reliable for generating questions.
  It generates generic unrelated text regardless of prompts.

  Solution: Smart dynamic templates for ALL 4 types.
  Dynamic because: skill_gaps + job_role + experience_level +
                   resume_context all embedded into every question.
  T5 is still loaded and used for answer EVALUATION (evaluation_service.py).
"""

import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# ── Model loaded for evaluation_service to reuse ─────────────────────────────
_model     = None
_tokenizer = None
MODEL_NAME = "google/flan-t5-base"


def _get_model():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[FLAN-T5] Loading {MODEL_NAME} on {device}...")
    _tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    _model     = T5ForConditionalGeneration.from_pretrained(MODEL_NAME).to(device)
    _model.eval()
    print(f"[FLAN-T5] Ready on {device}")
    return _model, _tokenizer


# ── Skill descriptions ────────────────────────────────────────────────────────
SKILL_DESC = {
    "python":       "Python programming language",
    "flask":        "Flask web framework (Python)",
    "django":       "Django web framework (Python)",
    "fastapi":      "FastAPI framework (Python)",
    "react":        "React.js JavaScript library",
    "angular":      "Angular TypeScript framework",
    "vue":          "Vue.js JavaScript framework",
    "node.js":      "Node.js JavaScript runtime",
    "nodejs":       "Node.js JavaScript runtime",
    "express":      "Express.js Node.js framework",
    "javascript":   "JavaScript programming language",
    "typescript":   "TypeScript programming language",
    "java":         "Java programming language",
    "mysql":        "MySQL relational database",
    "postgresql":   "PostgreSQL relational database",
    "mongodb":      "MongoDB NoSQL database",
    "redis":        "Redis in-memory cache",
    "docker":       "Docker containerization platform",
    "kubernetes":   "Kubernetes container orchestration",
    "aws":          "Amazon Web Services (AWS)",
    "azure":        "Microsoft Azure cloud",
    "git":          "Git version control system",
    "rest api":     "REST API web service design",
    "graphql":      "GraphQL API query language",
    "linux":        "Linux operating system",
    "sql":          "SQL database query language",
    "html":         "HTML web markup language",
    "css":          "CSS stylesheet language",
    "tailwind":     "Tailwind CSS framework",
    "nlp":          "Natural Language Processing",
    "machine learning": "Machine Learning",
    "tensorflow":   "TensorFlow ML framework",
    "pytorch":      "PyTorch deep learning framework",
    "agile":        "Agile development methodology",
    "ci/cd":        "CI/CD deployment pipeline",
    "microservices":"microservices architecture",
    "data structures": "Data Structures",
    "algorithms":   "Algorithms",
}

def _desc(skill: str) -> str:
    return SKILL_DESC.get(skill.lower(), skill)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def generate_interview_questions(
    job_role: str,
    resume_text: str,
    skill_gaps: list,
    matched_skills: list,
    experience_level: str = "fresher",
    questions_per_type: int = 3,
) -> dict:
    """
    Generate dynamic interview questions.
    T5 model is loaded (used by evaluation_service for answer scoring).
    Questions are generated via smart dynamic templates.
    """
    # Load T5 (evaluation_service will reuse this)
    _get_model()

    exp_level = _detect_experience(resume_text, experience_level)
    level_key = _normalize_level(exp_level)

    technical       = _gen_technical(job_role, matched_skills, skill_gaps, level_key, questions_per_type)
    problem_solving = _gen_problem_solving(job_role, skill_gaps, level_key, questions_per_type)
    behavioral      = _gen_behavioral(job_role, resume_text, level_key, questions_per_type)
    situational     = _gen_situational(job_role, skill_gaps, level_key, questions_per_type)

    total = len(technical) + len(problem_solving) + len(behavioral) + len(situational)

    return {
        "job_role":           job_role,
        "experience_level":   exp_level,
        "total_questions":    total,
        "questions": {
            "technical":       technical,
            "problem_solving": problem_solving,
            "behavioral":      behavioral,
            "situational":     situational,
        },
        "skill_gaps_covered": skill_gaps[:5],
        "focus_skills":       matched_skills[:5],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  GENERATORS — All template-based, dynamic via skill_gaps + job_role + level
# ══════════════════════════════════════════════════════════════════════════════

def _gen_technical(job_role, matched_skills, skill_gaps, level_key, count):
    """Technical questions — skill-specific, difficulty-adapted."""
    templates = {
        "fresher": [
            "What is {skill} and why is it important for a {role}?",
            "Explain the core concepts of {skill} with a practical example.",
            "What are the key features of {skill} that every {role} should know?",
            "How does {skill} work and where is it commonly used?",
            "What is the difference between {skill} and its most common alternative?",
        ],
        "mid": [
            "How have you used {skill} in a real-world {role} project?",
            "What are the best practices for using {skill} in production?",
            "How would you optimize performance when working with {skill}?",
            "What are common pitfalls when using {skill} and how do you avoid them?",
            "Explain an advanced feature of {skill} and when you would use it.",
        ],
        "senior": [
            "How would you design a scalable architecture using {skill}?",
            "What are the trade-offs of using {skill} at scale?",
            "How does {skill} fit into a microservices or distributed system?",
            "How would you evaluate whether {skill} is the right technology for a given problem?",
            "Describe a complex challenge you would solve using {skill} as a senior {role}.",
        ],
    }

    tmpl_list = templates.get(level_key, templates["fresher"])
    focus = (skill_gaps[:3] + matched_skills[:3])
    questions = []

    for i, skill in enumerate(focus):
        tmpl = tmpl_list[i % len(tmpl_list)]
        q    = tmpl.format(skill=_desc(skill), role=job_role)
        questions.append({
            "question":   q if q.endswith("?") else q + "?",
            "skill":      skill,
            "type":       "technical",
            "difficulty": level_key,
            "is_gap":     skill in skill_gaps,
        })
        if len(questions) >= count:
            break

    return questions


def _gen_problem_solving(job_role, skill_gaps, level_key, count):
    """Problem solving questions with skill gaps embedded."""
    gap  = _desc(skill_gaps[0]) if skill_gaps else "a new technology"
    gap2 = _desc(skill_gaps[1]) if len(skill_gaps) > 1 else gap

    templates = {
        "fresher": [
            f"How would you debug an issue in your {job_role} project where a module using {gap} returns unexpected results?",
            f"Your {job_role} application works locally but fails in production when using {gap}. What steps would you take to investigate?",
            f"As a {job_role}, how would you approach implementing a feature using {gap} that you have never worked with before?",
        ],
        "mid": [
            f"A {gap} related query in your {job_role} system is causing production timeouts. How would you diagnose and fix it?",
            f"Your {job_role} application using {gap} is experiencing memory leaks in production. Walk me through your debugging process.",
            f"How would you refactor existing {job_role} code to properly integrate {gap2} without breaking current functionality?",
        ],
        "senior": [
            f"How would you architect a {job_role} system that needs to scale to 1 million users while effectively using {gap}?",
            f"A critical security vulnerability is found in your {gap} implementation in production. What is your complete response plan?",
            f"How would you lead a team migration from the current {job_role} architecture to one that uses {gap} and {gap2} effectively?",
        ],
    }

    questions = []
    for q in templates.get(level_key, templates["fresher"])[:count]:
        questions.append({
            "question":   q if q.endswith("?") else q + "?",
            "type":       "problem_solving",
            "difficulty": level_key,
        })
    return questions


def _gen_behavioral(job_role, resume_text, level_key, count):
    """
    Behavioral questions — STAR format.
    Resume context (internship/project/team) personalizes questions.
    """
    resume_lower = resume_text.lower()

    if "intern" in resume_lower:
        ctx = "internship"
    elif "project" in resume_lower:
        ctx = "project"
    else:
        ctx = "work experience"

    # Check for specific resume signals
    has_team      = "team" in resume_lower
    has_react     = "react" in resume_lower
    has_flask     = "flask" in resume_lower

    templates = {
        "fresher": [
            f"Tell me about a time during your {ctx} when you faced a difficult technical challenge. What was the situation, what did you do, and what was the outcome?",
            f"Describe a situation during your {ctx} where you had to learn {'React.js or Flask' if has_react or has_flask else 'a new technology'} quickly to complete a task. How did you approach it?",
            f"Tell me about a time {'you collaborated with a team' if has_team else 'you worked on a group task'} during your {ctx}. What was your role and how did you contribute?",
        ],
        "mid": [
            f"Tell me about a time you significantly improved the performance or quality of a system during your {ctx}. What steps did you take?",
            f"Describe a situation where you disagreed with a technical decision made by your team. How did you handle it professionally?",
            f"Tell me about a time you had to deliver an important feature under a very tight deadline in your {ctx}. What was your approach?",
        ],
        "senior": [
            f"Tell me about a time you led a team through a major technical challenge or migration. What was your leadership approach and what was the outcome?",
            f"Describe a situation where you had to convince stakeholders to adopt a better technical solution. How did you build the case and what happened?",
            f"Tell me about a time you mentored a junior developer who was struggling. What did you do and how did it impact them?",
        ],
    }

    questions = []
    for q in templates.get(level_key, templates["fresher"])[:count]:
        questions.append({
            "question":   q if q.endswith("?") else q + "?",
            "type":       "behavioral",
            "difficulty": "medium",
            "format":     "STAR (Situation, Task, Action, Result)",
        })
    return questions


def _gen_situational(job_role, skill_gaps, level_key, count):
    """Situational questions — hypothetical scenarios with skill gaps."""
    gap  = _desc(skill_gaps[0]) if skill_gaps else "a new technology"
    gap2 = _desc(skill_gaps[1]) if len(skill_gaps) > 1 else gap

    templates = {
        "fresher": [
            f"If your project deadline is tomorrow and you realize the feature requires {gap} which you have never used before, what would you do?",
            f"If your manager asks you to build a {job_role} feature using {gap2} in 2 days with no prior experience, how would you approach it?",
            f"If you discover a critical bug in your {job_role} code right before an important client demo, what steps would you take?",
        ],
        "mid": [
            f"If a client urgently requests a change requiring {gap} that contradicts your current {job_role} architecture, how would you handle it?",
            f"If you discover a security vulnerability in your {gap2} integration in production, what is your immediate response and action plan?",
            f"If your team lead is suddenly unavailable during a critical production outage in your {job_role} system, how would you respond?",
        ],
        "senior": [
            f"If the CTO asks you to evaluate and adopt {gap} for the entire {job_role} team within one month, what is your process?",
            f"If two senior engineers on your team fundamentally disagree on using {gap} versus {gap2} for a critical system, how do you resolve it?",
            f"If the business demands a {gap}-based feature in 2 weeks but your engineering estimate is 2 months, how do you respond to stakeholders?",
        ],
    }

    questions = []
    for q in templates.get(level_key, templates["fresher"])[:count]:
        questions.append({
            "question":   q if q.endswith("?") else q + "?",
            "type":       "situational",
            "difficulty": level_key,
        })
    return questions


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _detect_experience(resume_text: str, default: str) -> str:
    text = resume_text.lower()
    if any(w in text for w in ["5+ years", "6 years", "7 years", "senior", "lead", "architect"]):
        return "senior"
    if any(w in text for w in ["3 years", "4 years", "mid-level"]):
        return "mid"
    if any(w in text for w in ["intern", "internship", "fresher", "b.tech", "btech", "entry", "graduate"]):
        return "fresher"
    return default or "fresher"


def _normalize_level(exp_level: str) -> str:
    return {
        "fresher": "fresher", "entry": "fresher", "junior": "fresher",
        "mid": "mid", "mid-level": "mid",
        "senior": "senior", "lead": "senior", "principal": "senior",
    }.get(exp_level.lower(), "fresher")