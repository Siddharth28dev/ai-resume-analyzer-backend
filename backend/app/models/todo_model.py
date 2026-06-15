from app.extensions import db
from datetime import datetime

class TodoItem(db.Model):
    __tablename__ = "todo_items"

    id           = db.Column(db.Integer, primary_key=True)
    feedback_id  = db.Column(db.Integer, db.ForeignKey("feedback_reports.id"), nullable=False)
    task         = db.Column(db.Text, nullable=False)
    priority     = db.Column(db.Enum("high", "medium", "low"), default="medium")
    status       = db.Column(db.Enum("pending", "completed"),  default="pending")
    resource_url = db.Column(db.String(500))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    feedback = db.relationship("FeedbackReport", back_populates="todo_items")

    def to_dict(self):
        return {
            "id":           self.id,
            "task":         self.task,
            "priority":     self.priority,
            "status":       self.status,
            "resource_url": self.resource_url,
        }