import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.registry import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcription", tags=["transcription"])


_SYSTEM_PROMPT = """Sei un assistente esperto in trascrizione medica italiana.
Ricevi una trascrizione GREZZA prodotta da un modello automatico (Whisper) durante
una visita o un referto clinico. La trascrizione può contenere:
- parole spezzate o ripetute
- termini medici sbagliati o anglicizzati a caso
- punteggiatura mancante
- numeri scritti a parole ("dieci diottrie" invece di "10 D")
- allucinazioni in silenzio (es. ripetizioni o frasi fuori contesto)

Il tuo compito:
1) Restituire la trascrizione corretta, fluente, in italiano clinico corretto.
2) NON aggiungere informazioni inventate. Se qualcosa non si capisce, lascialo
   tra parentesi quadre: [non chiaro].
3) Rimuovi le ripetizioni e le allucinazioni evidenti.
4) Normalizza i numeri e le unità (es. "dieci diottrie" -> "10 D",
   "venti su cento" -> "20/100", "quindici millimetri di mercurio" -> "15 mmHg").
5) Mantieni la terminologia medica corretta del contesto fornito.
6) NON commentare il tuo operato. Restituisci SOLO il testo pulito."""


class RefineRequest(BaseModel):
    text: str = Field(..., description="Trascrizione grezza da pulire")
    context: str | None = Field(
        default=None,
        description="Contesto clinico (specialità, glossario, anamnesi breve)",
    )
    max_new_tokens: int = Field(default=2048, ge=64, le=8192)


class RefineResponse(BaseModel):
    refined: str
    raw: str


@router.post("/refine", response_model=RefineResponse)
def refine_transcription(payload: RefineRequest) -> RefineResponse:
    llm = get_llm_service()

    user_parts: list[str] = []
    if payload.context and payload.context.strip():
        user_parts.append("Contesto clinico:\n" + payload.context.strip())
    user_parts.append("Trascrizione grezza:\n" + payload.text.strip())

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]

    logger.info(
        "[refine] input_chars=%d context_chars=%d",
        len(payload.text),
        len(payload.context or ""),
    )
    refined = llm.chat(messages, max_new_tokens=payload.max_new_tokens)
    return RefineResponse(refined=refined.strip(), raw=payload.text)
