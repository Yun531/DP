from pydantic import BaseModel

class CrawledPaper(BaseModel):
    title: str
    thesis_url: str
    text_content: str