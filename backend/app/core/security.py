from passlib.context import CryptContext
from jose import jwt, JWTError
from functools import wraps
from datetime import datetime, timedelta
from flask import current_app,request,jsonify
from backend.app.models.user import User
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from backend.app.utils.log import loger_user_action
import time

SECRET_KEY = "aeijcmejsiefmeiaeigr"  # 替换为强随机密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 过期时间

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 加密密码
def hash_password(password: str):
    return pwd_context.hash(password)

# 验证密码
def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

# 生成token
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 解析token
def decode_access_token(token: str):
    credentials_exception = Exception("Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


def require_role(required_roles, action_desc=None):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            start_time = time.time()

            # 获取当前用户 ID
            current_user_id = get_jwt_identity()
            print(f"Decoded user id: {current_user_id}")

            # 查询数据库获取用户信息
            user = User.query.get(current_user_id)
            if not user:
                return jsonify({"message": "User not found"}), 404

            user_id = user.id
            user_role = user.role

            # 如果 required_roles 是字符串，转为列表统一处理
            if isinstance(required_roles, str):
                roles = [required_roles]
            else:
                roles = required_roles

            # 权限检查
            if user_role not in roles:
                return jsonify({"error": "Forbidden: You do not have permission for this action"}), 403

            # 正式执行接口逻辑
            response = fn(*args, **kwargs)

            # 统计耗时
            end_time = time.time()
            duration = round(end_time - start_time, 2)

            loger_user_action(
                user_id=user_id,
                action=action_desc or fn.__name__,
                role=user_role,
                duration=duration,
                target=request.path
            )


            return response

        return wrapped

    return wrapper