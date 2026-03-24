"""Router.yaml 管理函数。"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_router(router_path: Path) -> Dict[str, Any]:
    """加载 router.yaml 文件。

    Args:
        router_path: router.yaml 文件路径

    Returns:
        Router 数据，格式：{"mappings": {report_type: template_name}}
    """
    if not router_path.exists():
        return {"mappings": {}}

    data = yaml.safe_load(router_path.read_text())
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
    router_path.parent.mkdir(parents=True, exist_ok=True)
    router_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))


def add_router_mapping(router_path: Path, report_type: str, template_name: str) -> None:
    """添加报告类型映射。

    Args:
        router_path: router.yaml 文件路径
        report_type: 报告类型（如：company, macro）
        template_name: 模板名称
    """
    data = load_router(router_path)
    data.setdefault("mappings", {})[report_type] = template_name
    save_router(router_path, data)


def remove_router_mapping(router_path: Path, report_type: str) -> None:
    """删除报告类型映射。

    Args:
        router_path: router.yaml 文件路径
        report_type: 报告类型
    """
    data = load_router(router_path)
    if "mappings" in data and report_type in data["mappings"]:
        del data["mappings"][report_type]
        save_router(router_path, data)


def get_router_mapping(router_path: Path, report_type: str) -> str | None:
    """获取报告类型对应的模板名称。

    Args:
        router_path: router.yaml 文件路径
        report_type: 报告类型

    Returns:
        模板名称，未找到返回 None
    """
    data = load_router(router_path)
    return data.get("mappings", {}).get(report_type)


def get_all_router_mappings(router_path: Path) -> Dict[str, str]:
    """获取所有报告类型映射。

    Args:
        router_path: router.yaml 文件路径

    Returns:
        {report_type: template_name} 字典
    """
    data = load_router(router_path)
    return data.get("mappings", {})
