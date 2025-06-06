from app.celery_app import celery_app
from app.services.openalex_service import query_openalex
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=2)

@celery_app.task(name='workers.openalex_worker.query_papers', bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 5}, time_limit=300, soft_time_limit=290)
def query_papers_task(self, combo, task_id):
    papers = query_openalex(combo)  # [{title, pdf, ...}, ...]
    # 각 논문에 combo 정보도 함께 저장 (reduce에서 활용 가능)
    for paper in papers:
        paper['combo'] = combo
        redis_client.rpush(f"openalex:{task_id}", json.dumps(paper))
    # Reduce 워커에 완료 신호(카운트)도 보낼 수 있음
    redis_client.incr(f"openalex:{task_id}:done")
    return True