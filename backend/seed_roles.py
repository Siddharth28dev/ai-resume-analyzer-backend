"""
seed_roles.py
─────────────
Paper §3 "Role Mapping and Skill Assessment":
  "Job role definitions are constructed from a curated database of position
   descriptions covering common roles across multiple industries. Each role
   specification enumerates required technical skills, soft skills,
   educational qualifications, and experience levels."

Populates the Role / RoleSkill / Skill tables so /api/analysis/roles has
something to serve and /api/analysis/skill-gap-by-role has data to match
against. Idempotent — safe to re-run (skips roles/skills that already exist).

Usage:
    python seed_roles.py
"""

from app import create_app
from app.extensions import db
from app.models import Role, Skill, RoleSkill

# role_name -> (description, industry, experience_level, core_skills, preferred_skills)
ROLES = [
    (
        "Backend Developer",
        "Builds server-side APIs, business logic, and database layers for web applications.",
        "Software Engineering", "fresher",
        ["python", "flask", "mysql", "rest api", "git"],
        ["postgresql", "redis", "aws", "ci/cd", "docker"],
    ),
    (
        "Frontend Developer",
        "Builds user interfaces, client-side logic, and interactive web experiences.",
        "Software Engineering", "fresher",
        ["javascript", "html", "css", "react", "git"],
        ["typescript", "tailwind", "webpack", "rest api"],
    ),
    (
        "Full Stack Developer",
        "Handles both frontend and backend development across the full web application stack.",
        "Software Engineering", "mid",
        ["python", "javascript", "react", "flask", "mysql", "git", "rest api"],
        ["docker", "aws", "typescript", "nodejs", "mongodb"],
    ),
    (
        "Data Scientist",
        "Analyzes data and builds statistical/machine learning models to drive decisions.",
        "Data & AI", "mid",
        ["python", "machine learning", "pandas", "numpy", "sql"],
        ["deep learning", "tensorflow", "pytorch", "scikit-learn"],
    ),
    (
        "ML Engineer",
        "Deploys, scales, and optimizes machine learning models in production systems.",
        "Data & AI", "mid",
        ["python", "machine learning", "pytorch", "docker", "rest api"],
        ["kubernetes", "aws", "tensorflow", "ci/cd"],
    ),
    (
        "DevOps Engineer",
        "Manages CI/CD pipelines, cloud infrastructure, and deployment automation.",
        "Infrastructure", "mid",
        ["docker", "kubernetes", "ci/cd", "linux", "git"],
        ["aws", "terraform", "ansible", "python"],
    ),
]


def seed():
    app = create_app()
    with app.app_context():
        for role_name, description, industry, exp_level, core, preferred in ROLES:
            role = Role.query.filter_by(role_name=role_name).first()
            if not role:
                role = Role(
                    role_name=role_name, description=description,
                    industry=industry, experience_level=exp_level,
                )
                db.session.add(role)
                db.session.flush()
                print(f"[seed] Created role: {role_name}")
            else:
                print(f"[seed] Role already exists, skipping creation: {role_name}")

            for skill_list, gap_type in [(core, "core"), (preferred, "preferred")]:
                for skill_name in skill_list:
                    skill = Skill.query.filter_by(skill_name=skill_name).first()
                    if not skill:
                        skill = Skill(skill_name=skill_name)
                        db.session.add(skill)
                        db.session.flush()

                    exists = RoleSkill.query.filter_by(role_id=role.id, skill_id=skill.id).first()
                    if not exists:
                        db.session.add(RoleSkill(role_id=role.id, skill_id=skill.id, gap_type=gap_type))

        db.session.commit()
        print(f"[seed] Done. {Role.query.count()} roles, {Skill.query.count()} skills in DB.")


if __name__ == "__main__":
    seed()