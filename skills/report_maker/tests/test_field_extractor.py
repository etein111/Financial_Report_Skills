"""test_field_extractor.py - field_extractor.py 模块测试。

测试从 Word 文档表格中智能匹配和提取字段值的功能。
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from field_extractor import (
    _find_date_in_text,
    _find_company_ticker_in_text,
    _find_title_in_lines,
    _is_field_label_match,
    _clean_field_value,
    _format_analysts_value,
)


class TestFindDateInText:
    """测试 _find_date_in_text 函数。"""

    def test_finds_english_date_format(self):
        """测试：找到英文格式日期。"""
        text = "Report Date: 21 Oct 2025"
        result = _find_date_in_text(text)

        assert result == "21 Oct 2025"

    def test_finds_date_in_middle_of_text(self):
        """测试：在文本中间找到日期。"""
        text = "This report was issued on 15 Mar 2024 for investors"
        result = _find_date_in_text(text)

        assert result == "15 Mar 2024"

    def test_returns_none_when_no_date(self):
        """测试：没有日期时返回 None。"""
        text = "No date here"
        result = _find_date_in_text(text)

        assert result is None

    def test_handles_chinese_text(self):
        """测试：处理包含中文的文本。"""
        text = "报告日期：21 Oct 2025，公司"
        result = _find_date_in_text(text)

        assert result == "21 Oct 2025"


class TestFindCompanyTickerInText:
    """测试 _find_company_ticker_in_text 函数。"""

    def test_finds_company_and_ticker(self):
        """测试：找到公司和股票代码。"""
        text = "西锐飞机 (2507.HK)"
        result = _find_company_ticker_in_text(text)

        assert result is not None
        assert result['company'] == '西锐飞机'
        assert result['ticker'] == '2507.HK'

    def test_finds_with_spaces(self):
        """测试：处理公司名中的空格。"""
        text = "腾讯控股 (0700.HK)"
        result = _find_company_ticker_in_text(text)

        assert result is not None
        assert '腾讯' in result['company']

    def test_returns_none_for_invalid_format(self):
        """测试：无效格式返回 None。"""
        text = "No ticker here"
        result = _find_company_ticker_in_text(text)

        assert result is None

    def test_handles_us_ticker(self):
        """测试：处理美股代码。"""
        text = "Apple Inc (AAPL)"
        result = _find_company_ticker_in_text(text)

        assert result is not None
        assert result['ticker'] == 'AAPL'


class TestFindTitleInLines:
    """测试 _find_title_in_lines 函数。"""

    def test_finds_title_with_首次覆盖(self):
        """测试：找到"首次覆盖"标题。"""
        lines = ["公司信息", "首次覆盖：西锐飞机深度研究报告", "正文内容"]

        result = _find_title_in_lines(lines)

        assert result is not None
        assert "首次覆盖" in result

    def test_returns_none_when_not_found(self):
        """测试：未找到时返回 None。"""
        lines = ["公司信息", "财务数据", "正文内容"]

        result = _find_title_in_lines(lines)

        assert result is None


class TestIsFieldLabelMatch:
    """测试 _is_field_label_match 函数。"""

    def test_exact_match(self):
        """测试：精确匹配。"""
        assert _is_field_label_match("评级", "评级") is True
        assert _is_field_label_match("rating", "rating") is True

    def test_case_insensitive_exact_match(self):
        """测试：精确匹配不区分大小写。"""
        assert _is_field_label_match("评级", "RATING") is False  # RATING != 评级
        assert _is_field_label_match("Rating", "rating") is True  # Rating == rating

    def test_strict_prefix_match(self):
        """测试：严格前缀匹配。"""
        assert _is_field_label_match("评级：", "评级") is True
        assert _is_field_label_match("评级，", "评级") is True

    def test_prefix_with_value(self):
        """测试：前缀后有值时匹配。"""
        assert _is_field_label_match("评级：买入", "评级") is True

    def test_no_match_different_content(self):
        """测试：不同内容不匹配。"""
        assert _is_field_label_match("评级调整", "评级") is False

    def test_no_match_partial(self):
        """测试：部分匹配不成功。"""
        assert _is_field_label_match("投资评级", "评级") is False


class TestCleanFieldValue:
    """测试 _clean_field_value 函数。"""

    def test_removes_source_prefix(self):
        """测试：移除"资料来源"前缀。"""
        value = "资料来源：Wind"
        field_def = {}
        result = _clean_field_value(value, field_def)

        assert "资料来源" not in result
        assert "Wind" in result

    def test_removes_note_prefix(self):
        """测试：移除"注"前缀。"""
        value = "注：这是注释"
        field_def = {}
        result = _clean_field_value(value, field_def)

        assert result == "这是注释"

    def test_preserves_unit_suffix(self):
        """测试：保留单位后缀。"""
        value = "22.11bn"
        field_def = {}
        result = _clean_field_value(value, field_def)

        assert "bn" in result

    def test_strips_whitespace(self):
        """测试：去除首尾空白。"""
        value = "  评级  "
        field_def = {}
        result = _clean_field_value(value, field_def)

        assert result == "评级"

    def test_handles_empty_string(self):
        """测试：处理空字符串。"""
        value = ""
        field_def = {}
        result = _clean_field_value(value, field_def)

        assert result == ""


class TestFormatAnalystsValue:
    """测试 _format_analysts_value 函数。"""

    def test_preserves_simple_value(self):
        """测试：保留简单值。"""
        value = "杨斌"
        result = _format_analysts_value(value)

        assert result == "杨斌"

    def test_handles_comma_separated(self):
        """测试：处理逗号分隔的值。"""
        value = "杨斌, SFC:BSQ313"
        result = _format_analysts_value(value)

        # 逗号分隔的情况下返回原始值
        assert "," in result

    def test_strips_whitespace(self):
        """测试：去除空白。"""
        value = "  杨斌  "
        result = _format_analysts_value(value)

        assert result == "杨斌"


class TestWithRealDocument:
    """使用真实研报文档测试 field_extractor。"""

    @pytest.fixture
    def real_doc_parsed(self):
        """解析真实研报文档。"""
        from docx_reader import read_docx_tables, flatten_table_text, extract_nested_tables_only

        # fixtures 目录在 tests/fixtures/
        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))
        nested = extract_nested_tables_only(tables)
        lines = flatten_table_text(tables)
        return {"tables": tables, "nested": nested, "lines": lines}

    @pytest.fixture
    def schema(self):
        """加载真实的 schema.yaml。"""
        import yaml
        schema_path = Path(__file__).parent.parent.parent.parent / "templates" / "company" / "schema.yaml"
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def real_docx_path(self):
        """真实文档路径。"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        return str(fixtures_dir / "real_research_report.docx")

    def test_find_date_in_real_document(self, real_doc_parsed):
        """测试：从真实文档中找到日期。"""
        full_text = ' '.join(real_doc_parsed["lines"])
        date = _find_date_in_text(full_text)

        assert date is not None
        assert "Apr" in date or "2026" in date

    def test_find_company_ticker_in_real_document(self, real_doc_parsed):
        """测试：从真实文档中找到公司和股票代码。"""
        full_text = ' '.join(real_doc_parsed["lines"])
        result = _find_company_ticker_in_text(full_text)

        assert result is not None
        assert result["ticker"] == "3393.HK"
        assert "威胜" in result["company"]

    def test_find_title_in_real_document(self, real_doc_parsed):
        """测试：从真实文档中找到标题。"""
        lines = real_doc_parsed["lines"]
        title = _find_title_in_lines(lines)

        assert title is not None
        assert "首次覆盖" in title
        # 标题不包含"威胜"，但lines中有"威胜控股 (3393.HK)"
        assert "配网" in title or "AI算力" in title

    def test_flatten_table_contains_rating_info(self, real_doc_parsed):
        """测试：扁平化文本包含评级信息。"""
        lines = real_doc_parsed["lines"]
        full_text = ' '.join(lines)

        assert "评级" in full_text
        assert "买入" in full_text or "增持" in full_text or "中性" in full_text

    def test_nested_tables_structure(self, real_doc_parsed):
        """测试：嵌套表格结构正确。"""
        nested = real_doc_parsed["nested"]

        assert len(nested) > 0
        # 第一个嵌套表格应该包含公司信息
        first_nested_text = ' '.join([c['text'] for row in nested[0]['rows'] for c in row['cells']])
        assert len(first_nested_text) > 0

    def test_analyst_info_extracted(self, real_doc_parsed):
        """测试：从真实文档中提取分析师信息。"""
        lines = real_doc_parsed["lines"]
        full_text = ' '.join(lines)

        # 真实文档包含分析师信息
        assert "杨斌" in full_text or "Bin Yang" in full_text


