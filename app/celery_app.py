from celery import Celery
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
)

# Celery 앱 설정
celery_app = Celery(
    'dp_project',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=[
        'app.workers.pdf_worker',
        'app.workers.llm_worker',
        'app.workers.invertedindex_worker',
        'app.workers.openalex_worker',
        'app.workers.openalex_reduce_worker',
    ]
)

# Celery 설정
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/1',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_log_level='INFO'
)

celery_app.conf.task_routes = {
    'workers.pdf_worker.*': {'queue': 'pdf'},
    'workers.llm_worker.*': {'queue': 'llm'},
    'workers.openalex_worker.*': {'queue': 'openalex'},
    'workers.openalex_reduce_worker.*': {'queue': 'reduce_openalex'},
    'workers.invertedindex_worker.*': {'queue': 'invertedindex'},
}