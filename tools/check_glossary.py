#!/usr/bin/env python3
"""Проверка идентификаторов диаграмм по глоссарию README (шаг CI render-docs).

Что проверяет:
1. Во всех .puml (кроме src/integrations) каждая связь Rel(...) ссылается на объявленный
   в этом же файле элемент или узел. Опечатка в ID иначе превращается в «пустой» прямоугольник
   на картинке, а синтаксическая проверка PlantUML её не ловит.
2. В сводных диаграммах (src/main_*.puml, src/dynamic_process.puml) и в диаграммах ЛР4
   участников (L0_*, dynamic_*, deployment_*) каждый элемент назван глобальным ID из README:
   таблицы с первым столбцом «ID» и столбец «Глобальный ID» таблицы компонентов.
   На диаграммах развёртывания второй экземпляр контейнера допускается с суффиксом
   (<глобальный ID>_<суффикс>, например database_replica). Узлы Deployment_Node и границы
   именуются свободно.

Выход: 0 — замечаний нет, 1 — есть замечания (сборка падает с красным крестом).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
README = ROOT / "README.md"

ELEMENT_MACROS = (
    "Person", "Person_Ext", "System", "System_Ext", "SystemDb", "SystemDb_Ext", "SystemQueue", "SystemQueue_Ext",
    "Container", "Container_Ext", "ContainerDb", "ContainerDb_Ext", "ContainerQueue", "ContainerQueue_Ext",
    "Component", "Component_Ext", "ComponentDb", "ComponentDb_Ext", "ComponentQueue", "ComponentQueue_Ext",
)
BOUNDARY_MACROS = (
    "Enterprise_Boundary", "System_Boundary", "Container_Boundary", "Boundary",
    "Deployment_Node", "Deployment_Node_L", "Deployment_Node_R", "Node", "Node_L", "Node_R",
)
ELEMENT_RE = re.compile(r"^\s*(" + "|".join(ELEMENT_MACROS) + r")\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,")
BOUNDARY_RE = re.compile(r"^\s*(" + "|".join(BOUNDARY_MACROS) + r")\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,")
REL_RE = re.compile(r"^\s*(?:Rel|BiRel|RelIndex)\(\s*(?:[0-9]+\s*,\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*,")
CODE_RE = re.compile(r"`([a-z][a-z0-9_]*)`")
GLOBAL_FILES = re.compile(r"^(main_[a-z_]+|dynamic_process|L0_[a-z_]+|dynamic_[a-z_]+|deployment_[a-z_]+)\.puml$")


def load_glossary() -> set[str]:
    ids: set[str] = set()
    header: list[str] | None = None
    for line in README.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        for i, name in enumerate(header):
            if i < len(cells) and (name == "ID" and i == 0 or name == "Глобальный ID"):
                ids.update(CODE_RE.findall(cells[i]))
    return ids


def check_file(path: Path, glossary: set[str]) -> list[str]:
    problems: list[str] = []
    rel = path.relative_to(ROOT)
    elements: dict[str, int] = {}
    boundaries: set[str] = set()
    rels: list[tuple[int, str, str]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith("'"):
            continue
        if m := ELEMENT_RE.match(line):
            elements[m.group(2)] = n
        elif m := BOUNDARY_RE.match(line):
            boundaries.add(m.group(2))
        elif m := REL_RE.match(line):
            rels.append((n, m.group(1), m.group(2)))
    known = set(elements) | boundaries
    for n, a, b in rels:
        for alias in (a, b):
            if alias not in known:
                problems.append(f"{rel}:{n}: связь ссылается на необъявленный ID «{alias}»")
    if GLOBAL_FILES.match(path.name):
        deployment = path.name.startswith(("deployment_", "main_deployment"))
        for alias, n in elements.items():
            if alias in glossary:
                continue
            base = alias.rsplit("_", 1)[0]
            if deployment and base in glossary:
                continue
            problems.append(f"{rel}:{n}: ID «{alias}» нет в глоссарии README")
    return problems


def main() -> int:
    glossary = load_glossary()
    if not glossary:
        print("::error::Не удалось прочитать глоссарий из README.md")
        return 1
    files = sorted(p for p in SRC.rglob("*.puml") if "integrations" not in p.parts and "core" not in p.parts)
    problems: list[str] = []
    for path in files:
        problems += check_file(path, glossary)
    print(f"Глоссарий: {len(glossary)} ID; проверено файлов: {len(files)}")
    for p in problems:
        file_line = p.split(": ", 1)[0]
        print(f"::error file={file_line.rsplit(':', 1)[0]},line={file_line.rsplit(':', 1)[1]}::{p.split(': ', 1)[1]}")
    if problems:
        print(f"Замечаний: {len(problems)}")
        return 1
    print("Все идентификаторы соответствуют глоссарию")
    return 0


if __name__ == "__main__":
    sys.exit(main())
