from __future__ import annotations

import json
import requests
from urllib.parse import quote_plus
from typing import List, Dict, Any
from app.dtos.paperItem_dto import PaperItem


# ──────────────────────────────────────────────────────────────
# 고정 파라미터
_PER_PAGE   = 4
_DATE_FROM  = "2015-01-01"
_BASE_URL   = "https://api.openalex.org/works"
_SELECT_PART = "display_name,primary_location"
# ──────────────────────────────────────────────────────────────


def retrieve_papers(request_json: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # ---------- 입력 검증 ----------
        conference_id = request_json.conference_id
        keywords: List[str] = request_json.keywords  # type: ignore

        if not conference_id or not isinstance(keywords, list) or len(keywords) != 5:
            raise ValueError("`keywords`는 정확히 5개의 단어가 들어있는 리스트여야 합니다.")

        # ---------- URL 구성 ----------
        search_str  = quote_plus(" ".join(keywords))
        filter_part = f"from_publication_date:{_DATE_FROM},has_fulltext:true"
        url = (
            f"{_BASE_URL}?search={search_str}"
            f"&filter={filter_part}"
            f"&per_page={_PER_PAGE}"
            f"&select={_SELECT_PART}"
        )

        # ---------- API 호출 ----------
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # ---------- 결과 파싱 ----------
        papers = []
        for rank, work in enumerate(data.get("results", []), start=1):
            primary = work.get("primary_location") or {}
            papers.append(
                {
                    "paper_id": rank,
                    "title": work.get("display_name"),
                    "pdf_url": primary.get("pdf_url"),
                    "landing_page_url": primary.get("landing_page_url"),
                }
            )

        return {
            "conference_id": conference_id,
            "status_code": 200,
            "papers": papers,
        }

    except (ValueError, json.JSONDecodeError, requests.RequestException) as exc:
        return {
            "conference_id": request_json.get("conference_id"),
            "status_code": 400,
            "error": str(exc),
        }

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