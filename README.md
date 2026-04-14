# TestForge

**Know what your PR broke — before CI does.**

TestForge analyzes your code changes, predicts regressions, and tells you exactly what to validate before merging.

---

## ⚡ Example

```bash
testforge validate --base main --feature my-branch
```

```
🔍 Behavioral Impact:
Change introduces conditional routing of requests based on configuration.

💥 Potential Regressions:

🔥 HIGH RISK:
- Requests may return 401 Unauthorized instead of expected success

🧪 Suggested Validations:

🔥 1. Merchant requiring dynamic token  
   → Expect: correct response via DynamicTokenRequestManager

🚨 Merge Risk: HIGH
```

👉 This is what your code change might break — instantly.

---

## 🚀 Why TestForge?

When you make a change:

* ❌ You don’t know what you broke
* ❌ CI tells you too late
* ❌ Tests don’t cover everything

TestForge helps you:

* 🔍 Identify impacted endpoints
* ⚠️ Understand risk of change
* 🧠 Get targeted validation suggestions
* 🚨 Catch regressions early

All before you merge.

---

## ⚡ Quick Start

```bash
pip install testforge
testforge init
testforge validate --base main --feature my-branch
```

---

## 🧰 Commands

```bash
testforge validate --base <branch> --feature <branch> [--path /path/to/repo]
testforge config show
testforge config check
```

---

## ⚙️ Configuration

Default location: `~/.testforge/config.yaml`

| Field           | Description                   | Default       |
| --------------- | ----------------------------- | ------------- |
| `llm_provider`  | Provider name (e.g. `openai`) | `openai`      |
| `llm_api_key`   | API key (set via `init`)      | empty         |
| `default_model` | Default model id              | `gpt-4o-mini` |
| `log_level`     | `DEBUG`, `INFO`, `ERROR`, …   | `INFO`        |

---

## 🧠 How It Works

TestForge uses a **change-aware validation pipeline**:

```
Git Diff
→ Change Analysis
→ Impact Mapping (functions → endpoints)
→ Risk Classification
→ LLM-based Validation Planning
```

It does **not** rely on:

* full test coverage
* running services
* complex infrastructure

Instead, it focuses on **what actually changed and what might break**.

---

## 🎯 When to Use

Use TestForge when:

* Reviewing a PR
* Before merging to main
* Validating risky changes
* Unsure what to test

---

## 🧪 Development

```bash
pytest
```

---

## 🤝 Contributing

Contributions, ideas, and feedback are welcome.

If TestForge helped you catch a bug — please open an issue or share your experience 🙌

---

## 📜 License

MIT
