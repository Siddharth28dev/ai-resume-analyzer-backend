from app.extensions import db
from datetime import datetime

class InterviewResponse(db.Model):
    __tablename__ = "interview_responses"

    id            = db.Column(db.Integer, primary_key=True)
    question_id   = db.Column(db.Integer, db.ForeignKey("interview_questions.id"), nullable=False)
    answer_text   = db.Column(db.Text(4294967295))  # LONGTEXT
    audio_path    = db.Column(db.String(500))
    response_time = db.Column(db.Integer)           # seconds
    answered_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    question   = db.relationship("InterviewQuestion",  back_populates="responses")
    evaluation = db.relationship("ResponseEvaluation", back_populates="response",
                                  cascade="all, delete", uselist=False)

    def to_dict(self):
        return {
            "id":            self.id,
            "question_id":   self.question_id,
            "answer_text":   self.answer_text,
            "response_time": self.response_time,
            "answered_at":   str(self.answered_at),
        }