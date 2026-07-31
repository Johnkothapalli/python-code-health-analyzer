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
