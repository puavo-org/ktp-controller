"""Generate a Graphviz DOT inter-module dependency graph for a Python project."""

import argparse
import ast
import enum
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}

_STDLIB_MODULES = sys.stdlib_module_names | set(sys.builtin_module_names)


class Category(enum.Enum):
    INTERNAL = "internal"
    THIRD_PARTY = "third_party"
    STDLIB = "stdlib"


_NODE_STYLE = {
    Category.INTERNAL: ('shape="box"', 'fillcolor="#AED6F1"'),
    Category.THIRD_PARTY: ('shape="ellipse"', 'fillcolor="#F5CBA7"'),
    Category.STDLIB: ('shape="diamond"', 'fillcolor="#D5D8DC"'),
}

_EDGE_STYLE = {
    Category.INTERNAL: "solid",
    Category.THIRD_PARTY: "dotted",
    Category.STDLIB: "dashed",
}


@dataclass
class Graph:
    node_categories: dict[str, Category] = field(default_factory=dict)
    edges: set[tuple[str, str, Category]] = field(default_factory=set)


def discover_modules(root: Path) -> dict[str, Path]:
    """Map dotted module name -> file path for every .py file under root."""
    modules: dict[str, Path] = {}
    for path in sorted(root.rglob("*.py")):
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        modules[".".join(parts)] = path
    return modules


def resolve_import(
    module_name: str, level: int, importer_module: str, importer_is_package: bool
) -> str:
    """Resolve a (possibly relative) import to an absolute dotted module name."""
    if level == 0:
        return module_name
    importer_parts = importer_module.split(".")
    # __package__ is the importer's own dotted name if it's a package
    # (__init__.py), otherwise its parent package.
    package_parts = importer_parts if importer_is_package else importer_parts[:-1]
    strip = level - 1
    base_parts = package_parts[: max(0, len(package_parts) - strip)]
    if module_name:
        return ".".join([*base_parts, module_name])
    return ".".join(base_parts)


def classify_module(name: str, top_level_internal_packages: set[str]) -> Category:
    top_level = name.split(".")[0]
    if top_level in top_level_internal_packages:
        return Category.INTERNAL
    if top_level in _STDLIB_MODULES:
        return Category.STDLIB
    return Category.THIRD_PARTY


def _imports_in_file(path: Path, module_name: str, is_package: bool) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_import(
                node.module or "", node.level, module_name, is_package
            )
            if resolved:
                imports.append(resolved)
    return imports


def build_graph(
    root: Path,
    exclude: set[Category],
    exclude_regexes: list[re.Pattern[str]],
) -> Graph:
    modules = discover_modules(root)
    internal_modules = set(modules)
    top_level_packages = {name.split(".")[0] for name in internal_modules}

    graph = Graph()
    for module_name in internal_modules:
        graph.node_categories[module_name] = Category.INTERNAL

    for module_name, path in modules.items():
        is_package = path.name == "__init__.py"
        for imported in _imports_in_file(path, module_name, is_package):
            category = classify_module(imported, top_level_packages)
            if category in exclude:
                continue
            if any(p.search(imported) for p in exclude_regexes):
                continue
            target = (
                imported if category == Category.INTERNAL else imported.split(".")[0]
            )
            graph.node_categories.setdefault(target, category)
            graph.edges.add((module_name, target, category))

    return graph


def wrap_description(text: str) -> list[str]:
    """Wrap words into lines of 5-12 words (fewer only if text has <5 words total)."""
    words = text.split()
    n = len(words)
    if not words:
        return []
    if n <= 12:
        return [" ".join(words)]
    num_lines = -(-n // 12)  # ceil(n / 12)
    base, remainder = divmod(n, num_lines)
    lines = []
    i = 0
    for line_idx in range(num_lines):
        count = base + 1 if line_idx < remainder else base
        lines.append(" ".join(words[i : i + count]))
        i += count
    return lines


def _escape_dot_label_line(line: str) -> str:
    return line.replace("\\", "\\\\").replace('"', '\\"')


def render_dot(graph: Graph, description: str | None) -> str:
    lines = [
        "digraph dependencies {",
        '    rankdir="LR";',
        '    node [style="filled"];',
        "",
    ]

    lines.append("    subgraph cluster_legend {")
    lines.append('        label="Legend";')
    for category in Category:
        shape, fillcolor = _NODE_STYLE[category]
        lines.append(
            f'        "legend_{category.value}" [label="{category.value} module", '
            f"{shape}, {fillcolor}];"
        )
    lines.append("    }")
    lines.append("")

    if description and description.strip():
        label = "\\n".join(
            _escape_dot_label_line(line) for line in wrap_description(description)
        )
        lines.append("    subgraph cluster_description {")
        lines.append('        label="Description";')
        lines.append(
            f'        "description" [shape="box", style="solid", label="{label}"];'
        )
        lines.append("    }")
        lines.append("")

    for node, category in sorted(graph.node_categories.items()):
        shape, fillcolor = _NODE_STYLE[category]
        lines.append(f'    "{node}" [{shape}, {fillcolor}];')

    lines.append("")
    for source, target, category in sorted(graph.edges):
        style = _EDGE_STYLE[category]
        lines.append(f'    "{source}" -> "{target}" [style="{style}"];')

    lines.append("}")
    return "\n".join(lines) + "\n"


def _compile_regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as e:
        raise argparse.ArgumentTypeError(f"invalid regex {pattern!r}: {e}") from e


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(),
        help="Project directory to scan for Python modules (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("dependency_graph.dot"),
        help="Path to write the DOT file to (default: dependency_graph.dot)",
    )
    parser.add_argument(
        "--exclude-internal",
        action="store_true",
        help="Omit dependencies on internal (project-local) modules",
    )
    parser.add_argument(
        "--exclude-third-party",
        action="store_true",
        help="Omit dependencies on third-party modules",
    )
    parser.add_argument(
        "--exclude-stdlib",
        action="store_true",
        help="Omit dependencies on standard library modules",
    )
    parser.add_argument(
        "--exclude-regex",
        action="append",
        default=[],
        type=_compile_regex,
        metavar="REGEX",
        help="Exclude imports whose resolved module name matches REGEX "
        "(repeatable; an import is excluded if it matches any regex)",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="Short free-text note rendered as a separate framed text box "
        "on the graph (omit to render no box)",
    )
    args = parser.parse_args()

    exclude = set()
    if args.exclude_internal:
        exclude.add(Category.INTERNAL)
    if args.exclude_third_party:
        exclude.add(Category.THIRD_PARTY)
    if args.exclude_stdlib:
        exclude.add(Category.STDLIB)

    graph = build_graph(args.root, exclude, args.exclude_regex)
    args.output.write_text(render_dot(graph, args.description))
    print(f"Written {args.output}")


if __name__ == "__main__":
    main()
