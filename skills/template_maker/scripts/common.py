"""template_maker 共享工具函数和常量。

此模块提供所有 template_maker 子模块共享的工具函数和常量定义。
遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

from pathlib import Path
from typing import Dict, Any, List, Union, Optional
import yaml


# ==================== 常量定义 ====================

# 字段名常量
FRAGMENT_TYPE_ABSTRACT = "abstract"
FRAGMENT_TYPE_BODY = "body"

# 占位符常量
PLACEHOLDER_ABSTRACT = "abstract"
PLACEHOLDER_BODY = "body"

# 默认范围常量
DEFAULT_ABSTRACT_SCOPE = "首页右侧"
DEFAULT_BODY_SCOPE = "首页之后到'附录APPENDIX'之前"

# 文本长度阈值
MIN_ABSTRACT_LENGTH = 50
MIN_CONTINUATION_LENGTH = 20

# 文件名常量
FILE_SCHEMA = "schema.yaml"
FILE_META = "meta.yaml"
FILE_ROUTER = "router.yaml"
FILE_TEMPLATE = "template.docx"
FILE_ELEMENTS = "elements.yaml"


# ==================== YAML 工具函数 ====================

def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """加载 YAML 文件。

    Args:
        path: YAML 文件路径

    Returns:
        解析后的字典，文件不存在时返回空字典
    """
    path = Path(path)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text())


def save_yaml(path: Union[str, Path], data: Dict[str, Any], sort_keys: bool = False) -> None:
    """保存数据到 YAML 文件。

    Args:
        path: YAML 文件路径
        data: 要保存的数据
        sort_keys: 是否排序键（默认 False）
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=sort_keys))


# ==================== Elements 工具函数 ====================

def flatten_elements(elements: Dict[str, Any]) -> Dict[str, str]:
    """展平所有 elements 字段。

    Args:
        elements: 原始 elements 字典

    Returns:
        展平后的 field_name -> field_value 映射
    """
    flat = {}
    for name, value in elements.items():
        if value is not None and value != "null":
            flat[name] = str(value)
    return flat


# ==================== 占位符工具函数 ====================

def format_placeholder(field_name: str) -> str:
    """格式化字段名为占位符。

    Args:
        field_name: 字段名（如 "company"）

    Returns:
        占位符字符串（如 "{{ company }}"）
    """
    return f"{{{{ {field_name} }}}}"


def format_abstract_placeholder() -> str:
    """获取摘要占位符。"""
    return format_placeholder(PLACEHOLDER_ABSTRACT)


def format_body_placeholder() -> str:
    """获取正文占位符。"""
    return format_placeholder(PLACEHOLDER_BODY)
