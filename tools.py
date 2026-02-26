import os
import re
import logging
from typing import List
from typing import Any
from typing import Optional

from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

logger = logging.getLogger(__name__)
_search_tool_unavailable_reason: Optional[str] = None


def get_search_tool() -> Optional[Any]:
    """Lazily initialize optional Serper search tool.

    Returns:
        Optional[Any]: Serper tool instance when available, otherwise None.
    """
    global _search_tool_unavailable_reason
    try:
        from crewai_tools.tools.serper_dev_tool import SerperDevTool
        return SerperDevTool()
    except (ImportError, ModuleNotFoundError) as exc:
        reason = str(exc)
        if _search_tool_unavailable_reason != reason:
            logger.warning("Search tool disabled due to dependency mismatch: %s", reason)
            _search_tool_unavailable_reason = reason
        return None


def _clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def read_pdf_text(path: str) -> str:
    """Read and normalize text from a PDF file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF file not found: {path}")

    reader = PdfReader(path)
    pages: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)

    if not pages:
        raise ValueError("The uploaded PDF appears to have no extractable text.")

    return _clean_text("\n\n".join(pages))
