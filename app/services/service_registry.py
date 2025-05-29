from app.services.llm_service import LLMService
from app.services.openalex_service import OpenAlexService

_llm_service = None
_openalex_service = None

def get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

def get_openalex_service():
    global _openalex_service
    if _openalex_service is None:
        _openalex_service = OpenAlexService()
    return _openalex_service