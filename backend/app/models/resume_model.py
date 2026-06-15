from app.extensions import db
from datetime import datetime

class Resume(db.Model):
    __tablename__ = "resumes"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_name   = db.Column(db.String(255))
    resume_text = db.Column(db.Text(4294967295))   # LONGTEXT
    education   = db.Column(db.Text)
    experience  = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user               = db.relationship("User",             back_populates="resumes")
    resume_skills      = db.relationship("ResumeSkill",      back_populates="resume", cascade="all, delete")
    skill_gaps         = db.relationship("SkillGap",         back_populates="resume", cascade="all, delete")
    interview_sessions = db.relationship("InterviewSession", back_populates="resume", cascade="all, delete")

    def to_dict(self):
        return {
            "id":          self.id,
            "user_id":     self.user_id,
            "file_name":   self.file_name,
            "education":   self.education,
            "experience":  self.experience,
            "uploaded_at": str(self.uploaded_at),
        }