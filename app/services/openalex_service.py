from __future__ import annotations

import requests, random, time
import re
import xml.etree.ElementTree as ET
import logging

from urllib.parse import quote_plus, urlparse
from typing import List, Optional

from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.paperItem_dto import PaperItem
from requests.exceptions import JSONDecodeError

# ───── 상수
_PER_PAGE      = 10
_TIME_OUT      = 30
_DATE_FROM     = "2015-01-01"
_BASE_URL      = "https://api.openalex.org/works"
_SS_BASE       = "https://api.semanticscholar.org/graph/v1"
_SELECT_PART   = "display_name,primary_location,doi,ids"

TRUSTED_PREFIXES = (
    "https://arxiv.org/pdf/",
    "https://ojs.aaai.org/index.php/AAAI/article/download/",
    "https://ieeexplore.ieee.org/ielx7/",
)
BACKOFF_CODES  = {429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)

# ───── 유틸리티

def _normalize_title(t: str) -> str:
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

def _get_json(url: str,
              *,
              retries: int = 1,
              backoff_factor: float = 0.8,
              timeout: int = _TIME_OUT,
              **kwargs):
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "ScholarBot/1.0"},
                **kwargs
            )
            # 정상 200 → JSON 디코딩
            if resp.status_code == 200:
                try:
                    return resp.json()
                except JSONDecodeError:
                    # HTML 에러 페이지가 200으로 오는 경우도 백오프
                    pass
            # 429·5xx → 백오프
            elif resp.status_code in BACKOFF_CODES:
                # print(f"  ↳ 백오프: HTTP {resp.status_code}")
                pass

            else:
                resp.raise_for_status()   # 4xx 치명 에러 즉시 전파
        except (requests.Timeout, requests.ConnectionError) as e:
            print(f"  ↳ 네트워크 예외: {type(e).__name__}")

        # 마지막 시도면 빈 딕셔너리 반환
        if attempt == retries:
            return {}

        # 재시도 전 대기
        sleep = backoff_factor * (2 ** attempt) + random.uniform(0, backoff_factor)
        time.sleep(sleep)

    return {}

def _clean_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    doi = doi.strip().lower()
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://doi.org/", "")
    doi = doi.replace("doi:", "")
    return doi


def retrieve_papers(ks: KeywordSummaryResult) -> List[PaperItem]:
    try:
        if len(ks.keywords) < 5:
            raise ValueError("`keywords`는 정확히 5개의 단어가 들어있는 리스트여야 합니다.")

        # OpenAlex 검색
        q   = quote_plus(" ".join(ks.keywords))
        flt = f"from_publication_date:{_DATE_FROM},has_fulltext:true"
        url = (
            f"{_BASE_URL}?search={q}&filter={flt}&per_page={_PER_PAGE}" \
            f"&select={_SELECT_PART}"
        )
        print(f"[OpenAlex] 논문 검색 URL: {url}")
        data = requests.get(url, timeout=_TIME_OUT).json()

        # 초기 후보 집계
        print(f"[OpenAlex] 검색 결과 후보 집계 시작")
        candidates = []
        for rank, work in enumerate(data.get("results", []), start=1):
            title = work.get("display_name")
            if not title:
                continue  # title이 없는 경우 스킵

            raw_pdf = (work.get("primary_location") or {}).get("pdf_url")
            pdf = None
            if raw_pdf and "bloomsburycollections.com" not in urlparse(raw_pdf).netloc:
                pdf = raw_pdf

            candidates.append({
                "rank":  rank,
                "title": title,
                "doi":   work.get("doi"),
                "ids":   work.get("ids", []),
                "pdf":   pdf,
            })
        print(f"[OpenAlex] 후보 논문 수: {len(candidates)}")


        # 최종 필터링 및 정렬
        ready = [c for c in candidates if c["pdf"]]
        ready.sort(key=lambda x: x["rank"])
        selected = ready[:4]
        print(f"[OpenAlex] 최종 선택 논문 수: {len(selected)}")

        # PaperItem 변환
        print(f"[OpenAlex] PaperItem 변환 시작")
        papers: List[PaperItem] = []
        for idx, cand in enumerate(selected, start=1):
            print(f"[OpenAlex] PaperItem 생성: {cand['title']} | PDF: {cand['pdf']}")
            papers.append(
                PaperItem(
                    paper_id = idx,
                    title    = cand["title"],
                    status   = "success",
                    pdf_url  = cand["pdf"],
                )
            )

        return papers

    except Exception as exc:
        print(f"[OpenAlex][ERROR] 실패: {exc}")
        return []

