import json
import logging
import re
from typing import Any

from app.services.fhir.base import FHIRStructuringService
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un esperto di informatica medica e dello standard FHIR R4.
Ricevi un documento medico anonimizzato in italiano (referto, visita, esame).
Produci un Bundle FHIR R4 in JSON, valido, contenente:
- Composition (il documento stesso, con type/section)
- Patient (placeholder anonimo, perché i dati sono stati rimossi)
- Observation (uno per ogni reperto clinico o misurazione)
- DiagnosticReport (se il documento è un esame strumentale)

Regole rigide:
- Rispondi SOLO con il JSON Bundle. Niente markdown, niente testo prima o dopo.
- Inizia con { e termina con }.
- Usa codici LOINC o SNOMED CT quando ragionevoli; altrimenti lascia il campo display testuale.
- Per i dati anonimizzati (es. [FIRSTNAME], [LASTNAME], [DATE]) usa "anonymized" come valore."""


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


_MAX_INPUT_CHARS = 6000


class LLMFHIRStructurer(FHIRStructuringService):
    def __init__(self, llm: LLMService, max_new_tokens: int = 2048) -> None:
        self._llm = llm
        self._max_new_tokens = max_new_tokens

    def structure(self, text: str) -> tuple[dict[str, Any] | None, str]:
        if len(text) > _MAX_INPUT_CHARS:
            logger.warning(
                "[fhir] input text truncated from %d to %d chars",
                len(text),
                _MAX_INPUT_CHARS,
            )
            text = text[:_MAX_INPUT_CHARS]
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        raw = self._llm.chat(messages, max_new_tokens=self._max_new_tokens)
        parsed = _extract_json(raw)
        if parsed is None:
            logger.warning("[fhir] LLM output is not valid JSON; returning raw")
        return parsed, raw
