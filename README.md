# TestForge

Turn a Git diff into a pre-merge validation report.

TestForge looks at what changed between two branches and tells you:

- what behavior actually changed
- what’s most likely to break
- what to verify before merging
- whether the change looks safe to merge

It’s meant to feel like a quick senior-engineer review of your PR, not a test generator.

---

## Example

```bash
testforge validate --base main --feature my-branch
```

```
🧭 Change Intent:
Intentional (High Confidence)

🎯 Analysis Confidence:
High
- Clear structural change detected
- Change is localized

🔍 Behavioral Impact:
Introduces conditional routing for merchants requiring dynamic tokens.

💥 Change-Induced Risks:

🔥 HIGH RISK:
- Change: DynamicTokenRequestManager
  Impact: alters handling of merchants without cached tokens

🧪 Suggested Validations:

🔥 1. Merchant requiring dynamic token
   → Expect: routed via DynamicTokenRequestManager, 200 OK

🚨 Merge Risk: HIGH
```

That’s what you get from a single command on your local branch, no CI needed.

---

## Install

Requires: **macOS or Linux**, **Python 3.10+**, and **Git**.

One-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/prashantmishra/testforge/main/install.sh | bash
```

The installer prefers `pipx` for an isolated install and falls back to `pip --user`. To install from source:

```bash
git clone https://github.com/prashantmishra/testforge.git
cd testforge
pip install -e ".[dev]"
```

---

## First use

1. Set up your config (prompts for LLM provider, model, and API key):

```bash
testforge init
```

2. From inside a Git repo, run:

```bash
testforge validate --base main --feature my-branch
```

Or from anywhere:

```bash
testforge validate --base main --feature my-branch --path /path/to/repo
```

3. Check your config anytime:

```bash
testforge config show
testforge config check
```

---

## Commands

```bash
# Core
testforge validate --base <branch> --feature <branch> [--path /path/to/repo] [--nocache]

# Setup / config
testforge init
testforge config show
testforge config check

# Local cache (per repo + commit pair, 7-day TTL)
testforge cache list
testforge cache purge --expired
testforge cache purge --all
```

Notable flags:

- `--path` — point at a repo outside your current directory
- `--nocache` — ignore the local cache and re-run the full pipeline

---

## Configuration

Config lives at `~/.testforge/config.yaml` (created by `testforge init`).

| Field           | Description                                  | Default         |
| --------------- | -------------------------------------------- | --------------- |
| `llm_provider`  | LLM provider (e.g. `openai`)                 | `openai`        |
| `llm_api_key`   | API key used for LLM calls                   | *(empty)*       |
| `default_model` | Model used for analysis                      | `gpt-4o-mini`   |
| `log_level`     | `DEBUG`, `INFO`, `WARNING`, `ERROR`          | `INFO`          |

Without an API key, TestForge falls back to a minimal, deterministic output.

---

## How it works

TestForge runs a deterministic-first pipeline over your Git diff:

```
Git Diff
  → Change Analyzer       (files, diff text; excludes lockfiles)
  → Intent Classifier     (intentional vs unintended)
  → Impact Mapper         (changed code → likely endpoints, LLM-assisted)
  → Risk Classifier       (validation / error handling / persistence / external calls)
  → Confidence Scorer     (how much to trust the analysis)
  → Validation Planner    (LLM, evidence-based, structured output)
```

Results are cached per `(repo, base SHA, feature SHA)` for **7 days**, so re-running is fast.

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

---

## License

MIT
