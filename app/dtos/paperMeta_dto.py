from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class PaperMeta(BaseModel):
    """
    개별 논문 메타데이터 (retrivePapers 1건)
    """
    paper_id: int = Field(..., ge=1)
    title: str
    pdf_url: Optional[HttpUrl] = None          # PDF 직링크가 없을 수도 있음
    landing_page_url: HttpUrl


class RetrievalResponse(BaseModel):
    conference_id: str
    status_code: int = 200
    papers: List[PaperMeta]