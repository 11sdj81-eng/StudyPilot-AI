"""Web Retrieval Supplement — controlled, optional web search for missing content.

Source priority (immutable): 教材/PPT/真题 > AI推导 > 联网检索 > AI兜底
"""

from core.pdf_content_v2.web_retrieval.web_retrieval_config import (
    WebRetrievalConfig, get_config,
)
from core.pdf_content_v2.web_retrieval.web_result_schema import WebResult, WebRetrievalReport
from core.pdf_content_v2.web_retrieval.web_retriever import WebRetriever
from core.pdf_content_v2.web_retrieval.web_source_validator import WebSourceValidator
