from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.registry import (
    get_fhir_structurer,
    get_ocr_service,
)
from app.core.settings import settings


class FHIRState(TypedDict, total=False):
    image_bytes: bytes
    ocr_text: str
    anonymized_text: str
    fhir: dict[str, Any] | None
    fhir_raw: str


def _ocr_node(state: FHIRState) -> FHIRState:
    cache_file = settings.ocr_cache_file
    if settings.ocr_cache_enabled and cache_file.exists():
        cached = cache_file.read_text(encoding="utf-8")
        if cached.strip():
            return {"ocr_text": cached}

    ocr = get_ocr_service()
    text = ocr.extract_text(state["image_bytes"])

    if settings.ocr_cache_enabled:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(text, encoding="utf-8")

    return {"ocr_text": text}


def _fhir_node(state: FHIRState) -> FHIRState:
    structurer = get_fhir_structurer()
    fhir, raw = structurer.structure(state["ocr_text"])
    return {"fhir": fhir, "fhir_raw": raw}


@lru_cache(maxsize=1)
def get_fhir_graph():
    graph = StateGraph(FHIRState)
    graph.add_node("ocr", _ocr_node)
    graph.add_node("structure", _fhir_node)
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "structure")
    graph.add_edge("structure", END)
    return graph.compile()
