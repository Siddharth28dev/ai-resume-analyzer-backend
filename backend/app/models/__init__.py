import os
from flask import Flask
from app.config import get_config
from app.extensions import cors, db, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Init extensions
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)

    # Register all models (so Flask-Migrate sees them)
    with app.app_context():
        from app.models.user_model              import User
        from app.models.resume_model            import Resume
        from app.models.skill_model             import Skill, ResumeSkill
        from app.models.role_model              import Role, RoleSkill
        from app.models.skill_gap_model         import SkillGap
        from app.models.interview_session_model import InterviewSession
        from app.models.interview_question_model import InterviewQuestion, QuestionKeyword
        from app.models.interview_response_model import InterviewResponse
        from app.models.response_evaluation_model import ResponseEvaluation
        from app.models.feedback_model          import FeedbackReport
        from app.models.todo_model              import TodoItem

    # Register blueprints
    from app.routes.resume_routes    import resume_bp
    from app.routes.analysis_routes  import analysis_bp
    from app.routes.interview_routes import interview_bp

    app.register_blueprint(resume_bp,    url_prefix="/api/resume")
    app.register_blueprint(analysis_bp,  url_prefix="/api/analysis")
    app.register_blueprint(interview_bp, url_prefix="/api/interview")

    @app.route("/api/health")
    def health():
        return {"status": "ok", "message": "AI Resume Analyzer API is running"}, 200

    return app