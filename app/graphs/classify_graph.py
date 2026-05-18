from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.registry import get_llm_service, get_ocr_service
from app.services.document_classification.llm_classifier import LLMDocumentClassifier


class ClassifyState(TypedDict, total=False):
    image_bytes: bytes
    categories: list[dict]
    max_new_tokens: int
    ocr_text: str
    result: dict
    raw: str


def _ocr_node(state: ClassifyState) -> ClassifyState:
    ocr = get_ocr_service()
    return {"ocr_text": ocr.extract_text(state["image_bytes"])}


def _classify_node(state: ClassifyState) -> ClassifyState:
    classifier = LLMDocumentClassifier(
        get_llm_service(),
        max_new_tokens=state.get("max_new_tokens", 1024),
    )
    result, raw = classifier.classify(
        state.get("ocr_text", ""),
        state.get("categories", []),
    )
    return {"result": result, "raw": raw}


@lru_cache(maxsize=1)
def get_classify_graph():
    graph = StateGraph(ClassifyState)
    graph.add_node("ocr", _ocr_node)
    graph.add_node("classify", _classify_node)
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "classify")
    graph.add_edge("classify", END)
    return graph.compile()
