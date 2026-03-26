"""Router.yaml 管理函数。"""

from pathlib import Path
from typing import Dict, Any, Optional

from . import common


# ==================== 文件操作 ====================

def load_router(router_path: Path) -> Dict[str, Any]:
    """加载 router.yaml 文件。

    Args:
        router_path: router.yaml 文件路径

    Returns:
        Router 数据，格式：{"mappings": {report_type: template_name}}
    """
    data = common.load_yaml(router_path)
    if not data:
        return {"mappings": {}}

    # 确保 mappings 字段存在且是字典
    if "mappings" not in data or data["mappings"] is None:
        data["mappings"] = {}

    return data


def save_router(router_path: Path, data: Dict[str, Any]) -> None:
    """保存 router.yaml 文件。

    Args:
        router_path: router.yaml 文件路径
        data: Router 数据
    """
    common.save_yaml(router_path, data)


# ==================== 查询（纯函数）====================

def get_router_mapping(data: Dict[str, Any], report_type: str) -> Optional[str]:
    """获取报告类型对应的模板名称。

    Args:
        data: Router 数据
        report_type: 报告类型

    Returns:
        模板名称，未找到返回 None
    """
    return data.get("mappings", {}).get(report_type)


def get_all_router_mappings(data: Dict[str, Any]) -> Dict[str, str]:
    """获取所有报告类型映射。

    Args:
        data: Router 数据

    Returns:
        {report_type: template_name} 字典
    """
    return data.get("mappings", {})


# ==================== 修改（纯函数）====================

def update_mapping(data: Dict[str, Any], report_type: str, template_name: str) -> Dict[str, Any]:
    """添加或更新报告类型映射（返回新数据）。

    Args:
        data: 原 Router 数据
        report_type: 报告类型
        template_name: 模板名称

    Returns:
        新的 Router 数据
    """
    new_data = data.copy()
    if "mappings" not in new_data:
        new_data["mappings"] = {}
    new_data["mappings"] = new_data["mappings"].copy()
    new_data["mappings"][report_type] = template_name
    return new_data


def remove_mapping(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """删除报告类型映射（返回新数据）。

    Args:
        data: 原 Router 数据
        report_type: 报告类型

    Returns:
        新的 Router 数据
    """
    new_data = data.copy()
    if "mappings" in new_data:
        new_data["mappings"] = new_data["mappings"].copy()
        if report_type in new_data["mappings"]:
            del new_data["mappings"][report_type]
    return new_data
