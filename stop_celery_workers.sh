#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./stop_celery_workers.sh <timestamp>"
    echo "Example: ./stop_celery_workers.sh 20240601_023016"
    exit 1
fi

TIMESTAMP=$1
PID_FILE="logs/worker_pids_${TIMESTAMP}.txt"

if [ ! -f "$PID_FILE" ]; then
    echo "Error: PID file not found: $PID_FILE"
    exit 1
fi

# PID 파일에서 각 워커의 PID를 읽어서 종료
while IFS='=' read -r name pid; do
    if [ -n "$pid" ]; then
        echo "Stopping $name (PID: $pid)..."
        kill $pid 2>/dev/null || echo "Process $pid not found"
    fi
done < "$PID_FILE"

# 로그 파일 정리
echo "Cleaning up log files..."
rm -f "logs/pdf_worker_${TIMESTAMP}.log"
rm -f "logs/llm_worker_${TIMESTAMP}.log"
rm -f "logs/openalex_worker_${TIMESTAMP}.log"
rm -f "logs/reduce_openalex_worker_${TIMESTAMP}.log"
rm -f "logs/invertedindex_worker_${TIMESTAMP}.log"
rm -f "logs/flower_${TIMESTAMP}.log"
rm -f "$PID_FILE"

# logs 디렉토리가 비어있으면 삭제
if [ -z "$(ls -A logs 2>/dev/null)" ]; then
    rmdir logs
    echo "Removed empty logs directory"
fi

echo "All workers stopped and log files cleaned up." 