import io
import logging

from PIL import Image
from transformers import pipeline

from app.core.device import pipeline_device
from app.services.image_classification.base import ImageClassificationService

logger = logging.getLogger(__name__)

_MODEL_NAME = "openai/clip-vit-base-patch32"


class CLIPImageClassificationService(ImageClassificationService):
    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        device = pipeline_device()
        logger.info("[image-clf] device=%s model=%s", "GPU" if device >= 0 else "CPU", model_name)
        self._pipeline = pipeline(
            task="zero-shot-image-classification",
            model=model_name,
            device=device,
        )

    def classify(self, image_bytes: bytes, candidate_labels: list[str]) -> list[dict]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        raw = self._pipeline(image, candidate_labels=candidate_labels)
        return [{"label": str(r["label"]), "score": float(r["score"])} for r in raw]
