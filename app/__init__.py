from flask import Flask
from .extensions import init_extensions
from .domains import register_domains

def create_app() -> Flask:
    app = Flask(__name__)
    init_extensions(app)
    register_domains(app)               # papers 도메인의 Blueprint 등록
    return app