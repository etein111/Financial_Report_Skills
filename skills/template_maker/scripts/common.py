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
    """展平所有 elements 字段，包括嵌套结构。

    支持以下嵌套结构：
    - 嵌套字典: sections.viewpoint -> sections_viewpoint
    - 单个元素列表: analysts[0].chinese_name -> analyst_chinese_name
    - 多个元素列表: analysts[0..n] -> analyst_0_chinese_name, analyst_1_chinese_name...

    注意：
    - 跳过超过 2 层嵌套的复杂结构（如 financial_data.rows.xxx.values）
    - 跳过空值和 "null" 字符串

    Args:
        elements: 原始 elements 字典

    Returns:
        展平后的 field_name -> field_value 映射
    """
    flat = {}

    def _is_simple_value(v: Any) -> bool:
        """判断是否为简单值（字符串、数字等，非容器类型）。"""
        return not isinstance(v, (dict, list))

    def _flatten_dict(prefix: str, d: Dict[str, Any], depth: int = 0) -> None:
        """展平字典，限制嵌套深度。"""
        if depth > 2:
            # 超过 2 层嵌套，整体作为字符串（如 financial_data）
            return

        for k, v in d.items():
            new_key = f"{prefix}_{k}" if prefix else k

            if v is None or v == "null":
                continue
            elif _is_simple_value(v):
                flat[new_key] = str(v)
            elif isinstance(v, dict):
                _flatten_dict(new_key, v, depth + 1)
            elif isinstance(v, list):
                _flatten_list(new_key, v, depth + 1)

    def _flatten_list(prefix: str, lst: List[Any], depth: int = 0) -> None:
        """展平列表。"""
        if not lst or depth > 2:
            return

        # 检查列表元素类型
        first = lst[0]

        if _is_simple_value(first):
            # 简单值列表，跳过（如 columns: [Dec-24A, Dec-25E, ...]）
            return

        if isinstance(first, dict):
            # 字典列表（如 analysts）
            # 单数形式前缀：analysts -> analyst
            singular = prefix.rstrip('s') if prefix.endswith('s') else prefix

            if len(lst) == 1:
                # 单个元素：直接展平，不带索引
                for k, v in first.items():
                    if v is None or v == "null":
                        continue
                    elif _is_simple_value(v):
                        flat[f"{singular}_{k}"] = str(v)
            else:
                # 多个元素：带索引展平
                for idx, item in enumerate(lst):
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v is None or v == "null":
                                continue
                            elif _is_simple_value(v):
                                flat[f"{singular}_{idx}_{k}"] = str(v)

    # 从顶层开始展平
    _flatten_dict("", elements, 0)

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
