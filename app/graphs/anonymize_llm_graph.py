from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.registry import get_llm_service, get_ocr_service
from app.services.anonymization.llm_anonymizer import LLMAnonymizationService


class AnonymizeLLMState(TypedDict, total=False):
    image_bytes: bytes
    ocr_text: str
    anonymized_text: str


def _ocr_node(state: AnonymizeLLMState) -> AnonymizeLLMState:
    ocr = get_ocr_service()
    return {"ocr_text": ocr.extract_text(state["image_bytes"])}


def _anonymize_node(state: AnonymizeLLMState) -> AnonymizeLLMState:
    anonymizer = LLMAnonymizationService(get_llm_service())
    return {"anonymized_text": anonymizer.anonymize(state["ocr_text"])}


@lru_cache(maxsize=1)
def get_anonymize_llm_graph():
    graph = StateGraph(AnonymizeLLMState)
    graph.add_node("ocr", _ocr_node)
    graph.add_node("anonymize", _anonymize_node)
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "anonymize")
    graph.add_edge("anonymize", END)
    return graph.compile()
