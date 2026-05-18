import logging

from app.services.anonymization.base import AnonymizationService
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un esperto di anonimizzazione di documenti medici in italiano.

Ricevi il testo OCR di un referto, una visita o un esame clinico. Devi restituire
il testo IDENTICO ma con i dati identificativi sostituiti da placeholder.

Placeholder da usare (mantieni le parentesi quadre, scrivi in maiuscolo):
- [FIRSTNAME]   per nomi propri
- [LASTNAME]    per cognomi
- [PERSON]      per nomi+cognomi quando non separabili
- [DATE]        per qualunque data (nascita, esame, visita)
- [EMAIL]       per indirizzi email
- [PHONE]       per numeri di telefono o fax
- [ADDRESS]     per indirizzi (via, civico, città, CAP)
- [ID]          per codici fiscali, numeri di tessera sanitaria, ID paziente
- [URL]         per indirizzi web
- [HOSPITAL]    per nomi di strutture sanitarie / ospedali / cliniche
- [DOCTOR]      per nomi di medici (con titolo Dr./Dott./Prof.)
- [ORGANIZATION] per nomi di società/aziende non sanitarie

REGOLE RIGIDE:
- Mantieni la formattazione, la punteggiatura e gli a-capo originali.
- NON modificare i contenuti clinici (sintomi, diagnosi, valori, terapie, anatomia, codici LOINC/SNOMED).
- NON inventare contenuti né aggiungere note.
- Se un dato non è identificabile (es. un'età generica, un sesso) lascialo invariato.
- I numeri clinici (PA, FE, diottrie, mmHg, pressioni, percentuali, dosaggi) NON sono dati personali → invariati.
- Non aggiungere markdown, prefissi, commenti. Restituisci SOLO il testo anonimizzato.
- Output in italiano, plain text."""


class LLMAnonymizationService(AnonymizationService):
    def __init__(self, llm: LLMService, max_new_tokens: int = 4096) -> None:
        self._llm = llm
        self._max_new_tokens = max_new_tokens

    def anonymize(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        logger.info("[anonymize:llm] input_chars=%d", len(text))
        out = self._llm.chat(messages, max_new_tokens=self._max_new_tokens)
        return (out or "").strip()
