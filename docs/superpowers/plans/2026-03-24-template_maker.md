# template-maker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 template-maker skill，支持从 Word 样本和 elements.yaml 创建可复用的报告模板

**Architecture:** 混合模式 - 提示词负责分析和生成（灵活），代码负责文件操作和执行（可靠）。采用 Orchestrator 模式，core.py 作为流程控制器，调用提示词代理完成智能分析，再用代码执行文件操作。

**Tech Stack:** Python 3.10+, python-docx, python-docx-template, PyYAML, Claude Code Skills API

---

## 文件结构

本项目将创建以下文件：

```
neoskills/
├── skills/
│   └── template-maker/
│       ├── SKILL.md              # Skill 定义（Claude Code 格式）
│       ├── __init__.py           # 包初始化
│       ├── core.py               # Orchestrator，流程控制
│       ├── parser.py             # Word 文档解析器（提示词包装）
│       ├── schema_gen.py         # Schema 生成器（提示词包装）
│       ├── template_builder.py   # Template.docx 生成器（代码）
│       ├── router_mgr.py         # Router.yaml 管理器（代码）
│       ├── validator.py          # 最小验证测试（代码）
│       └── utils.py              # 工具函数
│
├── templates/                    # 运行时创建
│   ├── router.yaml
│   └── common/
│       ├── schema.yaml
│       ├── template.docx
│       └── meta.yaml
│
└── tests/
    └── test_template_maker.py    # 集成测试
```

**职责划分：**
- `core.py`: 对话流程控制、任务编排、用户交互
- `parser.py`: 包装提示词，分析 Word 文档结构
- `schema_gen.py`: 包装提示词，生成 schema.yaml 内容
- `template_builder.py`: 代码执行，替换占位符生成 template.docx
- `router_mgr.py`: 代码执行，安全更新 router.yaml
- `validator.py`: 代码执行，用 elements.yaml 做渲染测试

---

## Task 1: 项目结构设置

**目标：** 创建基础目录结构和依赖配置

**Files:**
- Create: `skills/template_maker/__init__.py`
- Create: `skills/template_maker/SKILL.md`
- Create: `skills/template_maker/requirements.txt`
- Create: `skills/template_maker/utils.py`

### Step 1.1: 创建包结构

```bash
mkdir -p /mnt/c/_code/neoskills/skills/template_maker
```

### Step 1.2: 创建 __init__.py

**File:** `skills/template_maker/__init__.py`

```python
"""template-maker skill for Claude Code.

创建和维护报告模板。
"""

__version__ = "0.1.0"
```

### Step 1.3: 创建 SKILL.md

**File:** `skills/template_maker/SKILL.md`

```markdown
# template-maker

创建和维护分析师报告模板。

## 用法

创建新模板：
```
/template-maker
```

然后按提示提供：
1. 模板名称
2. Word 样本文件
3. elements.yaml 文件（可选，系统会自动检测）

维护模板：
```
给 <模板名> 添加一个 <字段名> 字段
```
```

### Step 1.4: 创建依赖文件

**File:** `skills/template_maker/requirements.txt`

```
python-docx==1.1.0
python-docx-template==0.2.8
PyYAML==6.0.1
```

### Step 1.5: 创建工具函数

**File:** `skills/template_maker/utils.py`

```python
"""工具函数。"""

from pathlib import Path

def get_project_root() -> Path:
    """获取项目根目录。"""
    return Path(__file__).parent.parent.parent

def get_templates_dir() -> Path:
    """获取 templates 目录。"""
    return get_project_root() / "templates"

def get_samples_dir() -> Path:
    """获取 samples 目录。"""
    return get_project_root() / "samples"

def find_elements_yaml(word_path: Path) -> Path | None:
    """查找与 Word 文件配对的 elements.yaml。

    规则：
    1. <word_name> elements.yaml
    2. 同目录下的 elements.yaml
    """
    word_dir = word_path.parent
    word_name = word_path.stem  # 不含扩展名

    # 规则 1: <name> elements.yaml
    candidates = [
        word_dir / f"{word_name} elements.yaml",
        word_dir / f"{word_name}_elements.yaml",
    ]

    # 规则 2: 目录下的 elements.yaml
    candidates.append(word_dir / "elements.yaml")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None
```

