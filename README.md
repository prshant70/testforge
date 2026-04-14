# TestForge

Change-aware validation assistant for Git diffs: identifies impacted areas, classifies risk, and suggests what should be validated before merging.

## Requirements

- Python 3.10+
- [Git](https://git-scm.com/) on `PATH`

## Install (editable)

```bash
pip install -e ".[dev]"
```

## Usage

```bash
testforge --help
testforge init                    # creates ~/.testforge/config.yaml
testforge config show             # prints config (API key masked)
testforge config check            # verify config file and field values

testforge validate --base main --feature my-branch [--path /path/to/repo]
```

### Configuration

Default location: `~/.testforge/config.yaml`

| Field           | Description                    | Default   |
|-----------------|--------------------------------|-----------|
| `llm_provider`  | Provider name (e.g. `openai`)  | `openai`  |
| `llm_api_key`     | API key (set via `init`)       | empty     |
| `default_model`   | Default model id               | `gpt-4o-mini` |
| `log_level`       | `DEBUG`, `INFO`, `ERROR`, …    | `INFO`    |

## Development

```bash
pytest
```

## License

MIT
