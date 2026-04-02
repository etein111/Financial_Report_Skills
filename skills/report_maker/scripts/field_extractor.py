"""field_extractor.py - 字段智能提取模块。

从 Word 文档表格中智能匹配和提取字段值。

遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

import re
from typing import Dict, Any, List, Optional, Tuple
import docx_reader


# ==================== 常量定义 ====================

# 字段分组常量
BASIC_FIELDS = frozenset(['abstract', 'body', 'report_date', 'company', 'ticker', 'title'])
SPECIAL_FIELDS = frozenset(['current_price_date', 'analysts'])
SKIP_FIELDS = BASIC_FIELDS | SPECIAL_FIELDS

# 正则表达式模式
PATTERN_ENGLISH_DATE = re.compile(r'\b\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\b')
PATTERN_CHINESE_DATE = re.compile(r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)')
PATTERN_TITLE = re.compile(r'首次覆盖[：:]\s*(.{10,100})')
PATTERN_EMAIL = re.compile(r'[\w.-]+@[\w.-]+\.\w+')
PATTERN_CHINESE_NAME = re.compile(r'([\u4e00-\u9fa5]{2,})')
PATTERN_ENGLISH_NAME = re.compile(r'([A-Z][a-z]+\s+[A-Z][a-z]+)')
PATTERN_SFC_CODE = re.compile(r'[SFC:]*([A-Z]{4}\d{3})', re.IGNORECASE)

# 关键词常量
KEYWORDS_PRICE_NOTE = ('注', '现价', '收盘价')
KEYWORDS_ANALYST = ('yang', '杨斌', 'analyst')


# ==================== 字段提取规则 ====================

# 常见字段的中英文别名
FIELD_ALIASES = {
    'report_date': ['报告日期', '日期', 'Date', 'Report Date'],
    'company': ['公司', '公司名称', 'Company', 'Company Name'],
    'ticker': ['股票代码', '代码', 'Ticker', 'Symbol', 'Stock Code'],
    'title': ['标题', '报告标题', 'Title', 'Report Title'],
    'rating': ['评级', '投资评级', 'Rating', 'Investment Rating'],
    'current_price': ['现价', '当前价', 'Current Price', 'Price'],
    'target_price': ['目标价', 'Target Price'],
    'market_cap': ['市值', 'Market Cap', 'Market Capitalization'],
    'shares_in_issue': ['发行股票数目', '股本', 'Shares', 'Shares Outstanding'],
    'one_year_high': ['52周高', '一年高', '52 Week High', '1 Year High', '1年股价最高最低值'],
    'one_year_low': ['52周低', '一年低', '52 Week Low', '1 Year Low', '1年股价最高最低值'],
    'current_price_date': ['现价日期', '价格日期', 'Price Date'],
    'analysts': ['分析师', 'Analyst', 'Table_Author'],
    'source': ['资料来源', '来源', 'Source', 'Data Source'],
}

# 数值字段的清理规则
NUMBER_CLEAN_PATTERNS = [
    (r'[^\d.]', ''),  # 移除非数字字符（保留小数点）
    (r'^HK\D*', ''),  # 移除 HK 前缀
    (r'\s*', ''),  # 移除空格
]


# ==================== 主要提取函数 ====================

def extract_fields_from_docx(
    docx_path: str,
    schema: Dict[str, Any],
    context: str = ""
) -> Dict[str, Any]:
    """从 Word 文档中提取字段。

    Args:
        docx_path: Word 文档路径
        schema: schema.yaml 内容（字段定义）
        context: 额外上下文信息

    Returns:
        提取的字段字典
    """
    # 读取所有表格（包括嵌套）
    tables = docx_reader.read_docx_tables(docx_path)

    # 初始化结果
    elements = {}
    for field_name in schema.keys():
        if field_name not in ['abstract', 'body']:
            elements[field_name] = ""

    # 设置 fragment 字段
    if 'abstract' in schema:
        elements['abstract'] = 'abstract.docx'
    if 'body' in schema:
        elements['body'] = 'body.docx'

    # 从主表格中提取基本信息（首页表格）
    basic_fields = _extract_basic_fields_from_main_tables(tables, schema)
    elements.update(basic_fields)

    # 从嵌套表格中提取详细财务信息
    financial_fields = _extract_financial_fields_from_nested_tables(tables, schema)
    elements.update(financial_fields)

    # 特殊处理需要拆分的字段
    _handle_split_fields(elements)

    return elements


def _extract_from_tables(
    tables: List[Dict[str, Any]],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """从表格中提取字段（已弃用，保留向后兼容）。

    Args:
        tables: 表格数据列表
        schema: schema.yaml 内容

    Returns:
        提取的字段字典
    """
    extracted = {}

    # 优先从嵌套表格中提取（首页财务数据通常在嵌套表格中）
    nested_tables = docx_reader.extract_nested_tables_only(tables)
    for field_name, field_def in schema.items():
        if field_name in ['abstract', 'body']:
            continue

        # 尝试从嵌套表格提取
        value = _extract_field_from_nested_tables(
            nested_tables,
            field_name,
            field_def
        )

        # 如果嵌套表格没找到，尝试从所有表格提取
        if not value:
            value = _extract_field_from_all_tables(
                tables,
                field_name,
                field_def
            )

        if value:
            extracted[field_name] = value

    return extracted


def _extract_basic_fields_from_main_tables(
    tables: List[Dict[str, Any]],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """从主表格（首页表格）中提取基本信息。

    主要提取：report_date, company, ticker, title

    Args:
        tables: 表格数据列表
        schema: schema.yaml 内容

    Returns:
        提取的字段字典
    """
    extracted = {}

    # 只查看第一个表格（通常是首页表格）
    if not tables:
        return extracted

    main_table = tables[0]
    all_lines = docx_reader.flatten_table_text([main_table])
    # 计算 full_text 一次，避免重复操作
    full_text = ' '.join(all_lines)

    # 提取 report_date（格式如 "21 Oct 2025"）
    if 'report_date' in schema:
        date_match = _find_date_in_text(full_text)
        if date_match:
            extracted['report_date'] = date_match

    # 提取 company 和 ticker（格式如 "西锐飞机 (2507.HK)"）
    if 'company' in schema or 'ticker' in schema:
        company_ticker = _find_company_ticker_in_text(full_text)
        if company_ticker:
            if 'company' in schema and company_ticker.get('company'):
                extracted['company'] = company_ticker['company']
            if 'ticker' in schema and company_ticker.get('ticker'):
                extracted['ticker'] = company_ticker['ticker']

    # 提取 title（只取第一个匹配，避免重复）
    if 'title' in schema:
        title = _find_title_in_lines(all_lines)
        if title:
            extracted['title'] = title

    return extracted


def _extract_financial_fields_from_nested_tables(
    tables: List[Dict[str, Any]],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """从嵌套表格中提取财务信息。

    主要提取：rating, current_price, target_price, market_cap, 等

    Args:
        tables: 表格数据列表
        schema: schema.yaml 内容

    Returns:
        提取的字段字典
    """
    extracted = {}
    nested_tables = docx_reader.extract_nested_tables_only(tables)

    # 先处理特殊字段（需要从注释中提取或特殊格式化）
    if 'current_price_date' in schema:
        date_value = _extract_current_price_date_from_notes(nested_tables)
        if date_value:
            extracted['current_price_date'] = date_value

    if 'analysts' in schema:
        analysts_value = _extract_analysts_from_tables(nested_tables)
        if analysts_value:
            extracted['analysts'] = analysts_value

    # 处理常规字段
    for field_name, field_def in schema.items():
        # 跳过已处理的特殊字段和 fragment 字段
        if field_name in SKIP_FIELDS:
            continue

        value = _extract_field_from_nested_tables(
            nested_tables,
            field_name,
            field_def
        )

        if value:
            extracted[field_name] = value

    return extracted


def _handle_split_fields(elements: Dict[str, Any]) -> None:
    """处理需要拆分的字段。

    例如：
    - "1年股价最高最低值" 字段包含 "73.40-20.50"
    - 需要拆分为 one_year_high="73.40", one_year_low="20.50"

    Args:
        elements: 元素字典（会直接修改）
    """
    # 处理 one_year_high 和 one_year_low 组合字段
    high_value = elements.get('one_year_high', '')
    low_value = elements.get('one_year_low', '')

    # 统一处理逻辑：找到包含 "-" 的值并拆分
    source_value = None
    if '-' in high_value and not low_value:
        source_value = high_value
    elif '-' in low_value and high_value == low_value:
        source_value = low_value

    if source_value:
        parts = source_value.split('-')
        if len(parts) == 2:
            elements['one_year_high'] = parts[0].strip()
            elements['one_year_low'] = parts[1].strip()


def _find_date_in_text(text: str) -> Optional[str]:
    """从文本中查找日期。

    格式如 "21 Oct 2025"

    Args:
        text: 文本

    Returns:
        找到的日期，未找到返回 None
    """
    match = PATTERN_ENGLISH_DATE.search(text)
    if match:
        return match.group(0)
    return None


def _find_company_ticker_in_text(text: str) -> Optional[Dict[str, str]]:
    """从文本中查找公司和股票代码。

    格式如 "西锐飞机 (2507.HK)"

    Args:
        text: 文本

    Returns:
        {'company': '西锐飞机', 'ticker': '2507.HK'}，未找到返回 None
    """
    # 匹配 "公司名 (TICKER)" 格式
    pattern = r'([\u4e00-\u9fa5a-zA-Z\s]+)\s*\(([A-Z0-9\.HK]+)\)'
    match = re.search(pattern, text)
    if match:
        company = match.group(1).strip()
        ticker = match.group(2).strip()
        return {'company': company, 'ticker': ticker}
    return None


def _find_title_in_lines(lines: List[str]) -> Optional[str]:
    """从行列表中查找标题（只取第一个匹配，避免重复）。

    通常是"首次覆盖：..."或"首次覆盖：..."

    Args:
        lines: 文本行列表

    Returns:
        找到的标题，未找到返回 None
    """
    for line in lines:
        if '首次覆盖' in line:
            # 匹配完整的标题
            match = PATTERN_TITLE.search(line)
            if match:
                return '首次覆盖：' + match.group(1).strip()
    return None


def _extract_field_from_nested_tables(
    nested_tables: List[Dict[str, Any]],
    field_name: str,
    field_def: Dict[str, Any]
) -> Optional[str]:
    """从嵌套表格中提取字段。

    Args:
        nested_tables: 嵌套表格列表
        field_name: 字段名
        field_def: 字段定义

    Returns:
        提取值，未找到返回 None
    """
    aliases = FIELD_ALIASES.get(field_name, [field_name])

    for table in nested_tables:
        value = _search_field_in_table(table, aliases, field_def)
        if value:
            return value

    return None


def _extract_field_from_all_tables(
    tables: List[Dict[str, Any]],
    field_name: str,
    field_def: Dict[str, Any]
) -> Optional[str]:
    """从所有表格中提取字段。

    Args:
        tables: 表格列表
        field_name: 字段名
        field_def: 字段定义

    Returns:
        提取值，未找到返回 None
    """
    aliases = FIELD_ALIASES.get(field_name, [field_name])

    for table in tables:
        value = _search_field_in_table(table, aliases, field_def)
        if value:
            return value

    return None


def _search_field_in_table(
    table: Dict[str, Any],
    aliases: List[str],
    field_def: Dict[str, Any]
) -> Optional[str]:
    """在单个表格中搜索字段（递归搜索嵌套表格）。

    Args:
        table: 表格数据
        aliases: 字段别名列表
        field_def: 字段定义

    Returns:
        提取值，未找到返回 None
    """
    # 先在当前表格的行中搜索
    for row in table.get('rows', []):
        cells = row.get('cells', [])

        # 查找包含字段别名的单元格
        for cell_idx, cell in enumerate(cells):
            cell_text = cell.get('text', '').strip()

            # 检查是否完全匹配字段别名（更精确）
            for alias in aliases:
                if _is_field_label_match(cell_text, alias):
                    # 找到匹配，尝试获取值（通常在下一个单元格）
                    if cell_idx + 1 < len(cells):
                        value_cell = cells[cell_idx + 1]
                        value = _clean_field_value(
                            value_cell.get('text', ''),
                            field_def
                        )
                        if value:
                            return value

            # 递归搜索单元格内的嵌套表格
            for nested_table in cell.get('nested_tables', []):
                value = _search_field_in_table(nested_table, aliases, field_def)
                if value:
                    return value

    return None


def _is_field_label_match(cell_text: str, alias: str) -> bool:
    """检查单元格文本是否匹配字段标签。

    只使用完全匹配和严格前缀匹配，避免误匹配。

    Args:
        cell_text: 单元格文本
        alias: 字段别名

    Returns:
        是否匹配
    """
    cell_text_clean = cell_text.strip().rstrip('：:')

    # 1. 完全匹配（最严格）
    if cell_text_clean.lower() == alias.lower():
        return True

    # 2. 严格前缀匹配（如"评级："匹配"评级"，但"评级调整"不匹配"评级"）
    # 检查是否以别名开头，并且后面只有冒号或空格
    if cell_text_clean.lower().startswith(alias.lower()):
        remainder = cell_text_clean[len(alias):].lstrip()
        # 如果剩余部分为空，或者只有标点符号，则匹配
        if not remainder or remainder[0] in '：:，,':
            return True

    return False


def _clean_field_value(value: str, field_def: Dict[str, Any]) -> str:
    """清理字段值。

    Args:
        value: 原始值
        field_def: 字段定义

    Returns:
        清理后的值
    """
    value = value.strip()

    # 移除常见的无用前缀
    prefixes_to_remove = [
        '资料来源：', '来源：', 'Source:',
        '注：', 'Note:', '说明：',
    ]

    for prefix in prefixes_to_remove:
        if value.startswith(prefix):
            value = value[len(prefix):].strip()

    # 注意：不再移除单位后缀（bn, mn 等），因为它们是值的一部分
    # 例如：22.11bn, 365.99mn

    # 特殊处理：analysts 字段
    if field_def.get('description') == 'analysts':
        value = _format_analysts_value(value)

    return value


def _format_analysts_value(value: str) -> str:
    """格式化 analysts 字段值。

    将各种格式的分析师信息转换为标准格式。

    Args:
        value: 原始值

    Returns:
        格式化后的值
    """
    # 简单的格式化，可以根据实际情况扩展
    # 例如：从 "杨斌 Bin Yang, SFC:BSQ313" 提取结构化数据
    value = value.strip()

    # 如果包含逗号分隔的信息，尝试解析
    if ',' in value:
        parts = [p.strip() for p in value.split(',')]
        # 这里可以添加更复杂的解析逻辑
        # 暂时返回原始值
        return value

    return value


# ==================== 辅助函数 ====================

def find_table_by_keyword(
    tables: List[Dict[str, Any]],
    keyword: str
) -> Optional[Dict[str, Any]]:
    """根据关键词查找表格。

    Args:
        tables: 表格列表
        keyword: 关键词

    Returns:
        匹配的表格，未找到返回 None
    """
    keyword_lower = keyword.lower()

    for table in tables:
        table_text = _get_table_text(table)
        if keyword_lower in table_text.lower():
            return table

    return None


def _get_table_text(table: Dict[str, Any]) -> str:
    """获取表格的所有文本。

    Args:
        table: 表格数据

    Returns:
        表格文本
    """
    texts = []

    def _collect_text(node: Dict[str, Any]) -> None:
        """递归收集文本。"""
        node_type = node.get('type', '')

        if node_type == 'cell':
            text = node.get('text', '').strip()
            if text:
                texts.append(text)

            for nested_table in node.get('nested_tables', []):
                _collect_text(nested_table)

        elif node_type == 'row':
            for cell in node.get('cells', []):
                _collect_text(cell)

        elif node_type == 'table':
            for row in node.get('rows', []):
                _collect_text(row)

    _collect_text(table)
    return ' '.join(texts)


def _extract_current_price_date_from_notes(
    nested_tables: List[Dict[str, Any]]
) -> Optional[str]:
    """从注释中提取 current_price_date。

    注释格式如：注：现价60.40为2026 年 01 月 15 日收盘价

    Args:
        nested_tables: 嵌套表格列表

    Returns:
        提取的日期字符串，未找到返回 None
    """
    for table in nested_tables:
        lines = docx_reader.flatten_table_text([table])
        for line in lines:
            # 查找包含"注"、"现价"、"收盘价"的行
            if all(keyword in line for keyword in KEYWORDS_PRICE_NOTE):
                # 提取日期（格式：2026 年 01 月 15 日）
                date_match = PATTERN_CHINESE_DATE.search(line)
                if date_match:
                    return date_match.group(1)

    return None


def _extract_analysts_from_tables(
    nested_tables: List[Dict[str, Any]]
) -> Optional[str]:
    """从嵌套表格中提取分析师信息并格式化。

    查找包含分析师信息的表格（Table_Author），并格式化为标准格式：
    [{'chinese_name': '杨斌', 'english_name': 'Bin Yang', 'sfc_code': 'BSQ313', 'email': 'harryyang@hfisec.com.hk'}]

    Args:
        nested_tables: 嵌套表格列表

    Returns:
        格式化后的分析师信息字符串，未找到返回 None
    """
    for table in nested_tables:
        lines = docx_reader.flatten_table_text([table])
        text = ' '.join(lines)

        # 查找包含分析师信息的表格
        if any(keyword in text.lower() for keyword in KEYWORDS_ANALYST):
            # 解析分析师信息
            chinese_name = None
            english_name = None
            sfc_code = None
            email = None

            for line in lines:
                # 提取中文姓名
                if PATTERN_CHINESE_NAME.search(line):
                    chinese_match = PATTERN_CHINESE_NAME.search(line)
                    if chinese_match:
                        chinese_name = chinese_match.group(1)

                # 提取英文姓名
                english_match = PATTERN_ENGLISH_NAME.search(line)
                if english_match:
                    english_name = english_match.group(1)

                # 提取 SFC 代码
                sfc_match = PATTERN_SFC_CODE.search(line)
                if sfc_match:
                    sfc_code = sfc_match.group(1)

                # 提取邮箱
                email_match = PATTERN_EMAIL.search(line)
                if email_match:
                    email = email_match.group(0)

            # 如果找到了至少一个字段，返回格式化结果
            if chinese_name or english_name:
                chinese_name = chinese_name or ''
                english_name = english_name or ''
                sfc_code = sfc_code or ''
                email = email or ''

                return f"[{{'chinese_name': '{chinese_name}', 'english_name': '{english_name}', 'sfc_code': '{sfc_code}', 'email': '{email}'}}]"

    return None