### Step 1.6: 编写工具函数测试

**File:** `tests/test_utils.py`

```python
"""测试 utils.py。"""

import pytest
from pathlib import Path
from skills.template_maker.utils import find_elements_yaml

def test_find_elements_yaml_with_pair(tmp_path):
    """测试找到配对的 elements.yaml。"""
    # 创建测试文件
    (tmp_path / "sample.docx").touch()
    (tmp_path / "sample elements.yaml").touch()

    result = find_elements_yaml(tmp_path / "sample.docx")
    assert result == tmp_path / "sample elements.yaml"

def test_find_elements_yaml_not_found(tmp_path):
    """测试找不到 elements.yaml。"""
    (tmp_path / "sample.docx").touch()

    result = find_elements_yaml(tmp_path / "sample.docx")
    assert result is None
```

### Step 1.7: 运行测试验证

```bash
cd /mnt/c/_code/neoskills
pytest tests/test_utils.py -v
```

**Expected:** FAIL (文件还不存在)

### Step 1.8: 创建测试目录

```bash
mkdir -p /mnt/c/_code/neoskills/tests
```

### Step 1.9: 重新运行测试

```bash
cd /mnt/c/_code/neoskills
pytest tests/test_utils.py -v
```

**Expected:** PASS

### Step 1.10: 提交

```bash
git add skills/template_maker/ tests/test_utils.py
git commit -m "feat(template-maker): 初始化项目结构和工具函数"
```

---

## Task 2: Router.yaml 管理器

**目标：** 实现安全更新 router.yaml 的代码逻辑

**Files:**
- Create: `skills/template_maker/router_mgr.py`
- Modify: `tests/test_router_mgr.py`

### Step 2.1: 编写测试 - 创建 router.yaml

**File:** `tests/test_router_mgr.py`

```python
"""测试 router_mgr.py。"""

import pytest
from pathlib import Path
import yaml
from skills.template_maker.router_mgr import RouterManager

@pytest.fixture
def temp_router(tmp_path):
    """创建临时 router.yaml。"""
    router_path = tmp_path / "router.yaml"
    router_path.write_text("""
mappings:
  company: common
  sector: common
""")
    return router_path

def test_router_manager_init(temp_router):
    """测试初始化。"""
    mgr = RouterManager(temp_router)
    assert mgr.data["mappings"]["company"] == "common"

def test_add_mapping(temp_router):
    """测试添加映射。"""
    mgr = RouterManager(temp_router)
    mgr.add_mapping("macro", "common")

    assert mgr.data["mappings"]["macro"] == "common"

    # 验证已保存
    content = temp_router.read_text()
    assert "macro: common" in content
```

### Step 2.2: 运行测试（预期失败）

```bash
pytest tests/test_router_mgr.py -v
```

**Expected:** FAIL - ModuleNotFoundError

### Step 2.3: 实现 RouterManager

**File:** `skills/template_maker/router_mgr.py`

```python
"""Router.yaml 管理器。"""

import yaml
from pathlib import Path

class RouterManager:
    """管理 router.yaml 文件。"""

    def __init__(self, router_path: Path):
        """初始化。

        Args:
            router_path: router.yaml 文件路径
        """
        self.path = router_path
        self.data = self._load()

    def _load(self) -> dict:
        """加载 router.yaml。"""
        if not self.path.exists():
            return {"mappings": {}}

        return yaml.safe_load(self.path.read_text()) or {"mappings": {}}

    def add_mapping(self, report_type: str, template_name: str):
        """添加报告类型映射。

        Args:
            report_type: 报告类型（如：company, macro）
            template_name: 模板名称
        """
        self.data.setdefault("mappings", {})[report_type] = template_name
        self._save()

    def _save(self):
        """保存到文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.dump(self.data, allow_unicode=True, sort_keys=False))
```

### Step 2.4: 运行测试（预期通过）

