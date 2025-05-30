from pydantic import BaseModel

class SummarizedPaper(BaseModel):
    # paper_id: int
    title: str
    thesis_url: str
    text_content: str
    summary: str