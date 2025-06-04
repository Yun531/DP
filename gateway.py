import uuid
import itertools
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os

# 환경변수 로드
load_dotenv()

from app.services.llm_service import extract_keywords
from app.celery_app import celery_app

app = Flask(__name__)

@app.route('/api/papers/inference', methods=['POST'])
def handle_meeting():
    data = request.json
    meeting_text = data['content']
    meeting_id = data.get('meetingId')

    ks = extract_keywords(meeting_text)
    keywords = ks.keywords

    combos = []
    for r in range(2, len(keywords)+1):
        combos.extend(list(itertools.combinations(keywords, r)))

    task_id = str(uuid.uuid4())
    for combo in combos:
        celery_app.send_task(
            'workers.openalex_worker.query_papers',
            args=[list(combo), task_id]
        )

    # Reduce 태스크 비동기 발행
    celery_app.send_task(
        'workers.openalex_reduce_worker.reduce',
        args=[task_id, len(combos), meeting_id]
    )

    response = {
        'meetingId': meeting_id,
        'summary': ks.summary,
        'keywords': keywords
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)