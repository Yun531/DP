import google.generativeai as genai
import os
from typing import List
from app.dtos.crawled_paper_dto import CrawledPaper
from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.summarized_paper_dto import SummarizedPaper
from google.api_core.exceptions import ResourceExhausted
import time
import random

# Gemini API 토큰 리스트
GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY_1'),
    os.getenv('GEMINI_API_KEY_2'),
    os.getenv('GEMINI_API_KEY_3')
]

# None이 아닌 토큰만 필터링
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]

if not GEMINI_API_KEYS:
    raise ValueError("환경변수에 Gemini API 토큰이 설정되지 않았습니다. .env 파일을 확인해주세요.")

# 토큰 사용 횟수를 추적하는 딕셔너리
token_usage = {key: 0 for key in GEMINI_API_KEYS}

def get_next_token() -> str:
    """사용 가능한 다음 토큰을 반환"""
    if not token_usage:
        raise Exception("사용 가능한 Gemini API 토큰이 없습니다.")
    
    # 가장 적게 사용된 토큰 선택
    min_usage = min(token_usage.values())
    available_tokens = [key for key, usage in token_usage.items() if usage == min_usage]
    return random.choice(available_tokens)

def configure_gemini(token: str):
    """Gemini API 설정"""
    genai.configure(api_key=token)

def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    """여러 토큰을 사용하여 Gemini API 호출"""
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            # 다음 사용할 토큰 선택
            token = get_next_token()
            configure_gemini(token)
            
            # Gemini API 호출
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            # 성공 시 토큰 사용 횟수 증가
            token_usage[token] += 1
            return response.text.strip()
            
        except ResourceExhausted as e:
            last_error = e
            print(f"[LLM Service] 토큰 {token} 할당량 초과. 다른 토큰으로 재시도...")
            # 실패한 토큰의 사용 횟수를 최대로 설정하여 우선순위 낮춤
            token_usage[token] = max(token_usage.values()) + 1
            retries += 1
            time.sleep(2)  # API 제한 회복을 위한 대기
            
        except Exception as e:
            last_error = e
            print(f"[LLM Service] 예상치 못한 에러 발생: {str(e)}")
            retries += 1
            time.sleep(2)
    
    raise Exception(f"최대 재시도 횟수 초과. 마지막 에러: {str(last_error)}")

def extract_keywords(text: str) -> KeywordSummaryResult:
    """
    회의록 텍스트로부터 키워드와 요약을 추출 (Gemini API 활용)
    """
    meeting_prompt = f"""
    The following is a meeting transcript from a research lab.
    Please extract exactly 5 core research keywords from the transcript.
    Each keyword must be a single English word (no phrases).
    Do not include any symbols (e.g., asterisks, parentheses, semicolons).
    Return only the 5 words as a plain list without any formatting or explanations.

    [Meeting Transcript]
    ---
    {text}
    ---
    """
    
    # 키워드 추출
    keywords_text = call_gemini_with_retry(meeting_prompt)
    keywords = []
    for line in keywords_text.splitlines():
        kw = line.strip("-•* ")
        if kw:
            keywords.append(kw)
    keywords = keywords[:5]

    # 요약 추출
    summary_prompt = f"""
    다음은 한 연구실의 회의록입니다.
    이 회의록의 주요 논의 내용을 3~4문장으로 자연스럽게 요약해 주세요.

    [회의록 입력]
    ---
    {text}
    ---
    """
    summary = call_gemini_with_retry(summary_prompt)

    return KeywordSummaryResult(
        summary=summary,
        keywords=keywords
    )

def summarize_papers(papers: List[CrawledPaper]) -> List[SummarizedPaper]:
    """
    크롤링된 논문 리스트에 대해 요약을 추가한 SummarizedPaper 리스트 반환 (Gemini API 활용)
    """
    results = []
    for paper in papers:
        text = paper.text_content
        print(f"[LLM] {paper.title} | 텍스트 길이: {len(text) if text else 0}")
        
        # 텍스트가 비어있거나 너무 짧은 경우만 실패로 처리
        if not text or len(text) < 100:  # 최소 100자 이상은 되어야 함
            print(f"[LLM] {paper.title} | 텍스트가 비어있거나 너무 짧음")
            summary = "크롤링에 실패하였습니다. url에 직접 접속해서 논문을 확인해주세요."
        else:
            paper_prompt = f"""
            다음 논문의 핵심 내용을 10~12문장 이내로 요약해 주세요.  
            논문이 해결하고자 한 문제, 제안한 방법, 실험 결과를 중심으로 간결하게 서술해 주세요.

            [논문 초록]
            ---
            {text}
            ---
            """
            try:
                print(f"[LLM] {paper.title} | Gemini API 호출 시작")
                summary = call_gemini_with_retry(paper_prompt)
                print(f"[LLM] {paper.title} | Gemini API 호출 성공")
            except Exception as e:
                print(f"[LLM] {paper.title} | 요약 중 예외: {e}")
                summary = "요약 불가: LLM 예외 발생"
        
        results.append(SummarizedPaper(
            title=paper.title,
            thesis_url=paper.thesis_url,
            text_content=paper.text_content,
            summary=summary
        ))
    return results
