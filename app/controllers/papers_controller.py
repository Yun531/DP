from flask import request, jsonify
from pydantic import ValidationError, BaseModel
from . import bp
from ..dtos.paperItem_dto import InferenceRequest
from ..services.papers_service import handle_inference,handle_papers_root


# POST /api/papers
class PapersRootRequest(BaseModel):
    """todo 추후 필요 필드가 정해지면 수정"""
    action: str | None = None
    payload: dict | None = None


@bp.post("")
def papers_root():
    """
    POST /api/papers
    현재는 입력 JSON을 그대로 echo 하는 플레이스홀더.
    """
    try:
        body = request.get_json(force=True)
        _ = PapersRootRequest.model_validate(body)   # 최소 구조 검증
    except (ValidationError, TypeError):
        return jsonify({"detail": "Invalid JSON body"}), 422

    resp_dict = handle_papers_root(body)
    return jsonify(resp_dict), 200


# POST /api/papers/inference
@bp.post("/inference")
def inference():
    try:
        req_dto = InferenceRequest.model_validate(request.get_json(force=True))
    except ValidationError as exc:
        return jsonify({"detail": exc.errors()}), 422

    resp_dto = handle_inference(req_dto)

    return jsonify(resp_dto.model_dump(mode="json")), 200