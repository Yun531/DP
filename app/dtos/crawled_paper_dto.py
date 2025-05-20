from pydantic import BaseModel

class CrawledPaper(BaseModel):
    paper_id: int
    title: str
    thesis_url: str
    text_content: str