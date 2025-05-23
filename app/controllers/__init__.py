from flask import Blueprint

bp = Blueprint("papers", __name__, url_prefix="/api/papers")

# 라우트 자동 임포트
from . import papers_controller