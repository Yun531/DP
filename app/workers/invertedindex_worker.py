from app.celery_app import celery_app
import pymysql
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name='workers.invertedindex_worker.build_inverted_index', bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 5}, time_limit=300, soft_time_limit=290)
def build_and_save_inverted_index(self, text, meeting_id):
    logger.info(f"[INVERTED INDEX] 태스크 시작: meeting_id={meeting_id}")
    # 1. 띄어쓰기 단위로 단어 분리
    words = text.split()
    # 2. 모두 소문자로 변환
    words = [w.lower() for w in words]
    # 3. 중복 제거 (원하면 set(words) 사용)
    unique_words = set(words)
    logger.info(f"[INVERTED INDEX] {len(unique_words)}개 단어 추출 및 중복 제거 완료")

    # 4. MySQL에 저장
    conn = pymysql.connect(
        host='localhost',
        user='janghyunjun',
        password='Wonjoon1206!',
        db='ds',
        charset='utf8mb4'
    )
    try:
        with conn.cursor() as cursor:
            for word in unique_words:
                sql = "INSERT INTO inverted_index (paper_word, meeting_id) VALUES (%s, %s)"
                cursor.execute(sql, (word, meeting_id))
        conn.commit()
        logger.info(f"[INVERTED INDEX] DB 저장 완료: {len(unique_words)}개 단어")
    finally:
        conn.close()
        logger.info(f"[INVERTED INDEX] DB 연결 종료")