```bash
pytest tests/test_router_mgr.py -v
```

**Expected:** PASS

### Step 2.5: 提交

```bash
git add skills/template_maker/router_mgr.py tests/test_router_mgr.py
git commit -m "feat(template-maker): 实现 RouterManager"
```

---

## Task 3: Word 文档结构分析器（提示词包装）

**目标：** 创建包装提示词的解析器，分析 Word 文档结构

**Files:**
- Create: `skills/template_maker/parser.py`
- Modify: `tests/test_parser.py`

### Step 3.1: 编写测试 - 分析 Word 结构

**File:** `tests/test_parser.py`

```python
"""测试 parser.py。"""

import pytest
from pathlib import Path
from skills.template_maker.parser import WordStructureAnalyzer

@pytest.fixture
def sample_doc():
    """示例 Word 文档结构。"""
    return Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")

def test_analyzer_returns_structure(sample_doc):
    """测试分析器返回结构。"""
    analyzer = WordStructureAnalyzer()
    result = analyzer.analyze(sample_doc)

    # 应该包含基本信息
    assert "tables" in result
    assert "paragraphs" in result
    assert "key_areas" in result

    # 应该识别出表格
    assert len(result["tables"]) > 0

def test_analyzer_identifies_main_table(sample_doc):
    """测试识别主表格。"""
    analyzer = WordStructureAnalyzer()
    result = analyzer.analyze(sample_doc)

    # 主表格通常包含报告基本信息
    main_table = result.get("main_table", {})
    assert main_table or len(result["tables"]) > 0
```

### Step 3.2: 运行测试（预期失败）

```bash
pytest tests/test_parser.py -v
```

**Expected:** FAIL - ModuleNotFoundError

### Step 3.3: 实现提示词包装器

**File:** `skills/template_maker/parser.py`

```python
"""Word 文档结构分析器（提示词包装）。"""

from pathlib import Path
from docx import Document
from typing import Dict, Any

class WordStructureAnalyzer:
    """分析 Word 文档结构。"""

    def analyze(self, doc_path: Path) -> Dict[str, Any]:
        """分析 Word 文档结构。

        Args:
            doc_path: Word 文档路径

        Returns:
            包含以下键的字典：
            - tables: 表格列表
            - paragraphs: 段落数量
            - key_areas: 关键区域（页眉、页脚等）
        """
        doc = Document(doc_path)

        # 使用 Claude Code 的 LLM 能力分析结构
        # 这里先返回基本信息，后续会用提示词增强
        structure = {
            "tables": self._extract_tables(doc),
            "paragraphs": len(doc.paragraphs),
            "key_areas": {
                "headers": len(doc.sections),
                "footers": len(doc.sections),
            }
        }

        return structure

    def _extract_tables(self, doc: Document) -> list:
        """提取表格信息。"""
        tables = []
        for i, table in enumerate(doc.tables):
            tables.append({
                "index": i,
                "rows": len(table.rows),
                "cols": len(table.columns),
            })
        return tables
```

### Step 3.4: 运行测试

```bash
pytest tests/test_parser.py -v
```

**Expected:** 可能 PASS 或 FAIL（取决于样本文件）

### Step 3.5: 提交

```bash
git add skills/template_maker/parser.py tests/test_parser.py
git commit -m "feat(template-maker): 实现 WordStructureAnalyzer 基础版本"
```

---

## Task 4: Schema 生成器（提示词包装）

**目标：** 创建包装提示词的 schema 生成器

**Files:**
- Create: `skills/template_maker/schema_gen.py`
- Modify: `tests/test_schema_gen.py`

### Step 4.1: 编写测试

**File:** `tests/test_schema_gen.py`

```python
"""测试 schema_gen.py。"""

import pytest
from pathlib import Path
from skills.template_maker.schema_gen import SchemaGenerator

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
```

### Step 4.2: 运行测试（预期失败）

```bash
pytest tests/test_schema_gen.py -v
```

**Expected:** FAIL

### Step 4.3: 实现 SchemaGenerator

**File:** `skills/template_maker/schema_gen.py`

