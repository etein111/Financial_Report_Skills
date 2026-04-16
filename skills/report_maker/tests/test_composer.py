"""test_composer.py - composer.py 模块测试。

测试文档合并功能。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestInsertBodyAtMarkerCompose:
    """测试 insert_body_at_marker_compose 函数。"""

    def test_returns_false_when_docxcompose_unavailable(self):
        """测试：docxcompose 不可用时返回 False。"""
        from composer import insert_body_at_marker_compose

        with patch('composer.DOCXCOMPOSE_AVAILABLE', False):
            result = insert_body_at_marker_compose(
                "doc.docx",
                "body.docx",
                "{{BODY}}",
                "output.docx"
            )

            assert result is False

    def test_returns_false_when_marker_not_found(self, tmp_path):
        """测试：找不到 marker 时返回 False。"""
        from composer import insert_body_at_marker_compose

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        with patch('composer.DOCXCOMPOSE_AVAILABLE', True):
            with patch('composer.Document') as mock_doc:
                mock_instance = MagicMock()
                mock_instance.element.body = MagicMock()
                mock_instance.element.body.__iter__ = MagicMock(return_value=iter([]))
                mock_doc.return_value = mock_instance

                result = insert_body_at_marker_compose(
                    str(tmp_path / "doc.docx"),
                    str(tmp_path / "body.docx"),
                    "{{BODY}}",
                    str(tmp_path / "output.docx")
                )

                assert result is False


class TestComposerModuleAvailability:
    """测试 composer 模块可用性标志。"""

    def test_docxcompose_available_flag_exists(self):
        """测试：DOCXCOMPOSE_AVAILABLE 标志存在。"""
        from composer import DOCXCOMPOSE_AVAILABLE

        assert isinstance(DOCXCOMPOSE_AVAILABLE, bool)

    def test_insert_body_at_marker_compose_exists(self):
        """测试：insert_body_at_marker_compose 函数存在。"""
        from composer import insert_body_at_marker_compose

        assert callable(insert_body_at_marker_compose)
