from pydantic import BaseModel

class SummarizedPaper(BaseModel):
    title: str
    thesis_url: str
    text_content: str
    summary: str