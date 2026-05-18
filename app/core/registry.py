from functools import lru_cache

from app.services.anonymization.base import AnonymizationService
from app.services.anonymization.openai_pf import OpenAIPrivacyFilterService
from app.services.anonymization.openmed import OpenMedPrivacyFilterService
from app.services.anonymization.piiranha import PiiranhaAnonymizationService
from app.services.fhir.base import FHIRStructuringService
from app.services.fhir.llm_structurer import LLMFHIRStructurer
from app.services.image_classification.base import ImageClassificationService
from app.services.image_classification.clip import CLIPImageClassificationService
from app.services.llm.base import LLMService
from app.services.llm.ollama_service import OllamaLLMService
from app.services.ocr.base import OCRService
from app.services.ocr.doctr import DocTROCRService
from app.services.pii_detection.base import PIIDetectionService
from app.services.pii_detection.openai_pf import OpenAIPrivacyFilterDetectionService
from app.services.pii_detection.openmed import OpenMedPIIDetectionService
from app.services.transcription.base import TranscriptionService
from app.services.transcription.faster_whisper import FasterWhisperTranscriptionService


@lru_cache(maxsize=1)
def get_ocr_service() -> OCRService:
    return DocTROCRService()


ANONYMIZATION_MODELS: dict[str, str] = {
    "openai-privacy-filter": "openai/privacy-filter",
    "openmed-privacy-filter-multilingual": "OpenMed/privacy-filter-multilingual",
    "piiranha": "iiiorg/piiranha-v1-detect-personal-information",
}
DEFAULT_ANONYMIZATION_MODEL = "openai-privacy-filter"


@lru_cache(maxsize=4)
def get_anonymization_service_by_key(
    key: str = DEFAULT_ANONYMIZATION_MODEL,
) -> AnonymizationService:
    if key == "openai-privacy-filter":
        return OpenAIPrivacyFilterService()
    if key == "openmed-privacy-filter-multilingual":
        return OpenMedPrivacyFilterService(
            model_name=ANONYMIZATION_MODELS[key]
        )
    if key == "piiranha":
        return PiiranhaAnonymizationService()
    raise ValueError(
        f"unknown anonymization model key '{key}'. "
        f"Valid: {list(ANONYMIZATION_MODELS.keys())}"
    )


def get_anonymization_service() -> AnonymizationService:
    return get_anonymization_service_by_key(DEFAULT_ANONYMIZATION_MODEL)


@lru_cache(maxsize=1)
def get_pii_detection_service() -> PIIDetectionService:
    return OpenMedPIIDetectionService()


@lru_cache(maxsize=1)
def get_transcription_service() -> TranscriptionService:
    return FasterWhisperTranscriptionService()


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return OllamaLLMService()


@lru_cache(maxsize=1)
def get_fhir_structurer() -> FHIRStructuringService:
    return LLMFHIRStructurer(get_llm_service())


@lru_cache(maxsize=1)
def get_image_classification_service() -> ImageClassificationService:
    return CLIPImageClassificationService()
