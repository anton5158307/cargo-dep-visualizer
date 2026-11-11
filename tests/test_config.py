"""Тесты для загрузки конфигурации."""

import os
import tempfile
import unittest

from src.main import load_config


class TestConfig(unittest.TestCase):
    """Проверка загрузки XML-конфигурации."""

    def _write_xml(self, content: str) -> str:
        """Создаёт временный XML-файл."""
        fd, path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_load_valid_config(self) -> None:
        """Корректный XML загружается без ошибок."""
        xml = """<config>
<package_name>serde</package_name>
<repo_url>https://crates.io</repo_url>
<test_mode>false</test_mode>
<max_depth>3</max_depth>
</config>"""
        path = self._write_xml(xml)
        try:
            cfg = load_config(path)
            self.assertEqual(cfg.package_name, "serde")
            self.assertEqual(cfg.max_depth, 3)
        finally:
            os.unlink(path)

    def test_missing_package_name(self) -> None:
        """Отсутствие package_name вызывает ValueError."""
        xml = "<config><repo_url>x</repo_url></config>"
        path = self._write_xml(xml)
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
