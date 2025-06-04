from app.celery_app import celery_app
from app.services.crawling_service import CrawlingService
from app.dtos.paperItem_dto import PaperItem
from app.celery_app import celery_app
import os
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=3)

@celery_app.task(name='workers.pdf_worker.download_and_extract')
def download_and_extract(title, pdf_url, meeting_id, meeting_text):
    crawler = CrawlingService()

    # todo PaperItem에서 paper_id 제거
    paper_item = PaperItem(paper_id=0, title=title, pdf_url=pdf_url, status="success")
    crawled = crawler.crawl_single_paper_text(paper_item)
    text = crawled.text_content

    # txt 파일로 저장
    txt_dir = './papers_txt'
    os.makedirs(txt_dir, exist_ok=True)
    txt_path = os.path.join(txt_dir, f'{meeting_id}_{title}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(crawled.text_content)

    # Redis에 논문 정보 push
    paper_info = {
        'title': title,
        'txt_path': txt_path,
        'text_content': crawled.text_content,
        'meeting_id': meeting_id,
        'pdf_url': pdf_url
    }
    redis_client.rpush(f"relevance:{meeting_id}:papers", json.dumps(paper_info))

    # relevance_worker에 태스크 발행 (논문 1개 도착 알림)
    celery_app.send_task(
        'workers.relevance_worker.check_and_select',
        args=[meeting_id, meeting_text]
    )

    # 역색인 워커에는 텍스트 자체 전달
    chunks = chunk_text(text, 2000)
    for chunk in chunks:
        celery_app.send_task(
            'workers.invertedindex_worker.build_inverted_index',
            args=[chunk, meeting_id]
        )

def chunk_text(text, chunk_size=2000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]



