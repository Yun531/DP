from flask import Flask
from .extensions import init_extensions
from .controllers import bp as papers_bp  # controllers/__init__.py에서 bp를 export

def create_app() -> Flask:
    app = Flask(__name__)
    init_extensions(app)
    app.register_blueprint(papers_bp)  # 이미 url_prefix가 설정돼 있음
    return app