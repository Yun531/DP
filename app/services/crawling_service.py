from app.dtos.paperItem_dto import PaperItem
from app.dtos.crawled_paper_dto import CrawledPaper
from typing import List, Optional
import requests
import PyPDF2
import logging
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import glob

logger = logging.getLogger(__name__)

class CrawlingService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.download_dir = os.path.abspath("./selenium_downloads")
        os.makedirs(self.download_dir, exist_ok=True)

    def _parse_pdf(self, pdf_path: str) -> Optional[str]:
        try:
            with open(pdf_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_content = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                return '\n'.join(text_content)
        except Exception as e:
            logger.error(f"PDF 파싱 실패: {str(e)}")
            return None

    def crawl_paper_texts(self, papers: List[PaperItem]) -> List[CrawledPaper]:
        logger.info(f"총 {len(papers)}개의 논문 크롤링 시작")
        crawled_papers = []
        for i, paper in enumerate(papers, 1):
            logger.warning(f"[{i}/{len(papers)}] 논문 '{paper.title}' 처리 시작")
            text_content = None
            pdf_path = os.path.join(self.download_dir, 'downloaded_paper.pdf')
            # 기존 파일 삭제
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            # 1. requests로 PDF 다운로드 시도
            try:
                logger.warning(f"논문 '{paper.title}' PDF 직접 다운로드 시도: {paper.pdf_url}")
                response = self.session.get(paper.pdf_url, timeout=30)
                response.raise_for_status()
                with open(pdf_path, "wb") as f:
                    f.write(response.content)
                logger.warning(f"논문 '{paper.title}' PDF 직접 다운로드 성공")
                text_content = self._parse_pdf(pdf_path)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    logger.warning(f"논문 '{paper.title}' 403 에러 발생, 셀레니움 다운로드 시도")
                    # 2. 셀레니움+pyautogui로 PDF 저장
                    chrome_options = Options()
                    chrome_options.add_experimental_option("prefs", {
                        "download.default_directory": self.download_dir,
                        "download.prompt_for_download": False,
                        "plugins.always_open_pdf_externally": True
                    })
                    # chrome_options.add_argument("--headless")  # headless 사용 금지
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    driver = webdriver.Chrome(options=chrome_options)
                    try:
                        driver.get(paper.pdf_url)
                        time.sleep(5)  # 페이지 로딩 대기
                        # 다운로드 완료 대기
                        wait_time = 0
                        latest_pdf_path = None

                        while wait_time < 10:
                            latest_pdf_path = self._find_latest_pdf()
                            if latest_pdf_path and os.path.getsize(latest_pdf_path) > 0:
                                break
                            time.sleep(1)
                            wait_time += 1
                        latest_pdf_path = self._find_latest_pdf()
                        if latest_pdf_path and os.path.getsize(latest_pdf_path) > 0:
                            logger.warning(f"논문 '{paper.title}' PDF 셀레니움 다운로드 성공: {latest_pdf_path}")
                            text_content = self._parse_pdf(latest_pdf_path)
                            os.remove(latest_pdf_path)
                        else:
                            logger.error(f"논문 '{paper.title}' PDF 셀레니움 다운로드 실패: 파일 없음 또는 크기 0")
                    except Exception as se:
                        logger.error(f"논문 '{paper.title}' 셀레니움 다운로드 중 예외: {str(se)}")
                    finally:
                        driver.quit()
                else:
                    logger.error(f"논문 '{paper.title}' PDF 다운로드 실패: {str(e)}")
            except Exception as e:
                logger.error(f"논문 '{paper.title}' PDF 다운로드 중 예외: {str(e)}")
            # 파일 정리
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            # CrawledPaper 생성
            crawled_paper = CrawledPaper(
                paper_id=paper.paper_id,
                title=paper.title,
                thesis_url=paper.pdf_url,
                text_content=text_content or ""
            )
            crawled_papers.append(crawled_paper)
            logger.info(f"[{i}/{len(papers)}] 논문 '{paper.title}' 처리 완료 (텍스트 길이: {len(text_content) if text_content else 0})")
            print(f"[DEBUG] {crawled_paper.title} | 텍스트 길이: {len(crawled_paper.text_content) if crawled_paper.text_content else 0}")
            print(f"[DEBUG] 일부 텍스트: {crawled_paper.text_content[:200] if crawled_paper.text_content else 'None'}")
        logger.info(f"크롤링 완료: 총 {len(crawled_papers)}/{len(papers)}개 논문 성공")
        return crawled_papers

    def _find_latest_pdf(self) -> Optional[str]:
        pdf_files = glob.glob(os.path.join(self.download_dir, '*.pdf'))
        if not pdf_files:
            return None
        latest_pdf = max(pdf_files, key=os.path.getctime)
        return latest_pdf

    def crawl_single_paper_text(self, paper: PaperItem) -> CrawledPaper:
        logger.info(f"단일 논문 크롤링 시작: {paper.title}")
        text_content = None
        pdf_path = os.path.join(self.download_dir, 'downloaded_paper.pdf')
        # 기존 파일 삭제
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        # 1. requests로 PDF 다운로드 시도
        try:
            logger.warning(f"논문 '{paper.title}' PDF 직접 다운로드 시도: {paper.pdf_url}")
            response = self.session.get(paper.pdf_url, timeout=30)
            response.raise_for_status()
            with open(pdf_path, "wb") as f:
                f.write(response.content)
            logger.warning(f"논문 '{paper.title}' PDF 직접 다운로드 성공")
            text_content = self._parse_pdf(pdf_path)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"논문 '{paper.title}' 403 에러 발생, 셀레니움 다운로드 시도")
                chrome_options = Options()
                chrome_options.add_experimental_option("prefs", {
                    "download.default_directory": self.download_dir,
                    "download.prompt_for_download": False,
                    "plugins.always_open_pdf_externally": True
                })
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                driver = webdriver.Chrome(options=chrome_options)
                try:
                    driver.get(paper.pdf_url)
                    time.sleep(5)
                    wait_time = 0
                    latest_pdf_path = None
                    while wait_time < 10:
                        latest_pdf_path = self._find_latest_pdf()
                        if latest_pdf_path and os.path.getsize(latest_pdf_path) > 0:
                            break
                        time.sleep(1)
                        wait_time += 1
                    latest_pdf_path = self._find_latest_pdf()
                    if latest_pdf_path and os.path.getsize(latest_pdf_path) > 0:
                        logger.warning(f"논문 '{paper.title}' PDF 셀레니움 다운로드 성공: {latest_pdf_path}")
                        text_content = self._parse_pdf(latest_pdf_path)
                        os.remove(latest_pdf_path)
                    else:
                        logger.error(f"논문 '{paper.title}' PDF 셀레니움 다운로드 실패: 파일 없음 또는 크기 0")
                except Exception as se:
                    logger.error(f"논문 '{paper.title}' 셀레니움 다운로드 중 예외: {str(se)}")
                finally:
                    driver.quit()
            else:
                logger.error(f"논문 '{paper.title}' PDF 다운로드 실패: {str(e)}")
        except Exception as e:
            logger.error(f"논문 '{paper.title}' PDF 다운로드 중 예외: {str(e)}")
        # 파일 정리
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        # CrawledPaper 생성
        crawled_paper = CrawledPaper(
            title=paper.title,
            thesis_url=paper.pdf_url,
            text_content=text_content or ""
        )
        logger.info(f"단일 논문 처리 완료 (텍스트 길이: {len(text_content) if text_content else 0})")
        print(f"[DEBUG] {crawled_paper.title} | 텍스트 길이: {len(crawled_paper.text_content) if crawled_paper.text_content else 0}")
        print(f"[DEBUG] 일부 텍스트: {crawled_paper.text_content[:200] if crawled_paper.text_content else 'None'}")
        return crawled_paper