"""CLI-инструмент визуализации графа зависимостей Cargo."""

import sys
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Callable

MAX_DEPTH_DEFAULT = 5


@dataclass
class Config:
    """Параметры, загружаемые из XML."""

    package_name: str = ""
    repo_url: str = ""
    test_mode: bool = False
    test_file_path: str = ""
    package_version: str = ""
    ascii_tree: bool = False
    max_depth: int = MAX_DEPTH_DEFAULT
    filter_substring: str = ""


def load_config(path: str) -> Config:
    """Загружает конфигурацию из XML-файла."""
    try:
        tree = ET.parse(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    root = tree.getroot()
    cfg = Config()

    cfg.package_name = _get_text(root, "package_name")
    cfg.repo_url = _get_text(root, "repo_url")
    cfg.test_mode = _get_bool(root, "test_mode", False)
    cfg.test_file_path = _get_text(root, "test_file_path", "")
    cfg.package_version = _get_text(root, "package_version", "")
    cfg.ascii_tree = _get_bool(root, "ascii_tree", False)
    cfg.max_depth = _get_int(root, "max_depth", MAX_DEPTH_DEFAULT)
    cfg.filter_substring = _get_text(root, "filter_substring", "")

    if not cfg.package_name:
        raise ValueError("package_name is required")

    return cfg


def _get_text(parent, tag: str, default: Optional[str] = None) -> str:
    """Извлекает текст дочернего элемента."""
    node = parent.find(tag)
    if node is None or node.text is None:
        if default is not None:
            return default
        raise ValueError(f"Missing required tag: {tag}")
    return node.text.strip()


def _get_bool(parent, tag: str, default: bool = False) -> bool:
    """Извлекает булево значение из тега."""
    node = parent.find(tag)
    if node is None or node.text is None:
        return default
    return node.text.strip().lower() in ("true", "1", "yes")


def _get_int(parent, tag: str, default: int) -> int:
    """Извлекает целое число из тега."""
    node = parent.find(tag)
    if node is None or node.text is None:
        return default
    try:
        return int(node.text.strip())
    except ValueError as exc:
        raise ValueError(f"Tag {tag} must be an integer") from exc


def print_config(cfg: Config) -> None:
    """Выводит параметры конфигурации."""
    print(f"package_name = {cfg.package_name}")
    print(f"repo_url = {cfg.repo_url}")
    print(f"test_mode = {cfg.test_mode}")
    print(f"test_file_path = {cfg.test_file_path}")
    print(f"package_version = {cfg.package_version}")
    print(f"ascii_tree = {cfg.ascii_tree}")
    print(f"max_depth = {cfg.max_depth}")
    print(f"filter_substring = {cfg.filter_substring}")


def fetch_dependencies_api(package: str, version: str = "") -> list[str]:
    """Извлекает прямые зависимости пакета с crates.io."""
    if version:
        url = (
            f"https://crates.io/api/v1/crates/"
            f"{package}/{version}/dependencies"
        )
    else:
        url = f"https://crates.io/api/v1/crates/{package}/dependencies"

    req = urllib.request.Request(
        url, headers={"User-Agent": "CargoDepVisualizer/1.0"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"Ошибка сети для {package}: {exc}", file=sys.stderr)
        return []

    deps = set()
    for item in data.get("dependencies", []):
        crate_id = item.get("crate_id")
        if crate_id:
            deps.add(crate_id)
    return list(deps)


def load_test_graph(filepath: str) -> dict[str, list[str]]:
    """Загружает граф из тестового файла формата 'A: B, C'."""
    graph = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    node, deps_str = line.split(":", 1)
                    node = node.strip()
                    deps = [d.strip() for d in deps_str.split(",")]
                    graph[node] = [d for d in deps if d]
    except FileNotFoundError:
        print(f"Файл {filepath} не найден", file=sys.stderr)
    return graph


def bfs_recursive(
    current_level: list[str],
    fetcher: Callable[[str], list[str]],
    max_depth: int,
    current_depth: int = 0,
    visited: Optional[set] = None,
    graph: Optional[dict] = None,
) -> dict[str, list[str]]:
    """Строит граф зависимостей рекурсивным BFS."""
    if visited is None:
        visited = set()
    if graph is None:
        graph = {}

    if current_depth > max_depth or not current_level:
        return graph

    next_level = []
    for node in current_level:
        if node in visited:
            continue
        visited.add(node)

        deps = fetcher(node)
        graph[node] = deps

        for dep in deps:
            if dep not in visited:
                next_level.append(dep)

    return bfs_recursive(
        next_level, fetcher, max_depth, current_depth + 1, visited, graph
    )


def main() -> int:
    """Точка входа приложения."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <config.xml>")
        return 1

    try:
        cfg = load_config(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_config(cfg)
    print("\nПостроение графа...")

    if cfg.test_mode:
        test_graph = load_test_graph(cfg.test_file_path)

        def fetcher(node: str) -> list[str]:
            return test_graph.get(node, [])
    else:
        def fetcher(node: str) -> list[str]:
            v = cfg.package_version if node == cfg.package_name else ""
            return fetch_dependencies_api(node, v)

    def filtered_fetcher(node: str) -> list[str]:
        deps = fetcher(node)
        if cfg.filter_substring:
            return [d for d in deps if cfg.filter_substring not in d]
        return deps

    graph = bfs_recursive(
        current_level=[cfg.package_name],
        fetcher=filtered_fetcher,
        max_depth=cfg.max_depth,
    )

    print("\nРезультат (Граф зависимостей):")
    for node, deps in graph.items():
        if deps:
            print(f"{node} -> {', '.join(deps)}")
        else:
            print(f"{node} -> (нет зависимостей)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
