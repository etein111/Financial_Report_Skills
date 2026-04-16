"""report_maker 共享工具函数和常量。

此模块提供所有 report_maker 子模块共享的工具函数和常量定义。
遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

import os
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from lxml import etree
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
FILE_ENGLISH_SUMMARY = "english_summary.docx"
FILE_APPENDIX = "appendix.docx"
FILE_OUTPUT_DOCX = "output.docx"  # 默认输出文件名（备用）
FILE_OUTPUT_PDF = "output.pdf"

# Word XML 命名空间
W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

# 英文摘要 section 起始标记（模板中固定的段落文本）
APPENDIX_1_MARKER = 'APPENDIX 1'

# 占位符标记（docxtpl 渲染时替换为特殊文本，后续步骤插入实际内容）
ABSTRACT_MARKER = '###ABSTRACT_MARKER###'
BODY_MARKER = '###BODY_MARKER###'
ENGLISH_SUMMARY_MARKER = '###ENGLISH_SUMMARY_MARKER###'
RELATIVE_CHART_MARKER = '###RELATIVE_CHART_MARKER###'
RECOMMENDATION_CHART_MARKER = '###RECOMMENDATION_CHART_MARKER###'

# Windows 文件名禁止字符
INVALID_FILENAME_CHARS = r'\/:*?"<>|'


# ==================== Docx Zip 工具函数 ====================

def read_docx_zip(path: str) -> Dict[str, bytes]:
    """读取 docx (zip) 文件中的所有条目。

    Args:
        path: docx 文件路径

    Returns:
        文件名 -> 内容的字节数据字典
    """
    with zipfile.ZipFile(path, 'r') as z:
        return {name: z.read(name) for name in z.namelist()}


def write_docx_zip(path: str, files: Dict[str, bytes]) -> None:
    """将文件字典写回 docx (zip)，覆盖原文件。

    先写入临时文件，成功后替换原文件，避免写入中断导致文件损坏。

    Args:
        path: docx 文件路径
        files: 文件名 -> 内容的字节数据字典
    """
    tmp_path = path + '.tmp'
    try:
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in files.items():
                z.writestr(name, content)
        os.replace(tmp_path, path)
    except BaseException:
        # 写入失败时清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def modify_docx_xml(path: str, modifier_fn, standalone=True, output_path: str = None) -> None:
    """读取 docx 的 document.xml，执行修改函数，写回 docx。

    将 read → parse → modify → serialize → write 模式封装为单次调用，
    避免在 6+ 个模块中重复相同的样板代码。

    Args:
        path: docx 文件路径
        modifier_fn: 接收 lxml etree.Element（document.xml 根节点）的回调函数
        standalone: XML declaration 的 standalone 属性（默认 True）
        output_path: 输出路径（默认覆盖原文件）
    """
    from lxml import etree

    files = read_docx_zip(path)
    if 'word/document.xml' not in files:
        return

    tree = etree.fromstring(files['word/document.xml'])
    modifier_fn(tree)
    files['word/document.xml'] = etree.tostring(
        tree, xml_declaration=True, encoding='UTF-8', standalone=standalone
    )
    write_docx_zip(output_path or path, files)


def get_element_text(elem) -> str:
    """提取 XML 元素中所有 w:t 子元素的文本内容。

    Args:
        elem: lxml 元素

    Returns:
        拼接后的文本字符串
    """
    return ''.join(t.text or '' for t in elem.iter(f'{W_NS}t'))


def local_tag(elem) -> str:
    """从带命名空间的 XML tag 中提取本地名称。

    Args:
        elem: lxml 元素

    Returns:
        去除命名空间后的标签名（如 'p'、'tbl'、'sectPr'）
    """
    return elem.tag.rsplit('}', 1)[-1]


def extract_margins_from_pgMar(pgMar_elem) -> Dict[str, str]:
    """从 w:pgMar 元素提取页边距属性。

    Args:
        pgMar_elem: lxml 的 w:pgMar 元素

    Returns:
        页边距字典 {'top': ..., 'bottom': ..., ...}，空字典表示无属性
    """
    if pgMar_elem is None:
        return {}
    margins = {}
    for attr in ['top', 'bottom', 'left', 'right', 'header', 'footer', 'gutter']:
        val = pgMar_elem.get(f'{W_NS}{attr}')
        if val is not None:
            margins[attr] = val
    return margins


# ==================== YAML 工具函数 ====================

def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """加载 YAML 文件。

    Args:
        path: YAML 文件路径

    Returns:
        解析后的字典，文件不存在时返回空字典
    """
    path = Path(path)
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def save_yaml(path: Union[str, Path], data: Dict[str, Any], sort_keys: bool = False) -> None:
    """保存数据到 YAML 文件。

    Args:
        path: YAML 文件路径
        data: 要保存的数据
        sort_keys: 是否排序键（默认 False）
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=sort_keys), encoding='utf-8')


