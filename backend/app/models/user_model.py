from app.extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    resumes            = db.relationship("Resume",           back_populates="user", cascade="all, delete")
    interview_sessions = db.relationship("InterviewSession", back_populates="user", cascade="all, delete")

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "created_at": str(self.created_at),
        }