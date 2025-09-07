from flask import Flask
from backend.app.config import Config
from backend.app.extensions import db
from backend.app.routes.ingest import ingest_bp
from backend.app.routes.login import auth_bp
from backend.app.routes.retrieval import search_bp
from backend.app.routes.chat import chat_bp
from backend.app.routes.kg import kg_bp
from backend.app.routes.PRA import pra_bp
from flask_cors import CORS
from flask_jwt_extended import JWTManager

jwt = JWTManager()
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)

    # 注册蓝图
    app.register_blueprint(ingest_bp, url_prefix="/ingest")
    app.register_blueprint(search_bp,url_prefix="/retrieval")
    app.register_blueprint(auth_bp,url_prefix="/auth")
    app.register_blueprint(chat_bp,url_prefix="/rag")
    app.register_blueprint(kg_bp,url_prefix="/kg")
    app.register_blueprint(pra_bp,url_prefix="/PRA")

    with app.app_context():
        db.create_all()

    return app
