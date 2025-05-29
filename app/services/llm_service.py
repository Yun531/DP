import google.generativeai as genai
genai.configure(api_key="AIzaSyAY3DtZzT-9yIJtoIwMP3_iFhGmNN6TlY0")
from typing import List
from app.dtos.crawled_paper_dto import CrawledPaper
from app.dtos.keyword_summary_dto import KeywordSummaryResult
from app.dtos.summarized_paper_dto import SummarizedPaper
import pika
import json


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
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(meeting_prompt)
    # Gemini 응답에서 키워드 리스트 추출 (예: ['키워드1', '키워드2', ...])
    keywords = []
    for line in response.text.strip().splitlines():
        kw = line.strip("-•* ")
        if kw:
            keywords.append(kw)
    keywords = keywords[:5]

    # #발표용 키워드
    # keywords = ["Big Data", "Lamda Architecture", "Hadoop"]

    summary_prompt = f"""
    다음은 한 연구실의 회의록입니다.
    이 회의록의 주요 논의 내용을 3~4문장으로 자연스럽게 요약해 주세요.

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
            summary = "크롤링에 실패하였습니다. url에 직접 접속해서 논문을 확인해주세요."
        else:
            # 너무 길면 앞부분만 사용
            # if len(text) > 15000:
            #     print(f"[LLM] {paper.title} | 텍스트가 너무 길어 앞 15000자만 사용")
            #     text = text[:15000]
            
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


class LLMService:
    def __init__(self):
        # RabbitMQ 연결
        credentials = pika.PlainCredentials('guest', 'guest')
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',  # 도커 사용 시: rabbitmq
                credentials=credentials
            )
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='paper_processing')
        self.start_consumer()

    def start_consumer(self):
        def consumer_thread():
            def callback(ch, method, properties, body):
                try:
                    papers_data = json.loads(body)
                    papers = [Paper.from_dict(p) for p in papers_data]

                    print(f"📦 받은 메시지 - 총 {len(papers)}개 논문")
                    for paper in papers:
                        print(f"- 논문 ID: {paper.paper_id}")
                        print(f"  제목: {paper.title}")
                        print(f"  URL: {paper.thesis_url}")
                        print(f"  내용 길이: {len(paper.text_content)}자")
                        print("--------------------------------------------------")

                except Exception as e:
                    print(f"[ERROR] 메시지 처리 중 예외 발생: {e}")
                finally:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue='paper_processing',
                on_message_callback=callback
            )
            print('[RabbitMQ] 논문 메시지 소비 시작...')
            self.channel.start_consuming()

        self.consumer_thread = threading.Thread(target=consumer_thread, daemon=True)
        self.consumer_thread.start()
