from app.dtos.crawled_paper_dto import CrawledPaper
from app.dtos.paperItem_dto import PaperItem

def fetch_paper_text(url: str) -> str:
    """
    (데모용) 주어진 URL에서 논문 본문을 긁어와
    텍스트만 추출·정제해 돌려준다고 가정한 더미 함수
    //todo: 임시 더미 함수, 스크래핑 함수 구현 뒤 교체 필요
    """
    return f"Dummy full‑text content from {url}"

def crawl_paper_texts(papers: list[PaperItem]) -> list[CrawledPaper]:
    """
    논문 리스트를 받아 각 논문의 본문을 크롤링하여 CrawledPaper DTO 리스트로 반환
    """
    results = []

    for paper in papers:
        paper_id = paper.paper_id
        title = paper.title
        thesis_url = paper.pdf_url or paper.landing_page_url

        if not thesis_url:
            results.append(CrawledPaper(
                paper_id=paper_id,
                title=title,
                thesis_url="",
                text_content="No usable url found in paper record"
            ))
            continue

        try:
            text = fetch_paper_text(thesis_url)
            results.append(CrawledPaper(
                paper_id=paper_id,
                title=title,
                thesis_url=thesis_url,
                text_content=text.strip()
            ))
        except Exception as e:
            results.append(CrawledPaper(
                paper_id=paper_id,
                title=title,
                thesis_url=thesis_url,
                text_content=f"Error during crawling: {str(e)}"
            ))
    return results