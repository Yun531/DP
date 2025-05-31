from celery import Celery

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
celery_app.conf.task_routes = {
    'workers.pdf_worker.*': {'queue': 'pdf'},
    'workers.llm_worker.*': {'queue': 'llm'},
    'workers.openalex_worker.*': {'queue': 'openalex'},
    'workers.openalex_reduce_worker.*': {'queue': 'reduce_openalex'},
    'workers.invertedindex_worker.*': {'queue': 'invertedindex'},
}