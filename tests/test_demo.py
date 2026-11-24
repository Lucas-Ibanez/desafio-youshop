"""Demo de ponta a ponta pelo MCP (T15). Precisa do modelo: roda com `tasks.py test-llm`."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from promessa.config import get_settings, has_api_key

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.llm


def test_demo_conclui_em_menos_de_60_segundos():
    settings = get_settings()
    if not (has_api_key(settings) or settings.llm_offline):
        pytest.skip("sem GEMINI_API_KEY e sem LLM_OFFLINE")
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "scripts/demo_e2e.py"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        timeout=120,
    )
    elapsed = time.perf_counter() - start
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "Demo concluída" in proc.stdout and "❌" not in proc.stdout
    assert "10 ferramentas" in proc.stdout
    assert elapsed < 60
