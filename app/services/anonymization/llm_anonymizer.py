import json
import logging
import re

from app.services.anonymization.base import AnonymizationService
from app.services.anonymization.utils import mask_text_with_entities
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un esperto di anonimizzazione di documenti medici in italiano.

Ricevi il testo OCR di un referto, una visita o un esame clinico.
Devi IDENTIFICARE i DATI PERSONALI presenti nel testo e restituirli come JSON.

NON riscrivere il testo, NON commentare: restituisci SOLO JSON con questa forma:

{
  "entities": [
    {"text": "<estratto LETTERALE dal documento>", "label": "<LABEL>"},
    ...
  ]
}

ETICHETTE possibili (label):
- FIRSTNAME    nomi propri di persone
- LASTNAME     cognomi
- PERSON       nome+cognome quando non separabili
- DATE         date personali (nascita, visita, esame, ricovero)
- EMAIL        indirizzi email
- PHONE        telefoni / fax
- ADDRESS      vie, civici, città, CAP
- ID           codici fiscali, ID paziente, tessera sanitaria, n. cartella
- URL          link personali
- DOCTOR       nomi di medici (Dr./Dott./Prof. + cognome)
- HOSPITAL     nome PROPRIO della struttura emittente del referto

COSA È DATO PERSONALE (DA includere):
- nomi/cognomi di persone (pazienti, medici, parenti, contatti)
- date riferite a persone (nascita, decesso, visita, esame)
- email, telefoni, fax personali
- indirizzi di residenza, città, CAP
- codici identificativi (CF, tessera sanitaria, ID, partita IVA)
- URL personali

COSA NON È DATO PERSONALE (NON includere):
- nomi di STRUMENTI/dispositivi/macchinari/software (es. Heidelberg Spectralis, OCT, Topcon)
- nomi di FARMACI e principi attivi
- nomi di ESAMI/procedure (tonometria, ECG, fluorangiografia, emocromo, TC)
- termini anatomici, patologie, sintomi, diagnosi
- codici clinici (LOINC, SNOMED, ICD-10, ATC, MeSH, NABM)
- unità di misura, range di riferimento (mmHg, mg/dL, v.n. 0.5-1.2)
- valori numerici clinici (PA, FE, diottrie, dosaggi, %)
- società scientifiche, riviste, linee guida (ESC, NICE, GOLD, SIO)
- strutture sanitarie generiche ("il policlinico", "l'ASL")
- titoli generici senza nome ("il medico", "il radiologo", "il paziente")

REGOLE RIGIDE:
- "text" DEVE essere ESATTAMENTE come compare nel documento (stessa maiuscola/minuscola, stessi spazi e punteggiatura). NON modificare nulla.
- Una entry per ogni occorrenza: se "Mario Rossi" compare 3 volte, metti 3 entries.
- Se non ci sono dati personali, ritorna {"entities": []}.
- Nessun markdown, nessun testo prima o dopo. Inizia con { e termina con }."""


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _spans_from_entities(text: str, llm_entities: list[dict]) -> list[dict]:
    """For each entity returned by the LLM (with literal `text` snippet),
    find its position in the original `text` and return spans.

    Handles multiple occurrences by tracking a per-snippet cursor.
    """
    out: list[dict] = []
    cursor_by_text: dict[str, int] = {}
    for e in llm_entities:
        snippet = (e.get("text") or "").strip()
        label = (e.get("label") or "PII").strip().upper()
        if not snippet:
            continue
        cursor = cursor_by_text.get(snippet, 0)
        pos = text.find(snippet, cursor)
        if pos < 0:
            # restart from the beginning
            pos = text.find(snippet)
            if pos < 0:
                logger.warning("[anonymize:llm] snippet not found in original: %r", snippet[:60])
                continue
        out.append(
            {
                "label": label,
                "text": snippet,
                "start": pos,
                "end": pos + len(snippet),
                "score": 1.0,
            }
        )
        cursor_by_text[snippet] = pos + len(snippet)
    # sort by start for downstream masking
    out.sort(key=lambda x: x["start"])
    return out


class LLMAnonymizationService(AnonymizationService):
    def __init__(self, llm: LLMService, max_new_tokens: int = 8192) -> None:
        self._llm = llm
        self._max_new_tokens = max_new_tokens

    def detect_entities(self, text: str) -> list[dict]:
        if not text or not text.strip():
            return []
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        logger.info("[anonymize:llm] input_chars=%d", len(text))
        raw = self._llm.chat(
            messages,
            max_new_tokens=self._max_new_tokens,
            json_mode=True,
            think=True,
        )
        raw = raw or ""
        logger.info("[anonymize:llm] output_chars=%d head=%r", len(raw), raw[:200])
        parsed = _extract_json(raw)
        if not parsed:
            logger.warning("[anonymize:llm] LLM did not return valid JSON. Full output: %r", raw[:2000])
            return []
        ents = parsed.get("entities", [])
        if not isinstance(ents, list):
            logger.warning("[anonymize:llm] entities is not a list, parsed=%r", parsed)
            return []
        spans = _spans_from_entities(text, ents)
        logger.info("[anonymize:llm] llm_entities=%d resolved_spans=%d", len(ents), len(spans))
        return spans

    def anonymize(self, text: str) -> str:
        return mask_text_with_entities(text, self.detect_entities(text))
