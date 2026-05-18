import json
import logging
import re
from typing import Any

from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un classificatore esperto di documenti clinici italiani.

Ricevi:
1) il TESTO OCR di un documento clinico (può essere imperfetto);
2) l'elenco delle CATEGORIE disponibili (key, label, description).

Devi assegnare al documento UNA SOLA categoria — la più probabile — e fornire
uno score 0-1 per OGNI categoria proposta. Lo score più alto deve coincidere con
la categoria scelta.

Output: SOLO JSON con questa forma:
{
  "category": "<key>",
  "confidence": <numero 0-1>,
  "scores": {
    "<key_1>": <numero 0-1>,
    "<key_2>": <numero 0-1>,
    ...
  },
  "reasoning": "<una frase breve in italiano che spiega la scelta>"
}

REGOLE RIGIDE:
- "category" DEVE essere ESATTAMENTE una delle key fornite nell'elenco.
- Per OGNI key dell'elenco deve esserci una entry in "scores" (anche se 0.0).
- "confidence" = score della categoria scelta.
- "reasoning" max ~150 caratteri, in italiano.
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


def _format_categories(categories: list[dict]) -> str:
    lines = []
    for c in categories:
        line = f'- key="{c["key"]}" | label="{c["label"]}"'
        desc = c.get("description")
        if desc:
            line += f' | desc="{desc}"'
        lines.append(line)
    return "\n".join(lines)


class LLMDocumentClassifier:
    def __init__(self, llm: LLMService, max_new_tokens: int = 1024) -> None:
        self._llm = llm
        self._max_new_tokens = max_new_tokens

    def classify(
        self, ocr_text: str, categories: list[dict]
    ) -> tuple[dict[str, Any], str]:
        if not categories:
            raise ValueError("categories list is empty")
        if not ocr_text or not ocr_text.strip():
            return (
                {"category": "other", "confidence": 0.0, "scores": {}, "reasoning": "Documento vuoto."},
                "",
            )

        valid_keys = {c["key"] for c in categories}
        cats_block = _format_categories(categories)
        user = (
            f"CATEGORIE DISPONIBILI:\n{cats_block}\n\n"
            f"TESTO OCR DEL DOCUMENTO:\n{ocr_text}"
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
        logger.info(
            "[classify] input_chars=%d categories=%d",
            len(ocr_text),
            len(categories),
        )
        raw = self._llm.chat(
            messages,
            max_new_tokens=self._max_new_tokens,
            json_mode=True,
            think=True,
        ) or ""
        logger.info("[classify] output_chars=%d", len(raw))

        parsed = _extract_json(raw)
        if not parsed:
            logger.warning("[classify] LLM did not return valid JSON. head=%r", raw[:300])
            return (
                {
                    "category": "other",
                    "confidence": 0.0,
                    "scores": {c["key"]: 0.0 for c in categories},
                    "reasoning": "Classificazione non disponibile (output LLM non valido).",
                },
                raw,
            )

        chosen = (parsed.get("category") or "").strip()
        if chosen not in valid_keys:
            logger.warning("[classify] LLM returned unknown key %r; falling back to 'other'", chosen)
            chosen = "other" if "other" in valid_keys else next(iter(valid_keys))

        scores_raw = parsed.get("scores", {})
        if not isinstance(scores_raw, dict):
            scores_raw = {}
        scores = {}
        for c in categories:
            v = scores_raw.get(c["key"], 0.0)
            try:
                scores[c["key"]] = max(0.0, min(1.0, float(v)))
            except (ValueError, TypeError):
                scores[c["key"]] = 0.0

        confidence = parsed.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else scores.get(chosen)
        except (ValueError, TypeError):
            confidence = scores.get(chosen)

        return (
            {
                "category": chosen,
                "confidence": confidence,
                "scores": scores,
                "reasoning": str(parsed.get("reasoning") or "")[:300] or None,
            },
            raw,
        )
