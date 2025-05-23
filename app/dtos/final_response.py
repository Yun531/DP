from typing import List

from pydantic import BaseModel

from app.dtos.summarized_paper_dto import SummarizedPaper


class RecommendedPaper(BaseModel):
    title: str
    url: str
    summary: str

class FinalResponse(BaseModel):
    summary: str
    keywords: List[str]
    recommendedPapers: List[RecommendedPaper]