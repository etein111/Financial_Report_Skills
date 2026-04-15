"""测试 extractor.py 模块的函数。"""
import pytest

from extractor import extract_elements, format_extraction_prompt, merge_llm_results


class TestExtractElements:
    """测试 extract_elements 函数。"""

    def test_returns_empty_elements(self):
        """测试：返回符合 schema 结构的空 elements。"""
        schema = {
            "ticker": {"description": "股票代码", "format": "2507.HK"},
            "company": {"description": "公司名"},
            "rating": {"description": "评级"}
        }

        # 禁用 LLM fallback 以便测试纯函数提取
        result = extract_elements("draft.docx", schema, use_llm_fallback=False)

        assert "ticker" in result
        assert "company" in result
        assert "rating" in result
        assert result["ticker"] == ""
        assert result["company"] == ""
        assert result["rating"] == ""

    def test_includes_fragment_fields(self):
        """测试：包含 abstract 和 body 字段。"""
        schema = {
            "ticker": {},
            "abstract": {"type": "fragment", "scope": "首页右侧"},
            "body": {"type": "fragment", "scope": "首页之后"}
        }

        result = extract_elements("draft.docx", schema, use_llm_fallback=False)

        assert result["abstract"] == "abstract.docx"
        assert result["body"] == "body.docx"


class TestFormatExtractionPrompt:
    """测试 format_extraction_prompt 函数。"""

    def test_format_prompt_basic(self):
        """测试：基本提示词格式化。"""
        schema = {
            "ticker": {"description": "股票代码", "format": "2507.HK"},
            "company": {"description": "公司名"}
        }

        prompt = format_extraction_prompt(schema, "company")

        assert "company" in prompt
        assert "股票代码" in prompt
        assert "公司名" in prompt
        assert "2507.HK" in prompt

    def test_format_prompt_with_hints(self):
        """测试：包含格式示例。"""
        schema = {
            "ticker": {"description": "股票代码", "format": "700 HK"},
            "rating": {"description": "评级", "format": "OUTPERFORM"}
        }

        prompt = format_extraction_prompt(schema, "company")

        assert "700 HK" in prompt
        assert "OUTPERFORM" in prompt


class TestMergeLlmResults:
    """测试 merge_llm_results 函数。"""

    def test_merge_results(self):
        """测试：合并 LLM 提取结果。"""
        elements = {"ticker": "", "company": "", "rating": ""}
        llm_results = {"ticker": "2507.HK", "company": "西锐飞机"}
        schema = {"ticker": {}, "company": {}, "rating": {}}

        result = merge_llm_results(elements, llm_results, schema)

        assert result["ticker"] == "2507.HK"
        assert result["company"] == "西锐飞机"
        assert result["rating"] == ""

    def test_handle_null_values(self):
        """测试：处理 None 值。"""
        elements = {"ticker": "", "company": ""}
        llm_results = {"ticker": None, "company": "西锐飞机"}
        schema = {"ticker": {}, "company": {}}

        result = merge_llm_results(elements, llm_results, schema)

        assert result["ticker"] == ""
        assert result["company"] == "西锐飞机"

    def test_preserve_fragment_fields(self):
        """测试：保留 fragment 字段。"""
        elements = {"ticker": "", "abstract": "abstract.docx"}
        llm_results = {"ticker": "2507.HK"}
        schema = {"ticker": {}, "abstract": {}}

        result = merge_llm_results(elements, llm_results, schema)

        assert result["ticker"] == "2507.HK"
        assert result["abstract"] == "abstract.docx"
