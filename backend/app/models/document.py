from datetime import datetime
from backend.app.extensions import db

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.PickleType, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
