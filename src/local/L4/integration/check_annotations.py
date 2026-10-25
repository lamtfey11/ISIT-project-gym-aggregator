"""Проверка полноты аннотаций типов (требование ЛР3 «строгая аннотация типов»).

Дополняет mypy --strict: убеждается, что у каждой функции и метода аннотированы
все параметры (кроме self/cls) и возвращаемое значение, а атрибуты классов имеют тип.
Запуск: python integration/check_annotations.py <папка> [<папка> ...]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def check_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg:
                params.append(args.vararg)
            if args.kwarg:
                params.append(args.kwarg)
            for index, param in enumerate(params):
                if index == 0 and param.arg in {"self", "cls"}:
                    continue
                if param.annotation is None:
                    problems.append(f"{path}:{node.lineno} {node.name}(): параметр «{param.arg}» без типа")
            if node.returns is None:
                problems.append(f"{path}:{node.lineno} {node.name}(): нет типа возвращаемого значения")
        if isinstance(node, ast.ClassDef):
            is_enum = any(isinstance(base, ast.Name) and base.id.endswith("Enum") for base in node.bases)
            for item in node.body:
                if not isinstance(item, ast.Assign) or is_enum:
                    continue
                names = [t.id for t in item.targets if isinstance(t, ast.Name)]
                # model_config уже объявлен в pydantic.BaseModel как ClassVar[ConfigDict]
                if all(name in {"model_config", "__slots__"} for name in names):
                    continue
                problems.append(f"{path}:{item.lineno} {node.name}: атрибут класса без аннотации")
    return problems


def main(roots: list[str]) -> int:
    files = sorted(p for root in roots for p in ([Path(root)] if Path(root).is_file() else Path(root).rglob("*.py")))
    problems = [problem for path in files for problem in check_file(path)]
    for problem in problems:
        print(problem)
    print(f"Проверено файлов: {len(files)}; замечаний: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["."]))
