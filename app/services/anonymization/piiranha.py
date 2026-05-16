from transformers import pipeline

from app.services.anonymization.base import AnonymizationService

_MODEL_NAME = "iiiorg/piiranha-v1-detect-personal-information"


class PiiranhaAnonymizationService(AnonymizationService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        self._pipeline = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple",
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
