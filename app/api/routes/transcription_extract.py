import logging

from fastapi import APIRouter, HTTPException, status

from app.graphs.extract_graph import get_extract_graph
from app.schemas.extraction import ExtractionRequest, ExtractionResponse
from app.services.extraction.templates import (
    DEFAULT_SPECIALTY,
    QUESTIONNAIRE_TEMPLATES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcription", tags=["transcription"])


@router.get("/templates")
def list_templates() -> dict:
    """Return the full questionnaire templates catalog (glossary + questionnaires
    per specialty). The frontend uses this to build its UI without hardcoding."""
    return {
        "default": DEFAULT_SPECIALTY,
        "specialties": list(QUESTIONNAIRE_TEMPLATES.keys()),
        "templates": QUESTIONNAIRE_TEMPLATES,
    }


@router.get("/templates/{specialty}")
def get_template(specialty: str) -> dict:
    if specialty not in QUESTIONNAIRE_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"specialty '{specialty}' not found. Available: {list(QUESTIONNAIRE_TEMPLATES.keys())}",
        )
    return QUESTIONNAIRE_TEMPLATES[specialty]


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
