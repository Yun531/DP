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


# key를 발급받지 않아서 요청 제한이 자주 걸림 >> 백오프 거침 >> 최종 응답 반환까지 오래걸림  todo: 키 발급되면 적용
def _get_pdf_semantic(title: str, doi: Optional[str] = None) -> Optional[str]:
    try:
        # DOI 직접 조회
        doi_clean = _clean_doi(doi)
        if doi_clean:
            url = f"{_SS_BASE}/paper/DOI:{quote_plus(doi_clean)}?fields=openAccessPdf"
            js  = _get_json(url)
            pdf = (js.get("openAccessPdf") or {}).get("url")
            if pdf and any(pdf.startswith(p) for p in TRUSTED_PREFIXES):
                return pdf

        # 제목 정확매치 검색
        q   = quote_plus(title)
        url = (
            f"{_SS_BASE}/paper/search"
            f"?query={q}"
            "&limit=5"
            "&match_title=true"
            "&open_access_pdf=true"
            "&fields=title,openAccessPdf"
        )
        js = _get_json(url)
        norm_target = _normalize_title(title)
        for item in js.get("data", []):
            cand_title = _normalize_title(item.get("title") or "")
            if cand_title != norm_target:
                continue
            pdf = (item.get("openAccessPdf") or {}).get("url")
            if pdf and any(pdf.startswith(p) for p in TRUSTED_PREFIXES):
                return pdf
        return None

    except RuntimeError as e:
        print(f"  [ERROR] 실패: {e}")
    except Exception as e:
        print(f"  [ERROR] 예외 발생: {type(e).__name__}: {e}")

    return None

def _get_pdf_arxiv(title: str, ids: List[str]) -> Optional[str]:
    try:
        # arXiv ID 직접 사용
        arxiv_id = next((s.split("arxiv:")[1] for s in ids if s.startswith("arxiv:")), None)
        if arxiv_id:
            link = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return link

        # 제목 검색 (fallback)
        query = quote_plus(title)
        url   = f"http://export.arxiv.org/api/query?search_query=ti:\"{query}\"&max_results=5"
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

def retrieve_papers(ks: KeywordSummaryResult) -> List[PaperItem]:
    try:
        if len(ks.keywords) < 3:
            raise ValueError("`keywords`는 정확히 3개의 단어가 들어있는 리스트여야 합니다.")

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

        # Semantic Scholar 보강
        for cand in candidates:
            if cand["pdf"]:
                continue
            pdf_sem = _get_pdf_semantic(cand["title"], cand["doi"])
            cand["pdf"] = pdf_sem

        # arXiv 보강
        for cand in candidates:
            if cand["pdf"]:
                continue
            pdf_ax = _get_pdf_arxiv(cand["title"], cand["ids"])
            cand["pdf"] = pdf_ax

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

        # while len(papers) < 4:
        #     papers.append(
        #         PaperItem(
        #             paper_id=len(papers) + 1,
        #             title="검색된 논문이 없습니다",
        #             status="dummy"
        #         )
        #     )

        return papers

    except Exception as exc:
        print(f"[OpenAlex][ERROR] 실패: {exc}")
        return []

#----------------------------
# openAlex api 만 사용하는 버전
#----------------------------
def retrieve_papers_(keywordSummaryResult: KeywordSummaryResult) -> List[PaperItem]:
    try:
        keywords      = keywordSummaryResult.keywords
        if len(keywords) != 3:
            raise ValueError("`keywords`는 정확히 3개의 단어가 들어있는 리스트여야 합니다.")

        # -------- URL & API 호출 --------
        search_str  = quote_plus(" ".join(keywords))
        filter_part = f"from_publication_date:{_DATE_FROM},has_fulltext:true"
        url = (
            f"{_BASE_URL}?search={search_str}"
            f"&filter={filter_part}"
            f"&per_page=10"
            f"&select=id,display_name,primary_location"
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

        candidates.sort(key=lambda x: x[0])           # rank 오름차순
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