# AI Code Review Agent

Repository-aware AI pull request reviews using GitHub Actions and OpenAI.

This is a small Docker-based GitHub Action. It reviews the PR diff with surrounding file context, validates findings deterministically, and publishes a GitHub pull request review with inline comments.

## What it does

On `pull_request` (`opened` / `synchronize` / `reopened`):

1. Reads the GitHub PR event and base/head SHAs
2. Collects the git diff and changed line numbers
3. Filters lockfiles, binaries, build artifacts, and other noisy paths
4. Collects lightweight surrounding source context
5. Sends diff + context to OpenAI (structured Pydantic output)
6. Validates findings (changed file/line, confidence, duplicates)
7. Publishes a PR review with inline comments for correctness / security / style

## Features

- Language-agnostic review (works across common text source files)
- Correctness, security, tests, and style/format focus
- Deterministic finding validator
- Inline GitHub review comments
- Duplicate review prevention per PR head SHA
- Conservative size limits for large PRs
- Bring-your-own-key (BYOK) OpenAI usage
- No hosted backend, database, Redis, RAG, or multi-agent runtime

## Supported languages

The Action implementation is Python, but the reviewer is language-agnostic and works on common text code such as:

- Python
- JavaScript / TypeScript
- React / React Native
- Java
- C#
- Go

It does **not** use language-specific ASTs. Quality is best when the diff itself shows concrete evidence.

## How it works

```text
PR event
  → git diff + changed lines
  → file filter + size limits
  → lightweight context windows
  → OpenAI structured review
  → validator (file/line/confidence/dedupe)
  → GitHub PR review (summary + inline comments)
```

## Setup

### 1. Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```

### 2. Secrets

Add an OpenAI API key as a repository (or org) Actions secret:

- Name: `OPENAI_API_KEY`
- Value: your OpenAI key

Do **not** put API keys in repository files.

`GITHUB_TOKEN` is provided by Actions automatically for `github-token`.

### 3. Workflow example

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: kkureli/ai-code-review-agent@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

Optional inputs:

```yaml
      - uses: kkureli/ai-code-review-agent@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          model: gpt-5-mini
          min-confidence: "0.80"
          min-severity: medium
          max-comments: "8"
```

## Action inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github-token` | yes | — | Token with `pull-requests: write` |
| `openai-api-key` | yes | — | OpenAI API key (BYOK) |
| `model` | no | `gpt-5-mini` | OpenAI model |
| `min-confidence` | no | `0.75` | Minimum confidence to publish |
| `min-severity` | no | `medium` | Minimum severity to publish (`low`, `medium`, or `high`) |
| `max-comments` | no | `10` | Max inline comments |

`min-severity: medium` publishes HIGH and MEDIUM findings and suppresses LOW. Use `low` to publish all severities.

## Security / BYOK

- This Action is **bring your own key**
- `OPENAI_API_KEY` must live in GitHub Actions Secrets
- The Action does not require a hosted backend or database
- Review prompts include PR diffs and nearby source context; treat that as sensitive data shared with OpenAI under your account

## Example output

A published review looks like:

- Summary body with a hidden marker such as `<!-- ai-code-review-agent:<head_sha> -->`
- Inline comments on changed lines for correctness / security / style
- PR-level details for test findings
- Or: `No meaningful issues found.` for a clean PR

Rerunning the same job for the **same head SHA** does not publish a duplicate review.

## Architecture overview

| Module | Role |
|--------|------|
| `src/main.py` | Action entrypoint / orchestration |
| `src/config.py` | Action input parsing |
| `src/filters.py` | Ignore rules + size limits |
| `src/diff_parser.py` | New-side changed line extraction |
| `src/context_collector.py` | Bounded surrounding context |
| `src/reviewer.py` | OpenAI structured review |
| `src/finding_validator.py` | Deterministic publish filters |
| `src/github_publisher.py` | GitHub review publish + duplicate marker |

## Limitations

- Not a replacement for human review or security audits
- No AST / typechecker / language server integration
- Large generated files are ignored or truncated
- Findings require evidence in the supplied diff/context
- OpenAI availability and model quality affect results
- Inline comments are capped; summary may still list additional findings

## Marketplace installation example

After publishing a Marketplace release (separate step):

1. Open the Action page on GitHub Marketplace
2. Click **Use latest version**
3. Paste the workflow example above
4. Add `OPENAI_API_KEY` to repository secrets

Until Marketplace publication, use the repo tag form:

```yaml
- uses: kkureli/ai-code-review-agent@v1
```

## Local development / tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest

PYTHONPATH=. python -m pytest -q

docker build -t ai-code-review-agent-test .
```

## Manual sandbox checks

See [RELEASE.md](./RELEASE.md) for the V1 release checklist and suggested sandbox PR scenarios (buggy JS/TS/React, clean PR, duplicate SHA rerun).

## License

MIT
