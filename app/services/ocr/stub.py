from app.services.ocr.base import OCRService


class StubOCRService(OCRService):
    def extract_text(self, image_bytes: bytes) -> str:
        _ = image_bytes
        return "[stub-ocr] testo estratto dal documento"
