import logging
from typing import Any

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
        predictor = ocr_predictor(det_arch=det_arch, reco_arch=reco_arch, pretrained=True)
        if has_cuda():
            try:
                predictor = predictor.cuda()
                logger.info("[ocr] device=GPU")
            except Exception:
                logger.info("[ocr] device=CPU")
        else:
            logger.info("[ocr] device=CPU")
        self._predictor = predictor

    def extract_text(self, image_bytes: bytes) -> str:
        document = DocumentFile.from_images(image_bytes)
        result = self._predictor(document)
        return result.render()

    def extract_text_and_words(self, image_bytes: bytes) -> dict[str, Any]:
        """Run OCR returning text plus per-word bounding boxes (pixel coords).
        Only the first page is processed. Output:
          {
            "text": str,                       # joined, with spaces between words and \n between lines
            "page_size": (W_px, H_px),
            "words": [
              {"text": str, "start": int, "end": int, "bbox": (x1, y1, x2, y2)}
            ]
          }
        """
        document = DocumentFile.from_images(image_bytes)
        result = self._predictor(document)
        if not result.pages:
            return {"text": "", "page_size": (0, 0), "words": []}

        page = result.pages[0]
        h_px, w_px = page.dimensions
        text_parts: list[str] = []
        words: list[dict[str, Any]] = []

        def cur_offset() -> int:
            return sum(len(p) for p in text_parts)

        for block in page.blocks:
            for line in block.lines:
                for w_idx, word in enumerate(line.words):
                    if w_idx > 0:
                        text_parts.append(" ")
                    start = cur_offset()
                    text_parts.append(word.value)
                    end = cur_offset()
                    (xmin, ymin), (xmax, ymax) = word.geometry
                    bbox = (
                        max(0, int(xmin * w_px)),
                        max(0, int(ymin * h_px)),
                        min(w_px, int(xmax * w_px)),
                        min(h_px, int(ymax * h_px)),
                    )
                    words.append(
                        {"text": word.value, "start": start, "end": end, "bbox": bbox}
                    )
                text_parts.append("\n")
            text_parts.append("\n")

        return {
            "text": "".join(text_parts),
            "page_size": (w_px, h_px),
            "words": words,
        }
