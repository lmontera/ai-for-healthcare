import logging
from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.registry import get_anonymization_service, get_ocr_service
from app.core.settings import settings

logger = logging.getLogger(__name__)


class AnonymizeState(TypedDict, total=False):
    image_bytes: bytes
    ocr_text: str
    anonymized_text: str


def _ocr_node(state: AnonymizeState) -> AnonymizeState:
    cache_file = settings.ocr_cache_file

    if settings.ocr_cache_enabled and cache_file.exists():
        cached = cache_file.read_text(encoding="utf-8")
        if cached.strip():
            logger.info("[ocr] cache hit: %s (chars=%d)", cache_file, len(cached))
            return {"ocr_text": cached}

    ocr = get_ocr_service()
    ocr_text = ocr.extract_text(state["image_bytes"])
    logger.info("[ocr] extracted chars=%d", len(ocr_text))

    if settings.ocr_cache_enabled:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(ocr_text, encoding="utf-8")
        logger.info("[ocr] cache written: %s", cache_file)

    return {"ocr_text": ocr_text}


def _anonymize_node(state: AnonymizeState) -> AnonymizeState:
    anonymizer = get_anonymization_service()
    anonymized_text = anonymizer.anonymize(state["ocr_text"])
    logger.info(
        "[anonymize] in_chars=%d out_chars=%d",
        len(state["ocr_text"]),
        len(anonymized_text),
    )
    return {"anonymized_text": anonymized_text}


@lru_cache(maxsize=1)
def get_anonymize_graph():
    graph = StateGraph(AnonymizeState)
    graph.add_node("ocr", _ocr_node)
    graph.add_node("anonymize", _anonymize_node)
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "anonymize")
    graph.add_edge("anonymize", END)
    return graph.compile()
