import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY          = os.getenv("SECRET_KEY", "dev-secret-key")
    UPLOAD_FOLDER       = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH  = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    ALLOWED_EXTENSIONS  = set(os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt").split(","))
    SPACY_MODEL         = os.getenv("SPACY_MODEL", "en_core_web_sm")
    SQLALCHEMY_DATABASE_URI     = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/ai_resume_analyzer")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_map = {"development": DevelopmentConfig, "production": ProductionConfig}

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)