import logging

from transformers import pipeline

from app.core.device import pipeline_device
from app.services.anonymization.base import AnonymizationService

logger = logging.getLogger(__name__)

_MODEL_NAME = "OpenMed/privacy-filter-multilingual"


class OpenMedPrivacyFilterService(AnonymizationService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        device = pipeline_device()
        logger.info("[anonymize] device=%s", "GPU" if device >= 0 else "CPU")
        self._pipeline = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple",
            trust_remote_code=True,
            device=device,
        )

    def anonymize(self, text: str) -> str:
        if not text:
            return text

        entities = self._pipeline(text)
        spans = sorted(entities, key=lambda e: e["start"], reverse=True)

        masked = text
        for entity in spans:
            label = entity["entity_group"]
            start, end = entity["start"], entity["end"]
            masked = f"{masked[:start]}[{label}]{masked[end:]}"

        return masked
