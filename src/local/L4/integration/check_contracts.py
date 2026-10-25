"""Проверка стыков между TypeScript- и Python-компонентами (конъюнкция сигнатур).

1. Поля интерфейсов contracts/ts/contracts.ts совпадают с полями моделей fitagg_contracts.
2. Значения строковых типов (Direction, MarkMethod) совпадают.
3. Сообщения, которые реально собирают adm_access_controller и gw_ratelimit, проходят
   валидацию Python-моделей (если доступны node и esbuild).

Запуск из папки lab3: python integration/check_contracts.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contracts" / "python"))

from pydantic import BaseModel  # noqa: E402

import fitagg_contracts as fc  # noqa: E402

TS_FILE = ROOT / "contracts" / "ts" / "contracts.ts"
MODELS: dict[str, type[BaseModel]] = {
    "AdminAccessMarkRequest": fc.AdminAccessMarkRequest,
    "AccessMarkResult": fc.AccessMarkResult,
    "RateLimitedError": fc.RateLimitedError,
}
ENUMS: dict[str, list[str]] = {
    "Direction": [d.value for d in fc.Direction],
    "MarkMethod": [m.value for m in fc.MarkMethod],
}


def ts_interfaces(source: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for name, body in re.findall(r"export interface (\w+) \{(.*?)\n\}", source, re.S):
        result[name] = set(re.findall(r"readonly (\w+)\??:", body))
    return result


def ts_unions(source: str) -> dict[str, list[str]]:
    return {
        name: re.findall(r'"([^"]+)"', body)
        for name, body in re.findall(r"export type (\w+) = ([^;]+);", source)
    }


def check_shapes() -> list[str]:
    source = TS_FILE.read_text(encoding="utf-8")
    problems: list[str] = []
    interfaces = ts_interfaces(source)
    for name, model in MODELS.items():
        ts_fields = interfaces.get(name)
        py_fields = set(model.model_fields)
        if ts_fields is None:
            problems.append(f"{name}: нет в contracts.ts")
        elif ts_fields != py_fields:
            problems.append(f"{name}: TS {sorted(ts_fields ^ py_fields)} расходятся с Python")
    unions = ts_unions(source)
    for name, values in ENUMS.items():
        if sorted(unions.get(name, [])) != sorted(values):
            problems.append(f"{name}: TS {unions.get(name)} != Python {values}")
    return problems


def run_samples() -> dict[str, list[dict[str, Any]]] | None:
    esbuild = shutil.which("esbuild")
    node = shutil.which("node")
    if esbuild is None or node is None:
        print("node/esbuild не найдены — проверка живых образцов пропущена")
        return None
    out = ROOT / "integration" / "build" / "contract_samples.js"
    subprocess.run(
        [esbuild, str(ROOT / "integration" / "contract_samples.ts"), "--bundle", "--platform=node",
         "--format=esm", f"--outfile={out}", "--log-level=warning"],
        check=True,
    )
    completed = subprocess.run([node, str(out)], check=True, capture_output=True, text=True)
    samples: dict[str, list[dict[str, Any]]] = json.loads(completed.stdout)
    return samples


def check_samples(samples: dict[str, list[dict[str, Any]]]) -> list[str]:
    problems: list[str] = []
    for name, items in samples.items():
        for item in items:
            try:
                MODELS[name].model_validate(item)
            except Exception as error:  # noqa: BLE001 — нужен текст любой ошибки валидации
                problems.append(f"{name}: образец {item} не прошёл валидацию: {error}")
    return problems


def main() -> int:
    problems = check_shapes()
    samples = run_samples()
    checked = 0
    if samples is not None:
        problems += check_samples(samples)
        checked = sum(len(v) for v in samples.values())
    for problem in problems:
        print("ОШИБКА:", problem)
    print(f"Контрактов: {len(MODELS)}, перечислений: {len(ENUMS)}, живых образцов: {checked}; расхождений: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
