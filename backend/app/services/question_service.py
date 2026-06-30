"""
question_service.py
────────────────────
Paper: "AI-Based Resume Analyzer and Interview Simulator"
§4 Interview Question Generation:

  "Dynamic interview question generation distinguishes our system
   from static question bank approaches. The generation process
   considers three primary inputs: the selected job role, the
   candidate's resume content, and identified skill gaps."

  "Question generation employs a large language model fine-tuned
   on interview question datasets [Ref 7]. Prompts to the model
   specify the role, required skills, and candidate experience level."

  "The system generates diverse question types spanning technical
   knowledge, problem-solving scenarios, and situational judgment."

Architecture:
  ┌─────────────────────────────────────────────┐
  │  Fine-tuned FLAN-T5 (LoRA adapter)          │
  │  Input:  role + skill + level + type        │
  │  Output: interview question                 │
  └─────────────────────────────────────────────┘
  Fallback → dynamic templates (if model not found)

Model path:
  Place fine-tuned model at:
  backend/app/models/flan_t5_interview/
    ├── adapter_config.json
    ├── adapter_model.safetensors
    ├── tokenizer_config.json
    ├── tokenizer.json
    └── model_config.json
"""

import os
import json
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# ── Try importing PEFT (for LoRA adapter loading) ────────────────────────────
try:
    from peft import PeftModel
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    print("[question_service] WARNING: peft not installed. Run: pip install peft")

# ── Model paths ───────────────────────────────────────────────────────────────

# Fine-tuned LoRA adapter directory (set after training)
_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINETUNED_DIR = os.path.join(_BASE_DIR, "models", "flan_t5_interview")
BASE_MODEL    = "google/flan-t5-base"

# ── Singletons ────────────────────────────────────────────────────────────────

_model     = None
_tokenizer = None
_use_finetuned = False   # Will be True after fine-tuned model loads

MAX_INPUT_LEN  = 128
MAX_TARGET_LEN = 64

