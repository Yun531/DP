import google.generativeai as genai
genai.configure(api_key="AIzaSyAY3DtZzT-9yIJtoIwMP3_iFhGmNN6TlY0")
from typing import List
from app.dtos.crawled_paper_dto import CrawledPaper
from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.summarized_paper_dto import SummarizedPaper


def extract_keywords(text: str) -> KeywordSummaryResult:
    """
    회의록 텍스트로부터 키워드와 요약을 추출 (Gemini API 활용)
    """
    meeting_prompt = f"""
    The following is a meeting transcript from a research lab.
    Please extract 3 core research keywords in English, each keyword should be 1-3 words, and output as a list.

    [Meeting Transcript]
    ---
    {text}
    ---
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(meeting_prompt)
    # Gemini 응답에서 키워드 리스트 추출 (예: ['키워드1', '키워드2', ...])
    keywords = []
    for line in response.text.strip().splitlines():
        kw = line.strip("-•* ")
        if kw:
            keywords.append(kw)
    keywords = keywords[:5]
    summary_prompt = f"""
    다음은 한 연구실의 회의록입니다.
    이 회의록의 주요 논의 내용을 2~3문장으로 자연스럽게 요약해 주세요.

    [회의록 입력]
    ---
    {text}
    ---
    """
    summary_response = model.generate_content(summary_prompt)
    summary = summary_response.text.strip()

    return KeywordSummaryResult(
        summary=summary,
        keywords=keywords
    )

def summarize_papers(papers: List[CrawledPaper]) -> List[SummarizedPaper]:
    """
    크롤링된 논문 리스트에 대해 요약을 추가한 SummarizedPaper 리스트 반환 (Gemini API 활용)
    """
    results = []
    model = genai.GenerativeModel("gemini-1.5-flash")
    for paper in papers:
        text = paper.text_content
        print(f"[LLM] {paper.title} | 텍스트 길이: {len(text) if text else 0}")
        
        # 텍스트가 비어있거나 너무 짧은 경우만 실패로 처리
        if not text or len(text) < 100:  # 최소 100자 이상은 되어야 함
            print(f"[LLM] {paper.title} | 텍스트가 비어있거나 너무 짧음")
            summary = "요약 불가: 본문 크롤링 실패"
        else:
            # 너무 길면 앞부분만 사용
            if len(text) > 15000:
                print(f"[LLM] {paper.title} | 텍스트가 너무 길어 앞 15000자만 사용")
                text = text[:15000]
            
            paper_prompt = f"""
            다음 논문의 핵심 내용을 4~5문장 이내로 요약해 주세요.  
            논문이 해결하고자 한 문제, 제안한 방법, 실험 결과를 중심으로 간결하게 서술해 주세요.

            [논문 초록]
            ---
            {text}
            ---
            """
            try:
                print(f"[LLM] {paper.title} | Gemini API 호출 시작")
                response = model.generate_content(paper_prompt)
                summary = response.text.strip()
                print(f"[LLM] {paper.title} | Gemini API 호출 성공")
            except Exception as e:
                print(f"[LLM] {paper.title} | 요약 중 예외: {e}")
                summary = "요약 불가: LLM 예외 발생"
        
        results.append(SummarizedPaper(
            paper_id=paper.paper_id,
            title=paper.title,
            thesis_url=paper.thesis_url,
            text_content=paper.text_content,
            summary=summary
        ))
    return results