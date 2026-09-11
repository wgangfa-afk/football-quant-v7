import ast
from pathlib import Path

ROOT = Path("src/football_quant")


def test_no_import_cycles_and_pure_domain() -> None:
    modules = {
        "football_quant." + ".".join(p.relative_to(ROOT).with_suffix("").parts): p
        for p in ROOT.rglob("*.py")
    }
    graph = {}
    for name, path in modules.items():
        nodes = ast.walk(ast.parse(path.read_text()))
        imports = {n.module for n in nodes if isinstance(n, ast.ImportFrom) and n.module}
        graph[name] = imports & modules.keys()
        if name == "football_quant.domain":
            assert not any(s.startswith(("football_quant.", "docx", "pathlib")) for s in imports)
        if name.startswith("football_quant.reporting"):
            assert not any(
                s.startswith(("football_quant.models", "football_quant.markets")) for s in imports
            )

    def visit(name: str, active: frozenset[str]) -> None:
        assert name not in active, f"cycle through {name}"
        for dependency in graph[name]:
            visit(dependency, active | {name})

    for name in modules:
        visit(name, frozenset())


def test_public_function_annotations_and_no_one_line_bodies() -> None:
    for path in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.returns is not None, (path, node.name)
                for argument in node.args.args:
                    if argument.arg not in ("self", "cls"):
                        assert argument.annotation is not None, (path, node.name, argument.arg)
                assert node.body[0].lineno > node.lineno, (path, node.name)
            if isinstance(node, ast.If):
                assert node.body[0].lineno > node.lineno, path
