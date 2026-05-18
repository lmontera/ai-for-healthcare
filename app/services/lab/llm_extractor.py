import json
import logging
import re
from typing import Any

from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un esperto di referti di laboratorio clinico in italiano.

Ricevi il testo OCR di un referto e devi estrarre SOLO i RISULTATI DI LABORATORIO
(analisi del sangue, urine, esami biochimici, ematologici, ormonali, ecc.).

NON includere:
- diagnosi, conclusioni, anamnesi, terapie
- dati anagrafici del paziente, dati del medico, ospedale, indirizzi
- referti strumentali (ECG, RX, TC, RMN, ecografie, OCT, ecc.) — solo laboratorio
- titoli di sezione, intestazioni, totali, note

Per ogni risultato di laboratorio estrai:
- "name": nome dell'analita (es. "Emoglobina", "Glicemia", "Colesterolo totale")
- "value": valore numerico misurato (numero JSON, NON stringa). Se mancante: null.
- "unit": unità di misura (es. "g/dL", "mg/dL", "mmol/L", "%"). Se mancante: null.
- "min_range_value": estremo inferiore del range di riferimento (numero o null)
- "max_range_value": estremo superiore del range di riferimento (numero o null)

Regole sui numeri:
- Virgola decimale italiana convertita in punto ("4,5" -> 4.5).
- Se il range è espresso come "< 200" -> min_range_value=null, max_range_value=200.
- Se il range è "> 60" -> min_range_value=60, max_range_value=null.
- Se il range è "5-10" -> min_range_value=5, max_range_value=10.
- Se il valore è qualitativo (es. "negativo", "presente") OMETTI il risultato.

Output: SOLO JSON con questa forma:
{
  "results": [
    {"name": "...", "value": 14.5, "unit": "g/dL", "min_range_value": 12.0, "max_range_value": 15.5},
    ...
  ]
}

- Nessun markdown, nessun testo prima o dopo. Inizia con { e termina con }.
- Se non trovi alcun risultato di laboratorio, ritorna {"results": []}."""


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


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


class LabResultsExtractor:
    def __init__(self, llm: LLMService, max_new_tokens: int = 4096) -> None:
        self._llm = llm
        self._max_new_tokens = max_new_tokens

    def extract(self, ocr_text: str) -> tuple[list[dict], str]:
        if not ocr_text or not ocr_text.strip():
            return [], ""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": ocr_text},
        ]
        logger.info("[lab:extract] input_chars=%d", len(ocr_text))
        raw = self._llm.chat(
            messages,
            max_new_tokens=self._max_new_tokens,
            json_mode=True,
            think=True,
        )
        raw = raw or ""
        logger.info("[lab:extract] output_chars=%d", len(raw))
        parsed = _extract_json(raw)
        if not parsed:
            logger.warning("[lab:extract] LLM did not return valid JSON. head=%r", raw[:300])
            return [], raw
        items = parsed.get("results", [])
        if not isinstance(items, list):
            return [], raw
        results: list[dict] = []
        for r in items:
            if not isinstance(r, dict):
                continue
            name = (r.get("name") or "").strip()
            if not name:
                continue
            results.append(
                {
                    "name": name,
                    "value": _to_float(r.get("value")),
                    "unit": (r.get("unit") or None),
                    "min_range_value": _to_float(r.get("min_range_value")),
                    "max_range_value": _to_float(r.get("max_range_value")),
                }
            )
        logger.info("[lab:extract] extracted=%d results", len(results))
        return results, raw
