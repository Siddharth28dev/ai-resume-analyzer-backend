from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.services.encryption_service import encrypt_if_not_empty, decrypt_if_not_empty


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    _name         = db.Column("name",  db.String(255), nullable=False)
    _email        = db.Column("email", db.String(500), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    resumes            = db.relationship("Resume",           back_populates="user", cascade="all, delete")
    interview_sessions = db.relationship("InterviewSession", back_populates="user", cascade="all, delete")

    @property
    def name(self) -> str:
        return decrypt_if_not_empty(self._name)

    @name.setter
    def name(self, value: str):
        self._name = encrypt_if_not_empty(value)

    @property
    def email(self) -> str:
        return decrypt_if_not_empty(self._email)

    @email.setter
    def email(self, value: str):
        self._email = encrypt_if_not_empty(value)

    def set_password(self, plain_password: str):
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self.password_hash, plain_password)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "created_at": str(self.created_at),
        }