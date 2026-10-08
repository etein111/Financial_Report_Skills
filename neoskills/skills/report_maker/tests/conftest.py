"""Pytest 配置文件。"""
import sys
from pathlib import Path
import pytest
import yaml

# 添加 scripts 目录到 Python 路径
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# 设置包路径以便支持相对导入
package_dir = Path(__file__).parent.parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

# 模块级常量
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"


@pytest.fixture
def fixtures_dir():
    """返回测试 fixtures 目录路径。"""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def company_schema():
    """加载 company schema.yaml（session 级别，只读一次）。"""
    schema_path = TEMPLATES_DIR / "company" / "schema.yaml"
    with open(schema_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def real_doc_parsed():
    """解析 real_research_report.docx（session 级别，只解析一次）。"""
    from docx_reader import read_docx_tables, flatten_table_text, extract_nested_tables_only

    docx_path = FIXTURES_DIR / "real_research_report.docx"
    tables = read_docx_tables(str(docx_path))
    nested = extract_nested_tables_only(tables)
    lines = flatten_table_text(tables)
    return {"tables": tables, "nested": nested, "lines": lines}


@pytest.fixture(scope="session")
def real_docx_path():
    """返回真实研报文档路径。"""
    return str(FIXTURES_DIR / "real_research_report.docx")
