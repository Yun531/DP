import requests
import time
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Tuple, List, Dict
import redis
import threading
import queue
import matplotlib
matplotlib.rc('font', family='AppleGothic')  # macOS의 경우
plt.rcParams['axes.unicode_minus'] = False   # 마이너스 깨짐 방지

# 결과를 저장할 큐
result_queue = queue.Queue()

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def on_message_received(message):
    """메시지 수신 콜백"""
    try:
        data = json.loads(message['data'])
        if data.get('type') == 'papers_completed':
            result_queue.put(data)
    except Exception as e:
        print(f"메시지 처리 중 에러 발생: {str(e)}")

def setup_redis_subscriber():
    """Redis 구독자 설정"""
    pubsub = redis_client.pubsub()
    pubsub.subscribe('benchmark_results')
    return pubsub

def calculate_relevance(meeting_text, papers):
    """회의록과 논문 간의 관련도 계산"""
    # TF-IDF 벡터화
    vectorizer = TfidfVectorizer(stop_words='english')
    
    # 회의록과 논문 텍스트를 하나의 리스트로 결합
    texts = [meeting_text] + [paper['summary'] for paper in papers]
    
    # TF-IDF 행렬 생성
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    # 회의록과 각 논문 간의 코사인 유사도 계산
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    
    # 키워드 매칭 점수 계산
    meeting_keywords = set(meeting_text.lower().split())
    keyword_scores = []
    
    for paper in papers:
        paper_keywords = set(paper['summary'].lower().split())
        common_keywords = meeting_keywords.intersection(paper_keywords)
        keyword_score = len(common_keywords) / len(meeting_keywords) if meeting_keywords else 0
        keyword_scores.append(keyword_score)
    
    # 최종 관련도 점수 계산 (코사인 유사도와 키워드 매칭 점수의 가중 평균)
    final_scores = 0.7 * similarities[0] + 0.3 * np.array(keyword_scores)
    
    return final_scores

