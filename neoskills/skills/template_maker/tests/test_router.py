"""测试 router.py 模块的函数。"""
import pytest
import tempfile
import yaml
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from router import (
    load_router,
    save_router,
    get_router_mapping,
    get_all_router_mappings,
    update_mapping,
    remove_mapping
)


class TestLoadRouter:
    """测试 load_router 函数。"""

    def test_load_router_from_nonexistent_file(self):
        """测试：加载不存在的文件返回空 mappings。"""
        result = load_router(Path("/nonexistent/router.yaml"))

        assert result == {"mappings": {}}

    def test_load_router_from_valid_file(self):
        """测试：加载有效的 router.yaml 文件。"""
        content = """
mappings:
  macro: common
  company: company
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "router.yaml"
            router_path.write_text(content)

            result = load_router(router_path)

            assert result["mappings"]["macro"] == "common"
            assert result["mappings"]["company"] == "company"

    def test_load_router_from_empty_file(self):
        """测试：加载空文件返回空 mappings。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "router.yaml"
            router_path.write_text("")

            result = load_router(router_path)

            assert result == {"mappings": {}}

    def test_load_router_with_null_mappings(self):
        """测试：mappings 为 null 时返回空字典。"""
        content = "mappings: null"
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "router.yaml"
            router_path.write_text(content)

            result = load_router(router_path)

            assert result == {"mappings": {}}

    def test_load_router_without_mappings_key(self):
        """测试：文件中没有 mappings 键时创建空字典。"""
        content = "version: 1.0"
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "router.yaml"
            router_path.write_text(content)

            result = load_router(router_path)

            assert "mappings" in result
            assert result["mappings"] == {}


class TestSaveRouter:
    """测试 save_router 函数。"""

    def test_save_router_creates_directory(self):
        """测试：保存时自动创建目录。"""
        data = {"mappings": {"macro": "common"}}

        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "subdir" / "router.yaml"

            save_router(router_path, data)

            assert router_path.exists()
            assert router_path.parent.is_dir()

    def test_save_and_load_roundtrip(self):
        """测试：保存后加载能得到相同数据。"""
        original_data = {
            "mappings": {
                "macro": "common",
                "company": "company",
                "sector_flash": "sector_flash"
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "router.yaml"

            save_router(router_path, original_data)
            loaded_data = load_router(router_path)

            assert loaded_data == original_data

    def test_save_router_preserves_format(self):
        """测试：保存的文件格式正确。"""
        data = {"mappings": {"macro": "common"}}

        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / "router.yaml"
            save_router(router_path, data)

            # 验证 YAML 格式
            content = router_path.read_text()
            parsed = yaml.safe_load(content)

            assert parsed["mappings"]["macro"] == "common"


class TestGetRouterMapping:
    """测试 get_router_mapping 函数。"""

    def test_get_existing_mapping(self):
        """测试：获取存在的映射。"""
        data = {"mappings": {"macro": "common"}}

        result = get_router_mapping(data, "macro")

        assert result == "common"

    def test_get_nonexistent_mapping(self):
        """测试：获取不存在的映射返回 None。"""
        data = {"mappings": {"macro": "common"}}

        result = get_router_mapping(data, "company")

        assert result is None

    def test_get_mapping_with_empty_data(self):
        """测试：空 mappings 返回 None。"""
        data = {"mappings": {}}

        result = get_router_mapping(data, "macro")

        assert result is None


class TestGetAllRouterMappings:
    """测试 get_all_router_mappings 函数。"""

    def test_get_all_mappings(self):
        """测试：获取所有映射。"""
        data = {"mappings": {"macro": "common", "company": "company"}}

        result = get_all_router_mappings(data)

        assert result == {"macro": "common", "company": "company"}

    def test_get_all_mappings_with_empty_data(self):
        """测试：空 mappings 返回空字典。"""
        data = {"mappings": {}}

        result = get_all_router_mappings(data)

        assert result == {}

    def test_get_all_mappings_without_mappings_key(self):
        """测试：没有 mappings 键时返回空字典。"""
        data = {"version": "1.0"}

        result = get_all_router_mappings(data)

        assert result == {}


class TestUpdateMapping:
    """测试 update_mapping 函数。"""

    def test_update_adds_new_mapping(self):
        """测试：添加新映射。"""
        data = {"mappings": {"macro": "common"}}

        result = update_mapping(data, "company", "company")

        assert result["mappings"]["company"] == "company"
        assert result["mappings"]["macro"] == "common"

    def test_update_updates_existing_mapping(self):
        """测试：更新已有映射。"""
        data = {"mappings": {"macro": "common"}}

        result = update_mapping(data, "macro", "new_macro")

        assert result["mappings"]["macro"] == "new_macro"

    def test_update_creates_mappings_if_missing(self):
        """测试：mappings 不存在时创建。"""
        data = {"version": "1.0"}

        result = update_mapping(data, "macro", "common")

        assert "mappings" in result
        assert result["mappings"]["macro"] == "common"

    def test_update_returns_new_data(self):
        """测试：返回新数据，不修改原数据（不可变性）。"""
        data = {"mappings": {"macro": "common"}}

        result = update_mapping(data, "macro", "new_macro")

        # 原 data 不应被修改
        assert data["mappings"]["macro"] == "common"
        # 新 data 被修改
        assert result["mappings"]["macro"] == "new_macro"


class TestRemoveMapping:
    """测试 remove_mapping 函数。"""

    def test_remove_existing_mapping(self):
        """测试：删除存在的映射。"""
        data = {"mappings": {"macro": "common", "company": "company"}}

        result = remove_mapping(data, "macro")

        assert "macro" not in result["mappings"]
        assert result["mappings"]["company"] == "company"

    def test_remove_nonexistent_mapping(self):
        """测试：删除不存在的映射不报错。"""
        data = {"mappings": {"macro": "common"}}

        result = remove_mapping(data, "company")

        assert result["mappings"]["macro"] == "common"

    def test_remove_without_mappings_key(self):
        """测试：没有 mappings 键时不报错。"""
        data = {"version": "1.0"}

        result = remove_mapping(data, "macro")

        assert result == data

    def test_remove_returns_new_data(self):
        """测试：返回新数据，不修改原数据（不可变性）。"""
        data = {"mappings": {"macro": "common"}}

        result = remove_mapping(data, "macro")

        # 原 data 不应被修改
        assert "macro" in data["mappings"]
        # 新 data 被修改
        assert "macro" not in result["mappings"]
