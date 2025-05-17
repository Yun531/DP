from typing import List

from pydantic import BaseModel

from app.dtos.summarized_paper_dto import SummarizedPaper


class FinalResponse(BaseModel):
    conference_id: str
    summary: str
    papers: List[SummarizedPaper]