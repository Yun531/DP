from __future__ import annotations

import requests
from urllib.parse import quote_plus
from typing import List

from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.paperItem_dto import PaperItem, InferenceRequest

# ──────────────────────────────────────────────────────────────
# 고정 파라미터
_PER_PAGE    = 10
_DATE_FROM   = "2015-01-01"
_BASE_URL    = "https://api.openalex.org/works"
_SELECT_PART = "display_name,primary_location"   # 실제 사용
# ──────────────────────────────────────────────────────────────


def retrieve_papers(keywordSummaryResult: KeywordSummaryResult) -> List[PaperItem]:
    """
    • OpenAlex에서 최대 10편 검색
    • pdf_url이 있는 논문만 원래 rank가 작은 순으로 4편 선별
    • paper_id는 1·2·3·4처럼 연속 번호로 부여
    """
    try:
        conference_id = keywordSummaryResult.conference_id
        keywords      = keywordSummaryResult.keywords
        if not conference_id or len(keywords) != 5:
            raise ValueError("`keywords`는 정확히 5개의 단어가 들어있는 리스트여야 합니다.")

        # -------- URL & API 호출 --------
        search_str  = quote_plus(" ".join(keywords))
        filter_part = f"from_publication_date:{_DATE_FROM},has_fulltext:true"
        url = (
            f"{_BASE_URL}?search={search_str}"
            f"&filter={filter_part}"
            f"&per_page={_PER_PAGE}"
            f"&select={_SELECT_PART}"
        )
        data = requests.get(url, timeout=30).json()

        # -------- pdf_url 존재 논문만 추리고 rank 기준 정렬 --------
        candidates = []
        for rank, work in enumerate(data.get("results", []), start=1):
            pdf = (work.get("primary_location") or {}).get("pdf_url")
            if pdf:
                candidates.append((rank, work, pdf))   # (원래 rank, 원본 dict, pdf_url)

        candidates.sort(key=lambda x: x[0])            # rank 오름차순
        selected = candidates[:4]                      # 상위 4편

        # -------- PaperItem 리스트 생성 (paper_id = 1,2,3,4) --------
        papers: List[PaperItem] = []
        for idx, (_, work, pdf) in enumerate(selected, start=1):
            papers.append(
                PaperItem(
                    paper_id=idx,                      # 1,2,3,4
                    title=work.get("display_name"),
                    status="success",
                    pdf_url=pdf,
                    text_content=None
                )
            )

        return papers

    except Exception as exc:
        print(f"[ERROR] Failed to retrieve papers: {exc}")
        return []

def fetch_mock() -> List[PaperItem]:
    """외부 OpenAlexAPI 대체 더미 데이터"""
    return [
        PaperItem(
            paper_id=1,
            title="Paper A",
            status="success",
            pdf_url="https://example.com/paperA.pdf",
            landing_page_url="https://publisher.com/paperA",
            text_content="Lorem ipsum...",
        ),
        PaperItem(
            paper_id=2,
            title="Paper B",
            status="fail",
            text_content="No usable url found in paper record",
        ),
        PaperItem(
            paper_id=3,
            title="Paper C",
            status="success",
            pdf_url="https://example.com/paperC.pdf",
            landing_page_url="https://publisher.com/paperC",
            text_content="Lorem ipsum...",
        ),
        PaperItem(
            paper_id=4,
            title="Paper D",
            status="success",
            pdf_url="https://example.com/paperD.pdf",
            landing_page_url="https://publisher.com/paperD",
            text_content="Lorem ipsum...",
        ),
    ]
