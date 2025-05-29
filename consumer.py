from app.services.service_registry import get_llm_service

if __name__ == "__main__":
    print("[CONSUMER] 논문 처리용 소비자 시작 중...")
    llm_service = get_llm_service()

    import time
    # main thread가 종료되지 않게 블로킹 대기
    while True:
        time.sleep(60)