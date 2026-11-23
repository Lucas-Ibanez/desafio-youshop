"""Cache em disco das respostas do modelo (CONTEXTO 5, princípio 6: reprodutível).

Chave = sha256(modelo + versão do prompt + entrada renderizada). Um arquivo JSON por chave.
"""

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(model: str, prompt_version: str, rendered: str) -> str:
    payload = json.dumps(
        {"model": model, "prompt": prompt_version, "input": rendered}, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DiskCache:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def set(self, key: str, value: dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=1)
        tmp.replace(path)
