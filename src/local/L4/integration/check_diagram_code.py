"""Проверка соответствия диаграммы кода (L4) и исходного кода компонента.

Для каждого класса, интерфейса и перечисления на диаграмме ищется объявление с тем же именем
в коде компонента или в общих контрактах, для каждого метода (`+имя(` / `-имя(`) — определение
с тем же именем. Классы со стереотипом <<module ...>> сверяются с именем файла модуля.

Запуск из папки lab3: python integration/check_diagram_code.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = [ROOT / "contracts" / "python", ROOT / "contracts" / "ts"]
EXTERNAL_TYPES = {"NginxHTTPRequest", "NgxSharedDict"}  # объявлены в src/types/njs.d.ts


@dataclass(frozen=True, slots=True)
class Component:
    name: str
    diagram: Path
    sources: list[Path]
    l3_id: str = ""


COMPONENTS = [
    Component("iot_occupancy_service", ROOT / "lisov/iot_occupancy_service/diagram/L4_iot_occupancy_service.puml",
              [ROOT / "lisov/iot_occupancy_service/src"], "occupancy_comp"),
    Component("core_tariff_service", ROOT / "kutenkov/core_tariff_service/diagram/L4_core_tariff_service.puml",
              [ROOT / "kutenkov/core_tariff_service/src"], "tariff_service"),
    Component("etl_dq_validator", ROOT / "erendzhenova/etl_dq_validator/diagram/L4_etl_dq_validator.puml",
              [ROOT / "erendzhenova/etl_dq_validator/src"], "dq_validator"),
    Component("gw_ratelimit", ROOT / "damakalshchikov/gw_ratelimit/diagram/L4_gw_ratelimit.puml",
              [ROOT / "damakalshchikov/gw_ratelimit/src"], "ratelimit_comp"),
    Component("adm_access_controller", ROOT / "osipov/adm_access_controller/diagram/L4_adm_access_controller.puml",
              [ROOT / "osipov/adm_access_controller/src"], "adm_access_controller"),
]

ELEMENT = re.compile(r"^\s*(?:abstract\s+class|class|interface|enum)\s+(\w+)(?:\s+<<([^>]*)>>)?", re.M)
METHOD = re.compile(r"^\s*[+\-#~](?:\{\w+\}\s*)?(\w+)\(", re.M)
STRATEGY_HINT = re.compile(r"Strategy|Policy|Rule|Algorithm", re.I)


def read_sources(paths: list[Path]) -> tuple[str, set[str]]:
    texts: list[str] = []
    modules: set[str] = set()
    for root in paths:
        for file in sorted(root.rglob("*")):
            if file.suffix in {".py", ".ts"}:
                texts.append(file.read_text(encoding="utf-8"))
                modules.add(file.stem)
    return "\n".join(texts), modules


def declared(name: str, code: str) -> bool:
    pattern = rf"\b(?:class|interface|type|enum)\s+{re.escape(name)}\b"
    return re.search(pattern, code) is not None


def method_defined(name: str, code: str) -> bool:
    patterns = [
        rf"\bdef\s+{re.escape(name)}\(",                 # Python
        rf"^\s*(?:export\s+)?(?:async\s+)?function\s+{re.escape(name)}\(",  # TS функция
        rf"^\s*(?:(?:public|private|protected|static|async|readonly)\s+)*{re.escape(name)}\??\(",  # TS метод
    ]
    return any(re.search(p, code, re.M) for p in patterns)


CODE_DECL = re.compile(r"^(?:export\s+)?(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)", re.M)


def code_declarations(paths: list[Path]) -> set[str]:
    """Классы, интерфейсы и перечисления из кода компонента (типы njs.d.ts не считаются)."""
    names: set[str] = set()
    for root in paths:
        for file in root.rglob("*"):
            if file.suffix in {".py", ".ts"} and not file.name.endswith(".d.ts"):
                names |= set(CODE_DECL.findall(file.read_text(encoding="utf-8")))
    return names


def check(component: Component, contracts_code: str) -> list[str]:
    diagram = component.diagram.read_text(encoding="utf-8")
    code, modules = read_sources(component.sources)
    everything = code + "\n" + contracts_code
    problems: list[str] = []
    elements = ELEMENT.findall(diagram)
    for name, stereotype in elements:
        if "module" in stereotype:
            if name not in modules:
                problems.append(f"модуль {name}: нет файла {name}.py/.ts")
        elif name not in EXTERNAL_TYPES and not declared(name, everything):
            problems.append(f"{name}: нет объявления в коде")
    for name in sorted(set(METHOD.findall(diagram))):
        if not method_defined(name, everything):
            problems.append(f"метод {name}(): нет определения в коде")
    on_diagram = {name for name, _ in elements}
    for name in sorted(code_declarations(component.sources) - on_diagram):
        problems.append(f"{name}: есть в коде, нет на диаграмме")
    title = re.search(r"^title (.+)$", diagram, re.M)
    if title is None or f"({component.name};" not in title.group(1):
        problems.append(f"в заголовке нет глобального ID «({component.name}; …»")
    if component.l3_id and component.l3_id != component.name and f"на L3 — {component.l3_id})" not in (title.group(1) if title else ""):
        problems.append(f"в заголовке нет локального ID L3 «на L3 — {component.l3_id}»")
    if "legend" not in diagram:
        problems.append("нет условных обозначений (legend) — пункт 2 контрольного перечня лекции 2")
    if not any(STRATEGY_HINT.search(n) for n, _ in elements):
        problems.append("на диаграмме не найден интерфейс стратегии")
    print(f"{component.name}: элементов {len(elements)}, методов {len(set(METHOD.findall(diagram)))}, расхождений {len(problems)}")
    return problems


def main() -> int:
    contracts_code, _ = read_sources(CONTRACTS)
    problems: list[str] = []
    for component in COMPONENTS:
        problems += [f"{component.name}: {p}" for p in check(component, contracts_code)]
    for problem in problems:
        print("ОШИБКА:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
