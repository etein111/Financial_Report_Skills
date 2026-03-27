"""Schema 操作函数。

扁平化 schema 结构：
- 普通字段（无 type）：从样本文档提取的字段值，用于填充模板
- Word 片段（type: fragment）：从原始文档摘取的 Word 片段文件
  - abstract: 报告摘要片段
  - body: 报告正文片段
"""

from typing import Dict, Any, Optional

import common


# 片段默认值
DEFAULT_ABSTRACT = {
    "type": "fragment",
    "description": "报告摘要部分",
    "scope": "首页右侧（长的话可能到第二页）",
    "hints": [
        "通常包含投资亮点、核心观点",
        "长度约 200-500 字",
        "不应包含表格和图表",
        "位于首页右侧区域",
    ],
}

DEFAULT_BODY = {
    "type": "fragment",
    "description": "报告正文部分",
    "scope": "从首页之后到报告结尾",
    "hints": [
        "包含各章节详细内容",
        "可能包含表格、图表引用",
        "按原文结构保留段落和标题层级",
    ],
}


# ==================== 生成 ====================

def generate_schema(elements: Dict[str, Any],
                   abstract_config: Optional[Dict[str, Any]] = None,
                   body_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """从 elements.yaml 生成扁平化的 schema 字典。

    Args:
        elements: elements.yaml 的内容
        abstract_config: abstract 配置（可选），覆盖默认值
        body_config: body 配置（可选），{"enabled": false} 可禁用

    Returns:
        schema 字典
    """
    schema = {}

    # 普通字段（扁平化结构，支持 a1_* 到 a8_* 等多个分析师）
    for name, value in elements.items():
        schema[name] = {"description": name}
        if value and value != "null":
            schema[name]["format"] = str(value)

    # abstract（可选，默认启用）
    if abstract_config is None or abstract_config.get("enabled", True):
        schema["abstract"] = _apply_fragment_config(DEFAULT_ABSTRACT, abstract_config)

    # body（可选，默认启用）
    if body_config is None or body_config.get("enabled", True):
        schema["body"] = _apply_fragment_config(DEFAULT_BODY, body_config)

    return schema


# ==================== 文件操作 ====================

def load_schema(path: str) -> Dict[str, Any]:
    """从文件加载 schema。

    Args:
        path: schema.yaml 文件路径

    Returns:
        schema 字典
    """
    return common.load_yaml(path)


def save_schema(path: str, schema: Dict[str, Any]) -> None:
    """保存 schema 到文件。

    Args:
        path: schema.yaml 文件路径
        schema: schema 字典
    """
    common.save_yaml(path, schema)


# ==================== 修改（纯函数）====================

def update_field(schema: Dict[str, Any],
                name: str,
                description: str,
                format: str = None) -> Dict[str, Any]:
    """更新或添加字段（返回新 schema）。

    Args:
        schema: 原 schema 字典
        name: 字段名
        description: 字段描述
        format: 格式示例（可选）

    Returns:
        新的 schema 字典
    """
    new_schema = schema.copy()
    field_def = {"description": description}
    if format:
        field_def["format"] = format
    new_schema[name] = field_def
    return new_schema


def update_fragment(schema: Dict[str, Any],
                   name: str,
                   scope: str = None,
                   hints: list = None) -> Dict[str, Any]:
    """更新片段配置（返回新 schema）。

    Args:
        schema: 原 schema 字典
        name: 片段名（"abstract" 或 "body"）
        scope: 位置描述（可选）
        hints: 提示信息列表（可选）

    Returns:
        新的 schema 字典
    """
    default = DEFAULT_ABSTRACT if name == "abstract" else DEFAULT_BODY
    config = {}
    if scope:
        config["scope"] = scope
    if hints is not None:
        config["hints"] = hints

    new_schema = schema.copy()
    new_schema[name] = _apply_fragment_config(default, config if config else None)
    return new_schema


# ==================== 辅助函数 ====================

def _apply_fragment_config(default: Dict[str, Any],
                          config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """应用用户配置到默认片段。

    Args:
        default: 默认片段配置
        config: 用户配置

    Returns:
        合并后的片段配置
    """
    fragment = default.copy()
    if config:
        if config.get("scope"):
            fragment["scope"] = config["scope"]
        if config.get("hints") is not None:
            fragment["hints"] = config["hints"]
    return fragment
