from __future__ import annotations

import requests
import re
import xml.etree.ElementTree as ET

from urllib.parse import quote_plus
from typing import List, Optional

from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.paperItem_dto import PaperItem

# ──────────────────────────────────────────────────────────────
# ───── 상수
_PER_PAGE      = 10
_TIME_OUT      = 30
_DATE_FROM     = "2015-01-01"
_BASE_URL      = "https://api.openalex.org/works"
_SS_BASE       = "https://api.semanticscholar.org/graph/v1"
_SELECT_PART   = "display_name,primary_location,doi,ids"

## semantic api 의 경우 .pdf 링크를 받아와도 논문 랜딩 페이지 등으로 리다이렉션 되는경우가 많음을 확인
## 확실하게 pdf 로 연결되는 경로에 대해 선언 후 사용
TRUSTED_PREFIXES = (
    "https://arxiv.org/pdf/",
    "https://ojs.aaai.org/index.php/AAAI/article/download/",
    "https://ieeexplore.ieee.org/ielx7/",
)


def _normalize_title(t: str) -> str:
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

## 런타임마다 실행 결과가 한번씩 다른것 같은데 아직 확인 못함
def _get_pdf_semantic(title: str, doi: Optional[str] = None) -> Optional[str]:
    try:
        # DOI 우선
        if doi:
            url = f"{_SS_BASE}/paper/DOI:{quote_plus(doi)}?fields=openAccessPdf"
            js  = requests.get(url, timeout=_TIME_OUT).json()
            pdf = (js.get("openAccessPdf") or {}).get("url")
            if pdf and any(pdf.startswith(p) for p in TRUSTED_PREFIXES):
                return pdf

        # 제목 검색 후 완전 일치
        q   = quote_plus(title)
        url = f"{_SS_BASE}/paper/search?query={q}&limit=3&fields=title,openAccessPdf"
        js  = requests.get(url, timeout=_TIME_OUT).json()
        norm_target = _normalize_title(title)
        for item in js.get("data", []):
            cand_title = item.get("title") or ""
            if _normalize_title(cand_title) != norm_target:
                continue
            pdf = (item.get("openAccessPdf") or {}).get("url")
            if pdf and any(pdf.startswith(p) for p in TRUSTED_PREFIXES):
                return pdf
    except Exception as e:
        print(f"  ↳ 예외 발생: {e}")
    return None


def _get_pdf_arxiv(title: str, ids: List[str]) -> Optional[str]:
    try:
        # arXiv ID 직접 사용
        arxiv_id = next((s.split("arxiv:")[1] for s in ids if s.startswith("arxiv:")), None)
        if arxiv_id:
            pdf = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return pdf

        # 제목 검색
        query = quote_plus(title)
        url   = f"http://export.arxiv.org/api/query?search_query=ti:\"{query}\"&max_results=1"
        xml   = requests.get(url, timeout=_TIME_OUT).text
        root  = ET.fromstring(xml)
        ns    = {"a": "http://www.w3.org/2005/Atom"}
        base  = _normalize_title(title)
        for entry in root.findall("a:entry", ns):
            e_title = entry.find("a:title", ns).text or ""
            if _normalize_title(e_title) != base:
                continue
            for l in entry.findall("a:link", ns):
                if l.attrib.get("type") == "application/pdf":
                    return l.attrib["href"]
    except Exception as e:
        print(f"  ↳ 예외 발생: {e}")
    return None

# ──────────────────────────────────────────────────────────────
# 메인 파이프라인
# ──────────────────────────────────────────────────────────────

def retrieve_papers(ks: KeywordSummaryResult) -> List[PaperItem]:
    try:
        if not ks.conference_id or len(ks.keywords) != 5:
            raise ValueError("`keywords`는 정확히 5개의 단어가 들어있는 리스트여야 합니다.")

        # 1) OpenAlex 검색
        q   = quote_plus(" ".join(ks.keywords))
        flt = f"from_publication_date:{_DATE_FROM},has_fulltext:true"
        url = (
            f"{_BASE_URL}?search={q}&filter={flt}&per_page={_PER_PAGE}" \
            f"&select={_SELECT_PART}"
        )
        data = requests.get(url, timeout=_TIME_OUT).json()

        # 2) 초기 후보 집계
        candidates = []
        for rank, work in enumerate(data.get("results", []), start=1):
            title = work.get("display_name")
            pdf   = (work.get("primary_location") or {}).get("pdf_url")
            candidates.append({
                "rank":  rank,
                "title": title,
                "doi":   work.get("doi"),
                "ids":   work.get("ids", []),
                "pdf":   pdf,
            })

        # 3) Semantic Scholar 보강
        for cand in candidates:
            if cand["pdf"]:
                continue
            pdf_sem = _get_pdf_semantic(cand["title"], cand["doi"])
            cand["pdf"] = pdf_sem

        # 4) arXiv 보강
        for cand in candidates:
            if cand["pdf"]:
                continue
            pdf_ax = _get_pdf_arxiv(cand["title"], cand["ids"])
            cand["pdf"] = pdf_ax

        # 5) 최종 필터링 및 정렬
        ready = [c for c in candidates if c["pdf"]]
        ready.sort(key=lambda x: x["rank"])
        selected = ready[:7]

        # 6) PaperItem 변환
        papers: List[PaperItem] = []
        for idx, cand in enumerate(selected, start=1):
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
        print(f"[ERROR] 실패: {exc}")
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
