import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import seaborn as sns

# 샘플 데이터 생성
meeting_text = "인공지능과 머신러닝의 발전에 대한 회의"
papers = [
    "인공지능과 머신러닝의 최신 연구 동향",
    "딥러닝 기반 자연어 처리 기술",
    "컴퓨터 비전과 이미지 인식의 발전",
    "강화학습의 응용과 한계점",
    "인공지능의 윤리적 고려사항"
]

# TF-IDF 벡터화
vectorizer = TfidfVectorizer()
texts = [meeting_text] + papers
tfidf_matrix = vectorizer.fit_transform(texts)

# 코사인 유사도 계산
similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

# 시각화
plt.figure(figsize=(15, 10))

# 1. TF-IDF 벡터 시각화
plt.subplot(2, 1, 1)
feature_names = vectorizer.get_feature_names_out()
tfidf_array = tfidf_matrix.toarray()

# 상위 10개 단어만 선택
top_words = 10
top_indices = np.argsort(tfidf_array[0])[-top_words:]
top_words_list = [feature_names[i] for i in top_indices]
top_values = tfidf_array[0][top_indices]

plt.barh(top_words_list, top_values)
plt.title('회의록의 TF-IDF 벡터 (상위 10개 단어)')
plt.xlabel('TF-IDF 값')
plt.ylabel('단어')

# 2. 코사인 유사도 시각화
plt.subplot(2, 1, 2)
plt.bar(range(len(similarities)), similarities)
plt.title('회의록과 논문 간의 코사인 유사도')
plt.xlabel('논문 인덱스')
plt.ylabel('유사도 점수')
plt.xticks(range(len(papers)), [f'논문 {i+1}' for i in range(len(papers))], rotation=45)

plt.tight_layout()
plt.savefig('tfidf_visualization.png', dpi=300, bbox_inches='tight')
plt.close() 