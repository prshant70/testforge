"""Smoke tests for the TestForge CLI."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from testforge.cli import app

runner = CliRunner()


def _exit_code_main(*args: str) -> int:
    """Run the real console entrypoint (same as the `testforge` script)."""
    old = sys.argv[:]
    try:
        sys.argv = ["testforge", *args]
        from testforge.cli import main

        try:
            main()
        except SystemExit as exc:
            return int(exc.code) if exc.code is not None else 0
        return 0
    finally:
        sys.argv = old


def _git_init_with_commit(repo: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_root_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "TestForge" in result.stdout


def test_generate_requires_path() -> None:
    result = runner.invoke(app, ["generate"])
    assert result.exit_code != 0


def test_generate_runs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    svc = tmp_path / "svc"
    svc.mkdir()
    result = runner.invoke(app, ["generate", "--path", str(svc)])
    assert result.exit_code == 0
    assert "Generating tests" in caplog.text


def test_perf_stub(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    result = runner.invoke(app, ["perf"])
    assert result.exit_code == 0
    assert "not implemented" in caplog.text.lower()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "testforge" in result.stdout


def test_config_check_ok(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "llm_provider: openai\n"
        "llm_api_key: sk-test\n"
        "default_model: gpt-4o-mini\n"
        "log_level: INFO\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["config", "check", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "Configuration is valid" in result.stdout
    assert "llm_provider" in result.stdout
    assert "openai" in result.stdout


def test_config_check_warns_empty_api_key(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "llm_provider: openai\n"
        "llm_api_key: ''\n"
        "default_model: gpt-4o-mini\n"
        "log_level: INFO\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["config", "check", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "llm_api_key is empty" in (result.stdout + result.stderr)


def test_config_check_invalid_log_level(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "llm_provider: openai\n"
        "llm_api_key: x\n"
        "default_model: gpt-4o-mini\n"
        "log_level: BOGUS\n",
        encoding="utf-8",
    )
    code = _exit_code_main("config", "check", "--config", str(cfg))
    assert code == 3


def test_config_check_missing_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    code = _exit_code_main("config", "check")
    assert code == 3


def test_diff_rejects_non_git_directory(tmp_path: Path) -> None:
    plain = tmp_path / "not_a_repo"
    plain.mkdir()
    code = _exit_code_main(
        "diff",
        "--base",
        "main",
        "--feature",
        "feature",
        "--path",
        str(plain),
    )
    assert code == 2


def test_diff_and_validate_git_repo(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    _git_init_with_commit(tmp_path)
    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    diff_result = runner.invoke(
        app,
        ["diff", "--base", "main", "--feature", "feature", "--path", str(tmp_path)],
    )
    assert diff_result.exit_code == 0
    assert "Analyzing diff" in caplog.text
    val = runner.invoke(
        app,
        ["validate", "--base", "main", "--feature", "feature", "--path", str(tmp_path)],
    )
    assert val.exit_code == 0
    assert "Validating regressions" in caplog.text
