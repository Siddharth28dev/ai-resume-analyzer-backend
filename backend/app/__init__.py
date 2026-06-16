import os
from flask import Flask
from app.config import get_config
from app.extensions import cors, db, migrate


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object(get_config())

    # Create upload folder
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Init extensions
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)

    # Register all models so Flask-Migrate detects tables
    with app.app_context():
        from app.models import (               # noqa: F401
            User, Resume,
            Skill, ResumeSkill,
            Role, RoleSkill,
            SkillGap,
            InterviewSession,
            InterviewQuestion, QuestionKeyword,
            InterviewResponse,
            ResponseEvaluation,
            FeedbackReport,
            TodoItem,
        )

    # Register blueprints
    from app.routes.resume_routes   import resume_bp
    from app.routes.analysis_routes import analysis_bp
    from app.routes.interview_routes import interview_bp
    from app.routes.feedback_routes  import feedback_bp

    app.register_blueprint(resume_bp,   url_prefix="/api/resume")
    app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
    app.register_blueprint(interview_bp, url_prefix="/api/interview")
    app.register_blueprint(feedback_bp,  url_prefix="/api/feedback")

    # Health check
    @app.route("/api/health")
    def health():
        return {
            "status":  "ok",
            "message": "AI Resume Analyzer API is running",
            "routes": [
                "POST /api/resume/upload",
                "POST /api/analysis/skill-gap",
                "POST /api/analysis/similarity",
                "POST /api/interview/generate-questions",
                "POST /api/interview/evaluate",
                "POST /api/interview/evaluate-all",
                "POST /api/feedback/generate",
                "POST /api/feedback/todo",
                "DELETE /api/feedback/delete-account",
            ]
        }, 200

    return app
