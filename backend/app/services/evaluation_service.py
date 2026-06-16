"""
evaluation_service.py
──────────────────────
Paper: "Response evaluation employs multiple analytical dimensions:
        1. Content analysis
        2. Language quality
        3. Completeness scoring
        4. Keyword matching"

Problem 3 Fix:
  Previously: Hardcoded knowledge bank for expected answers + keywords.
  Now:        FLAN-T5 generates expected answer AND keywords dynamically
              per question, with knowledge bank as fallback only.
"""

import re
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import T5ForConditionalGeneration, T5Tokenizer


# ── Singletons ────────────────────────────────────────────────────────────────
_minilm       = None
_t5_model     = None
_t5_tokenizer = None


def _get_minilm() -> SentenceTransformer:
    global _minilm
    if _minilm is not None:
        return _minilm
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[MiniLM] Loading all-MiniLM-L6-v2 on {device}...")
    _minilm = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    print("[MiniLM] Ready")
    return _minilm


def _get_t5():
    global _t5_model, _t5_tokenizer
    if _t5_model is not None:
        return _t5_model, _t5_tokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[FLAN-T5] Loading google/flan-t5-base on {device}...")
    _t5_tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
    _t5_model     = T5ForConditionalGeneration.from_pretrained(
        "google/flan-t5-base"
    ).to(device)
    _t5_model.eval()
    print("[FLAN-T5] Ready")
    return _t5_model, _t5_tokenizer


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_answer(
    question:         str,
    candidate_answer: str,
    question_type:    str = "technical",
    skill:            str = "",
    job_role:         str = "",
) -> dict:
    """Evaluate a single candidate answer against all 4 dimensions."""
    if not candidate_answer or len(candidate_answer.strip()) < 10:
        return {
            "score":           0.0,
            "rating":          "No Answer",
            "feedback":        "No answer was provided.",
            "similarity":      0.0,
            "expected_answer": "",
            "keywords_used":   [],
            "keywords_missing": [],
            "dimensions":      {},
        }

    minilm = _get_minilm()

    # Step 1: Generate expected answer (AI-first, fallback second)
    expected = _generate_expected_answer(question, question_type, skill, job_role)

    # Step 2: AI-generated keywords for this specific question
    keywords = _generate_keywords_for_question(question, skill, question_type, job_role)

    # Step 3: Encode with MiniLM
    expected_emb  = minilm.encode(expected,          convert_to_tensor=True)
    candidate_emb = minilm.encode(candidate_answer,  convert_to_tensor=True)

    # Step 4: Cosine similarity
    similarity = float(util.cos_sim(expected_emb, candidate_emb)[0][0])
    similarity = round(similarity, 4)
    score      = round(similarity * 100, 1)

    # Step 5: 4 evaluation dimensions
    dimensions = _evaluate_dimensions(
        question, candidate_answer, expected,
        similarity, question_type, keywords
    )

    # Step 6: Rating + feedback
    rating   = _get_rating(similarity)
    feedback = _generate_feedback(rating, dimensions, skill, question_type)

    # Step 7: Keyword hit/miss analysis
    candidate_lower  = candidate_answer.lower()
    keywords_used    = [k for k in keywords if k.lower() in candidate_lower]
    keywords_missing = [k for k in keywords if k.lower() not in candidate_lower]

    return {
        "score":            score,
        "similarity":       similarity,
        "rating":           rating,
        "expected_answer":  expected,
        "feedback":         feedback,
        "keywords_used":    keywords_used,
        "keywords_missing": keywords_missing,
        "dimensions":       dimensions,
    }


