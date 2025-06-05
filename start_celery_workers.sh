#!/bin/bash

# 로그 디렉토리 생성
mkdir -p logs

# 타임스탬프 생성
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 환경변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# PDF Worker (4개 프로세스)
echo "Starting PDF Worker..."
celery -A app.celery_app worker -Q pdf -n pdf_worker@%h -c 4 -l info > "logs/pdf_worker_${TIMESTAMP}.log" 2>&1 &
echo $! > "logs/worker_pids_${TIMESTAMP}.txt"

# LLM Worker (2개 프로세스 - API 제한 고려)
echo "Starting LLM Worker..."
celery -A app.celery_app worker -Q llm -n llm_worker@%h -c 3 -l info > "logs/llm_worker_${TIMESTAMP}.log" 2>&1 &
echo $! >> "logs/worker_pids_${TIMESTAMP}.txt"

# OpenAlex Worker (4개 프로세스)
echo "Starting OpenAlex Worker..."
celery -A app.celery_app worker -Q openalex -n openalex_worker@%h -c 4 -l info > "logs/openalex_worker_${TIMESTAMP}.log" 2>&1 &
echo $! >> "logs/worker_pids_${TIMESTAMP}.txt"

# Reduce OpenAlex Worker (2개 프로세스)
echo "Starting Reduce OpenAlex Worker..."
celery -A app.celery_app worker -Q reduce_openalex -n reduce_openalex_worker@%h -c 2 -l info > "logs/reduce_openalex_worker_${TIMESTAMP}.log" 2>&1 &
echo $! >> "logs/worker_pids_${TIMESTAMP}.txt"

# InvertedIndex Worker (4개 프로세스)
echo "Starting InvertedIndex Worker..."
celery -A app.celery_app worker -Q invertedindex -n invertedindex_worker@%h -c 6 -l info > "logs/invertedindex_worker_${TIMESTAMP}.log" 2>&1 &
echo $! >> "logs/worker_pids_${TIMESTAMP}.txt"

echo "Starting Relevance Worker..."
celery -A app.celery_app worker -Q relevance -n relevance_worker@%h -c 4 -l info > "logs/relevance_worker_${TIMESTAMP}.log" 2>&1 &
echo $! >> "logs/worker_pids_${TIMESTAMP}.txt"

echo "Starting Flower..."
celery -A app.celery_app flower --port=5555 > "logs/flower_${TIMESTAMP}.log" 2>&1 &
echo "flower=$!" >> "logs/worker_pids_${TIMESTAMP}.txt"

echo "All workers started. Logs are in the logs directory."
echo "To stop workers, use: ./stop_celery_workers.sh ${TIMESTAMP}"
