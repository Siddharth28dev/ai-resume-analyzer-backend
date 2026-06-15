from app.extensions import db

class SkillGap(db.Model):
    __tablename__ = "skill_gaps"

    id        = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    skill_id  = db.Column(db.Integer, db.ForeignKey("skills.id"),  nullable=False)
    severity  = db.Column(db.Enum("low", "medium", "high"), default="medium")

    resume = db.relationship("Resume", back_populates="skill_gaps")
    skill  = db.relationship("Skill",  back_populates="skill_gaps")

    def to_dict(self):
        return {
            "id":        self.id,
            "skill":     self.skill.skill_name if self.skill else None,
            "severity":  self.severity,
        }