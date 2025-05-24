from typing import List, Optional
from pydantic import BaseModel, Field


class PaperItem(BaseModel):
    """
    검색된 논문 메타데이터 + text(본문)
    """
    paper_id: int
    title: str
    # status: str = Field(..., pattern="^(success|fail|dummy)$")
    # pdf_url: Optional[str] = None
    status: str = Field(..., pattern="^(success|fail)$")
    pdf_url: str
    text_content: Optional[str] = None


class InferenceRequest(BaseModel):
    content: str


class InferenceResponse(BaseModel):
    status_code: int = 200
    papers: List[PaperItem]