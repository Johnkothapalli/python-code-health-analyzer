"""Internal import graph construction and cycle detection."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path


def _module_name(root: Path, path: Path) -> str:
    source_root = root / "src"
    base = source_root if source_root.is_dir() and path.is_relative_to(source_root) else root
    relative = path.relative_to(base).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _best_match(candidate: str, modules: set[str]) -> str | None:
    current = candidate
    while current:
        if current in modules:
            return current
        current = current.rpartition(".")[0]
    return None


def _from_module(current: str, node: ast.ImportFrom, *, is_package: bool) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = current.split(".")
    if not is_package:
        package_parts.pop()
    remove = max(0, node.level - 1)
    if remove:
        package_parts = package_parts[:-remove]
    if node.module:
        package_parts.extend(node.module.split("."))
    return ".".join(package_parts)


def _dependencies(path: Path, current: str, modules: set[str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return set()

    dependencies: set[str] = set()
    for node in ast.walk(tree):
        candidates: list[str] = []
        if isinstance(node, ast.Import):
            candidates.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _from_module(current, node, is_package=path.name == "__init__.py")
            candidates.extend(f"{base}.{alias.name}" for alias in node.names)
            candidates.append(base)
        dependencies.update(
            match
            for candidate in candidates
            if (match := _best_match(candidate.strip("."), modules)) is not None
            and match != current
        )
    return dependencies


class ImportGraph:
    """Directed module graph with deterministic strongly connected components."""

    def __init__(self, edges: dict[str, set[str]]) -> None:
        self.edges = {module: set(dependencies) for module, dependencies in edges.items()}

    @classmethod
    def build(cls, root: Path, files: Iterable[Path]) -> ImportGraph:
        paths = tuple(files)
        names = {path: _module_name(root, path) for path in paths}
        modules = {name for name in names.values() if name}
        edges: dict[str, set[str]] = {name: set() for name in modules}

        for path, current in names.items():
            if not current:
                continue
            edges[current] = _dependencies(path, current, modules)
        return cls(edges)

    def cycles(self) -> tuple[tuple[str, ...], ...]:
        """Return cycles as strongly connected components using Tarjan's algorithm."""

        index = 0
        indices: dict[str, int] = {}
        low_links: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[tuple[str, ...]] = []

        def connect(module: str) -> None:
            nonlocal index
            indices[module] = index
            low_links[module] = index
            index += 1
            stack.append(module)
            on_stack.add(module)

            for dependency in sorted(self.edges.get(module, ())):
                if dependency not in indices:
                    connect(dependency)
                    low_links[module] = min(low_links[module], low_links[dependency])
                elif dependency in on_stack:
                    low_links[module] = min(low_links[module], indices[dependency])

            if low_links[module] != indices[module]:
                return
            component: list[str] = []
            while stack:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == module:
                    break
            if len(component) > 1:
                components.append(tuple(sorted(component)))

        for module in sorted(self.edges):
            if module not in indices:
                connect(module)
        return tuple(sorted(components))