# ═══════════════════════════════════════════════════════════════════════════════
#  MODEL LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def _get_model():
    """
    Load model with priority:
      1. Fine-tuned LoRA adapter (paper-compliant)
      2. Base FLAN-T5 (fallback, still paper-referenced model)
    """
    global _model, _tokenizer, _use_finetuned

    if _model is not None:
        return _model, _tokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    adapter_config = os.path.join(FINETUNED_DIR, "adapter_config.json")

    # ── Path 1: Load fine-tuned LoRA adapter ─────────────────────────────────
    if PEFT_AVAILABLE and os.path.exists(adapter_config):
        print(f"[FLAN-T5] Loading fine-tuned LoRA adapter from: {FINETUNED_DIR}")
        try:
            # Load tokenizer from adapter dir (may contain custom tokenizer)
            _tokenizer = T5Tokenizer.from_pretrained(FINETUNED_DIR)

            # Load base model
            base = T5ForConditionalGeneration.from_pretrained(
                BASE_MODEL,
                torch_dtype=torch.float32,
            )

            # Apply LoRA adapter on top
            _model = PeftModel.from_pretrained(base, FINETUNED_DIR)
            _model = _model.to(device)
            _model.eval()

            _use_finetuned = True
            print(f"[FLAN-T5] ✓ Fine-tuned model ready on {device}")
            print(f"[FLAN-T5] LoRA adapter applied — paper-compliant question generation active")
            return _model, _tokenizer

        except Exception as e:
            print(f"[FLAN-T5] Fine-tuned load failed: {e}")
            print(f"[FLAN-T5] Falling back to base model...")
            _model = None
            _tokenizer = None

    # ── Path 2: Base FLAN-T5 (fallback) ──────────────────────────────────────
    if not os.path.exists(adapter_config):
        print(f"[FLAN-T5] Fine-tuned model not found at: {FINETUNED_DIR}")
        print(f"[FLAN-T5] Run fine-tuning notebook first, then place model in that directory.")
        print(f"[FLAN-T5] Loading base FLAN-T5 with template generation as fallback...")

    _tokenizer = T5Tokenizer.from_pretrained(BASE_MODEL)
    _model     = T5ForConditionalGeneration.from_pretrained(BASE_MODEL).to(device)
    _model.eval()
    _use_finetuned = False
    print(f"[FLAN-T5] Base model ready on {device} (templates will be used for generation)")
    return _model, _tokenizer


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE: AI QUESTION GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_one_question(
    job_role:         str,
    skill:            str,
    experience_level: str,
    question_type:    str,
    num_beams:        int = 4,
) -> str | None:
    """
    Paper §4: "Prompts to the model specify the role, required skills,
               and candidate experience level."

    Uses fine-tuned FLAN-T5 when available.
    Returns None if model output is unusable (will trigger template fallback).
    """
    model, tokenizer = _get_model()

    # Same prompt format used during fine-tuning (prepare_dataset.py)
    prompt = (
        f"Generate a {question_type} interview question for a {job_role} role. "
        f"Skill: {skill}. Experience level: {experience_level}. "
        f"Question:"
    )

    try:
        device = next(model.parameters()).device
        inputs = tokenizer(
            prompt,
            return_tensors = "pt",
            max_length     = MAX_INPUT_LEN,
            truncation     = True,
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens       = MAX_TARGET_LEN,
                num_beams            = num_beams,
                no_repeat_ngram_size = 3,
                early_stopping       = True,
                temperature          = 0.8 if _use_finetuned else 1.0,
                do_sample            = False,
            )

        generated = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # Quality check: must be a proper question
        if (
            len(generated.split()) >= 6          # Not too short
            and len(generated.split()) <= 60      # Not too long
            and ("?" in generated or generated[-1] in ".!?")
        ):
            if not generated.endswith("?"):
                generated = generated.rstrip(".!") + "?"
            return generated

    except Exception as e:
        print(f"[FLAN-T5 generation] Error: {e}")

    return None   # Signal to use template fallback


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def generate_interview_questions(
    job_role:           str,
    resume_text:        str,
    skill_gaps:         list,
    matched_skills:     list,
    experience_level:   str = "fresher",
    questions_per_type: int = 3,
) -> dict:
    """
    Paper §4: Generate dynamic interview questions using fine-tuned FLAN-T5.

    Three primary inputs (paper-exact):
      1. job_role          — selected target role
      2. resume_text       — parsed resume content (for context & experience detection)
      3. skill_gaps        — identified gaps (drive question focus)

    Returns 4 question types: technical, problem_solving, behavioral, situational
    """
    # Load model on first call
    _get_model()

    exp_level = _detect_experience(resume_text, experience_level)
    level_key = _normalize_level(exp_level)

    # Skills to focus on: gaps first (paper: "gaps inform interview questions")
    focus_skills  = skill_gaps[:4] + matched_skills[:3]
    gap_skill_set = set(skill_gaps)

    technical       = _generate_type("technical",       job_role, focus_skills, level_key, questions_per_type, gap_skill_set, resume_text)
    problem_solving = _generate_type("problem_solving", job_role, focus_skills, level_key, questions_per_type, gap_skill_set, resume_text)
    behavioral      = _generate_type("behavioral",      job_role, focus_skills, level_key, questions_per_type, gap_skill_set, resume_text)
    situational     = _generate_type("situational",     job_role, focus_skills, level_key, questions_per_type, gap_skill_set, resume_text)

    total = len(technical) + len(problem_solving) + len(behavioral) + len(situational)

    return {
        "job_role":           job_role,
        "experience_level":   exp_level,
        "total_questions":    total,
        "generation_method":  "finetuned_lora" if _use_finetuned else "template_fallback",
        "questions": {
            "technical":       technical,
            "problem_solving": problem_solving,
            "behavioral":      behavioral,
            "situational":     situational,
        },
        "skill_gaps_covered": skill_gaps[:5],
        "focus_skills":       matched_skills[:5],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  QUESTION TYPE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_type(
    question_type: str,
    job_role:      str,
    focus_skills:  list,
    level_key:     str,
    count:         int,
    gap_skill_set: set,
    resume_text:   str,
) -> list:
    """
    Paper §4: "Template-based constraints ensure questions follow
               effective interviewing practices."

    Strategy:
      - Try fine-tuned model FIRST for each question
      - If model output fails quality check → use template fallback
      - Track seen questions to avoid duplicates
    """
    questions  = []
    seen_texts = set()

    # Skills to iterate over
    skills_for_type = focus_skills if focus_skills else [job_role.lower()]

    for i, skill in enumerate(skills_for_type):
        if len(questions) >= count:
            break

        # ── Try fine-tuned model ───────────────────────────────────────────
        model_q = _generate_one_question(
            job_role         = job_role,
            skill            = skill,
            experience_level = level_key,
            question_type    = question_type.replace("_", " "),
        )

        # Dedup check
        if model_q and model_q.lower()[:40] not in seen_texts:
            seen_texts.add(model_q.lower()[:40])
            questions.append(_build_q_dict(
                question      = model_q,
                question_type = question_type,
                skill         = skill,
                level_key     = level_key,
                is_gap        = skill in gap_skill_set,
                source        = "model",
            ))
            continue

        # ── Template fallback ─────────────────────────────────────────────
        template_q = _template_fallback(
            question_type = question_type,
            job_role      = job_role,
            skill         = skill,
            level_key     = level_key,
            idx           = i,
            resume_text   = resume_text,
            skill_gaps    = list(gap_skill_set),
        )
        if template_q and template_q.lower()[:40] not in seen_texts:
            seen_texts.add(template_q.lower()[:40])
            questions.append(_build_q_dict(
                question      = template_q,
                question_type = question_type,
                skill         = skill,
                level_key     = level_key,
                is_gap        = skill in gap_skill_set,
                source        = "template",
            ))

    return questions


def _build_q_dict(question, question_type, skill, level_key, is_gap, source) -> dict:
    q = question if question.endswith("?") else question + "?"
    d = {
        "question":   q,
        "skill":      skill,
        "type":       question_type,
        "difficulty": level_key,
        "is_gap":     is_gap,
        "source":     source,   # "model" or "template" — useful for eval
    }
    if question_type == "behavioral":
        d["format"] = "STAR (Situation, Task, Action, Result)"
    return d


# ═══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE FALLBACK (paper: "template-based constraints")
# ═══════════════════════════════════════════════════════════════════════════════

_SKILL_DESC = {
    "python": "Python programming", "flask": "Flask web framework",
    "django": "Django web framework", "fastapi": "FastAPI framework",
    "react": "React.js", "angular": "Angular", "vue": "Vue.js",
    "nodejs": "Node.js", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "mysql": "MySQL", "postgresql": "PostgreSQL",
    "mongodb": "MongoDB", "docker": "Docker", "kubernetes": "Kubernetes",
    "aws": "AWS cloud services", "git": "Git version control",
    "rest api": "REST API design", "machine learning": "Machine Learning",
    "nlp": "Natural Language Processing", "sql": "SQL",
}

def _desc(skill: str) -> str:
    return _SKILL_DESC.get(skill.lower(), skill)


def _template_fallback(
    question_type: str,
    job_role:      str,
    skill:         str,
    level_key:     str,
    idx:           int,
    resume_text:   str,
    skill_gaps:    list,
) -> str | None:
    """Dynamic templates as fallback when model output fails quality check."""

    skill_d = _desc(skill)
    gap1 = _desc(skill_gaps[0]) if skill_gaps else skill_d
    gap2 = _desc(skill_gaps[1]) if len(skill_gaps) > 1 else gap1

    TEMPLATES = {
        "technical": {
            "fresher": [
                f"What is {skill_d} and why is it important for a {job_role}?",
                f"Explain the core concepts of {skill_d} with a practical example.",
                f"What are the key features of {skill_d} that every {job_role} should know?",
            ],
            "mid": [
                f"How have you used {skill_d} in a real-world {job_role} project?",
                f"What are the best practices for using {skill_d} in production?",
                f"How would you optimize performance when working with {skill_d}?",
            ],
            "senior": [
                f"How would you design a scalable architecture using {skill_d}?",
                f"What are the trade-offs of using {skill_d} at scale in a {job_role} system?",
                f"How does {skill_d} fit into a microservices or distributed system?",
            ],
        },
        "problem_solving": {
            "fresher": [
                f"How would you debug an issue in your {job_role} project where {gap1} returns unexpected results?",
                f"Your {job_role} application works locally but fails in production when using {gap1}. What steps would you take?",
                f"As a {job_role}, how would you approach implementing {gap1} for the first time?",
            ],
            "mid": [
                f"A {gap1}-related query in your {job_role} system is causing production timeouts. How would you diagnose and fix it?",
                f"Your {job_role} application using {gap1} is experiencing memory leaks. Walk through your debugging process.",
                f"How would you refactor existing {job_role} code to integrate {gap2} without breaking current functionality?",
            ],
            "senior": [
                f"How would you architect a {job_role} system that scales to 1M users while using {gap1} effectively?",
                f"A critical security vulnerability is found in your {gap1} implementation. What is your complete response plan?",
                f"How would you lead a team migration to an architecture using {gap1} and {gap2}?",
            ],
        },
        "behavioral": {
            "fresher": [
                f"Tell me about a time during your project or internship when you faced a difficult technical challenge. What did you do and what was the outcome?",
                f"Describe a situation where you had to learn {skill_d} quickly to complete a task. How did you approach it?",
                f"Tell me about a time you collaborated with a team on a technical problem. What was your role?",
            ],
            "mid": [
                f"Tell me about a time you significantly improved the performance of a system. What steps did you take?",
                f"Describe a situation where you disagreed with a technical decision. How did you handle it professionally?",
                f"Tell me about a time you delivered an important feature under a very tight deadline. What was your approach?",
            ],
            "senior": [
                f"Tell me about a time you led a team through a major technical challenge. What was your leadership approach?",
                f"Describe a situation where you convinced stakeholders to adopt a better technical solution. How did you build the case?",
                f"Tell me about a time you mentored a junior developer who was struggling. What did you do?",
            ],
        },
        "situational": {
            "fresher": [
                f"If your project deadline is tomorrow and the feature requires {gap1} which you have never used before, what would you do?",
                f"If your manager asks you to build a {job_role} feature using {gap2} in 2 days, how would you approach it?",
                f"If you discover a critical bug right before an important client demo, what steps would you take?",
            ],
            "mid": [
                f"If a client urgently requests a change requiring {gap1} that contradicts your current {job_role} architecture, how would you handle it?",
                f"If you discover a security vulnerability in your {gap2} integration in production, what is your immediate response?",
                f"If your team lead is suddenly unavailable during a critical production outage, how would you respond?",
            ],
            "senior": [
                f"If the CTO asks you to evaluate and adopt {gap1} for the entire {job_role} team in one month, what is your process?",
                f"If two senior engineers fundamentally disagree on using {gap1} versus {gap2}, how do you resolve it?",
                f"If the business demands a {gap1}-based feature in 2 weeks but your engineering estimate is 2 months, how do you respond?",
            ],
        },
    }

    tmpl_group = TEMPLATES.get(question_type, TEMPLATES["technical"])
    tmpl_list  = tmpl_group.get(level_key, tmpl_group["fresher"])
    q = tmpl_list[idx % len(tmpl_list)]
    return q if q.endswith("?") else q + "?"


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_experience(resume_text: str, default: str) -> str:
    text = resume_text.lower()
    if any(w in text for w in ["5+ years", "6 years", "7 years", "senior", "lead", "architect"]):
        return "senior"
    if any(w in text for w in ["3 years", "4 years", "mid-level"]):
        return "mid"
    if any(w in text for w in ["intern", "fresher", "b.tech", "entry", "graduate"]):
        return "fresher"
    return default or "fresher"


def _normalize_level(exp_level: str) -> str:
    return {
        "fresher": "fresher", "entry": "fresher", "junior": "fresher",
        "mid": "mid", "mid-level": "mid",
        "senior": "senior", "lead": "senior", "principal": "senior",
    }.get(exp_level.lower(), "fresher")


def is_finetuned_model_loaded() -> bool:
    """Utility for health check endpoint — returns True if LoRA adapter is active."""
    return _use_finetuned


def get_model_info() -> dict:
    """Return model info for transparency report."""
    return {
        "model":          BASE_MODEL,
        "finetuned":      _use_finetuned,
        "adapter_path":   FINETUNED_DIR if _use_finetuned else None,
        "generation":     "LoRA fine-tuned FLAN-T5" if _use_finetuned else "Base model + templates",
        "paper_compliant": _use_finetuned,
    }