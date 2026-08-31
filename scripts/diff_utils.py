"""
ReviewSentry diff utilities.

Splitting, batching, and aggregation helpers used by review.py.
All functions are pure (no I/O, no env reads) so tests can import them directly.
"""

import re

# ── Verdict constants ──────────────────────────────────────────────────────────

_VERDICT_RE = re.compile(
    r'\*\*AI Recommendation: (APPROVE WITH NOTES|REQUEST CHANGES|APPROVE)\*{0,2}'
)
_VERDICT_RANK = {"REQUEST CHANGES": 2, "APPROVE WITH NOTES": 1, "APPROVE": 0}
_VERDICT_EMOJI = {"APPROVE": "✅", "APPROVE WITH NOTES": "📝", "REQUEST CHANGES": "❌"}


# ── Diff splitting ─────────────────────────────────────────────────────────────

def split_diff_by_file(diff_text: str) -> list[str]:
    """Split a unified diff into per-file sections at diff --git boundaries."""
    files: list[str] = []
    current: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith('diff --git ') and current:
            files.append(''.join(current))
            current = []
        current.append(line)
    if current:
        files.append(''.join(current))
    return files


def file_path(file_diff: str) -> str:
    """Extract the b-side path from a diff --git header line."""
    first = file_diff.split('\n', 1)[0]
    parts = first.split(' b/', 1)
    return parts[1].strip() if len(parts) == 2 else first.strip()


def batch_file_diffs(file_diffs: list[str], char_limit: int) -> list[list[str]]:
    """
    Group file diffs into batches each fitting within char_limit.

    A single file that exceeds char_limit on its own is placed in its own
    batch rather than dropped — the caller decides how to handle oversized
    individual files. If char_limit is very small, each file still gets its
    own batch (no infinite loop, no data loss).
    """
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for fd in file_diffs:
        if size + len(fd) > char_limit and current:
            batches.append(current)
            current = []
            size = 0
        current.append(fd)
        size += len(fd)
    if current:
        batches.append(current)
    return batches


# ── Verdict extraction and aggregation ────────────────────────────────────────

def extract_verdict(text: str) -> str:
    """Return the verdict string from a review, or empty string if not found."""
    m = _VERDICT_RE.search(text)
    return m.group(1) if m else ""


def strip_verdict_line(text: str) -> str:
    """Remove the trailing verdict line(s) from a review pass."""
    lines = text.rstrip().splitlines()
    while lines and _VERDICT_RE.search(lines[-1]):
        lines.pop()
    return '\n'.join(lines)


def aggregate_reviews(reviews: list[str]) -> str:
    """
    Combine N per-batch reviews into a single output with a unified verdict.

    Each pass is labelled "Review pass N of M". The combined verdict is the
    worst-case across all passes (REQUEST CHANGES > APPROVE WITH NOTES > APPROVE).
    """
    verdicts = [extract_verdict(r) for r in reviews]
    ranked = [_VERDICT_RANK[v] for v in verdicts if v in _VERDICT_RANK]

    if ranked:
        worst = max(ranked)
        label = next(k for k, v in _VERDICT_RANK.items() if v == worst)
        verdict_line = f'{_VERDICT_EMOJI[label]} **AI Recommendation: {label}**'
    else:
        verdict_line = (
            "⚠️ Could not extract verdict from all review passes — "
            "review may be incomplete."
        )

    parts = [
        f'### Review pass {i} of {len(reviews)}\n\n{strip_verdict_line(r)}'
        for i, r in enumerate(reviews, 1)
    ]

    return '\n\n---\n\n'.join(parts) + f'\n\n---\n\n{verdict_line}'


# ── Review splitting ───────────────────────────────────────────────────────────

# Criterion sections start with ✅/⚠️ (per-criterion headers) or ### (multi-pass
# pass headers from chunked reviews).
_SECTION_RE = re.compile(r'^(✅|⚠️|###\s)', re.MULTILINE)

COMMENT_CHAR_LIMIT = 50_000  # GitHub's hard limit is 65,536; 50K gives a safe margin


def split_review_for_posting(review: str, char_limit: int = COMMENT_CHAR_LIMIT) -> list[str]:
    """
    Split a review into parts each ≤ char_limit characters, breaking at
    criterion-section boundaries (lines starting with ✅, ⚠️, or ###).

    If a single section exceeds char_limit it is placed in its own part rather
    than truncated — no content is dropped. The verdict line is always in the
    last part because splits occur at section *starts*, keeping each section
    with the content that follows it (including any trailing verdict).

    Returns a list of 1 or more non-empty strings.
    """
    if len(review) <= char_limit:
        return [review]

    boundaries = [m.start() for m in _SECTION_RE.finditer(review)]
    if not boundaries:
        # No section markers — hard split at char_limit
        return [review[i: i + char_limit] for i in range(0, len(review), char_limit)]

    parts: list[str] = []
    start = 0

    while start < len(review):
        end = start + char_limit
        if end >= len(review):
            parts.append(review[start:])
            break
        # Last section boundary strictly between start and end
        split_at = next((b for b in reversed(boundaries) if start < b < end), None)
        if split_at is None:
            # Current section alone exceeds limit — include it whole
            split_at = next((b for b in boundaries if b > end), len(review))
        parts.append(review[start:split_at].rstrip())
        start = split_at

    return parts or [review]
