from __future__ import annotations

import itertools

import requests, random
import logging
import time
import pika
import json

from urllib.parse import quote_plus, urlparse
from typing import List

from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.paperItem_dto import PaperItem
from bs4 import BeautifulSoup



# ───── 상수
_PER_PAGE       = 15
_TIMEOUT        = 30
_DATE_FROM      = "2015-01-01"
_BASE_URL       = "https://api.openalex.org/works"
_SELECT_PART    = "display_name,primary_location,doi,ids"

TRUSTED_PDF_PREFIXES = (
    "https://arxiv.org/pdf/",
    "https://ojs.aaai.org/index.php/AAAI/article/download/",
    "https://ieeexplore.ieee.org/",
)
_BACKOFF_CODES  = {429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)


# ───── 유틸리티
def is_valid_pdf_url(url: str) -> bool:
    try:
        head = requests.head(url, allow_redirects=True, timeout=_TIMEOUT)
        if head.status_code == 404:
            return False

        final_url = head.url
        domain = urlparse(final_url).netloc

        # MIT Press 특화: title 태그 기반 필터
        if "mit.edu" in domain:
            resp = requests.get(final_url, timeout=_TIMEOUT)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = (soup.title.string or "").strip().lower()
            if "not found" in title:
                return False

        # 신뢰 PDF 링크
        if any(prefix in final_url for prefix in TRUSTED_PDF_PREFIXES):
            return True

        # 일반 필터
        if any(x in final_url for x in ["login", "subscribe", "abstract", "overview"]):
            return False

        return True
    except Exception:
        return False


def query_openalex(keywords: List[str]) -> List[dict]:
    q = quote_plus(" ".join(keywords))
    flt = f"from_publication_date:{_DATE_FROM},has_fulltext:true"
    url = (
        f"{_BASE_URL}?search={q}&filter={flt}&per_page={_PER_PAGE}"
        f"&select=display_name,primary_location"
    )
    print(f"[OpenAlex] 검색 URL: {url}")

    for attempt in range(2):  # 최대 2번 시도 (기본 1회 + 백오프 1회)
        try:
            response = requests.get(url, timeout=_TIMEOUT)
            if response.status_code in _BACKOFF_CODES:
                print(f"[OpenAlex] 상태코드 {response.status_code} → 백오프 시도")
                if attempt == 0:
                    time.sleep(2)  # 2초 대기 후 재시도
                    continue
                else:
                    return []
            data = response.json()
            break
        except Exception as e:
            print(f"[OpenAlex] 요청 실패: {e}")
            if attempt == 0:
                time.sleep(2)
                continue
            return []

    results = []
    for rank, work in enumerate(data.get("results", []), start=1):
        title = work.get("display_name")
        if not title:
            continue

        raw_pdf = (work.get("primary_location") or {}).get("pdf_url")
        if raw_pdf and "bloomsburycollections.com" not in urlparse(raw_pdf).netloc:
            if is_valid_pdf_url(raw_pdf):
                results.append({
                    "rank": rank,
                    "title": title.strip(),
                    "pdf": raw_pdf
                })

    return results


def retrieve_papers(ks: KeywordSummaryResult) -> List[PaperItem]:
    if len(ks.keywords) != 5:
        raise ValueError("`keywords`는 정확히 5개의 단어가 들어있는 리스트여야 합니다.")

    collected = []
    used_titles = set()

    for r in range(5, 0, -1):
        # 1) 이 단계의 모든 조합에 대해 API 호출
        combos = list(itertools.combinations(ks.keywords, r))
        stage_all = []
        for combo in combos:
            papers = query_openalex(list(combo))
            stage_all.extend(papers)

        # 2) 이 단계 내 중복 제목 제거 (첫 등장 유지)
        seen_stage = set()
        stage_unique = []
        for p in stage_all:
            if p["title"] not in seen_stage:
                seen_stage.add(p["title"])
                stage_unique.append(p)

        # 3) 이전 단계에서 이미 뽑힌 논문 제외
        stage_new = [p for p in stage_unique if p["title"] not in used_titles]

        remaining = 10 - len(collected)
        if remaining <= 0:
            break

        # 4) 수집량 초과 시 무작위 선택
        if len(stage_new) > remaining:
            selected = random.sample(stage_new, remaining)
        else:
            selected = stage_new

        collected.extend(selected)
        used_titles.update(p["title"] for p in selected)

        if len(collected) >= 10:
            break

    # PaperItem 형태로 변환
    papers: List[PaperItem] = []
    for idx, cand in enumerate(collected, start=1):
        print(f"[OpenAlex] 선택된 논문: {cand['title']} | PDF: {cand['pdf']}")
        papers.append(
            PaperItem(
                paper_id=idx,
                title   =cand["title"],
                status  ="success",
                pdf_url =cand["pdf"]
            )
        )

    return papers


class OpenAlexService:
    def __init__(self):
        credentials = pika.PlainCredentials('guest', 'guest')
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                credentials=credentials
            )
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='paper_processing')

    def retrieve_and_publish_papers(self, keyword_result: KeywordSummaryResult) -> List[PaperItem]:
        # 논문 검색 유틸 함수 호출
        papers = retrieve_papers(keyword_result)

        # 메시지 변환 (직렬화)
        papers_data = [paper.to_dict() for paper in papers]

        # 큐에 메시지 발행
        self.channel.basic_publish(
            exchange='',
            routing_key='paper_processing',
            body=json.dumps(papers_data),
            properties=pika.BasicProperties(delivery_mode=2)  # 내구성 옵션
        )

        return papers

    def __del__(self):
        if hasattr(self, 'connection') and not self.connection.is_closed:
            self.connection.close()


# url = "https://direct.mit.edu/books/monograph/5167/bookpreview-pdf/2238858"
# print(is_valid_pdf_url(url))