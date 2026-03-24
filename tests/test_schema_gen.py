"""测试 schema_gen.py。"""

import pytest
from pathlib import Path
from skills.template_maker.scripts.schema_gen import SchemaGenerator

def test_generate_schema_from_elements():
    """测试从 elements.yaml 生成 schema。"""
    gen = SchemaGenerator()
    elements = {
        "report_date": "21 Oct 2025",
        "company": "西锐飞机",
        "ticker": "2507.HK",
        "title": "首次覆盖：...",
        "rating": "优于大市",
        "target_price": "11.12美元",
    }

    schema = gen.generate(elements)

    # 验证结构
    assert "fields" in schema
    assert "report_date" in schema["fields"]
    assert schema["fields"]["report_date"]["description"] == "报告日期"

def test_schema_format_inference():
    """测试格式推断。"""
    gen = SchemaGenerator()
    elements = {
        "report_date": "21 Oct 2025",
        "ticker": "2507.HK",
    }

    schema = gen.generate(elements)

    # 验证格式推断
    assert "format" in schema["fields"]["report_date"]
    assert "21 Oct 2025" in schema["fields"]["report_date"]["format"]
