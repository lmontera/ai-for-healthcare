from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.registry import get_llm_service, get_ocr_service
from app.services.lab.llm_extractor import LabResultsExtractor


class LabState(TypedDict, total=False):
    image_bytes: bytes
    max_new_tokens: int
    ocr_text: str
    results: list[dict]
    raw: str


def _ocr_node(state: LabState) -> LabState:
    ocr = get_ocr_service()
    return {"ocr_text": ocr.extract_text(state["image_bytes"])}


def _extract_node(state: LabState) -> LabState:
    extractor = LabResultsExtractor(
        get_llm_service(),
        max_new_tokens=state.get("max_new_tokens", 4096),
    )
    results, raw = extractor.extract(state.get("ocr_text", ""))
    return {"results": results, "raw": raw}


@lru_cache(maxsize=1)
def get_lab_graph():
    graph = StateGraph(LabState)
    graph.add_node("ocr", _ocr_node)
    graph.add_node("extract", _extract_node)
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "extract")
    graph.add_edge("extract", END)
    return graph.compile()
