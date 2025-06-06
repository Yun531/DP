from app.celery_app import celery_app
import redis
import json
import logging

redis_client = redis.Redis(host='localhost', port=6379, db=2)
logger = logging.getLogger(__name__)

@celery_app.task(name='workers.openalex_reduce_worker.reduce', bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 5}, time_limit=300, soft_time_limit=290)
def reduce_openalex_results(self, task_id, total_map_tasks, meeting_id, meeting_text):
    logger.info(f"[REDUCE] 태스크 시작: task_id={task_id}, total_map_tasks={total_map_tasks}, meeting_id={meeting_id}")
    # 모든 map 태스크가 끝났는지 확인
    while int(redis_client.get(f"openalex:{task_id}:done") or 0) < total_map_tasks:
        logger.info(f"[REDUCE] map 태스크 완료 대기 중... 현재 완료: {redis_client.get(f'openalex:{task_id}:done')} / {total_map_tasks}")
        import time; time.sleep(0.5)

    # 모든 논문 결과 집계
    all_results = []
    for item in redis_client.lrange(f"openalex:{task_id}", 0, -1):
        all_results.append(json.loads(item))
    logger.info(f"[REDUCE] 논문 결과 {len(all_results)}개 집계 완료")

    # 논문별 등장 빈도 집계
    freq = {}
    paper_info = {}
    for paper in all_results:
        title = paper['title']
        freq[title] = freq.get(title, 0) + 1
        paper_info[title] = paper

    # 등장 빈도 기준 상위 20개 논문 후보 추출
    top_titles = sorted(freq, key=lambda x: -freq[x])[:20]
    top_papers = [paper_info[title] for title in top_titles]
    logger.info(f"[REDUCE] 상위 20개 논문 선정: {[p['title'] for p in top_papers]}")

    # PDF 워커에 태스크 발행
    for paper in top_papers:
        logger.info(f"[REDUCE] PDF 워커에 태스크 발행: {paper['title']}")
        celery_app.send_task(
            'workers.pdf_worker.download_and_extract',
            args=[paper['title'], paper['pdf'], meeting_id, meeting_text]
        )
    # 필요시 결과를 Spring 서버 등에도 전달 가능
    logger.info(f"[REDUCE] 최종 top_papers 반환")
    return top_papers