def evaluate_multiple_answers(answers: list) -> dict:
    """Evaluate multiple question-answer pairs."""
    results     = []
    total_score = 0.0

    for item in answers:
        result = evaluate_answer(
            question         = item.get("question", ""),
            candidate_answer = item.get("candidate_answer", ""),
            question_type    = item.get("question_type", "technical"),
            skill            = item.get("skill", ""),
            job_role         = item.get("job_role", ""),
        )
        result["question"] = item.get("question", "")
        results.append(result)
        total_score += result["score"]

    avg_score = round(total_score / len(results), 1) if results else 0.0

    return {
        "overall_score":      avg_score,
        "overall_rating":     _get_rating(avg_score / 100),
        "total_questions":    len(results),
        "individual_results": results,
        "summary":            _overall_summary(avg_score, results),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  AI KEYWORD GENERATION (Problem 3 Fix)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_keywords_for_question(
    question:      str,
    skill:         str,
    question_type: str,
    job_role:      str,
) -> list:
    """
    Problem 3 Fix: Generate expected keywords using FLAN-T5.
    Previously hardcoded — now AI-generated per question.
    Fallback to knowledge bank if T5 output is too short/empty.
    """
    try:
        model, tokenizer = _get_t5()
        device = next(model.parameters()).device

        prompt = (
            f"List 6 key technical terms expected in a good answer to this "
            f"interview question about {skill} for a {job_role} role. "
            f"Question: {question} "
            f"Output only comma-separated terms, nothing else."
        )

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=256,
            truncation=True,
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=60,
                num_beams=4,
                early_stopping=True,
            )

        generated = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # Parse comma-separated terms
        keywords = [k.strip().lower() for k in generated.split(",") if len(k.strip()) > 2]

        # Validate: must have at least 3 meaningful keywords
        if len(keywords) >= 3:
            return keywords[:8]   # cap at 8

    except Exception as e:
        print(f"[FLAN-T5 keyword gen] Failed: {e} — using fallback")

    # Fallback: knowledge bank (used when T5 output is insufficient)
    return _keyword_fallback(skill, question_type)


def _keyword_fallback(skill: str, question_type: str) -> list:
    """
    Fallback keyword bank — used only when FLAN-T5 generation fails
    or produces insufficient output.
    """
    KEYWORD_BANK = {
        "python":           ["functions", "classes", "libraries", "syntax", "interpreter", "pip", "modules"],
        "flask":            ["routes", "blueprints", "request", "response", "jinja2", "sqlalchemy", "decorator"],
        "django":           ["models", "views", "templates", "orm", "admin", "urls", "migrations"],
        "react":            ["components", "hooks", "state", "props", "virtual dom", "jsx", "useeffect"],
        "docker":           ["container", "image", "dockerfile", "compose", "volume", "network", "registry"],
        "aws":              ["ec2", "s3", "rds", "lambda", "iam", "cloudwatch", "vpc"],
        "mysql":            ["tables", "joins", "indexes", "transactions", "foreign key", "query", "acid"],
        "postgresql":       ["tables", "joins", "indexes", "transactions", "constraints", "query", "acid"],
        "mongodb":          ["collections", "documents", "bson", "aggregation", "indexes", "schema", "nosql"],
        "git":              ["commit", "branch", "merge", "pull request", "clone", "push", "rebase"],
        "machine learning": ["training", "testing", "model", "features", "accuracy", "overfitting", "validation"],
        "nlp":              ["tokenization", "embeddings", "transformers", "bert", "sentiment", "ner", "corpus"],
        "rest api":         ["endpoints", "http", "get", "post", "json", "authentication", "status codes"],
        "kubernetes":       ["pods", "nodes", "deployment", "service", "cluster", "namespace", "ingress"],
        "javascript":       ["variables", "functions", "async", "promises", "dom", "events", "closures"],
        "typescript":       ["types", "interfaces", "generics", "decorators", "strict", "compile", "classes"],
    }

    TYPE_KEYWORDS = {
        "behavioral":    ["situation", "task", "action", "result", "team", "challenge", "outcome"],
        "situational":   ["approach", "prioritize", "communicate", "resolve", "plan", "steps", "decision"],
        "problem_solving": ["debug", "analyze", "root cause", "solution", "test", "reproduce", "fix"],
    }

    skill_lower = skill.lower()
    if skill_lower in KEYWORD_BANK:
        return KEYWORD_BANK[skill_lower]
    return TYPE_KEYWORDS.get(question_type, ["explain", "example", "implement", "use", "benefit"])


