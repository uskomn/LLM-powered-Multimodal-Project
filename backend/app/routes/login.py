from flask import Blueprint, request, jsonify
from backend.app.models.user import User
from backend.app.utils.log import loger_user_action
from backend.app.core.security import create_access_token, verify_password, hash_password
from backend.app.schemas.user import UserRegister, UserLogin, UserInfo
from backend.app.extensions import db

auth_bp = Blueprint('auth', __name__)

# 注册
# 普通用户注册接口
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    if role not in ["user", "admin"]:
        return jsonify({"message": "不允许注册该角色"}), 400

    # 检查用户名是否存在
    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({"message": "Username already exists"}), 400

    # 加密密码并存储
    hashed_password = hash_password(password)
    new_user = User(username=username, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    db.session.refresh(new_user)

    loger_user_action(user_id=new_user.id, action="Register", role=new_user.role, target=request.method)

    return jsonify(UserInfo.from_orm(new_user).dict()), 201

# 登录
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # 获取数据
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    # 查找用户
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "用户不存在"}), 400
    if not verify_password(password, user.password):
        return jsonify({"message": "密码不符"}), 401

    if not user.is_active:
        return jsonify({"error": "该账户已经被禁用"}), 403

    # 生成 JWT 令牌
    access_token = create_access_token({"sub": str(user.id),"role": user.role})
    loger_user_action(user_id=user.id,action="login in",role=user.role,target=request.method)

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "role":user.role,
        "user_id":user.id
    }), 200
