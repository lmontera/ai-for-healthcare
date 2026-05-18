import io
import logging
from typing import Any

from PIL import Image, ImageDraw

from app.schemas.pii import PIIEntity

logger = logging.getLogger(__name__)


def _bboxes_for_span(words: list[dict[str, Any]], start: int, end: int) -> list[tuple]:
    """Return the bboxes of the words whose [start_char, end_char] overlap with the span."""
    out = []
    for w in words:
        if w["end"] <= start or w["start"] >= end:
            continue
        out.append(w["bbox"])
    return out


def mask_image_with_entities(
    image_bytes: bytes,
    words: list[dict[str, Any]],
    entities: list[PIIEntity],
    padding: int = 2,
) -> bytes:
    """Cover each PII entity bbox with a filled black rectangle and return PNG bytes."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    masked = 0
    for ent in entities:
        bboxes = _bboxes_for_span(words, ent.start, ent.end)
        for x1, y1, x2, y2 in bboxes:
            draw.rectangle(
                [
                    max(0, x1 - padding),
                    max(0, y1 - padding),
                    min(img.width, x2 + padding),
                    min(img.height, y2 + padding),
                ],
                fill="black",
            )
            masked += 1

    logger.info(
        "[anonymize:image] entities=%d masked_boxes=%d image=%dx%d",
        len(entities),
        masked,
        img.width,
        img.height,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
