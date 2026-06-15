import os
from flask import Flask
from app.config import get_config
from app.extensions import cors


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object(get_config())

    # Create upload folder if it doesn't exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Init extensions
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.routes.resume_routes import resume_bp
    from app.routes.analysis_routes import analysis_bp
    from app.routes.interview_routes import interview_bp

    app.register_blueprint(resume_bp, url_prefix="/api/resume")
    app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
    app.register_blueprint(interview_bp, url_prefix="/api/interview")

    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "message": "AI Resume Analyzer API is running"}, 200

    return app