# ══════════════════════════════════════════════════════════════════════════════
#  EXPECTED ANSWER GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def _generate_expected_answer(
    question:      str,
    question_type: str,
    skill:         str,
    job_role:      str,
) -> str:
    """
    Generate reference answer using FLAN-T5.
    Falls back to template if T5 output is too short.
    """
    try:
        model, tokenizer = _get_t5()
        device = next(model.parameters()).device

        prompt = (
            f"Provide a comprehensive answer to this {question_type} interview "
            f"question about {skill} for a {job_role} position. "
            f"Question: {question}"
        )

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=300,
            truncation=True,
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=2,
            )

        generated = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # Use T5 output only if it's substantive (30+ words)
        if len(generated.split()) >= 30:
            return generated

    except Exception as e:
        print(f"[FLAN-T5 answer gen] Failed: {e} — using template fallback")

    # Fallback templates
    return _answer_template_fallback(question_type, skill, job_role)


def _answer_template_fallback(question_type: str, skill: str, job_role: str) -> str:
    templates = {
        "technical": (
            f"A strong answer explains what {skill} is, its core concepts and architecture, "
            f"practical use cases in {job_role} projects, how it differs from alternatives, "
            f"and includes real-world examples with specific technical details."
        ),
        "behavioral": (
            "A strong STAR answer describes the Situation with clear context, "
            "the Task or challenge faced, the concrete Actions taken step by step "
            "with reasoning, and the measurable Result achieved. "
            "Be specific with examples and quantify impact where possible."
        ),
        "situational": (
            "A strong answer identifies the problem clearly, outlines a prioritized "
            "action plan with specific steps, mentions communicating with stakeholders, "
            "and demonstrates calm structured thinking under pressure with a clear outcome."
        ),
        "problem_solving": (
            "A strong answer follows a systematic approach: understand and reproduce "
            "the problem, investigate root cause using logs or debugging tools, "
            "implement and test a fix thoroughly, deploy carefully, and document the solution."
        ),
    }
    return templates.get(question_type, templates["technical"])


