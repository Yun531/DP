from typing import List

from pydantic import BaseModel

from app.dtos.summarized_paper_dto import SummarizedPaper


class FinalResponse(BaseModel):
    summary: str
    papers: List[SummarizedPaper]