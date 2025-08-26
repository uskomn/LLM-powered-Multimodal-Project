from flask import Flask
from backend.app.config import Config
from backend.app.extensions import db
from backend.app.routes.ingest import ingest_bp
from backend.app.routes.login import auth_bp
from backend.app.routes.retrieval import retrieval_bp
from backend.app.routes.chat import rag_bp
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # 初始化扩展
    db.init_app(app)

    # 注册蓝图
    app.register_blueprint(ingest_bp, url_prefix="/ingest")
    app.register_blueprint(retrieval_bp,url_prefix="/retrieval")
    app.register_blueprint(auth_bp,url_prefix="/auth")
    app.register_blueprint(rag_bp,url_prefix="/rag")

    with app.app_context():
        db.create_all()

    return app
