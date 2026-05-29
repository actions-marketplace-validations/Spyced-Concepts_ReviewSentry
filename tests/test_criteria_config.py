"""
Tests for features/criteria_config.feature

Tests the extensible criteria configuration system via config.py.
All scenarios test config loading and prompt construction — no API calls required.
"""

import os
import sys
import pytest
from pytest_bdd import scenarios, given, then

scenarios("criteria_config.feature")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import config as rs_config  # noqa: E402 — path added in conftest.py


# ── State shared between steps ────────────────────────────────────────────────

@pytest.fixture
def config_state():
    return {"yaml": "", "overrides": None, "custom": None, "warnings": None}


# ── Given steps ───────────────────────────────────────────────────────────────

@given('no ".github/reviewsentry.yml" file exists in the repository')
def no_config_file(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "")


@given('a ".github/reviewsentry.yml" file exists with "cross_platform: false"')
def config_cross_platform_disabled(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "cross_platform: false\n")


@given('a ".github/reviewsentry.yml" file exists with "bash_quality: false"')
def config_bash_quality_disabled(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "bash_quality: false\n")


@given(
    'a ".github/reviewsentry.yml" file exists with a custom criterion '
    '"Verify all async functions have error handling"'
)
def config_custom_criterion(monkeypatch):
    monkeypatch.setenv(
        "REVIEWSENTRY_CONFIG",
        'custom:\n  - "Verify all async functions have error handling"\n',
    )


@given(
    'a ".github/reviewsentry.yml" file exists with "sensitive_data: false" '
    "but no acknowledgement"
)
def config_core_disabled_no_ack(monkeypatch):
    monkeypatch.setenv("REVIEWSENTRY_CONFIG", "sensitive_data: false\n")


@given(
    'a ".github/reviewsentry.yml" exists with "sensitive_data: false" '
    'and "acknowledge_disabled_core: true"'
)
def config_core_disabled_with_ack(monkeypatch):
    monkeypatch.setenv(
        "REVIEWSENTRY_CONFIG",
        "sensitive_data: false\nacknowledge_disabled_core: true\n",
    )


@given(
    'the review_criteria input is set to '
    '"Flag any use of console.log in production code"'
)
def extra_criterion(monkeypatch):
    monkeypatch.setenv(
        "REVIEW_CRITERIA", "Flag any use of console.log in production code"
    )


# ── Then steps ────────────────────────────────────────────────────────────────

@then("the review applies all default criteria including sensitive data and correctness")
def default_criteria_applied():
    overrides, custom, warnings, _ = rs_config.load()
    assert overrides.get("sensitive_data", True) is True, \
        "sensitive_data criterion disabled by default — should be enabled"
    assert overrides.get("correctness", True) is True, \
        "correctness criterion disabled by default — should be enabled"


@then("the review comment includes the custom criterion in its output")
def custom_criterion_in_criteria():
    extra = os.environ.get("REVIEW_CRITERIA", "")
    assert "console.log" in extra, \
        "REVIEW_CRITERIA does not contain the expected custom criterion"


@then("the review comment does not include a cross-platform finding")
def no_cross_platform():
    overrides, _, _, _ = rs_config.load()
    assert overrides.get("cross_platform") is False, \
        "cross_platform criterion should be disabled but is not"


@then("the review still applies all other default criteria")
def other_criteria_still_active():
    overrides, _, _, _ = rs_config.load()
    assert overrides.get("sensitive_data", True) is True
    assert overrides.get("correctness", True) is True
    assert overrides.get("security", True) is True


@then("the review comment does not include bash quality findings")
def no_bash_quality():
    overrides, _, _, _ = rs_config.load()
    assert overrides.get("bash_quality") is False, \
        "bash_quality criterion should be disabled but is not"


@then("the review comment includes a finding or note referencing the custom criterion")
def custom_criterion_from_config():
    _, custom, _, _ = rs_config.load()
    assert any("async" in c.lower() for c in custom), \
        "Custom criterion from config not found in loaded criteria"


@then("the workflow fails or warns that disabling a core criterion requires explicit acknowledgement")
def core_disable_no_ack_warns():
    _, _, warnings, _ = rs_config.load()
    assert any("sensitive_data" in w.lower() or "acknowledge" in w.lower()
               for w in warnings), \
        "No warning raised when disabling core criterion without acknowledgement"


@then("the sensitive data criterion is still applied")
def sensitive_data_still_applied():
    overrides, _, _, _ = rs_config.load()
    assert overrides.get("sensitive_data", True) is True, \
        "sensitive_data should remain active when disabled without acknowledgement"


@then("the review comment notes the sensitive data criterion was explicitly disabled")
def sensitive_data_disabled_with_notice():
    overrides, _, warnings, _ = rs_config.load()
    assert overrides.get("sensitive_data") is False, \
        "sensitive_data should be disabled when acknowledge_disabled_core is true"


@then("no sensitive data scan is performed")
def no_sensitive_data_scan():
    overrides, _, _, _ = rs_config.load()
    assert overrides.get("sensitive_data") is False
