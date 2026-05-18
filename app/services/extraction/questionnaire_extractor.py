import json
import logging
import re
from typing import Any

from app.schemas.extraction import Questionnaire
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un assistente clinico esperto in compilazione automatica di
questionari medici a partire da trascrizioni di visite in italiano. La trascrizione è
un dialogo continuo tra PAZIENTE e MEDICO (senza etichette di speaker — devi dedurre tu
chi sta parlando dal contesto).

Ricevi:
1) una TRASCRIZIONE cumulativa della visita (dialogo paziente↔medico);
2) un elenco di QUESTIONARI da compilare, ciascuno con i suoi campi (name,
   description, e per i campi a scelta anche le options ammesse).

Devi restituire SOLO un JSON con la forma:
{
  "questionnaires": {
    "<questionnaireId>": {
      "<fieldName>": <value>,
      ...
    },
    ...
  }
}

REGOLE FONDAMENTALI — CHI STA PARLANDO:
- DEVI distinguere chiaramente CHI dice ogni informazione: il PAZIENTE o il MEDICO.
- Indicatori che parla il PAZIENTE: prima persona singolare ("ho", "sento", "soffro",
  "prendo", "da tre giorni mi…", "mi fa male…"), risposte a domande, racconto di
  sintomi/storia personale/farmaci assunti, descrizione di disagio.
- Indicatori che parla il MEDICO: tono valutativo/clinico in terza persona ("il
  paziente presenta…", "all'esame obiettivo…", "noto…", "rilevo…", refrazione,
  pressione misurata, lettura di un parametro, formulazione diagnostica,
  prescrizione di terapia/follow-up, domande dirette al paziente.

REGOLE DI ATTRIBUZIONE AI CAMPI:
- ANAMNESI (anamnestici, motivo visita, allergie, terapie preesistenti, sintomi,
  fattori di rischio, abitudini): RIPORTA SOLO quello che dice il PAZIENTE.
  Se il medico riassume/parafrasa quello che il paziente ha detto, va comunque in
  anamnesi (la fonte resta il paziente). Riformula in terza persona, sintetica e
  clinica (es. paziente dice "da tre giorni vedo male" → motivo_visita:
  "calo del visus da tre giorni").
- ESAME OBIETTIVO / parametri misurati (PA, FC, FE, refrazione, tono oculare,
  reperti anatomici, valori strumentali): SOLO ciò che dice o misura il MEDICO
  durante la visita. MAI da quello che dice il paziente.
- DIAGNOSI: solo formulazione conclusiva del MEDICO. Sintetica (max ~150 caratteri).
- TERAPIA: solo quella PRESCRITTA OGGI dal medico (non quella preesistente che
  riferisce il paziente — quella va in "terapia preesistente" se esiste come campo
  in anamnesi).

REGOLE RIGIDE (non negoziabili):
- MAI inventare. Ogni valore deve essere giustificabile da testo esplicito nella
  trascrizione. Se non c'è informazione → OMETTI il campo (non mettere "" o null).
- Se non sei sicuro CHI ha detto un'informazione, OMETTI il campo. È meglio non
  riempirlo che metterlo nel campo sbagliato.
- Per campi numerici: numero JSON, virgola decimale italiana convertita in punto
  (es. "uno virgola venticinque" → 1.25, "dieci diottrie" → 10).
- Per radio/select: ESATTAMENTE uno dei "value" delle options. Mai testo libero.
- Per checkbox multi-select: array di "value" delle options.
- Per booleani: true/false JSON.
- Lateralità (OD/OS, destro/sinistro) sempre preservata sui campi distinti.
- Non duplicare la stessa info tra campi diversi a meno che siano davvero
  campi distinti (es. visus_corretto ≠ sfera/cilindro/asse).
- Nessun markdown, nessun testo prima o dopo il JSON.
- Inizia con { e termina con }."""


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


def _serialize_questionnaires(qs: list[Questionnaire]) -> str:
    payload = []
    for q in qs:
        payload.append(
            {
                "id": q.id,
                "name": q.name,
                "fields": [
                    {
                        k: v
                        for k, v in {
                            "name": f.name,
                            "description": f.description,
                            "type": f.type,
                            "options": [o.model_dump() for o in f.options]
                            if f.options
                            else None,
                        }.items()
                        if v is not None
                    }
                    for f in q.fields
                ],
                "existingData": q.existing_data,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


class QuestionnaireExtractor:
    def __init__(self, llm: LLMService) -> None:
        self._llm = llm

    def extract(
        self,
        transcript: str,
        questionnaires: list[Questionnaire],
        context: str | None = None,
        max_new_tokens: int = 2048,
    ) -> tuple[dict[str, dict[str, Any]], str]:
        user_parts: list[str] = []
        if context and context.strip():
            user_parts.append("CONTESTO CLINICO:\n" + context.strip())
        user_parts.append("TRASCRIZIONE:\n" + transcript.strip())
        user_parts.append(
            "QUESTIONARI DA COMPILARE:\n" + _serialize_questionnaires(questionnaires)
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

        logger.info(
            "[extract] transcript_chars=%d questionnaires=%d",
            len(transcript),
            len(questionnaires),
        )
        raw = self._llm.chat(messages, max_new_tokens=max_new_tokens, json_mode=True)
        parsed = _extract_json(raw)
        if parsed is None:
            logger.warning("[extract] LLM output is not valid JSON; returning empty")
            return {}, raw

        out = parsed.get("questionnaires", {})
        if not isinstance(out, dict):
            logger.warning("[extract] 'questionnaires' is not an object; returning empty")
            return {}, raw
        return out, raw
