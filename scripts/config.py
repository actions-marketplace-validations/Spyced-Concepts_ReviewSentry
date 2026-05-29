"""
ReviewSentry criteria configuration loader.

Reads .github/reviewsentry.yml from REVIEWSENTRY_CONFIG env var (set by
action.yml via GitHub API fetch). Parses a limited YAML subset — no external
dependencies, stdlib only.

Config file schema (.github/reviewsentry.yml):
    # Disable optional criteria
    cross_platform: false
    bash_quality: false

    # Disable a core criterion — requires explicit acknowledgement
    sensitive_data: false
    acknowledge_disabled_core: true

    # Add custom criteria (appended after defaults)
    custom:
      - "Verify all async functions include error handling"
      - "Check for hardcoded TODO comments without an owner"
"""

import os
import re
import sys

# Core criteria cannot be silently disabled — they protect against critical issues.
# To disable one, the config must include acknowledge_disabled_core: true.
CORE_CRITERIA = {"sensitive_data", "merge_conflicts"}

# Optional criteria can be disabled freely.
OPTIONAL_CRITERIA = {
    "correctness", "cross_platform", "bash_quality",
    "security", "code_quality", "dependencies", "documentation", "pr_scope",
}

ALL_CRITERIA = CORE_CRITERIA | OPTIONAL_CRITERIA

# Behaviour flags — control how the action processes the diff.
# Not criteria; not subject to core/optional criterion rules.
BEHAVIOUR_FLAGS = {"chunk_large_diffs"}

# All keys permitted in reviewsentry.yml. Anything else is rejected.
ALLOWED_KEYS = ALL_CRITERIA | BEHAVIOUR_FLAGS | {"acknowledge_disabled_core", "custom"}

# Hard cap on config file size — prevents oversized payloads.
MAX_LINES = 100
MAX_BYTES = 10_000  # 10 KB — prevents oversized payloads regardless of line length
MAX_CUSTOM_CRITERIA = 20
MAX_CRITERION_LENGTH = 500


def _parse(text):
    """Parse the limited YAML subset used in reviewsentry.yml."""
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        raise ValueError(
            f"reviewsentry.yml exceeds {MAX_LINES} line limit ({len(lines)} lines). "
            f"Reduce file size."
        )

    result = {}
    current_list_key = None

    for line in lines:
        stripped = re.sub(r"#.*$", "", line).rstrip()
        if not stripped:
            continue

        if re.match(r"^\s+-\s+", stripped):
            if current_list_key is not None:
                item = re.sub(r"^\s+-\s+", "", stripped).strip().strip("\"'")
                result.setdefault(current_list_key, []).append(item)
            continue

        m = re.match(r"^(\w+):\s*(.*)", stripped)
        if m:
            current_list_key = None
            key, value = m.group(1), m.group(2).strip()

            # Reject unrecognised keys immediately
            if key not in ALLOWED_KEYS:
                raise ValueError(
                    f"Unrecognised key '{key}' in reviewsentry.yml. "
                    f"Allowed keys: {', '.join(sorted(ALLOWED_KEYS))}."
                )

            if value == "":
                current_list_key = key
                result[key] = []
            elif value.lower() == "true":
                result[key] = True
            elif value.lower() == "false":
                result[key] = False
            else:
                result[key] = value.strip("\"'")

    return result


def load():
    """
    Load and validate reviewsentry.yml from REVIEWSENTRY_CONFIG env var.

    Exits the process with an error if the config file is present but invalid —
    a malformed config is a signal the user needs to fix, not something to silently
    ignore. If no config file is present (empty env var), returns defaults silently.

    Returns (overrides, custom_criteria, warnings, behaviour):
        overrides       — dict of criterion_name -> bool (True=enabled, False=disabled)
        custom_criteria — list of additional criterion strings
        warnings        — list of warning messages to surface in the review
        behaviour       — dict of behaviour flag name -> value (e.g. chunk_large_diffs)
    """
    content = os.environ.get("REVIEWSENTRY_CONFIG", "").strip()
    if not content:
        return {}, [], [], {}

    if len(content.encode("utf-8")) > MAX_BYTES:
        print(
            f"::error::reviewsentry.yml exceeds {MAX_BYTES} byte limit "
            f"({len(content.encode('utf-8'))} bytes). Reduce file size."
        )
        sys.exit(1)

    try:
        data = _parse(content)
    except ValueError as e:
        # Config file exists but is invalid — fail explicitly so the user knows.
        print(f"::error::reviewsentry.yml is invalid: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"::error::reviewsentry.yml could not be parsed: {e}")
        sys.exit(1)

    warnings = []
    overrides = {}
    custom_criteria = []

    # Check for disabled core criteria without acknowledgement
    disabled_core = [k for k in CORE_CRITERIA if data.get(k) is False]
    if disabled_core:
        if not data.get("acknowledge_disabled_core"):
            warnings.append(
                f"⚠️ reviewsentry.yml attempted to disable core criteria "
                f"{[k.replace('_', ' ') for k in disabled_core]} but "
                f"'acknowledge_disabled_core: true' was not set — "
                f"these criteria are still active. Add "
                f"'acknowledge_disabled_core: true' to suppress them explicitly."
            )
            for k in disabled_core:
                data.pop(k)
        else:
            warnings.append(
                f"Core criteria {disabled_core} explicitly disabled via "
                f"acknowledge_disabled_core. Sensitive data scan will not run."
            )

    # Collect criterion overrides (only boolean values accepted)
    for key in ALL_CRITERIA:
        if key in data and isinstance(data[key], bool):
            overrides[key] = data[key]

    # Collect custom criteria with length and count caps
    if "custom" in data and isinstance(data["custom"], list):
        raw = [str(c).strip() for c in data["custom"] if str(c).strip()]
        if len(raw) > MAX_CUSTOM_CRITERIA:
            print(
                f"::warning::reviewsentry.yml defines {len(raw)} custom criteria; "
                f"only the first {MAX_CUSTOM_CRITERIA} will be used."
            )
            raw = raw[:MAX_CUSTOM_CRITERIA]
        for c in raw:
            if len(c) > MAX_CRITERION_LENGTH:
                print(
                    f"::warning::reviewsentry.yml custom criterion exceeds "
                    f"{MAX_CRITERION_LENGTH} characters and will be skipped: "
                    f"'{c[:60]}...'"
                )
        custom_criteria = [c for c in raw if len(c) <= MAX_CRITERION_LENGTH]

    # Collect behaviour flags (boolean values only)
    behaviour: dict[str, bool] = {}
    for key in BEHAVIOUR_FLAGS:
        if key in data and isinstance(data[key], bool):
            behaviour[key] = data[key]

    return overrides, custom_criteria, warnings, behaviour
