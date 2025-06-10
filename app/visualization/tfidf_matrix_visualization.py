import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import seaborn as sns
import matplotlib.font_manager as fm
import platform

# 한글 폰트 설정
if platform.system() == 'Darwin':  # macOS
    plt.rc('font', family='AppleGothic')
elif platform.system() == 'Windows':  # Windows
    plt.rc('font', family='Malgun Gothic')
else:  # Linux
    plt.rc('font', family='NanumGothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 샘플 데이터 생성
meeting_text = "인공지능과 머신러닝의 발전에 대한 회의: 딥러닝 기술의 최신 동향과 응용 분야"
papers = [
    "딥러닝 기반 자연어 처리 기술의 최신 연구 동향과 발전 방향",
    "머신러닝과 딥러닝의 발전에 따른 인공지능 응용 사례 분석",
    "인공지능 기술의 발전과 딥러닝 기반 시스템 구현 방법론",
    "딥러닝 기술의 발전과 인공지능 응용 분야의 확장",
    "머신러닝 알고리즘의 발전과 딥러닝 기반 시스템 설계"
]

# TF-IDF 벡터화
vectorizer = TfidfVectorizer()
texts = [meeting_text] + papers
tfidf_matrix = vectorizer.fit_transform(texts)
feature_names = vectorizer.get_feature_names_out()

# 시각화
plt.figure(figsize=(15, 10))

# 1. TF-IDF 행렬 시각화
plt.subplot(2, 1, 1)
tfidf_array = tfidf_matrix.toarray()
sns.heatmap(tfidf_array, 
            xticklabels=feature_names,
            yticklabels=['회의록'] + [f'논문 {i+1}' for i in range(len(papers))],
            cmap='YlOrRd',
            annot=True,
            fmt='.2f',
            cbar_kws={'label': 'TF-IDF 값'})
plt.title('TF-IDF 행렬', pad=20)
plt.xticks(rotation=45, ha='right')

# 2. 코사인 유사도 계산 과정 시각화
plt.subplot(2, 1, 2)
similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

# 코사인 유사도 계산 과정을 단계별로 시각화
plt.bar(range(len(similarities)), similarities)
plt.title('회의록과 논문 간의 코사인 유사도', pad=20)
plt.xlabel('논문')
plt.ylabel('유사도 점수')
plt.xticks(range(len(papers)), [f'논문 {i+1}' for i in range(len(papers))])

# 각 막대 위에 유사도 값 표시
for i, v in enumerate(similarities):
    plt.text(i, v, f'{v:.3f}', ha='center', va='bottom')

plt.tight_layout()
plt.savefig('tfidf_matrix_visualization.png', dpi=300, bbox_inches='tight')
plt.close()

# 계산 과정 설명을 위한 텍스트 파일 생성
with open('tfidf_explanation.txt', 'w', encoding='utf-8') as f:
    f.write("TF-IDF와 코사인 유사도 계산 과정 설명\n\n")
    f.write("1. TF-IDF 행렬 계산\n")
    f.write("- 각 문서(회의록, 논문)의 단어별 TF-IDF 값을 계산\n")
    f.write("- TF(단어 빈도): 문서 내 단어 출현 빈도\n")
    f.write("- IDF(역문서 빈도): 전체 문서에서 단어의 희소성\n\n")
    
    f.write("2. 코사인 유사도 계산\n")
    f.write("- 회의록 벡터와 각 논문 벡터 간의 코사인 유사도 계산\n")
    f.write("- 유사도 = 두 벡터의 내적 / (벡터 크기의 곱)\n")
    f.write("- 결과값 범위: 0(완전히 다름) ~ 1(완전히 같음)\n\n")
    
    f.write("3. 유사도 점수 해석\n")
    for i, sim in enumerate(similarities):
        f.write(f"논문 {i+1}과의 유사도: {sim:.3f}\n") 