# ══════════════════════════════════════════════════════════════════════════════
#  4 EVALUATION DIMENSIONS
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_dimensions(
    question:      str,
    candidate_answer: str,
    expected:      str,
    similarity:    float,
    question_type: str,
    keywords:      list,
) -> dict:
    """
    Paper: 4 dimensions —
    1. Content relevance
    2. Completeness
    3. Language quality
    4. Keyword coverage (now AI-generated keywords)
    """
    minilm = _get_minilm()

    # 1. Content relevance — answer vs question similarity
    q_emb   = minilm.encode(question,         convert_to_tensor=True)
    ans_emb = minilm.encode(candidate_answer, convert_to_tensor=True)
    content_score = round(float(util.cos_sim(q_emb, ans_emb)[0][0]) * 100, 1)

    # 2. Completeness — word count proxy
    word_count = len(candidate_answer.split())
    if word_count >= 80:
        completeness_label = "Complete"
        completeness_score = 100
    elif word_count >= 40:
        completeness_label = "Adequate"
        completeness_score = 70
    elif word_count >= 15:
        completeness_label = "Brief"
        completeness_score = 40
    else:
        completeness_label = "Too Short"
        completeness_score = 10

    # 3. Language quality — filler words check
    filler_words = ["um", "uh", "like", "basically", "literally", "you know", "kind of"]
    filler_count = sum(candidate_answer.lower().count(w) for w in filler_words)
    language_score = max(0, 100 - (filler_count * 10))

    # 4. Keyword coverage — AI-generated keywords
    candidate_lower = candidate_answer.lower()
    if keywords:
        hits = [k for k in keywords if k.lower() in candidate_lower]
        keyword_score = round(len(hits) / len(keywords) * 100, 1)
    else:
        keyword_score = 50.0
        hits = []

    return {
        "content_relevance": {
            "score":       content_score,
            "label":       _score_label(content_score),
            "description": "How well the answer addresses the question",
        },
        "completeness": {
            "score":       completeness_score,
            "label":       completeness_label,
            "word_count":  word_count,
            "description": "Whether the answer is elaborated sufficiently",
        },
        "language_quality": {
            "score":       language_score,
            "label":       _score_label(language_score),
            "filler_count": filler_count,
            "description": "Clarity and professional tone of the answer",
        },
        "keyword_coverage": {
            "score":        keyword_score,
            "label":        _score_label(keyword_score),
            "keywords_hit": hits,
            "total_keywords": len(keywords),
            "description":  "Key concepts from expected answer covered",
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  RATING + FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

def _get_rating(similarity: float) -> str:
    if similarity >= 0.90: return "Excellent"
    if similarity >= 0.75: return "Good"
    if similarity >= 0.60: return "Average"
    return "Poor"


def _generate_feedback(
    rating:        str,
    dimensions:    dict,
    skill:         str,
    question_type: str,
) -> dict:
    strengths    = []
    improvements = []

    content_score = dimensions["content_relevance"]["score"]
    if content_score >= 70:
        strengths.append("Your answer is relevant and addresses the question well.")
    else:
        improvements.append("Try to more directly address what the question is asking.")

    comp_label = dimensions["completeness"]["label"]
    word_count = dimensions["completeness"]["word_count"]
    if comp_label in ["Complete", "Adequate"]:
        strengths.append(f"Good level of detail with {word_count} words.")
    else:
        improvements.append(
            f"Your answer is too brief ({word_count} words). "
            "Aim for at least 50-80 words with specific examples."
        )

    kw_score = dimensions["keyword_coverage"]["score"]
    kw_hit   = dimensions["keyword_coverage"]["keywords_hit"]
    if kw_score >= 60:
        strengths.append(f"Good use of technical terminology: {', '.join(kw_hit[:3])}.")
    else:
        improvements.append(
            f"Include more specific terminology related to {skill}. "
            "Use proper technical vocabulary in your answers."
        )

    lang_score = dimensions["language_quality"]["score"]
    if lang_score >= 80:
        strengths.append("Clear and professional communication style.")
    else:
        improvements.append("Avoid filler words and maintain a professional tone.")

    type_tips = {
        "technical":       "For technical questions, include examples, code concepts, or real use cases.",
        "behavioral":      "Use the STAR method: Situation → Task → Action → Result.",
        "situational":     "Structure your answer: identify the issue → list steps → explain outcome.",
        "problem_solving": "Walk through your thought process step by step systematically.",
    }

    return {
        "overall_rating": rating,
        "strengths":      strengths,
        "improvements":   improvements,
        "tip":            type_tips.get(question_type, "Be specific and structured."),
    }


def _overall_summary(avg_score: float, results: list) -> dict:
    excellent = sum(1 for r in results if r["rating"] == "Excellent")
    good      = sum(1 for r in results if r["rating"] == "Good")
    average   = sum(1 for r in results if r["rating"] == "Average")
    poor      = sum(1 for r in results if r["rating"] == "Poor")

    if avg_score >= 90:
        verdict = "Outstanding performance! You are very well prepared for this interview."
    elif avg_score >= 75:
        verdict = "Good performance. Review the areas marked for improvement."
    elif avg_score >= 60:
        verdict = "Average performance. Focus on more detailed and structured answers."
    else:
        verdict = "Needs improvement. Practice with specific examples and technical depth."

    return {
        "verdict":   verdict,
        "breakdown": {
            "excellent": excellent,
            "good":      good,
            "average":   average,
            "poor":      poor,
        },
    }


def _score_label(score: float) -> str:
    if score >= 85: return "Excellent"
    if score >= 70: return "Good"
    if score >= 50: return "Average"
    return "Poor"
