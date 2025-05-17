from pydantic import BaseModel
from typing import List

class KeywordSummaryResult(BaseModel):
    conference_id: str
    summary: str
    keywords: List[str]