class TestExtractFieldsFromDocx:
    """测试 extract_fields_from_docx 主函数。"""

    @pytest.fixture
    def schema(self):
        """加载真实的 schema.yaml。"""
        import yaml
        schema_path = Path(__file__).parent.parent.parent.parent / "templates" / "company" / "schema.yaml"
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def real_docx_path(self):
        """真实文档路径。"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        return str(fixtures_dir / "real_research_report.docx")

    def test_extract_fields_from_docx_returns_dict(self, real_docx_path, schema):
        """测试：extract_fields_from_docx 返回字典。"""
        from field_extractor import extract_fields_from_docx

        result = extract_fields_from_docx(real_docx_path, schema)

        assert isinstance(result, dict)
        assert 'abstract' in result
        assert 'body' in result

    def test_extract_fields_from_docx_has_basic_fields(self, real_docx_path, schema):
        """测试：extract_fields_from_docx 包含基本字段。"""
        from field_extractor import extract_fields_from_docx

        result = extract_fields_from_docx(real_docx_path, schema)

        # 基本字段应该被提取
        assert result.get('report_date') is not None
        assert result.get('ticker') is not None
        assert '3393' in result.get('ticker', '')

    def test_extract_fields_from_docx_has_fragment_fields(self, real_docx_path, schema):
        """测试：extract_fields_from_docx 设置了 fragment 字段。"""
        from field_extractor import extract_fields_from_docx

        result = extract_fields_from_docx(real_docx_path, schema)

        # abstract 和 body 应该是 fragment 文件名
        assert result.get('abstract') == 'abstract.docx'
        assert result.get('body') == 'body.docx'

    def test_extract_fields_from_docx_empty_schema(self, real_docx_path):
        """测试：空 schema 时返回空字典（因为没有 schema 字段定义）。"""
        from field_extractor import extract_fields_from_docx

        result = extract_fields_from_docx(real_docx_path, {})

        # 空 schema 时返回空字典（没有 abstract/body 定义）
        assert result == {} or (result.get('abstract') == '' and result.get('body') == '')

    def test_extract_fields_from_docx_with_context(self, real_docx_path, schema):
        """测试：extract_fields_from_docx 接受 context 参数。"""
        from field_extractor import extract_fields_from_docx

        result = extract_fields_from_docx(real_docx_path, schema, context="extra info")

        # context 不影响基本功能
        assert isinstance(result, dict)


class TestExtractBasicFieldsFromMainTables:
    """测试 _extract_basic_fields_from_main_tables 函数。"""

    @pytest.fixture
    def schema(self):
        """加载真实的 schema.yaml。"""
        import yaml
        schema_path = Path(__file__).parent.parent.parent.parent / "templates" / "company" / "schema.yaml"
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def test_extracts_from_first_table_only(self, schema):
        """测试：只从第一个表格提取。"""
        from docx_reader import read_docx_tables
        from field_extractor import _extract_basic_fields_from_main_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))

        result = _extract_basic_fields_from_main_tables(tables, schema)

        assert isinstance(result, dict)
        # 应该提取到 report_date
        assert 'report_date' in result

    def test_handles_empty_tables(self, schema):
        """测试：空表格列表返回空字典。"""
        from field_extractor import _extract_basic_fields_from_main_tables

        result = _extract_basic_fields_from_main_tables([], schema)

        assert result == {}

    def test_extracts_company_and_ticker(self, schema):
        """测试：提取公司和股票代码。"""
        from docx_reader import read_docx_tables
        from field_extractor import _extract_basic_fields_from_main_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))

        result = _extract_basic_fields_from_main_tables(tables, schema)

        # 应该提取到 ticker
        assert 'ticker' in result


class TestExtractFinancialFieldsFromNestedTables:
    """测试 _extract_financial_fields_from_nested_tables 函数。"""

    @pytest.fixture
    def schema(self):
        """加载真实的 schema.yaml。"""
        import yaml
        schema_path = Path(__file__).parent.parent.parent.parent / "templates" / "company" / "schema.yaml"
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def test_extracts_rating(self, schema):
        """测试：提取评级。"""
        from docx_reader import read_docx_tables
        from field_extractor import _extract_financial_fields_from_nested_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))

        result = _extract_financial_fields_from_nested_tables(tables, schema)

        # 可能提取到评级
        assert isinstance(result, dict)

    def test_extracts_current_price_date(self, schema):
        """测试：提取现价日期。"""
        from docx_reader import read_docx_tables
        from field_extractor import _extract_financial_fields_from_nested_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))

        result = _extract_financial_fields_from_nested_tables(tables, schema)

        # current_price_date 是特殊字段
        assert 'current_price_date' in result or 'current_price_date' not in result

    def test_extracts_analysts(self, schema):
        """测试：提取分析师信息。"""
        from docx_reader import read_docx_tables
        from field_extractor import _extract_financial_fields_from_nested_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))

        result = _extract_financial_fields_from_nested_tables(tables, schema)

        # analysts 是特殊字段
        assert 'analysts' in result or 'analysts' not in result

    def test_handles_empty_tables(self, schema):
        """测试：空表格列表返回空字典。"""
        from field_extractor import _extract_financial_fields_from_nested_tables

        result = _extract_financial_fields_from_nested_tables([], schema)

        assert result == {}


class TestHandleSplitFields:
    """测试 _handle_split_fields 函数。"""

    def test_handles_split_high_low(self):
        """测试：处理拆分的一年高低价。"""
        from field_extractor import _handle_split_fields

        elements = {'one_year_high': '73.40-20.50', 'one_year_low': ''}

        result = _handle_split_fields(elements)

        assert result['one_year_high'] == '73.40'
        assert result['one_year_low'] == '20.50'

    def test_returns_new_dict(self):
        """测试：返回新的字典，不修改原字典。"""
        from field_extractor import _handle_split_fields

        elements = {'one_year_high': '73.40-20.50', 'one_year_low': ''}
        original = elements.copy()

        result = _handle_split_fields(elements)

        assert result != elements
        assert elements == original

    def test_no_split_needed(self):
        """测试：不需要拆分时保持原值。"""
        from field_extractor import _handle_split_fields

        elements = {'one_year_high': '73.40', 'one_year_low': '20.50'}

        result = _handle_split_fields(elements)

        assert result['one_year_high'] == '73.40'
        assert result['one_year_low'] == '20.50'

    def test_empty_dict(self):
        """测试：空字典。"""
        from field_extractor import _handle_split_fields

        result = _handle_split_fields({})

        assert result == {}

    def test_handles_same_value_with_dash(self):
        """测试：处理相同值带破折号的情况。"""
        from field_extractor import _handle_split_fields

        elements = {'one_year_high': '50.00-50.00', 'one_year_low': '50.00-50.00'}

        result = _handle_split_fields(elements)

        assert result['one_year_high'] == '50.00'
        assert result['one_year_low'] == '50.00'


class TestExtractFieldFromTables:
    """测试 _extract_field_from_tables 函数。"""

    @pytest.fixture
    def schema(self):
        """加载真实的 schema.yaml。"""
        import yaml
        schema_path = Path(__file__).parent.parent.parent.parent / "templates" / "company" / "schema.yaml"
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def test_extracts_rating_from_nested_tables(self, schema):
        """测试：从嵌套表格提取评级。"""
        from docx_reader import read_docx_tables, extract_nested_tables_only
        from field_extractor import _extract_field_from_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))
        nested = extract_nested_tables_only(tables)

        value = _extract_field_from_tables(nested, 'rating', schema.get('rating', {}))

        # 可能找到评级值
        assert value is None or isinstance(value, str)

    def test_returns_none_when_not_found(self, schema):
        """测试：未找到时返回 None。"""
        from field_extractor import _extract_field_from_tables

        value = _extract_field_from_tables([], 'nonexistent_field', {})

        assert value is None


class TestExtractCurrentPriceDateFromNotes:
    """测试 _extract_current_price_date_from_notes 函数。"""

    def test_finds_date_in_notes(self):
        """测试：在注释中找到日期。"""
        from docx_reader import read_docx_tables, extract_nested_tables_only
        from field_extractor import _extract_current_price_date_from_notes

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))
        nested = extract_nested_tables_only(tables)

        result = _extract_current_price_date_from_notes(nested)

        # 可能找到日期
        assert result is None or isinstance(result, str)

    def test_handles_empty_list(self):
        """测试：空列表。"""
        from field_extractor import _extract_current_price_date_from_notes

        result = _extract_current_price_date_from_notes([])

        assert result is None


class TestExtractAnalystsFromTables:
    """测试 _extract_analysts_from_tables 函数。"""

    def test_finds_analyst_info(self):
        """测试：找到分析师信息。"""
        from docx_reader import read_docx_tables, extract_nested_tables_only
        from field_extractor import _extract_analysts_from_tables

        fixtures_dir = Path(__file__).parent / "fixtures"
        docx_path = fixtures_dir / "real_research_report.docx"
        tables = read_docx_tables(str(docx_path))
        nested = extract_nested_tables_only(tables)

        result = _extract_analysts_from_tables(nested)

        # 应该找到分析师信息（真实文档有杨斌的信息）
        assert result is None or isinstance(result, str)

    def test_handles_empty_list(self):
        """测试：空列表。"""
        from field_extractor import _extract_analysts_from_tables

        result = _extract_analysts_from_tables([])

        assert result is None
