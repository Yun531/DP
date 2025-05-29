from __future__ import annotations
from typing import Any, Dict, List

from ..dtos.final_response import FinalResponse, RecommendedPaper
from ..dtos.paperItem_dto import InferenceRequest, PaperItem
from . import openalex_service, llm_service, crawling_service
from app.services.crawling_service import CrawlingService

from app.services.service_registry import get_openalex_service

import logging
logger = logging.getLogger(__name__)

def handle_papers_root(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    /api/papers 루트 엔드포인트용 서비스 함수.
    컨트롤러가 받은 JSON을 그대로 받아서 비즈니스 로직을 수행한다.
    (지금은 데모용으로 단순 echo)
    """
    # TODO: 실제 로직 구현

    # meta = retrivePapers(
    #     keywords=["graph", "neural", "network", "optimization", "method"],  # 5단어
    # )
    # papersText = getPapersText(meta)    # 메타데이터 + 논문 본문

    return {
        "message": "papers_root placeholder response from service",
        "echo": request_body,
    }


def get_papers_text(
    conference_json: Dict[str, Any],
    *,
    crawler: CrawlingService = CrawlingService(),
    status_code: int = 200,
) -> Dict[str, Any]:
    """
    retrivePapers() 결과(JSON dict)에 본문 텍스트를 붙여 반환.
    """
    paper_records: List[Dict[str, Any]] = conference_json.get("papers", [])
    
    # PaperItem 리스트로 변환
    papers = [
        PaperItem(
            paper_id=paper.get("paper_id"),
            title=paper.get("title"),
            pdf_url=paper.get("pdf_url")
        )
        for paper in paper_records
    ]
    
    # CrawlingService를 사용하여 텍스트 크롤링
    crawled_papers = crawler.crawl_paper_texts(papers)
    
    # 결과 변환
    processed = [
        {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "status": "success" if paper.text_content and not paper.text_content.startswith("Error") else "fail",
            "pdf_url": paper.thesis_url,
            "text_content": paper.text_content,
        }
        for paper in crawled_papers
    ]

    return {
        "status_code": status_code,
        "papers": processed,
    }


def handle_inference(req: InferenceRequest) -> FinalResponse:
    meeting_text = req.content

    # 1. 키워드 및 요약 추출
    keyword_result = llm_service.extract_keywords(meeting_text)
    print(f"[LOG] keyword_result 타입: {type(keyword_result)} | 값: {str(keyword_result)}")

    # 2. 키워드를 기반으로 논문 검색
    try:
        openalex = get_openalex_service()
        papers = openalex.retrieve_and_publish_papers(keyword_result)
        print(f"[LOG] RabbitMQ 정상 작동")
    except Exception as e:
        logger.error("RabbitMQ 발행 실패", exc_info=True)
        papers = openalex_service.retrieve_papers(keyword_result)
    print(f"[LOG] papers 크기: {len(papers)}")

    # 3. 논문 본문 크롤링
    crawling_service = CrawlingService()
    crawled_papers = crawling_service.crawl_paper_texts(papers)

    # 4. 논문 요약 생성
    summarized_papers = llm_service.summarize_papers(crawled_papers)
    # print(f"[LOG] summarized_papers 타입: {type(summarized_papers)} | 값: {str(summarized_papers)}")

    # 5. recommendedPapers 변환
    recommended = [
        RecommendedPaper(
            title=sp.title,
            url=sp.thesis_url,
            summary=sp.summary
        ) for sp in summarized_papers
    ]
    # print(f"[LOG] recommended 타입: {type(recommended)} | 값: {str(recommended)}")

    # 6. 최종 응답 DTO 구성
    final_response = FinalResponse(
        summary=keyword_result.summary,
        keywords=keyword_result.keywords,
        recommendedPapers=recommended,
    )
    # print(f"[LOG] 최종 반환 DTO: {final_response}")
    return final_response