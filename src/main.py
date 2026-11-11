"""CLI-инструмент визуализации графа зависимостей Cargo."""

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