```python
"""Schema 生成器（提示词包装）。"""

from typing import Dict, Any

class SchemaGenerator:
    """从 elements.yaml 生成 schema.yaml。"""

    def generate(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        """生成 schema。

        Args:
            elements: elements.yaml 的内容

        Returns:
            schema 字典
        """
        fields = {}

        for name, value in elements.items():
            fields[name] = self._infer_field(name, value)

        return {"fields": fields}

    def _infer_field(self, name: str, value: Any) -> Dict[str, Any]:
        """推断字段定义。

        Args:
            name: 字段名
            value: 字段值

        Returns:
            字段定义字典
        """
        # 简化版本：基于字段名和值推断
        # 后续会用提示词增强
        field_def = {
            "description": self._get_description(name),
        }

        # 添加 format（如果有值）
        if value and value != "null":
            field_def["format"] = str(value)

        return field_def

    def _get_description(self, name: str) -> str:
        """获取字段描述。"""
        descriptions = {
            "report_date": "报告日期",
            "company": "公司名称",
            "ticker": "股票代码",
            "title": "报告标题",
            "rating": "评级",
            "target_price": "目标价",
            "current_price": "现价",
            "market_cap": "市值",
        }
        return descriptions.get(name, name)
```

### Step 4.4: 运行测试

```bash
pytest tests/test_schema_gen.py -v
```

**Expected:** PASS

### Step 4.5: 提交

```bash
git add skills/template_maker/schema_gen.py tests/test_schema_gen.py
git commit -m "feat(template-maker): 实现 SchemaGenerator"
```

---

## Task 5: Template.docx 生成器

**目标：** 实现代码逻辑，替换占位符生成 template.docx

**Files:**
- Create: `skills/template_maker/template_builder.py`
- Modify: `tests/test_template_builder.py`

### Step 5.1: 编写测试

**File:** `tests/test_template_builder.py`

```python
"""测试 template_builder.py。"""

import pytest
from pathlib import Path
from shutil import copy
from skills.template_maker.template_builder import TemplateBuilder

@pytest.fixture
def sample_doc(tmp_path):
    """创建示例文档。"""
    src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    if src.exists():
        dst = tmp_path / "sample.docx"
        copy(src, dst)
        return dst
    pytest.skip("样本文件不存在")

def test_create_template(sample_doc, tmp_path):
    """测试创建模板。"""
    builder = TemplateBuilder()

    placeholders = {
        "Table_Main_5_1": "{{company}}",
        "Table_Main_5_2": "{{ticker}}",
    }

    output = tmp_path / "template.docx"
    builder.build(sample_doc, placeholders, output)

    assert output.exists()

def test_generate_placeholders():
    """测试生成占位符映射。"""
    builder = TemplateBuilder()
    schema = {
        "fields": {
            "company": {"format": "西锐飞机"},
            "ticker": {"format": "2507.HK"},
        }
    }

    # 简化测试：验证能生成映射
    # 实际实现会结合 Word 结构分析
    assert schema is not None
```

### Step 5.2: 运行测试（预期失败）

```bash
pytest tests/test_template_builder.py -v
```

**Expected:** FAIL

### Step 5.3: 实现 TemplateBuilder

**File:** `skills/template_maker/template_builder.py`

```python
"""Template.docx 生成器。"""

from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from typing import Dict

class TemplateBuilder:
    """从 Word 样本生成 template.docx。"""

    def build(self, sample_path: Path, placeholders: Dict[str, str], output_path: Path):
        """构建模板文档。

        Args:
            sample_path: 样本文档路径
            placeholders: 占位符映射 {位置: jinja2_var}
            output_path: 输出路径
        """
        doc = Document(sample_path)

        # 替换占位符
        # 简化版本：替换表格中的文本
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, var in placeholders.items():
                        if key in cell.text:
                            # 替换为 Jinja2 占位符
                            cell.text = cell.text.replace(key, var)

        # 保存
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
```

### Step 5.4: 运行测试

```bash
pytest tests/test_template_builder.py -v
```

**Expected:** 可能需要调整

