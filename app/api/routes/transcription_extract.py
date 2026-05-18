import logging

from fastapi import APIRouter

from app.graphs.extract_graph import get_extract_graph
from app.schemas.extraction import ExtractionRequest, ExtractionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcription", tags=["transcription"])


@router.post("/extract", response_model=ExtractionResponse)
def extract_questionnaires(payload: ExtractionRequest) -> ExtractionResponse:
    graph = get_extract_graph()
    state = graph.invoke(
        {
            "transcript": payload.transcript,
            "questionnaires": payload.questionnaires,
            "context": payload.context,
            "max_new_tokens": payload.max_new_tokens,
        }
    )
    return ExtractionResponse(
        questionnaires=state.get("result", {}),
        raw=state.get("raw", ""),
    )
