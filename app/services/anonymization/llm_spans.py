"""Derive entity spans in the ORIGINAL text from an LLM-anonymized text
that contains [PLACEHOLDER] tokens.

The LLM is instructed to preserve formatting and only replace personal data
with [LABEL] tokens. We walk both strings in parallel, anchoring on the
unchanged segments to recover the (start, end) of each replaced span.
"""
import re

_PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9_]*)\]")


def spans_from_llm_anonymized(original: str, anonymized: str) -> list[dict]:
    """Return entities in `original` corresponding to each placeholder in `anonymized`.

    Output: list of {label, text, start, end, score} (score is always 1.0).
    If alignment fails at some point, returns what was matched so far.
    """
    entities: list[dict] = []
    if not original or not anonymized:
        return entities

    orig_cursor = 0
    anon_cursor = 0
    placeholders = list(_PLACEHOLDER_RE.finditer(anonymized))
    if not placeholders:
        return entities

    for idx, m in enumerate(placeholders):
        # Segment in anonymized BEFORE this placeholder, after the previous cursor
        pre_anon = anonymized[anon_cursor:m.start()]

        # Locate pre_anon in original starting at orig_cursor.
        # Try strict, then fall back to a whitespace-tolerant search.
        new_orig = _find(original, pre_anon, orig_cursor)
        if new_orig is None:
            # alignment lost: stop
            break
        orig_cursor = new_orig + len(pre_anon)

        # Anchor AFTER the placeholder: text in anonymized until next placeholder (or end).
        next_start = placeholders[idx + 1].start() if idx + 1 < len(placeholders) else len(anonymized)
        anchor = anonymized[m.end():next_start]

        if anchor.strip() == "":
            # rest of anon is whitespace or empty -> entity goes to end of original
            ent_end = len(original)
        else:
            # Take leading non-whitespace portion of anchor (avoid trailing newlines)
            stripped_lead = anchor.lstrip()
            lead_skip = len(anchor) - len(stripped_lead)
            # Use a moderate-length anchor (first 30 chars max) to be tolerant to small diffs
            probe = stripped_lead[:30]
            if not probe:
                ent_end = len(original)
            else:
                anchor_pos = _find(original, probe, orig_cursor)
                if anchor_pos is None:
                    break
                ent_end = anchor_pos - lead_skip
                ent_end = max(ent_end, orig_cursor)  # avoid negative-length spans

        ent_start = orig_cursor
        if ent_end > ent_start:
            entities.append(
                {
                    "label": m.group(1),
                    "text": original[ent_start:ent_end],
                    "start": ent_start,
                    "end": ent_end,
                    "score": 1.0,
                }
            )
        orig_cursor = ent_end
        anon_cursor = m.end()

    return entities


def _find(haystack: str, needle: str, start: int) -> int | None:
    """Strict + whitespace-tolerant substring search starting at `start`."""
    if not needle:
        return start
    pos = haystack.find(needle, start)
    if pos >= 0:
        return pos
    # Tolerant: collapse runs of whitespace in both sides
    needle_re = re.escape(needle)
    needle_re = re.sub(r"(?:\\\s)+", r"\\s+", needle_re)
    m = re.search(needle_re, haystack[start:])
    if m:
        return start + m.start()
    return None
