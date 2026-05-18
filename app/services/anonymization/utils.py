def mask_text_with_entities(text: str, entities: list[dict]) -> str:
    """Replace each entity span with [LABEL] in the original text.

    entities: list of dicts with keys label, start, end (and optionally score, text).
    """
    if not text or not entities:
        return text or ""
    spans = sorted(entities, key=lambda e: e["start"], reverse=True)
    out = text
    for e in spans:
        start, end = int(e["start"]), int(e["end"])
        label = e.get("label", "PII")
        out = f"{out[:start]}[{label}]{out[end:]}"
    return out
