from app.celery_app import celery_app
from app.services.llm_service import summarize_papers
from app.dtos.crawled_paper_dto import CrawledPaper
import requests
import os
import redis
import json
import logging

# 로거 설정
logger = logging.getLogger('celery.task')

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@celery_app.task(name='workers.llm_worker.summarize_paper')
def summarize_paper(title, meeting_id, txt_path, pdf_url):
    logger.info(f"[LLM Worker] 논문 요약 시작: {title}")
    
    try:
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
        try:
            response = requests.post(
                'http://localhost:8080/api/save_paper',
                json={'meetingId': meeting_id, 'title': title, 'summary': summary, 'url': pdf_url}
            )
            response.raise_for_status()
            logger.info(f"[LLM Worker] 논문 요약 결과 저장 완료: meeting_id={meeting_id}, title={title}")
        except Exception as e:
            logger.error(f"[LLM Worker] 논문 요약 결과 저장 실패: {str(e)}")

        # Redis에 결과 발행
        try:
            result = {
                'type': 'papers_completed',
                'meetingId': meeting_id,
                'paper': {
                    'title': title,
                    'summary': summary,
                    'url': pdf_url
                }
            }
            redis_client.publish('benchmark_results', json.dumps(result))
            logger.info(f"[LLM Worker] Redis에 결과 발행 완료: {title}")
        except Exception as e:
            logger.error(f"[LLM Worker] Redis 결과 발행 실패: {str(e)}")

        # txt 파일 삭제
        try:
            os.remove(txt_path)
            logger.info(f"[LLM Worker] txt 파일 삭제 완료: {txt_path}")
        except Exception as e:
            logger.error(f"[LLM Worker] txt 파일 삭제 실패: {txt_path}, 에러: {e}")
        
        logger.info(f"[LLM Worker] 논문 요약 작업 완료: {title}")
        
    except Exception as e:
        logger.error(f"[LLM Worker] 논문 요약 중 예외 발생: {str(e)}")
        raise