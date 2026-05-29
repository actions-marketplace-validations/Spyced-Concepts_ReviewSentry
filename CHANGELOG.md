# Changelog

All notable changes to ReviewSentry are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html) — applied by *type of change*, not by a fixed release cadence:

- **MAJOR** (`vX.0.0`) — breaking changes
- **MINOR** (`v0.X.0`) — new features
- **PATCH** (`v0.X.Y`) — bug fixes, hotfixes, and documentation-only changes

Releases are not scheduled — they ship when there is something to ship.

> **Prior name.** Before 2026-05-09 (v0.2.2-alpha) this project was called `ai-pr-review`. The action's `name:` field has been `ReviewSentry` since v0.2.2-alpha; the GitHub repository slug was renamed to `Spyced-Concepts/ReviewSentry` on 2026-05-14. Historical CHANGELOG entries and UAT records below preserve their original wording.

---

## [0.3.5-beta] — 2026-05-29

### Security

- **Gemini API key removed from URL** — key was previously passed as a `?key=` query parameter, logging it in server-side access logs and CDN traces. Moved to the `X-goog-api-key` request header. (#129)
- **`GITHUB_OUTPUT` multiline delimiter randomised** — the static `AI_REVIEW_EOF` delimiter is replaced with `f"AI_REVIEW_EOF_{secrets.token_hex(8)}"` to prevent output truncation if the AI-generated review happens to contain the delimiter string on its own line. Matches the fix already applied to the `REVIEWSENTRY_CONFIG` heredoc in #131. (#158)
- **`set -euo pipefail` added** to the `Post no-changes comment` step — the only `run:` block in `action.yml` that previously lacked it. (#136)
- **`actions/checkout` pinned to full commit SHA** in the test workflow (`11bd71901bbe5b1630ceea73d27597364c9af683` — v4.2.2), consistent with the SHA-pinning guidance in `SECURITY.md`. (#161)

### Fixed

- **Draft PR skip logic** — `exit 0` inside a composite action `run:` step does not skip downstream steps; replaced with `echo "draft_skip=true" >> "$GITHUB_OUTPUT"` and `if: steps.draft-check.outputs.draft_skip != 'true'` guards on all downstream steps. (#130)
- **`custom_rules` feature fully implemented** — the `custom_rules` input was wired in `action.yml` and documented, but `review.py` never read `CUSTOM_RULES` from the environment. Custom sensitive data patterns are now read, parsed, and appended to the Sensitive data criterion as High-severity project-specific terms. (#145)
- **Heredoc delimiter for `REVIEWSENTRY_CONFIG`** — `openssl rand -hex 8` replaced with `python3 -c 'import secrets; print(secrets.token_hex(8))'`; `openssl` is not guaranteed available on all runner images. (#131)
- **Adapter interface check** in `test.yml` now includes `max_tokens` in `required_sig` — a new adapter omitting the parameter would previously pass the check and fail silently at runtime. (#162)

### Added

- **`pr_body_chars` input** — configures the maximum PR description characters included in the review context (default 2000; previously hardcoded 500). When truncated, the prompt includes the character count omitted so the AI does not flag the description as incomplete.

### Changed

- Severity indicator wording tightened: 🟡 Moderate = *"a specific code change is recommended"*; 🔵 Low/Informational = *"observation only, no fix needed — choose 🔵 when your analysis concludes the code is already correct"*.

---

## [0.3.4-beta] — 2026-05-29

### Added

- **Diff chunking** (`chunk_large_diffs` in `.github/reviewsentry.yml`) — set `chunk_large_diffs: true` to review the full diff across multiple passes rather than truncating. When `false` or absent (default), large diffs are still truncated at `diff_lines` lines but the review now lists any files that were not reviewed so nothing is silently skipped. Multi-pass reviews aggregate all findings with a combined worst-case verdict. (#95)
- `scripts/diff_utils.py` — pure utility module for diff splitting, file batching, verdict extraction, review aggregation, and review-output splitting. Importable directly by tests.
- Empty-diff handling: sync/promotion PRs (e.g. `main → functional-test`) that produce no diff now exit with a pass and post an informational comment instead of failing CI. (#95)
- **`max_tokens` input** — configurable AI response token limit, default 4096 (was hardcoded 1024 in all adapters). Reviews no longer cut off mid-criterion on non-trivial PRs. Values below 256 are clamped. (#96)
- **Output splitting** — reviews exceeding 50,000 characters are automatically split at criterion-section boundaries and posted as sequential PR comments labelled `(1/N)`, `(2/N)`, etc. The verdict always appears in the last comment. (#96)
- 14 new tests in `tests/test_output_splitting.py`.
- **Four-level severity indicators** — 🔴 Critical (block merge) · 🟠 High (fix before merge) · 🟡 Moderate (worth fixing) · 🔵 Low/Informational (noted, no action required). Previously 🟡 covered both Moderate and Low, making informational notes visually indistinguishable from genuine warnings. (#97)
- Severity legend added to the comment footer so the colour scheme is self-explanatory without reading the docs.

### Changed

- `diff_lines` input repurposed from a hard truncation cap to a lines-per-chunk threshold. Existing values continue to work; the behaviour change is that the diff is no longer silently cut — skipped files are now listed.
- Diff capture step no longer uses `head -n` — the full diff is always captured; Python handles truncation or chunking.
- All four adapters (`anthropic`, `openai`, `gemini`, `github_models`) now accept a `max_tokens` keyword argument (default 4096) passed from `review.py`. Default raised from 1024 → 4096.
- Post review comment step updated: review.py writes per-part files to `$RUNNER_TEMP`; action.yml iterates and posts each file. Header, per-part label, and footer are written by Python.

---

## [0.3.3-beta] — 2026-05-15

### Added
- **`fail_on` input** — set to `request_changes` to exit non-zero when the AI verdict is REQUEST CHANGES, enabling merge blocking via required status checks. Default `never`.
- **`verdict` output** — exposes the AI verdict as an action output for downstream workflow steps.
- **`show_passing_criteria` input** — set to `false` to show only criteria with findings, keeping reviews concise on large PRs. Default `true`.
- **`review_drafts` input** — set to `false` to skip review on draft PRs. Default `true` (current behaviour unchanged).
- **`system_context` input** — optional project-specific context appended to the AI system prompt.
- **Extensible criteria configuration** via `.github/reviewsentry.yml` — disable optional criteria, add custom criteria, and (with explicit acknowledgement) disable core criteria per-repo.
- **Advisory verdict format** — verdict line includes emoji and `AI Recommendation:` prefix; always the absolute last line of the review.
- **Colour indicators** — 🔴/🟠/🟡 per finding severity; ✅/⚠️ per criterion section header.
- **Self-review CI** — ReviewSentry now reviews its own pull requests via GitHub Models at zero external cost.
- **BDD test suite** — `features/` Gherkin feature files and `tests/` pytest-bdd step definitions; 19 scenarios pass locally, e2e scenarios run in CI.
- **KNOWN_ISSUES.md** — documents four user-facing limitations with workarounds.
- **Recommended workflow** in README — six-step guide: draft → address findings → ready for review → confirm checks → peer review → merge.

### Fixed
- `gh pr diff` and `gh pr comment` missing `--repo` flag causing failures when running without a checkout step.
- False-positive model name validation in reviews — model identifiers are now treated as opaque strings per the system prompt.
- Prompt injection hardening — `pr_title` and `pr_body` documented as untrusted and passed via environment variables only.
- Verdict extraction robust against token-limit truncation — optional closing `**`; extraction failure emits `::warning::` and exits 0 rather than failing the check.

### Changed
- Review footer updated to make advisory nature explicit: *AI-generated advisory review. All verdicts are recommendations only — the final merge decision rests with the human maintainer.*
- `docs/uat/` removed — UAT coverage replaced by BDD feature files in `features/`.

---

## [0.3.2-beta] — 2026-05-14

### Security
- **Removed the `@v0` floating tag** to eliminate the supply-chain risk class. Floating tags are mutable — the maintainer (or anyone gaining write access) can rewrite where they point, and consumers' next run silently executes the new code with their secrets. SHA pinning is now the only supported pattern. See `SECURITY.md`.

### Changed
- **All documentation now recommends SHA pinning with a version comment** (Dependabot-readable). Tag pinning, including version tags, is no longer documented as a supported pattern.
- **Repository renamed from `ai-pr-review` to `ReviewSentry`** to match the marketplace listing and the action's `name:` field. GitHub Actions does NOT redirect `uses:` references for renamed action repositories (deliberate security policy) — every consumer must update their `uses:` line to the new slug.
- Documentation, issue/discussion templates, and code docstrings updated to use the current name `ReviewSentry` throughout. Historical CHANGELOG entries and UAT records preserved unchanged.

---

## [Unreleased] — v0.2.0-alpha

### Added
- **Provider adapter architecture** — `scripts/adapters/` package; core `review.py` is now provider-agnostic with zero AI-vendor references; dispatches via `AI_PROVIDER` env var
- **Anthropic adapter** (`adapters/anthropic.py`) — extracted from original `review.py`; prompt caching retained
- **OpenAI adapter** (`adapters/openai.py`) — OpenAI Chat Completions API; also works with Groq, Azure OpenAI, Mistral, Ollama, and **GitHub Models** via `ai_base_url`
- **Gemini adapter** (`adapters/gemini.py`) — Google Gemini generateContent API
- **`ai_provider` input** — selects the adapter; default `anthropic` (backwards-compatible)
- **`ai_base_url` input** — optional base URL override for OpenAI-compatible endpoints
- **`custom_rules` input** — user-definable sensitive data scan rules (FR-009)
- **Sensitive data disclosure scan** — always-on, always-first criterion (FR-008): credentials, personal identifiers, private paths, computer/host names, private repo names; severity-classified Critical → High → Moderate
- **GitHub Models support** — free AI code review using `GITHUB_TOKEN`; documented in `docs/setup-github-models.md`
- **Schema metadata** — YAML frontmatter in all `docs/setup-*.md` files (provider, adapter, cost, available models, complexity)
- **Provider setup docs** — `docs/setup-anthropic.md`, `docs/setup-openai.md`, `docs/setup-gemini.md`, `docs/setup-github-models.md`
- `CHANGELOG.md` (this file)
- `CONTRIBUTING.md`
- **`SECURITY.md`** — includes per-provider data handling policy links, what data is transmitted, and user responsibility statement
- **Data Handling Notice** in `LICENSE` — explicit user responsibility clauses for third-party AI data transmission

### Changed
- `action.yml` description updated — leads with security-first and zero-cost positioning for GitHub Marketplace
- `README.md` rewritten — differentiation table, security-first positioning, GitHub Models as the zero-cost quick start, architecture diagram, provider comparison table
- Review criteria renumbered — sensitive data disclosure is criterion 1 (was absent in v0.1.0)

### Breaking change

**`ai_provider` is now required.** There is no default. This is an intentional choice — as an open-source, provider-agnostic tool we do not favour any particular AI. Existing workflows that did not set `ai_provider` will now fail with a clear error listing the supported providers.

**Migration:** add `ai_provider: anthropic` (or your chosen provider) to any workflow that previously omitted it.

### Changed
- Review criteria renumbered — sensitive data disclosure is now criterion 1 (was absent); all others shifted by one
- `review.py` docstring updated — removes AI-vendor references; reflects new adapter architecture

### Migration guide (v0.1.0 → v0.2.0)

No breaking changes. Existing workflows that don't set `ai_provider` default to `anthropic` and behave identically to v0.1.0. To opt in to a different provider, add `ai_provider: openai` (or `gemini`) to your workflow step.

---

## [0.1.0] — 2026-05-05

### Added
- Initial release
- `action.yml` — composite GitHub Action
- `scripts/review.py` — single-file review script (Anthropic default)
- `README.md`, `LICENSE` (MIT, England and Wales governing law)
- Product specification (`docs/` — vault-side)
