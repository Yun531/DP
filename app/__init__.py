from flask import Flask
from .extensions import init_extensions
from .controllers import bp as papers_bp  # controllers/__init__.py에서 export한 Blueprint

def create_app() -> Flask:
    app = Flask(__name__)
    init_extensions(app)
    app.register_blueprint(papers_bp)  # /api/papers
    return app