import importlib
import pkgutil
from flask import Flask


def register_domains(app: Flask):
    """
    domains 패키지 하위에 있는 <domain>.<controllers> 모듈에서
    'bp' 변수를 찾아 앱에 등록한다.
    """
    package = importlib.import_module(__name__)  # app.domains
    for _, name, ispkg in pkgutil.iter_modules(package.__path__):
        if not ispkg:
            continue                      # 서브패키지(도메인)만 탐색
        mod_name = f"{__name__}.{name}.controllers"
        try:
            controllers = importlib.import_module(mod_name)
            if hasattr(controllers, "bp"):
                app.register_blueprint(controllers.bp)
        except ModuleNotFoundError:
            # controllers 패키지가 없으면 건너뜀
            pass