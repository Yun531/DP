from __future__ import annotations
from typing import Any, Callable, Dict, List

from ..dtos.paperItem_dto import (
    InferenceRequest,
    InferenceResponse,
)
from ..repositories import openalex_repo, parser






def handle_papers_root(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    /api/papers 루트 엔드포인트용 서비스 함수.
    컨트롤러가 받은 JSON을 그대로 받아서 비즈니스 로직을 수행한다.
    (지금은 데모용으로 단순 echo)
    """
    # TODO: 실제 로직 구현

    # meta = retrivePapers(
    #     conference_id="ICML-2025",
    #     keywords=["graph", "neural", "network", "optimization", "method"],  # 5단어
    # )
    # papersText = getPapersText(meta)    # 메타데이터 + 논문 본문

    return {
        "message": "papers_root placeholder response from service",
        "echo": request_body,
    }


def getPapersText(
    conference_json: Dict[str, Any],
    *,
    crawler: Callable[[str], str] = parser.fetch_paper_text,  #  todo: 기본값으로 더미 사용, 스크래핑 함수 구현한 뒤 교체 필요
    status_code: int = 200,
) -> Dict[str, Any]:
    """
    retrivePapers() 결과(JSON dict)에 본문 텍스트를 붙여 반환.
    """
    conference_id = conference_json.get("conference_id")
    paper_records: List[Dict[str, Any]] = conference_json.get("papers", [])

    processed: List[Dict[str, Any]] = []

    for paper in paper_records:
        paper_id = paper.get("paper_id")
        title = paper.get("title")

        pdf_url = paper.get("pdf_url")
        landing_url = paper.get("landing_page_url")
        target_url = pdf_url or landing_url  # 우선순위: PDF → 랜딩

        # ▸ URL 없음 → 실패
        if not target_url:
            processed.append(
                {
                    "paper_id": paper_id,
                    "title": title,
                    "status": "fail",
                    "text_content": "No usable url found in paper record",
                }
            )
            continue

        # ▸ 크롤링 시도 (현재는 더미 fetch_paper_text 사용)
        try:
            text = crawler(target_url)
            processed.append(
                {
                    "paper_id": paper_id,
                    "title": title,
                    "status": "success",
                    "pdf_url": pdf_url,
                    "landing_page_url": landing_url,
                    "text_content": text,
                }
            )
        except Exception as exc:
            processed.append(
                {
                    "paper_id": paper_id,
                    "title": title,
                    "status": "fail",
                    "text_content": str(exc),
                }
            )

    return {
        "conference_id": conference_id,
        "status_code": status_code,
        "papers": processed,
    }


def handle_inference(req: InferenceRequest) -> InferenceResponse:
    """
    1) 논문 검색·크롤링 (Repository)
    2) (선택) LLM 후처리
    3) DTO 직렬화
    """
    papers = openalex_repo.fetch_mock()

    return InferenceResponse(
        conference_id=req.conference_id,
        status_code=200,
        papers=papers,
    )