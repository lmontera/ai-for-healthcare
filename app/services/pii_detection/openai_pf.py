import logging

from transformers import pipeline

from app.core.device import pipeline_device
from app.schemas.pii import PIIEntity
from app.services.pii_detection.base import PIIDetectionService

logger = logging.getLogger(__name__)

_MODEL_NAME = "openai/privacy-filter"


class OpenAIPrivacyFilterDetectionService(PIIDetectionService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        device = pipeline_device()
        logger.info("[pii] device=%s", "GPU" if device >= 0 else "CPU")
        self._pipeline = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple",
            device=device,
        )

    def detect(self, text: str) -> list[PIIEntity]:
        if not text:
            return []

        raw = self._pipeline(text)
        return [
            PIIEntity(
                label=item["entity_group"],
                text=item["word"],
                start=int(item["start"]),
                end=int(item["end"]),
                score=float(item["score"]),
            )
            for item in raw
        ]