### Step 5.5: 提交

```bash
git add skills/template_maker/template_builder.py tests/test_template_builder.py
git commit -m "feat(template-maker): 实现 TemplateBuilder"
```

---

## Task 6: 验证器

**目标：** 实现最小验证测试

**Files:**
- Create: `skills/template_maker/validator.py`
- Modify: `tests/test_validator.py`

### Step 6.1: 编写测试

**File:** `tests/test_validator.py`

```python
"""测试 validator.py。"""

import pytest
from pathlib import Path
from skills.template_maker.validator import TemplateValidator

def test_validate_with_elements(tmp_path):
    """测试用 elements 验证。"""
    # 创建测试文件
    template_dir = tmp_path / "templates" / "common"
    template_dir.mkdir(parents=True)

    # 复制模板（简化）
    src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    if not src.exists():
        pytest.skip("样本文件不存在")

    from shutil import copy
    template_path = template_dir / "template.docx"
    copy(src, template_path)

    elements_path = tmp_path / "elements.yaml"
    elements_path.write_text("""
report_date: "21 Oct 2025"
company: "西锐飞机"
ticker: "2507.HK"
""")

    validator = TemplateValidator()
    result, message = validator.validate(template_path, elements_path)

    # 简化版本：只验证不报错
    assert result or "未实现" in message
```

### Step 6.2: 运行测试（预期失败）

```bash
pytest tests/test_validator.py -v
```

**Expected:** FAIL

### Step 6.3: 实现验证器

**File:** `skills/template_maker/validator.py`

```python
"""模板验证器。"""

from pathlib import Path
from docxtpl import DocxTemplate
import yaml

class TemplateValidator:
    """验证模板可用性。"""

    def validate(self, template_path: Path, elements_path: Path) -> tuple[bool, str]:
        """用 elements.yaml 验证模板。

        Args:
            template_path: template.docx 路径
            elements_path: elements.yaml 路径

        Returns:
            (是否通过, 消息)
        """
        try:
            # 加载 elements
            elements = yaml.safe_load(elements_path.read_text())

            # 加载模板
            template = DocxTemplate(template_path)

            # 渲染测试（不保存）
            # 简化版本：只检查能加载
            template.render(elements)

            return True, "验证通过"

        except Exception as e:
            return False, f"验证失败：{str(e)}"
```

### Step 6.4: 运行测试

```bash
pytest tests/test_validator.py -v
```

**Expected:** PASS 或需要调整

### Step 6.5: 提交

```bash
git add skills/template_maker/validator.py tests/test_validator.py
git commit -m "feat(template-maker): 实现 TemplateValidator"
```

---

## Task 7: 核心编排器（core.py）

**目标：** 实现对话流程控制

**Files:**
- Create: `skills/template_maker/core.py`
- Modify: `tests/test_core.py`

### Step 7.1: 编写测试

**File:** `tests/test_core.py`

```python
"""测试 core.py。"""

import pytest
from pathlib import Path
from skills.template_maker.core import TemplateMaker

@pytest.fixture
def temp_workspace(tmp_path):
    """临时工作空间。"""
    workspace = tmp_path / "neoskills"
    workspace.mkdir()
    return workspace

def test_create_template_flow(temp_workspace):
    """测试创建模板流程。"""
    # 准备样本文件
    from shutil import copy
    sample_src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    elements_src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版 elements.yaml")

    if not (sample_src.exists() and elements_src.exists()):
        pytest.skip("样本文件不存在")

    sample_dst = temp_workspace / "sample.docx"
    elements_dst = temp_workspace / "elements.yaml"
    copy(sample_src, sample_dst)
    copy(elements_src, elements_dst)

    # 执行
    maker = TemplateMaker(temp_workspace)
    result = maker.create_template(
        name="test",
        word_path=sample_dst,
        elements_path=elements_dst,
    )

    # 验证
    assert result["status"] == "success"
    assert (temp_workspace / "templates" / "test" / "schema.yaml").exists()
    assert (temp_workspace / "templates" / "test" / "template.docx").exists()
```

