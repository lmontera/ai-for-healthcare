import logging

from transformers import pipeline

from app.core.device import pipeline_device
from app.services.anonymization.base import AnonymizationService
from app.services.anonymization.utils import mask_text_with_entities

logger = logging.getLogger(__name__)

_MODEL_NAME = "openai/privacy-filter"


class OpenAIPrivacyFilterService(AnonymizationService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        device = pipeline_device()
        logger.info("[anonymize] device=%s", "GPU" if device >= 0 else "CPU")
        self._pipeline = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple",
            device=device,
        )

    def analyze(self, text: str) -> list[dict]:
        if not text:
            return []
        entities = self._pipeline(text)
        return [
            {
                "label": e["entity_group"],
                "text": e["word"],
                "start": int(e["start"]),
                "end": int(e["end"]),
                "score": float(e["score"]),
            }
            for e in entities
        ]

    def anonymize(self, text: str) -> str:
        return mask_text_with_entities(text, self.analyze(text))
