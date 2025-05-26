from flask import Blueprint

bp = Blueprint("papers", __name__, url_prefix="/api/papers")
from . import papers_controller

__all__ = ["bp"]