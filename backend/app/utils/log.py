from backend.app.models.log import UserBehaviorLog
from backend.app.extensions import db
from datetime import datetime

# 将用户行为记录到数据库中
def loger_user_action(user_id, action, role,  duration=0, target=None):
    log_entry=UserBehaviorLog(
        user_id=user_id,
        action=action,
        role=role,
        duration=duration,
        target=target,
        created_at=datetime.utcnow())
    db.session.add(log_entry)
    db.session.commit()
    db.session.refresh(log_entry)

# 得到用户信息
def get_logs_by_role(role):
    return UserBehaviorLog.query.filter_by(role=role).all()