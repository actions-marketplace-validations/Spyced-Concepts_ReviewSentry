"""
Tests for RS-96 output splitting.

Covers split_review_for_posting() from diff_utils and the action.yml
max_tokens input documentation. No AI adapter calls required.
"""

import os
import sys
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import diff_utils


# ── split_review_for_posting ──────────────────────────────────────────────────

_VERDICT = "✅ **AI Recommendation: APPROVE**"

_SECTION_A = "✅ **Sensitive data disclosure**\n\nNo issues found.\n\n"
_SECTION_B = "⚠️ **Correctness**\n\n🟡 Minor edge case.\n\n"
_SECTION_C = "✅ **PR scope**\n\nLooks good.\n\n"


def _review(*sections: str, verdict: str = _VERDICT) -> str:
    return "".join(sections) + verdict


def test_short_review_returns_single_part():
    review = _review(_SECTION_A, _SECTION_B)
    parts = diff_utils.split_review_for_posting(review, char_limit=100_000)
    assert len(parts) == 1
    assert parts[0] == review


def test_review_at_exact_limit_returns_single_part():
    review = _review(_SECTION_A)
    parts = diff_utils.split_review_for_posting(review, char_limit=len(review))
    assert len(parts) == 1


def test_review_one_over_limit_splits():
    review = _review(_SECTION_A, _SECTION_B, _SECTION_C)
    # Set limit just below full length but above section A alone
    limit = len(_SECTION_A) + 1
    parts = diff_utils.split_review_for_posting(review, char_limit=limit)
    assert len(parts) > 1


def test_split_preserves_all_content():
    review = _review(_SECTION_A, _SECTION_B, _SECTION_C)
    parts = diff_utils.split_review_for_posting(review, char_limit=len(_SECTION_A) + 5)
    combined = "\n".join(p.strip() for p in parts)
    # Every section header should appear somewhere in the combined output
    assert "Sensitive data disclosure" in combined
    assert "Correctness" in combined
    assert "PR scope" in combined


def test_verdict_is_in_last_part():
    review = _review(_SECTION_A, _SECTION_B, _SECTION_C)
    parts = diff_utils.split_review_for_posting(review, char_limit=len(_SECTION_A) + 5)
    assert _VERDICT in parts[-1]


def test_verdict_not_in_first_part_when_split():
    review = _review(_SECTION_A, _SECTION_B, _SECTION_C)
    parts = diff_utils.split_review_for_posting(review, char_limit=len(_SECTION_A) + 5)
    if len(parts) > 1:
        assert _VERDICT not in parts[0]


def test_oversized_single_section_gets_own_part():
    big_section = "✅ **Huge section**\n\n" + "x" * 200_000 + "\n\n"
    small_section = "✅ **Small section**\n\nOK\n\n"
    review = big_section + small_section + _VERDICT
    parts = diff_utils.split_review_for_posting(review, char_limit=1_000)
    # Big section must appear — not dropped
    assert any("Huge section" in p for p in parts)
    assert any("Small section" in p for p in parts)


def test_no_section_markers_hard_splits_at_limit():
    review = "a" * 150
    parts = diff_utils.split_review_for_posting(review, char_limit=50)
    assert len(parts) == 3
    assert all(len(p) <= 50 for p in parts)


def test_empty_review_returns_single_part():
    parts = diff_utils.split_review_for_posting("")
    assert len(parts) == 1


def test_each_part_within_char_limit():
    review = _review(_SECTION_A, _SECTION_B, _SECTION_C)
    limit = max(len(_SECTION_A), len(_SECTION_B), len(_SECTION_C)) + 10
    parts = diff_utils.split_review_for_posting(review, char_limit=limit)
    for p in parts:
        assert len(p) <= limit


# ── action.yml and README documentation ──────────────────────────────────────

def test_max_tokens_input_in_action_yml():
    action_path = os.path.join(REPO_ROOT, "action.yml")
    content = open(action_path).read()
    assert "max_tokens:" in content, "max_tokens input missing from action.yml"
    assert "4096" in content, "Default value 4096 missing from action.yml"


def test_max_tokens_documented_in_readme():
    readme_path = os.path.join(REPO_ROOT, "README.md")
    content = open(readme_path).read()
    assert "max_tokens" in content, "max_tokens missing from README.md"


def test_review_parts_output_wired_in_action_yml():
    action_path = os.path.join(REPO_ROOT, "action.yml")
    content = open(action_path).read()
    assert "review_parts" in content, "review_parts output reference missing from action.yml"


def test_max_tokens_env_passed_to_review_step():
    action_path = os.path.join(REPO_ROOT, "action.yml")
    content = open(action_path).read()
    assert "MAX_TOKENS" in content, "MAX_TOKENS env var not passed to review step in action.yml"
