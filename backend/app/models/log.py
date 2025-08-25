from datetime import datetime
from backend.app.extensions import db

class UserBehaviorLog(db.Model):
    __tablename__='user_behavior_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(128), nullable=False)
    duration = db.Column(db.Integer)
    target = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
