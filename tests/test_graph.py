from pathlib import Path

from code_health.graph import ImportGraph


def test_tarjan_finds_import_cycle(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text("import beta\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("import gamma\n", encoding="utf-8")
    (tmp_path / "gamma.py").write_text("import alpha\n", encoding="utf-8")
    files = tuple(tmp_path.glob("*.py"))

    graph = ImportGraph.build(tmp_path, files)

    assert graph.cycles() == (("alpha", "beta", "gamma"),)


def test_acyclic_graph_has_no_cycles(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text("import beta\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("answer = 42\n", encoding="utf-8")

    graph = ImportGraph.build(tmp_path, tmp_path.glob("*.py"))

    assert graph.cycles() == ()


def test_relative_import_cycle_in_package(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from . import b\n", encoding="utf-8")
    (pkg / "b.py").write_text("from . import a\n", encoding="utf-8")

    graph = ImportGraph.build(tmp_path, tmp_path.rglob("*.py"))

    cycles = graph.cycles()
    assert len(cycles) == 1
    cycle = cycles[0]
    assert "mypkg.a" in cycle
    assert "mypkg.b" in cycle


def test_acyclic_package_with_relative_imports(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from . import b\n", encoding="utf-8")
    (pkg / "b.py").write_text("x = 1\n", encoding="utf-8")

    graph = ImportGraph.build(tmp_path, tmp_path.rglob("*.py"))

    assert graph.cycles() == ()
