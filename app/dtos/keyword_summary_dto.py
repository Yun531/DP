from pydantic import BaseModel
from typing import List

class KeywordSummaryResult(BaseModel):
    summary: str
    keywords: List[str]