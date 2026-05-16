from transformers import pipeline

from app.core.device import pipeline_device
from app.schemas.pii import PIIEntity
from app.services.pii_detection.base import PIIDetectionService

_MODEL_NAME = "OpenMed/OpenMed-PII-Italian-SnowflakeMed-Large-568M-v1"


class OpenMedPIIDetectionService(PIIDetectionService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        self._pipeline = pipeline(
            task="ner",
            model=model_name,
            aggregation_strategy="simple",
            device=pipeline_device(),
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