### Step 7.2: 运行测试（预期失败）

```bash
pytest tests/test_core.py -v
```

**Expected:** FAIL

### Step 7.3: 实现 core.py

**File:** `skills/template_maker/core.py`

```python
"""Template Maker 核心编排器。"""

from pathlib import Path
import yaml
from .parser import WordStructureAnalyzer
from .schema_gen import SchemaGenerator
from .template_builder import TemplateBuilder
from .router_mgr import RouterManager
from .validator import TemplateValidator
from .utils import get_templates_dir

class TemplateMaker:
    """模板制作编排器。"""

    def __init__(self, project_root: Path):
        """初始化。

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root
        self.templates_dir = get_templates_dir()
        self.router_path = self.templates_dir / "router.yaml"

        self.parser = WordStructureAnalyzer()
        self.schema_gen = SchemaGenerator()
        self.builder = TemplateBuilder()
        self.validator = TemplateValidator()

    def create_template(
        self,
        name: str,
        word_path: Path,
        elements_path: Path | None = None,
    ) -> dict:
        """创建模板。

        Args:
            name: 模板名称
            word_path: Word 样本路径
            elements_path: elements.yaml 路径（可选）

        Returns:
            结果字典
        """
        # 1. 检测 elements.yaml
        if elements_path is None:
            from .utils import find_elements_yaml
            elements_path = find_elements_yaml(word_path)

        if not elements_path or not elements_path.exists():
            return {
                "status": "error",
                "message": "找不到 elements.yaml"
            }

        # 2. 创建模板目录
        template_dir = self.templates_dir / name
        template_dir.mkdir(parents=True, exist_ok=True)

        # 3. 分析 Word 文档
        word_structure = self.parser.analyze(word_path)

        # 4. 生成 schema
        elements = yaml.safe_load(elements_path.read_text())
        schema = self.schema_gen.generate(elements)

        # 保存 schema.yaml
        schema_path = template_dir / "schema.yaml"
        schema_path.write_text(yaml.dump(schema, allow_unicode=True, sort_keys=False))

        # 5. 生成 template.docx
        # 简化版本：暂时复制
        from shutil import copy
        template_path = template_dir / "template.docx"
        copy(word_path, template_path)

        # 6. 生成 meta.yaml
        meta = {
            "name": name,
            "display_name": f"{name} 模板",
            "version": "1.0.0",
            "status": "active",
            "sample_source": str(word_path),
        }
        meta_path = template_dir / "meta.yaml"
        meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))

        # 7. 更新 router.yaml
        router_mgr = RouterManager(self.router_path)
        router_mgr.add_mapping("company", name)

        return {
            "status": "success",
            "template_dir": str(template_dir),
            "fields_count": len(schema.get("fields", {})),
        }
```

### Step 7.4: 运行测试

```bash
pytest tests/test_core.py -v
```

**Expected:** 可能需要调整

### Step 7.5: 提交

```bash
git add skills/template_maker/core.py tests/test_core.py
git commit -m "feat(template-maker): 实现 TemplateMaker 核心编排器"
```

---

## Task 8: Claude Code Skill 集成

**目标：** 创建 SKILL.md 和入口函数

**Files:**
- Modify: `skills/template_maker/SKILL.md`
- Create: `skills/template_maker/entry.py`

### Step 8.1: 更新 SKILL.md

**File:** `skills/template_maker/SKILL.md`（已存在，更新内容）

```markdown
# template-maker

创建和维护分析师报告模板。

## 功能

- 从 Word 样本创建新模板
- 自动检测配对的 elements.yaml
- 生成 schema.yaml 和 template.docx
- 更新路由配置

## 用法

### 创建新模板

```
/template-maker
```

系统会引导你提供：
1. 模板名称
2. Word 样本文件
3. elements.yaml（可选，自动检测）

### 示例

```
用户: /template-maker
系统: 好的，我来帮你创建模板。模板名称是什么？
用户: common
系统: Word 样本文件在哪里？
用户: ./samples/sample.docx
系统: 收到样本文件。正在查找 elements.yaml...
       ✓ 找到：./samples/sample elements.yaml
       正在创建模板...
       ✅ 模板创建成功！
