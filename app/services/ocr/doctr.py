from doctr.io import DocumentFile
from doctr.models import ocr_predictor

from app.services.ocr.base import OCRService


class DocTROCRService(OCRService):
    def __init__(
        self,
        det_arch: str = "db_resnet50",
        reco_arch: str = "crnn_vgg16_bn",
    ) -> None:
        self._predictor = ocr_predictor(
            det_arch=det_arch,
            reco_arch=reco_arch,
            pretrained=True,
        )

    def extract_text(self, image_bytes: bytes) -> str:
        document = DocumentFile.from_images(image_bytes)
        result = self._predictor(document)
        return result.render()
