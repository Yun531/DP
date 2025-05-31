from app.celery_app import celery_app
from app.services.llm_service import summarize_papers
from app.dtos.crawled_paper_dto import CrawledPaper
import requests
import os

@celery_app.task(name='workers.llm_worker.summarize_paper')
def summarize_paper(title, meeting_id, txt_path, pdf_url):
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # CrawledPaper 객체 생성
    paper = CrawledPaper(
        title=title,
        thesis_url=pdf_url,
        text_content=text
    )
    
    # llm_service의 summarize_papers 메서드 사용
    summarized = summarize_papers([paper])[0]
    summary = summarized.summary
    
    # 스프링 서버에 요약 결과 저장 요청
    # requests.post(
    #     'http://localhost:8080/api/save_paper',
    #     json={'meetingId': meeting_id, 'title': title, 'summary': summary, 'url': pdf_url}
    # )
    print(f"[LLM Worker] 논문 요약 결과: meeting_id={meeting_id}, title={title}, summary={summary}, pdf_url={pdf_url}")

    # txt 파일 삭제
    try:
        os.remove(txt_path)
        print(f"[LLM Worker] txt 파일 삭제 완료: {txt_path}")
    except Exception as e:
        print(f"[LLM Worker] txt 파일 삭제 실패: {txt_path}, 에러: {e}")