from typing import List

from app.dtos.crawled_paper_dto import CrawledPaper
from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.summarized_paper_dto import SummarizedPaper


def extract_keywords(conference_id: str, text: str) -> KeywordSummaryResult:
    """
    회의록 텍스트로부터 키워드와 요약을 추출
    """
    # TODO: 실제 Gemini API 호출로 교체
    return KeywordSummaryResult(
        conference_id=conference_id,
        summary="Transformer 모델의 연산 효율성에 대한 논의 요약...",
        keywords=["graph", "neural", "network", "optimization", "framework"]
    )

def summarize_papers(papers: List[CrawledPaper]) -> List[SummarizedPaper]:
    """
    크롤링된 논문 리스트에 대해 요약을 추가한 SummarizedPaper 리스트 반환
    """
    results = []

    for paper in papers:
        text = paper.text_content
        if not text or "error" in text.lower() or "no usable" in text.lower():
            summary = "요약 불가: 본문 크롤링 실패"
        else:
            # TODO: 실제 Gemini 요약 API 호출
            summary = f"[요약] {paper.title} 논문에 대한 요약 결과입니다."

        results.append(SummarizedPaper(
            paper_id=paper.paper_id,
            title=paper.title,
            thesis_url=paper.thesis_url,
            text_content=paper.text_content,
            summary=summary
        ))

    return results