# ==================== 路由工具函数 ====================

def get_template_name(report_type: str, router_path: Union[str, Path] = None) -> Optional[str]:
    """根据报告类型获取模板名。

    注意：此函数已被 neolyst_integration.resolve_template_for_report 替代，
    保留仅为向后兼容。

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


def generate_report_filename(elements: Dict[str, Any], extension: str = ".docx") -> str:
    """根据 elements 生成报告文件名。

    格式：{company_cn}({ticker})：{title}{extension}
    示例：西锐飞机(2507 HK)：首次覆盖：安全、创新与强大生态系统铸就西锐私人航空全球领导者地位.docx

    Args:
        elements: 要素字典，需要包含 company_cn、ticker、title 字段
        extension: 文件扩展名，默认为 ".docx"

    Returns:
        生成的文件名，如果缺少必要字段则返回默认文件名
    """
    company_cn = elements.get('company_cn', '').strip()
    ticker = elements.get('ticker', '').strip()
    title = elements.get('title', '').strip()

    # 如果缺少必要字段，返回默认文件名
    if not company_cn or not ticker or not title:
        return FILE_OUTPUT_DOCX if extension == ".docx" else FILE_OUTPUT_PDF

    # 格式化 ticker：将点号替换为空格（如 2507.HK -> 2507 HK）
    ticker_formatted = ticker.replace('.', ' ')

    # 构建文件名（使用中文全角冒号，避免 Windows 禁止字符）
    filename = f"{company_cn}({ticker_formatted})：{title}"

    # 清理文件名中的非法字符
    filename = sanitize_filename(filename)

    # 添加扩展名
    return filename + extension


def sanitize_filename(filename: str) -> str:
    """清理文件名中的非法字符。

    移除 Windows 文件名中禁止的字符：\\ / : * ? \" < > |
    保留中文全角字符（如中文冒号 ：）

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    result = filename
    for char in INVALID_FILENAME_CHARS:
        result = result.replace(char, '')
    return result


def get_report_output_path(
    report_dir: Union[str, Path],
    elements: Dict[str, Any],
    extension: str = ".docx"
) -> Path:
    """获取报告输出文件的完整路径。

    Args:
        report_dir: 报告目录路径
        elements: 要素字典
        extension: 文件扩展名

    Returns:
        完整的输出文件路径
    """
    filename = generate_report_filename(elements, extension)
    return Path(report_dir) / filename


# ==================== Schema 工具函数 ====================


def init_elements_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """从 schema 初始化 elements 字典，fragment 字段设为文件引用。

    Args:
        schema: schema.yaml 内容

    Returns:
        初始化后的 elements 字典
    """
    elements = {}
    for field_name in schema.keys():
        if field_name not in ['abstract', 'body']:
            elements[field_name] = ""
    if 'abstract' in schema:
        elements['abstract'] = FILE_ABSTRACT
    if 'body' in schema:
        elements['body'] = FILE_BODY
    return elements


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

    # 获取 schema 中非自动生成的字段
    schema_fields = set()
    auto_generated_fields = set()
    boolean_status_fields = set()  # *_generated 类型的布尔状态字段
    for field_name, field_config in schema.items():
        if isinstance(field_config, dict):
            field_format = field_config.get('format', '')
            if field_format == '自动生成':
                auto_generated_fields.add(field_name)
            elif field_format == 'boolean' and field_name.endswith('_generated'):
                boolean_status_fields.add(field_name)
            else:
                schema_fields.add(field_name)
        else:
            schema_fields.add(field_name)

    elements_fields = set(elements.keys())

    # 检查是否缺少字段（排除自动生成的字段和布尔状态字段）
    missing_fields = schema_fields - elements_fields
    if missing_fields:
        errors.append(f"缺少字段: {', '.join(missing_fields)}")

    # 检查是否有多余字段（排除自动生成的字段和布尔状态字段）
    extra_fields = elements_fields - schema_fields - auto_generated_fields - boolean_status_fields
    if extra_fields:
        errors.append(f"多余字段: {', '.join(extra_fields)}")

    # 检查图表生成状态（布尔状态字段必须为 true）
    for field_name in boolean_status_fields:
        if field_name.endswith('_generated'):
            chart_name = field_name.replace('_generated', '')
            status = elements.get(field_name, False)
            if not status:
                errors.append(f"图表 {chart_name} 生成失败，请检查渲染日志")

    return errors
