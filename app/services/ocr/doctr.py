import logging

from doctr.io import DocumentFile
from doctr.models import ocr_predictor

from app.core.device import has_cuda
from app.services.ocr.base import OCRService

logger = logging.getLogger(__name__)


class DocTROCRService(OCRService):
    def __init__(
        self,
        det_arch: str = "db_resnet50",
        reco_arch: str = "crnn_vgg16_bn",
    ) -> None:
        predictor = ocr_predictor(
            det_arch=det_arch,
            reco_arch=reco_arch,
            pretrained=True,
        )
        if has_cuda():
            try:
                import torch

                predictor = predictor.cuda()
                logger.info("[ocr] docTR predictor moved to CUDA")
            except Exception as exc:
                logger.warning("[ocr] failed to move docTR to CUDA (%s) — using CPU", exc)
        else:
            logger.info("[ocr] docTR predictor running on CPU")
        self._predictor = predictor

    def extract_text(self, image_bytes: bytes) -> str:
        document = DocumentFile.from_images(image_bytes)
        result = self._predictor(document)
        return result.render()