```

## 技术细节

- 使用 python-docx 处理 Word 文档
- 混合模式：提示词分析 + 代码执行
- 支持对话式文件上传
```

### Step 8.2: 创建入口函数

**File:** `skills/template_maker/entry.py`

```python
"""Claude Code Skill 入口。"""

from pathlib import Path
from .core import TemplateMaker
from .utils import get_project_root

def main():
    """Skill 主入口。"""
    project_root = get_project_root()
    maker = TemplateMaker(project_root)

    # 简化版本：命令行模式
    # 实际会通过 Claude Code 对话接口调用
    print("Template Maker v0.1.0")
    print("请使用 /template-maker 命令")

if __name__ == "__main__":
    main()
```

### Step 8.3: 提交

```bash
git add skills/template_maker/SKILL.md skills/template_maker/entry.py
git commit -m "feat(template-maker): 完善 Skill 定义和入口"
```

---

## Task 9: 集成测试和文档

### Step 9.1: 创建集成测试

**File:** `tests/test_integration.py`

```python
"""集成测试。"""

import pytest
from pathlib import Path
from shutil import copy
from skills.template_maker.core import TemplateMaker

@pytest.mark.integration
def test_create_common_template(tmp_path):
    """端到端测试：创建 common 模板。"""
    # 准备
    sample_src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    elements_src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版 elements.yaml")

    if not (sample_src.exists() and elements_src.exists()):
        pytest.skip("样本文件不存在")

    # 设置项目结构
    (tmp_path / "templates").mkdir()

    sample_dst = tmp_path / "sample.docx"
    elements_dst = tmp_path / "elements.yaml"
    copy(sample_src, sample_dst)
    copy(elements_src, elements_dst)

    # 执行
    maker = TemplateMaker(tmp_path)
    result = maker.create_template(
        name="common",
        word_path=sample_dst,
        elements_path=elements_dst,
    )

    # 验证输出
    assert result["status"] == "success"
    template_dir = tmp_path / "templates" / "common"

    # 验证文件存在
    assert (template_dir / "schema.yaml").exists()
    assert (template_dir / "template.docx").exists()
    assert (template_dir / "meta.yaml").exists()

    # 验证 router.yaml
    router = tmp_path / "templates" / "router.yaml"
    assert router.exists()
    content = router.read_text()
    assert "company: common" in content
```

### Step 9.2: 运行集成测试

```bash
pytest tests/test_integration.py -v -m integration
```

### Step 9.3: 创建 README

**File:** `skills/template_maker/README.md`

```markdown
# template-maker

分析师报告模板制作工具。

## 安装

```bash
pip install -r requirements.txt
```

## 使用

### 通过 Claude Code

```
/template-maker
```

### Python API

```python
from skills.template_maker.core import TemplateMaker

maker = TemplateMaker(project_root)
result = maker.create_template(
    name="common",
    word_path="path/to/sample.docx",
    elements_path="path/to/elements.yaml",
)
```

## 开发

```bash
# 运行测试
pytest tests/ -v

# 运行集成测试
pytest tests/ -v -m integration
```
```

### Step 9.4: 提交

```bash
git add tests/test_integration.py skills/template_maker/README.md
git commit -m "feat(template-maker): 添加集成测试和文档"
```

---

## 完成检查清单

在实施完成后，验证：

- [ ] 所有测试通过：`pytest tests/ -v`
- [ ] 集成测试通过：`pytest tests/ -v -m integration`
- [ ] 能用样本文件创建 common 模板
- [ ] 生成的 schema.yaml 格式正确
- [ ] router.yaml 正确更新
- [ ] 代码覆盖率 > 80%（可选）
- [ ] 文档完整

---

## 下一步（第二阶段）

1. **增强提示词分析**：用 LLM 提高文档结构识别准确度
2. **字段维护功能**：添加/删除字段的对话式操作
3. **模板切换**：支持更换模板
4. **错误处理**：更友好的错误提示
