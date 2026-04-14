import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolate_home_and_disable_llm(tmp_path_factory: pytest.TempPathFactory) -> None:
    """
    Ensure tests never make real LLM/network calls and never touch the user's
    real ~/.testforge cache/config.
    """
    home = tmp_path_factory.mktemp("home")
    os.environ["HOME"] = str(home)
    os.environ["TESTFORGE_DISABLE_LLM"] = "1"

