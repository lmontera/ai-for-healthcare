"""Derive entity spans in the ORIGINAL text from an LLM-anonymized text
that contains [PLACEHOLDER] tokens.

Uses TOKEN-level diff (word + whitespace tokens) to avoid spurious
character-level matches like 'D' of "Dr." matching 'D' of "[DOCTOR]".
"""
import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9_]*)\]")


def _tokenize(s: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Split into runs of non-whitespace and runs of whitespace.

    Returns parallel lists: tokens, and (start, end) char positions in s.
    """
    tokens: list[str] = []
    positions: list[tuple[int, int]] = []
    i, n = 0, len(s)
    while i < n:
        if s[i].isspace():
            j = i
            while j < n and s[j].isspace():
                j += 1
        else:
            j = i
            while j < n and not s[j].isspace():
                j += 1
        tokens.append(s[i:j])
        positions.append((i, j))
        i = j
    return tokens, positions


def spans_from_llm_anonymized(original: str, anonymized: str) -> list[dict]:
    """For each diff region whose replacement contains a [PLACEHOLDER], return
    the corresponding (start, end) span in `original` plus the label.

    Output: list of {label, text, start, end, score=1.0}, in document order.
    """
    if not original or not anonymized:
        return []

    o_toks, o_pos = _tokenize(original)
    a_toks, _a_pos = _tokenize(anonymized)

    sm = SequenceMatcher(a=o_toks, b=a_toks, autojunk=False)
    entities: list[dict] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if i1 == i2:
            # pure insert in anonymized with no original span -> nothing to mask
            continue
        replacement_text = "".join(a_toks[j1:j2])
        m = _PLACEHOLDER_RE.search(replacement_text)
        if not m:
            # diff region without any placeholder -> LLM reformatted something
            # not classified as PII (rare). Skip.
            continue
        label = m.group(1)
        start = o_pos[i1][0]
        end = o_pos[i2 - 1][1]
        # Trim leading/trailing whitespace from the span (avoid masking empty whitespace boxes)
        snippet = original[start:end]
        stripped = snippet.strip()
        if not stripped:
            continue
        lead = len(snippet) - len(snippet.lstrip())
        trail = len(snippet) - len(snippet.rstrip())
        entities.append(
            {
                "label": label,
                "text": original[start + lead:end - trail],
                "start": start + lead,
                "end": end - trail,
                "score": 1.0,
            }
        )

    logger.info("[llm_spans] derived %d spans from LLM diff", len(entities))
    return entities
