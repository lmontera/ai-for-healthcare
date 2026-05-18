from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.registry import get_llm_service
from app.schemas.extraction import Questionnaire
from app.services.extraction.questionnaire_extractor import QuestionnaireExtractor


class ExtractState(TypedDict, total=False):
    transcript: str
    questionnaires: list[Questionnaire]
    context: str | None
    max_new_tokens: int
    result: dict[str, dict[str, Any]]
    raw: str


def _extract_node(state: ExtractState) -> ExtractState:
    extractor = QuestionnaireExtractor(get_llm_service())
    result, raw = extractor.extract(
        transcript=state["transcript"],
        questionnaires=state["questionnaires"],
        context=state.get("context"),
        max_new_tokens=state.get("max_new_tokens", 2048),
    )
    return {"result": result, "raw": raw}


@lru_cache(maxsize=1)
def get_extract_graph():
    graph = StateGraph(ExtractState)
    graph.add_node("extract", _extract_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", END)
    return graph.compile()
