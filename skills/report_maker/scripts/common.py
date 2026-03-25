"""report_maker 共享工具函数和常量。

此模块提供所有 report_maker 子模块共享的工具函数和常量定义。
遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

from pathlib import Path
from typing import Dict, Any, List, Union, Optional
import yaml


# ==================== 常量定义 ====================

# 目录常量
DIR_REPORTS = "reports"
DIR_TEMPLATES = "templates"
DIR_ASSETS = "assets"

# 文件名常量
FILE_SCHEMA = "schema.yaml"
FILE_ROUTER = "router.yaml"
FILE_TEMPLATE = "template.docx"
FILE_ELEMENTS = "elements.yaml"
FILE_META = "meta.yaml"

# 报告文件名
FILE_DRAFT = "draft.docx"
FILE_ABSTRACT = "abstract.docx"
FILE_BODY = "body.docx"
FILE_OUTPUT_DOCX = "output.docx"
FILE_OUTPUT_PDF = "output.pdf"


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


# ==================== 路由工具函数 ====================

def get_template_name(report_type: str, router_path: Union[str, Path] = None) -> Optional[str]:
    """根据报告类型获取模板名。

    Args:
        report_type: 报告类型（如 "company", "sector"）
        router_path: router.yaml 文件路径，默认为 templates/router.yaml

    Returns:
        模板名，如果未找到则返回 None
    """
    if router_path is None:
        router_path = Path(DIR_TEMPLATES) / FILE_ROUTER
    else:
        router_path = Path(router_path)

    router_data = load_yaml(router_path)
    mappings = router_data.get('mappings', {})
    return mappings.get(report_type)


def list_report_types(router_path: Union[str, Path] = None) -> List[str]:
    """列出所有报告类型。

    Args:
        router_path: router.yaml 文件路径

    Returns:
        报告类型列表
    """
    if router_path is None:
        router_path = Path(DIR_TEMPLATES) / FILE_ROUTER
    else:
        router_path = Path(router_path)

    router_data = load_yaml(router_path)
    mappings = router_data.get('mappings', {})
    return list(mappings.keys())


# ==================== 报告目录工具函数 ====================

def create_report_dir(report_name: str, reports_dir: Union[str, Path] = None) -> Path:
    """创建报告目录。

    Args:
        report_name: 报告名称
        reports_dir: reports 目录路径，默认为 "reports"

    Returns:
        报告目录的 Path 对象
    """
    if reports_dir is None:
        reports_dir = DIR_REPORTS
    else:
        reports_dir = Path(reports_dir)

    report_dir = Path(reports_dir) / report_name
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def normalize_report_name(filename: str) -> str:
    """规整化报告名称。

    去除无用前缀和后缀，保留业务名称。

    Args:
        filename: 原始文件名

    Returns:
        规整化后的报告名称
    """
    # 去除扩展名
    name = Path(filename).stem

    # 去除常见前缀
    prefixes_to_remove = [
        'draft_', '草稿_', '最终_', 'final_', 'v2_', 'v3_',
        '备份_', 'bak_', 'temp_', 'tmp_'
    ]
    for prefix in prefixes_to_remove:
        if name.lower().startswith(prefix):
            name = name[len(prefix):]
            break

    # 去除常见后缀
    suffixes_to_remove = [
        '_draft', '_草稿', '_final', '_最终', '_v2', '_v3',
        '_bak', '_备份', '_temp', '_tmp'
    ]
    for suffix in suffixes_to_remove:
        if name.lower().endswith(suffix):
            name = name[:-len(suffix)]
            break

    return name


# ==================== Schema 工具函数 ====================

def get_all_field_names(schema: Dict[str, Any]) -> List[str]:
    """从 schema 中获取所有字段名。

    Args:
        schema: schema.yaml 内容

    Returns:
        字段名列表（按顺序）
    """
    return list(schema.keys())


def filter_fragment_fields(fields: List[str]) -> List[str]:
    """过滤出非 fragment 类型的字段。

    Args:
        fields: 所有字段名列表

    Returns:
        非 fragment 类型的字段名列表
    """
    fragment_fields = {'abstract', 'body'}
    return [f for f in fields if f not in fragment_fields]


def ensure_all_fields(elements: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """确保 elements 包含 schema 中的所有字段。

    缺失的字段使用空字符串填充。

    Args:
        elements: 当前 elements 字典
        schema: schema.yaml 内容

    Returns:
        补全后的 elements 字典
    """
    result = elements.copy()
    for field_name in schema.keys():
        if field_name not in result:
            result[field_name] = ""
    return result


# ==================== Elements 验证工具函数 ====================

def validate_elements_against_schema(
    elements: Dict[str, Any],
    schema: Dict[str, Any]
) -> List[str]:
    """验证 elements 是否与 schema 一致。

    Args:
        elements: elements.yaml 内容
        schema: schema.yaml 内容

    Returns:
        错误信息列表，空列表表示验证通过
    """
    errors = []

    # 检查是否缺少字段
    schema_fields = set(schema.keys())
    elements_fields = set(elements.keys())
    missing_fields = schema_fields - elements_fields

    if missing_fields:
        errors.append(f"缺少字段: {', '.join(missing_fields)}")

    # 检查是否有多余字段
    extra_fields = elements_fields - schema_fields
    if extra_fields:
        errors.append(f"多余字段: {', '.join(extra_fields)}")

    return errors
