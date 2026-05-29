"""
Tests for the RS-95 diff-chunking feature.

Covers diff_utils helpers (split, batch, aggregate) and the config loading
of the chunk_large_diffs behaviour flag. No AI adapter calls required.
"""

import os
import sys
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import diff_utils
import config as rs_config


# ── split_diff_by_file ────────────────────────────────────────────────────────

MULTI_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
index 0000000..1111111 100644
--- a/foo.py
+++ b/foo.py
@@ -1,2 +1,3 @@
 unchanged
+added line
diff --git a/bar.ts b/bar.ts
index 2222222..3333333 100644
--- a/bar.ts
+++ b/bar.ts
@@ -10,1 +10,2 @@
 existing
+new line
diff --git a/baz.sh b/baz.sh
index 4444444..5555555 100644
--- a/baz.sh
+++ b/baz.sh
@@ -1,1 +1,2 @@
 #!/bin/bash
+echo hello
"""

def test_split_diff_by_file_returns_three_sections():
    parts = diff_utils.split_diff_by_file(MULTI_FILE_DIFF)
    assert len(parts) == 3


def test_split_diff_by_file_each_starts_with_diff_git():
    for part in diff_utils.split_diff_by_file(MULTI_FILE_DIFF):
        assert part.startswith("diff --git ")


def test_split_diff_by_file_single_file_returns_one_section():
    single = "diff --git a/only.py b/only.py\n+line\n"
    parts = diff_utils.split_diff_by_file(single)
    assert len(parts) == 1


def test_split_diff_by_file_empty_string_returns_empty_list():
    assert diff_utils.split_diff_by_file("") == []


# ── file_path ─────────────────────────────────────────────────────────────────

def test_file_path_extracts_b_side():
    fd = "diff --git a/src/foo.py b/src/foo.py\nindex 000..111\n"
    assert diff_utils.file_path(fd) == "src/foo.py"


def test_file_path_handles_path_with_spaces():
    fd = "diff --git a/my file.py b/my file.py\n"
    assert diff_utils.file_path(fd) == "my file.py"


# ── batch_file_diffs ──────────────────────────────────────────────────────────

def _make_file_diff(name: str, size: int) -> str:
    return f"diff --git a/{name} b/{name}\n" + "+" * size + "\n"


def test_batch_single_file_one_batch():
    fd = [_make_file_diff("a.py", 100)]
    assert len(diff_utils.batch_file_diffs(fd, 10_000)) == 1


def test_batch_splits_when_over_limit():
    fds = [_make_file_diff(f"{i}.py", 500) for i in range(10)]
    # Each file ~502 chars; limit 1000 → ~2 files per batch → 5 batches
    batches = diff_utils.batch_file_diffs(fds, 1_000)
    assert len(batches) > 1
    assert sum(len(b) for b in batches) == len(fds)


def test_batch_oversized_single_file_gets_own_batch():
    # A file larger than the limit must still be included, not dropped
    big = _make_file_diff("huge.py", 10_000)
    small = _make_file_diff("small.py", 10)
    batches = diff_utils.batch_file_diffs([big, small], 500)
    all_files = [fd for batch in batches for fd in batch]
    assert big in all_files
    assert small in all_files


# ── extract_verdict / strip_verdict_line / aggregate_reviews ─────────────────

def test_extract_verdict_approve():
    text = "Some review text.\n\n✅ **AI Recommendation: APPROVE**"
    assert diff_utils.extract_verdict(text) == "APPROVE"


def test_extract_verdict_request_changes():
    text = "Issues found.\n\n❌ **AI Recommendation: REQUEST CHANGES**"
    assert diff_utils.extract_verdict(text) == "REQUEST CHANGES"


def test_extract_verdict_missing_returns_empty():
    assert diff_utils.extract_verdict("No verdict here.") == ""


def test_strip_verdict_line_removes_verdict():
    text = "Review body.\n\n✅ **AI Recommendation: APPROVE**"
    stripped = diff_utils.strip_verdict_line(text)
    assert "AI Recommendation" not in stripped
    assert "Review body" in stripped


def test_aggregate_worst_case_verdict():
    reviews = [
        "Pass 1.\n\n✅ **AI Recommendation: APPROVE**",
        "Pass 2.\n\n📝 **AI Recommendation: APPROVE WITH NOTES**",
        "Pass 3.\n\n❌ **AI Recommendation: REQUEST CHANGES**",
    ]
    result = diff_utils.aggregate_reviews(reviews)
    assert "REQUEST CHANGES" in result


def test_aggregate_approve_when_all_approve():
    reviews = [
        "Pass 1.\n\n✅ **AI Recommendation: APPROVE**",
        "Pass 2.\n\n✅ **AI Recommendation: APPROVE**",
    ]
    result = diff_utils.aggregate_reviews(reviews)
    assert "APPROVE" in result
    assert "REQUEST CHANGES" not in result
    assert "APPROVE WITH NOTES" not in result


def test_aggregate_labels_each_pass():
    reviews = [
        "Pass 1.\n\n✅ **AI Recommendation: APPROVE**",
        "Pass 2.\n\n✅ **AI Recommendation: APPROVE**",
    ]
    result = diff_utils.aggregate_reviews(reviews)
    assert "Review pass 1 of 2" in result
    assert "Review pass 2 of 2" in result


def test_aggregate_no_verdicts_shows_warning():
    reviews = ["No verdict here.", "Also no verdict."]
    result = diff_utils.aggregate_reviews(reviews)
    assert "incomplete" in result.lower() or "could not extract" in result.lower()


# ── config: chunk_large_diffs behaviour flag ──────────────────────────────────

def test_chunk_large_diffs_true_parsed(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "chunk_large_diffs: true\n")
    _, _, _, behaviour = rs_config.load()
    assert behaviour.get("chunk_large_diffs") is True


def test_chunk_large_diffs_false_parsed(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "chunk_large_diffs: false\n")
    _, _, _, behaviour = rs_config.load()
    assert behaviour.get("chunk_large_diffs") is False


def test_chunk_large_diffs_missing_not_in_behaviour(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "")
    _, _, _, behaviour = rs_config.load()
    assert "chunk_large_diffs" not in behaviour


def test_chunk_large_diffs_does_not_affect_criteria(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "chunk_large_diffs: true\n")
    overrides, _, _, _ = rs_config.load()
    assert "chunk_large_diffs" not in overrides