def test_single_server(meeting_text, meeting_id=None):
    """단일 서버 API 테스트"""
    start_time = time.time()
    
    # API 요청
    response = requests.post(
        'http://localhost:5002/api/papers/inference',
        json={'content': meeting_text, 'meetingId': meeting_id}
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    if response.status_code == 200:
        result = response.json()
        papers = result['recommendedPapers']
        
        # 관련도 계산
        relevance_scores = calculate_relevance(meeting_text, papers)
        
        return {
            'duration': duration,
            'keywords': result['keywords'],
            'summary': result['summary'],
            'papers_count': len(papers),
            'papers': papers,
            'relevance_scores': relevance_scores.tolist()
        }
    else:
        raise Exception(f"API 요청 실패: {response.status_code}")

def test_distributed_server(meeting_text: str, meeting_id: int = None) -> Tuple[float, List[str], str, str, List[Dict], List[float]]:
    """분산 서버 API 테스트"""
    start_time = time.time()
    
    # 최대 3번까지 재시도
    max_retries = 3
    retry_delay = 5  # 재시도 간 대기 시간 (초)
    
    for attempt in range(max_retries):
        try:
            # 초기 요청
            response = requests.post(
                'http://localhost:5001/api/papers/inference',
                json={'content': meeting_text, 'meetingId': meeting_id},
                timeout=300  # 5분 타임아웃
            )
            response.raise_for_status()
            data = response.json()
            
            # 초기 응답 시간
            initial_duration = time.time() - start_time
            print(f"초기 응답 시간: {initial_duration:.2f}초")
            
            # Redis에서 결과 대기
            max_wait_time = 300  # 최대 5분 대기
            start_wait = time.time()
            processed_papers = []
            
            while time.time() - start_wait < max_wait_time:
                try:
                    # 큐에서 결과 확인 (1초 타임아웃)
                    result_data = result_queue.get(timeout=1)
                    if result_data.get('meetingId') == meeting_id:
                        paper = result_data.get('paper', {})
                        if paper:
                            processed_papers.append(paper)
                            print(f"논문 처리 완료 ({len(processed_papers)}/10): {paper.get('title', '')}")
                            
                            # 모든 논문이 처리되었는지 확인
                            if len(processed_papers) >= 10:
                                # 관련도 계산
                                relevance_scores = calculate_relevance(meeting_text, processed_papers)
                                total_duration = time.time() - start_time
                                
                                return (
                                    total_duration,
                                    data.get('keywords', []),
                                    data.get('summary', ''),
                                    data.get('meetingId', ''),
                                    processed_papers,
                                    relevance_scores.tolist()
                                )
                except queue.Empty:
                    continue
            
            raise Exception(f"논문 처리 시간 초과 (처리된 논문: {len(processed_papers)}/10)")
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"요청 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                print(f"{retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"최대 재시도 횟수 초과. 마지막 에러: {str(e)}")

def run_benchmark(meeting_text, meeting_id=None, num_runs=5):
    """벤치마크 실행"""
    # Redis 구독자 설정
    pubsub = setup_redis_subscriber()
    
    # 구독자 스레드 시작
    def listen_for_messages():
        for message in pubsub.listen():
            if message['type'] == 'message':
                on_message_received(message)
    
    consumer_thread = threading.Thread(target=listen_for_messages)
    consumer_thread.daemon = True
    consumer_thread.start()
    
    results = {
        'single': [],
        'distributed': []
    }
    
    print(f"\n=== 벤치마크 시작 (총 {num_runs}회 실행) ===")
    
    try:
        for i in range(num_runs):
            print(f"\n실행 {i+1}/{num_runs}")

            # 분산 서버 테스트
            print("분산 서버 테스트 중...")
            dist_result = test_distributed_server(meeting_text, meeting_id)
            results['distributed'].append({
                'duration': dist_result[0],
                'keywords': dist_result[1],
                'summary': dist_result[2],
                'meeting_id': dist_result[3],
                'papers': dist_result[4],
                'relevance_scores': dist_result[5]
            })
            print(f"완료 시간: {dist_result[0]:.2f}초")
            
            # 단일 서버 테스트
            print("단일 서버 테스트 중...")
            single_result = test_single_server(meeting_text, meeting_id)
            results['single'].append(single_result)
            print(f"완료 시간: {single_result['duration']:.2f}초")
            
            
            # 결과를 파일로 저장
            save_benchmark_result(meeting_id, i+1, single_result, dist_result)
    
    finally:
        # Redis 구독 해제
        pubsub.unsubscribe()
    
    return results

def save_benchmark_result(meeting_id, run_number, single_result, dist_result):
    """벤치마크 결과를 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{meeting_id}_{timestamp}.txt"
    
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"\n=== 벤치마크 결과 (회의 ID: {meeting_id}, 실행 {run_number}) ===\n")
        
        # 단일 서버 결과
        f.write("\n[단일 서버]\n")
        f.write(f"실행 시간: {single_result['duration']:.2f}초\n")
        f.write(f"키워드: {', '.join(single_result['keywords'])}\n")
        f.write(f"요약: {single_result['summary']}\n")
        f.write(f"논문 수: {single_result['papers_count']}\n")
        f.write(f"평균 관련도: {np.mean(single_result['relevance_scores']):.4f}\n")
        
        # 분산 서버 결과
        f.write("\n[분산 서버]\n")
        f.write(f"실행 시간: {dist_result[0]:.2f}초\n")
        f.write(f"키워드: {', '.join(dist_result[1])}\n")
        f.write(f"요약: {dist_result[2]}\n")
        f.write(f"논문 수: {len(dist_result[4])}\n")
        f.write(f"평균 관련도: {np.mean(dist_result[5]):.4f}\n")
        
        f.write("\n" + "="*50 + "\n")

def analyze_results(results):
    """결과 분석 및 시각화"""
    # 데이터프레임 생성
    single_df = pd.DataFrame(results['single'])
    dist_df = pd.DataFrame(results['distributed'])
    
    # 기본 통계
    print("\n=== 성능 분석 결과 ===")
    print("\n단일 서버:")
    print(single_df['duration'].describe())
    print("\n분산 서버 (초기 응답):")
    print(dist_df['duration'].describe())
    
    # 관련도 분석
    print("\n=== 관련도 분석 결과 ===")
    print("\n단일 서버 평균 관련도:", np.mean([np.mean(scores) for scores in single_df['relevance_scores']]))
    print("분산 서버 평균 관련도:", np.mean([np.mean(scores) for scores in dist_df['relevance_scores']]))
    
    # 시각화
    plt.figure(figsize=(15, 10))
    
    # 응답 시간 박스플롯
    plt.subplot(2, 2, 1)
    data = pd.DataFrame({
        '단일 서버': single_df['duration'],
        '분산 서버': dist_df['duration']
    })
    sns.boxplot(data=data)
    plt.title('응답 시간 분포')
    plt.ylabel('시간 (초)')
    
    # 평균 응답 시간 바플롯
    plt.subplot(2, 2, 2)
    means = pd.DataFrame({
        '서버 유형': ['단일 서버', '분산 서버'],
        '평균 응답 시간': [single_df['duration'].mean(), dist_df['duration'].mean()]
    })
    sns.barplot(data=means, x='서버 유형', y='평균 응답 시간')
    plt.title('평균 응답 시간 비교')
    
    # 관련도 박스플롯
    plt.subplot(2, 2, 3)
    relevance_data = pd.DataFrame({
        '단일 서버': [score for scores in single_df['relevance_scores'] for score in scores],
        '분산 서버': [score for scores in dist_df['relevance_scores'] for score in scores]
    })
    sns.boxplot(data=relevance_data)
    plt.title('관련도 분포')
    plt.ylabel('관련도 점수')
    
    # 평균 관련도 바플롯
    plt.subplot(2, 2, 4)
    relevance_means = pd.DataFrame({
        '서버 유형': ['단일 서버', '분산 서버'],
        '평균 관련도': [
            np.mean([np.mean(scores) for scores in single_df['relevance_scores']]),
            np.mean([np.mean(scores) for scores in dist_df['relevance_scores']])
        ]
    })
    sns.barplot(data=relevance_means, x='서버 유형', y='평균 관련도')
    plt.title('평균 관련도 비교')
    
    plt.tight_layout()
    plt.savefig('benchmark_results.png')
    print("\n결과가 'benchmark_results.png'에 저장되었습니다.")

if __name__ == "__main__":
    # 테스트용 회의록 텍스트
    meeting_text = """
    [교수님] 음, 지난주에 이야기했던 리더 선출 알고리즘 논문 다 읽었죠? Raft랑 Viewstamped Replication 비교해봤을 때 우리 과제에는 뭐가 더 맞는 것 같아요?

[석사1 민재] 저는 Raft가 구현하기엔 조금 더 직관적인 것 같습니다. 리더 선출 과정이 로그랑 연계돼 있어서 실험 설계하기 수월할 것 같고요.

[학부연구생 혜진] 근데 Viewstamped Replication은 state transfer를 따로 처리하지 않아도 돼서, 복구 시나리오에선 오히려 안정적인 것 같았어요.

[교수님] 그치, 그게 딱 핵심인데, 지금 우리가 처리하려는 상황은 장애 복구가 많은 분산 환경이잖아. 장애 빈도가 높으면 state transfer cost가 핵심이 되지. 두 방식 다 간단히 프로토타입 만들어보고 실험 돌려보는 게 어때?

[석사2 윤석] 저희 지난 학기에 만든 클러스터 환경 그대로 써도 되겠죠? 총 5개 노드 띄우고, 하나씩 kill해서 리더 전환 시간 측정하는 방식으로요.

[교수님] 좋아. 그럼 그 실험은 윤석 씨가 맡고, 혜진 씨는 Viewstamped Replication 프로토콜 구현 가능한지 검토해보고요. 코드베이스는 지난 분산 키밸류 저장소 코드 재활용하면 되니까. 민재 씨는 Raft 베이스로 정리해서 성능 비교 지표 준비하고요.

[학부연구생 혜진] 아, 근데 그 코드에서 네트워크 딜레이는 어떻게 넣을까요? 지금은 다 localhost에서 돌리니까 의미가 잘 안 보일 것 같아요.

[석사2 윤석] 저 그거 지난주에 tc 설정으로 시뮬레이션 한 번 해봤어요. 50ms 딜레이 넣으면 리더 전환 감지 시간이 확 늘어나더라고요. 실험 조건으로 잘 쓸 수 있을 것 같아요.

[교수님] 오, 잘했네요. 그럼 딜레이도 변수로 넣어서 각 알고리즘이 딜레이에 얼마나 민감한지까지 확인해보죠. 결과는 다음 회의 때 공유하는 걸로 합시다.

    """
    
    # 벤치마크 실행
    results = run_benchmark(meeting_text, meeting_id=1, num_runs=2)
    
    # 결과 분석
    analyze_results(results) 