"""测试 router_mgr.py。"""

import pytest
from pathlib import Path
import yaml
from skills.template_maker.scripts.router_mgr import RouterManager

@pytest.fixture
def temp_router(tmp_path):
    """创建临时 router.yaml。"""
    router_path = tmp_path / "router.yaml"
    router_path.write_text("""
mappings:
  company: common
  sector: common
""")
    return router_path

def test_router_manager_init(temp_router):
    """测试初始化。"""
    mgr = RouterManager(temp_router)
    assert mgr.data["mappings"]["company"] == "common"

def test_add_mapping(temp_router):
    """测试添加映射。"""
    mgr = RouterManager(temp_router)
    mgr.add_mapping("macro", "common")

    assert mgr.data["mappings"]["macro"] == "common"

    # 验证已保存
    content = temp_router.read_text()
    assert "macro: common" in content

def test_add_mapping_to_nonexistent_file(tmp_path):
    """测试添加映射到不存在的文件。"""
    router_path = tmp_path / "new_router.yaml"
    mgr = RouterManager(router_path)
    mgr.add_mapping("industry", "common")

    assert mgr.data["mappings"]["industry"] == "common"
    assert router_path.exists()

def test_update_existing_mapping(temp_router):
    """测试更新现有映射。"""
    mgr = RouterManager(temp_router)
    mgr.add_mapping("company", "custom")

    assert mgr.data["mappings"]["company"] == "custom"

    # 验证已保存
    content = temp_router.read_text()
    assert "company: custom" in content

def test_load_empty_file(tmp_path):
    """测试加载空文件。"""
    router_path = tmp_path / "empty.yaml"
    router_path.write_text("")

    mgr = RouterManager(router_path)
    assert mgr.data == {"mappings": {}}

def test_load_file_with_only_mappings(tmp_path):
    """测试加载只有 mappings 的文件。"""
    router_path = tmp_path / "minimal.yaml"
    router_path.write_text("mappings: {}")

    mgr = RouterManager(router_path)
    assert mgr.data == {"mappings": {}}
