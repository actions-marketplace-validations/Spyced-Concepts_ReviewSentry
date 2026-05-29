# ReviewSentry

**Security-first automated code review for every pull request. Free with GitHub Models — or bring your own Anthropic, OpenAI, or Gemini key.**

No dashboards. No per-review billing. No vendor lock-in. MIT licensed.

> Built by [Spyced Concepts Ltd.](https://spycedconcepts.co.uk) — a security-focused software company.

---

## Why ReviewSentry

Most AI code review tools focus on code quality. This one leads with **security**.

Every review starts with a sensitive data disclosure scan — catching credentials, personal identifiers, private paths, and computer names before they reach your commit history. This criterion runs first, always, before any other finding is reported.

| | ReviewSentry | Typical AI review action |
|---|---|---|
| Sensitive data scan | ✅ First criterion, always | ✗ Not included |
| Free with existing GitHub account | ✅ GitHub Models | ✗ Requires paid AI subscription |
| Multiple providers (your key) | ✅ 5 providers + any OpenAI-compatible | Usually 1–2 |
| Custom scan rules | ✅ Add your own patterns | Rarely |
| MIT open source | ✅ | Sometimes |
| No dashboard or account required | ✅ | Often required |

---

## Supported providers

| Provider | `ai_provider` | Cost | Notes |
|---|---|---|---|
| **GitHub Models** | `github-models` | **Free** | Uses your `GITHUB_TOKEN` — no extra account needed |
| Anthropic | `anthropic` | Per-token | Prompt caching enabled — lower cost on repeated reviews |
| OpenAI | `openai` | Per-token | |
| Google Gemini | `gemini` | Per-token / free tier | |
| Groq | `openai` + `ai_base_url` | Per-token / free tier | Fast inference |
| Azure OpenAI | `openai` + `ai_base_url` | Per-token | Enterprise data handling |
| Ollama (self-hosted) | `openai` + `ai_base_url` | Free | Run locally or on your own server |

**Required fields per provider:**

| Provider | `ai_provider` | `ai_api_key` | `ai_model` | `ai_base_url` | `permissions` |
|---|---|---|---|---|---|
| GitHub Models | `github-models` | `${{ secrets.GITHUB_TOKEN }}` | e.g. `gpt-4o` | not needed | `models: read` |
| Anthropic | `anthropic` | `${{ secrets.AI_API_KEY }}` | e.g. `claude-sonnet-4-6` | not needed | standard |
| OpenAI | `openai` | `${{ secrets.AI_API_KEY }}` | e.g. `gpt-4o` | not needed | standard |
| Groq | `openai` | `${{ secrets.AI_API_KEY }}` | e.g. `llama-3.3-70b-versatile` | `https://api.groq.com/openai` | standard |
| Azure OpenAI | `openai` | `${{ secrets.AI_API_KEY }}` | your deployment name | your Azure endpoint | standard |
| Gemini | `gemini` | `${{ secrets.AI_API_KEY }}` | e.g. `gemini-2.0-flash` | not needed | standard |
| Ollama | `openai` | any value | e.g. `qwen2.5-coder` | your Ollama host | standard |

> **Standard permissions:** `pull-requests: write`. GitHub Models additionally requires `models: read`.
>
> **Secret and variable names are yours to choose.** The names `AI_API_KEY` and `AI_MODEL` used throughout this documentation are examples only. Store your key under any name you like and reference it with `${{ secrets.YOUR_CHOSEN_NAME }}`. The action only reads what you pass to its inputs — it has no dependency on specific environment variable names.

**Full setup guides:** [`docs/`](docs/)

---

## Quick start

Choose your provider and add the workflow. `ai_provider` is required — no default is set so you make an explicit, informed choice.

**GitHub Models** — free, uses your existing `GITHUB_TOKEN`, no extra account:
```yaml
          ai_api_key:  ${{ secrets.GITHUB_TOKEN }}
          ai_model:    gpt-4o
          ai_provider: github-models
```
> Requires `models: read` in your workflow permissions block.

**Anthropic:**
```yaml
          ai_api_key:  ${{ secrets.YOUR_API_KEY }}
          ai_model:    claude-sonnet-4-6
          ai_provider: anthropic
```

**OpenAI:**
```yaml
          ai_api_key:  ${{ secrets.YOUR_API_KEY }}
          ai_model:    gpt-4o
          ai_provider: openai
```

**Gemini:**
```yaml
          ai_api_key:  ${{ secrets.YOUR_API_KEY }}
          ai_model:    gemini-2.0-flash
          ai_provider: gemini
```

**Full workflow file:**
```yaml
# .github/workflows/ai-review.yml
name: AI PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: reviewsentry-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      pull-requests: write
      # models: read   # add this line if using github-models
    steps:
      - uses: Spyced-Concepts/ReviewSentry@<commit-sha>  # see Releases for latest, e.g. v0.3.3-beta
        with:
          ai_api_key:   ${{ secrets.YOUR_API_KEY }}
          ai_model:     your-model-identifier
          ai_provider:  your-provider     # anthropic | openai | gemini | github-models
          pr_number:    ${{ github.event.pull_request.number }}
          pr_title:     ${{ github.event.pull_request.title }}
          pr_body:      ${{ github.event.pull_request.body }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

See the [setup guides](docs/) for provider-specific instructions and model lists.

### Version pinning — SHA only

**SHA pinning is the only supported pattern.** Tags are mutable; floating tags (`@v0`, `@v1`) and version tags (`@v0.3.3-beta`) can all be rewritten by the maintainer or anyone who gains access to the repository, and consumers' next workflow run would silently execute the new code with their secrets. Pinning to a full commit SHA gives cryptographic immutability — the exact code you reviewed is the exact code that will run.

```yaml
# Recommended (the only supported pattern)
- uses: Spyced-Concepts/ReviewSentry@<full-40-char-sha>  # v0.3.3-beta
```

The trailing version comment is human metadata and is read by Dependabot, which can open auto-update PRs when newer releases ship.

Find the SHA for any release on the [Releases page](https://github.com/Spyced-Concepts/ReviewSentry/releases) — click the release and copy the full commit SHA, then update your workflow.

The `@v0` floating tag was removed on 2026-05-14. See the [CHANGELOG](CHANGELOG.md).

---

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `ai_api_key` | ✓ | — | AI provider API key. Use `${{ secrets.GITHUB_TOKEN }}` for GitHub Models. |
| `ai_model` | ✓ | — | Model identifier — see provider setup guide |
| `ai_provider` | ✓ | — | Adapter: `anthropic`, `openai`, `gemini`, or `github-models` |
| `ai_base_url` | | `""` | Base URL override for OpenAI-compatible endpoints (GitHub Models, Groq, Azure, Ollama) |
| `pr_number` | ✓ | — | Pull request number |
| `pr_title` | ✓ | — | Pull request title |
| `pr_body` | | `""` | Pull request description |
| `diff_lines` | | `1500` | Lines-per-chunk threshold for diff processing. Behaviour depends on `chunk_large_diffs` in `.github/reviewsentry.yml`: if chunking is enabled, this is the max lines per review pass; if chunking is disabled (default), diffs exceeding this limit are truncated and the review lists any files that were not reviewed. Raise this value for large refactors; lower it if you hit provider token limits. |
| `review_criteria` | | `""` | Additional review criteria, one per line |
| `custom_rules` | | `""` | Custom sensitive data scan patterns, one per line |
| `show_passing_criteria` | | `true` | Default: `true`. Whether to include passing criteria (no issues found) in the review output. Set to `false` to show only criteria with findings, keeping reviews concise on large PRs. Accepted values: `true`/`1`/`yes` or `false`/`0`/`no`. Any other value triggers a workflow warning and defaults to `true`. |
| `fail_on` | | `never` | Default: `never`. When to fail the workflow based on the AI verdict. Set to `request_changes` to exit non-zero when the verdict is REQUEST CHANGES, blocking PR merges via required status checks. Accepted values: `never`, `request_changes`. Any other value triggers a workflow warning and defaults to `never`. |
| `review_drafts` | | `true` | Default: `true`. Whether to review draft pull requests — drafts are reviewed by default. Set to `false` to skip review until the PR is marked ready for review. Accepted values: `true`/`1`/`yes` or `false`/`0`/`no`. Any other value triggers a workflow warning and defaults to `true`. |
| `github_token` | ✓ | — | GitHub token for posting the review comment |

## Outputs

| Output | Description |
|---|---|
| `review` | The full review text posted as a PR comment |
| `verdict` | The AI verdict — one of `APPROVE`, `APPROVE WITH NOTES`, or `REQUEST CHANGES`. Empty string if the verdict could not be extracted (workflow warning emitted). |

---

## Recommended workflow

ReviewSentry works best when it acts as a first-pass reviewer that your team builds on, not a gate that replaces human judgement.

**1. Open your PR as a draft**

Raise the pull request as a draft. ReviewSentry reviews it immediately — any issues flagged before a human even looks at it.

**2. Address the review findings**

For each finding in the AI review comment:
- **Fix it** — commit the fix to the same branch; ReviewSentry re-reviews automatically.
- **Explain it** — if the finding is a false positive or an intentional choice, leave a short comment on the PR explaining why. This creates a record for the human reviewer.

**3. Mark the PR ready for review**

Once you are satisfied with the AI review findings, mark the PR ready for review. Push a final trivial commit if you want to trigger one last ReviewSentry run at this point (see [KI-004](KNOWN_ISSUES.md#ki-004) — the ready-for-review event does not currently re-trigger the check automatically).

**4. Confirm all checks are green**

Check that all required status checks pass and that the AI review verdict is `APPROVE` or `APPROVE WITH NOTES`. A verdict of `REQUEST CHANGES` with unresolved findings warrants a second look before requesting a human reviewer.

**5. Request a peer review**

Assign a human reviewer. Share the AI review comment as context — it gives the reviewer a structured starting point and surfaces any issues you've already addressed or explained.

**6. Merge**

The human reviewer merges when they are satisfied with both the code and the AI review. The AI verdict is advisory — the final merge decision always rests with the human maintainer.

---

## Review criteria

Every review checks these criteria in order:

1. **Sensitive data disclosure** *(security-first)* — credentials, API keys, personal information, file paths revealing usernames, computer/host names, private repo names. Severity-classified: Critical → High → Moderate. Always reported before any other finding.
2. **Merge conflicts** — immediate blocker
3. **Correctness** — edge cases, logic errors
4. **Cross-platform compatibility** — macOS, Linux, Windows (Git Bash)
5. **Bash quality** — `set -euo pipefail`, quoting, portability
6. **Security** — injection risks, unsafe variable expansion
7. **Code quality** — magic values, code smells, correct approach
8. **Dependencies** — external modules flagged
9. **Documentation** — docs updated alongside code changes
10. **PR scope** — single concern?

Add custom criteria via `review_criteria`. Add domain-specific sensitive data patterns via `custom_rules` (e.g. internal product names, employee identifiers).

---

## Per-repo configuration (`.github/reviewsentry.yml`)

Drop a `.github/reviewsentry.yml` file in your repository to customise ReviewSentry's behaviour without touching the workflow file.

### Diff handling for large PRs

By default, ReviewSentry truncates the diff at `diff_lines` lines and lists any files that were not reviewed. To review the entire diff across multiple passes instead, set:

```yaml
# .github/reviewsentry.yml
chunk_large_diffs: true
```

| `chunk_large_diffs` value | Behaviour |
|---|---|
| Missing or `false` | Truncate at `diff_lines`; list skipped files in the review comment |
| `true` | Capture the full diff; split by file boundary if over threshold; run one review pass per batch; aggregate findings with a combined worst-case verdict |

### Disabling criteria

```yaml
# Disable optional criteria
cross_platform: false
bash_quality: false

# Disable a core criterion — requires explicit acknowledgement
sensitive_data: false
acknowledge_disabled_core: true
```

### Custom criteria

```yaml
custom:
  - "Verify all async functions include error handling"
  - "Flag any use of console.log in production code"
```

---

## Architecture

```
scripts/
  review.py            # Provider-agnostic core — zero vendor references
  diff_utils.py        # Diff splitting, batching, and review aggregation
  config.py            # .github/reviewsentry.yml loader and validator
  adapters/
    anthropic.py       # Anthropic Claude
    openai.py          # OpenAI + any OpenAI-compatible endpoint
    gemini.py          # Google Gemini
    github_models.py   # GitHub Models (zero-cost with GITHUB_TOKEN)
docs/
  setup-anthropic.md
  setup-openai.md
  setup-gemini.md
  setup-github-models.md
```

Adding a new provider means implementing one function in a new adapter file. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Security and data handling

This action transmits only the PR diff and PR title/body to your chosen AI provider. See [SECURITY.md](SECURITY.md) for:
- Exactly what data is transmitted
- Per-provider data handling policy links
- Your responsibilities when using with private or regulated codebases

**Important:** You are responsible for ensuring your use of this action — and the transmission of code content to third-party AI providers — complies with your applicable legal obligations, IP rights, and your provider's terms of service. See the [Data Handling Notice](LICENSE) in the licence.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). To add a new AI provider, implement `call_api()` in `scripts/adapters/<provider>.py` and add a setup guide in `docs/`. The adapter interface is fully documented.

---

## Licence

MIT — see [LICENSE](LICENSE). Governing law: England and Wales.

Made by [Spyced Concepts Ltd.](https://spycedconcepts.co.uk)
