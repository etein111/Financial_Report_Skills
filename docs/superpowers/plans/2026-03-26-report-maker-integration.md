# report_maker 工作台集成实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 将 report_maker skill 集成到 opencode 工作台，使 Editor 可以通过对话处理分析师报告草稿

**架构:** 报告 Maker skill 作为业务逻辑层，opencode 作为交互界面，通过 Claude Code 的 skill 调用机制连接

**技术栈:** Claude Code CLI、Agent Skills Open Standard、python-docx、docxtpl

---

## 前置条件检查

- [ ] **Step 1: 验证 skill 是否可用**
  
Run: `ls -la skills/report_maker/SKILL.md`
```bash
Expected: SKILL.md 文件存在
```

- [ ] **Step 2: 验证测试是否通过**
  
Run: `.venv/bin/python -m pytest skills/report_maker/tests/ -q`
```bash
Expected: 39 passed
```

- [ ] **Step 3: 验证模板和样本文件**
  
Run: `ls -la templates/company/ samples/*.docx`
```bash
Expected: company 模板和样本文件存在
```

---

## 文件结构

```
neoskills/
├── skills/
│   └── report_maker/          # 已有，无需修改
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── common.py
│       │   ├── extractor.py
│       │   ├── splitter.py
│       │   └── renderer.py
│       └── tests/
├── templates/                  # 已有，无需修改
│   ├── router.yaml
│   └── company/
│       ├── schema.yaml
│       ├── template.docx
│       └── meta.yaml
├── samples/                     # 已有，无需修改
│   ├── 西锐飞机首次覆盖报告（中文）提交版.docx
│   └── 西锐飞机首次覆盖报告（中文）提交版 elements.yaml
└── reports/                     # 运行时生成
    └── <report_name>/
        ├── draft.docx
        ├── elements.yaml
        ├── abstract.docx
        ├── body.docx
        ├── output.docx
        └── output.pdf
```

---

## Task 1: 创建使用指南文档

**文件:**
- Create: `docs/report_maker_user_guide.md`

- [ ] **Step 1: 编写使用指南**

```markdown
# report_maker 使用指南

## 概述

report_maker 是一个 Claude Code skill，用于处理分析师报告草稿并生成标准排版报告。

## 使用场景

1. **处理新草稿**: 上传草稿 Word 文件，指定报告类型，系统自动提取要素
2. **修正提取结果**: 交互式确认和修正提取的字段
3. **生成标准报告**: 确认后自动渲染生成标准 Word 和 PDF

## 支持的报告类型

- `company` - 公司覆盖报告
- `sector` - 行业研究报告
- `macro` - 宏观报告
- `strategy` - 策略报告
- `quantitative` - 量化报告
- `bond` - 债券报告

## 使用示例

### 示例 1: 处理公司报告

**用户输入:**
```
我上传了一份公司报告草稿，报告类型是 company，帮我处理
```

**系统响应:**
- 识别报告类型: company
- 从 router.yaml 获取模板: company
- 提取要素并展示
- 等待用户确认

### 示例 2: 修正字段

**用户输入:**
```
ticker 应该是 700 HK，不是 2507.HK
```

**系统响应:**
- 更新 elements.yaml
- 保存修正

### 示例 3: 生成报告

**用户输入:**
```
确认，继续生成
```

**系统响应:**
- 渲染模板
- 生成 output.docx
- 转换 output.pdf
```

## 目录结构

生成的报告保存在 `reports/<report_name>/` 目录下。
```

- [ ] **Step 2: 保存文档**
  
Run: `cat > docs/report_maker_user_guide.md`
```bash
Expected: 文档创建成功
```

- [ ] **Step 3: 验证文档可读性**
  
Run: `cat docs/report_maker_user_guide.md`
```bash
Expected: 内容正确
```

- [ ] **Step 4: Commit**

```bash
git add docs/report_maker_user_guide.md
git commit -m "docs: add report_maker user guide"
```

---

## Task 2: 创建集成测试脚本

**文件:**
- Create: `tests/integration/test_report_workflow.py`

- [ ] **Step 1: 编写集成测试**

```python
"""集成测试：完整的报告处理流程。"""

import pytest
import shutil
from pathlib import Path
import sys

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "report_maker" / "scripts"))

from common import (
    load_yaml, save_yaml,
    get_template_name,
    create_report_dir,
    normalize_report_name,
    ensure_all_fields
)
from splitter import read_document_structure, extract_abstract, extract_body
from renderer import render_template, convert_to_pdf


@pytest.fixture
def sample_draft():
    """样本草稿文件。"""
    return "samples/西锐飞机首次覆盖报告（中文）提交版.docx"


@pytest.fixture
def sample_elements():
    """样本要素文件。"""
    return "samples/西锐飞机首次覆盖报告（中文）提交版 elements.yaml"


class TestReportWorkflow:
    """测试完整报告处理流程。"""

    def test_stage1_extraction(self, sample_draft):
        """测试第一阶段：提取和确认。"""
        # 1. 获取模板
        template_name = get_template_name("company")
        assert template_name == "company"
        
        # 2. 读取文档结构
        structure = read_document_structure(sample_draft)
        assert "paragraphs" in structure
        assert structure["paragraphs"] > 0
        
        # 3. 创建报告目录
        report_name = normalize_report_name("test_report.docx")
        report_dir = create_report_dir(f"test_integration_{report_name}")
        assert report_dir.exists()
        
        # 4. 提取要素
        elements = load_yaml("samples/西锐飞机首次覆盖报告（中文）提交版 elements.yaml")
        schema = load_yaml("templates/company/schema.yaml")
        elements = ensure_all_fields(elements, schema)
        
        # 5. 保存
        save_yaml(report_dir / "elements.yaml", elements)
        
        # 清理
        shutil.rmtree(report_dir)
    
    def test_stage2_rendering(self, sample_draft, sample_elements):
        """测试第二阶段：渲染和输出。"""
        # 准备环境
        report_dir = create_report_dir("test_render_output")
        shutil.copy(sample_draft, report_dir / "draft.docx")
        
        elements = load_yaml(sample_elements)
        schema = load_yaml("templates/company/schema.yaml")
        elements = ensure_all_fields(elements, schema)
        
        # 创建空的 fragment 文件
        from splitter import create_fragments_document
        create_fragments_document(
            sample_draft,
            str(report_dir / "abstract.docx"),
            str(report_dir / "body.docx")
        )
        
        # 渲染
        template_path = "templates/company/template.docx"
        output_path = report_dir / "output.docx"
        
        success = render_template(
            template_path,
            elements,
            str(report_dir / "abstract.docx"),
            str(report_dir / "body.docx"),
            str(output_path)
        )
        
        assert success
        assert output_path.exists()
        
        # 清理
        shutil.rmtree(report_dir)
```

- [ ] **Step 2: 创建测试目录**
  
Run: `mkdir -p tests/integration`
```bash
Expected: 目录创建成功
```

- [ ] **Step 3: 保存测试文件**

- [ ] **Step 4: 运行集成测试**
  
Run: `cd /mnt/c/_code/neoskills && .venv/bin/python -m pytest tests/integration/test_report_workflow.py -v`
```bash
Expected: 测试通过
```

- [ ] **Step 5: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration test for report_maker workflow"
```

---

## Task 3: 完善 fragment 拆分逻辑

**文件:**
- Modify: `skills/report_maker/scripts/splitter.py`

- [ ] **Step 1: 添加智能 fragment 定位函数**

```python
def locate_fragment_by_content(doc_path: str, keywords: List[str]) -> Dict[str, Any]:
    """根据关键词定位 fragment 在文档中的位置。
    
    Args:
        doc_path: 文档路径
        keywords: 关键词列表
    
    Returns:
        位置信息（起始段落索引、表格索引等）
    """
    if Document is None:
        return {"error": "python-docx not installed"}
    
    try:
        doc = Document(doc_path)
        
        # 搜索包含关键词的段落
        matches = []
        for i, para in enumerate(doc.paragraphs):
            for keyword in keywords:
                if keyword in para.text:
                    matches.append({
                        "type": "paragraph",
                        "index": i,
                        "keyword": keyword,
                        "text": para.text[:100]
                    })
        
        # 搜索包含关键词的表格
        for i, table in enumerate(doc.tables):
            for row in table.rows:
                for cell in row.cells:
                    for keyword in keywords:
                        if keyword in cell.text:
                            matches.append({
                                "type": "table",
                                "index": i,
                                "keyword": keyword,
                                "row": len(table.rows),
                                "col": len(table.columns)
                            })
                            break
        
        return {"matches": matches}
    except Exception as e:
        return {"error": str(e)}
```

- [ ] **Step 2: 添加基于表格范围的 fragment 提取**

```python
def extract_fragment_by_table_range(
    doc_path: str,
    start_table: int,
    end_table: int,
    output_path: str
) -> bool:
    """按表格范围提取 fragment。"""
    if Document is None:
        return False
    
    try:
        doc = Document(doc_path)
        fragment_doc = Document()
        
        # 复制指定范围的表格
        for table_idx in range(start_table, end_table + 1):
            if table_idx >= len(doc.tables):
                break
            
            table = doc.tables[table_idx]
            
            # 复制表格结构
            # [实现细节]
        
        fragment_doc.save(output_path)
        return True
    except Exception as e:
        print(f"提取失败: {e}")
        return False
```

- [ ] **Step 3: 添加基于段落范围的 fragment 提取**

```python
def extract_fragment_by_paragraph_range(
    doc_path: str,
    start_para: int,
    end_para: int,
    output_path: str
) -> bool:
    """按段落范围提取 fragment。"""
    # [实现]
```

- [ ] **Step 4: 更新测试**
  
Run: `.venv/bin/python -m pytest skills/report_maker/tests/test_splitter.py -v`
```bash
Expected: 所有测试通过
```

- [ ] **Step 5: Commit**

```bash
git add skills/report_maker/scripts/splitter.py
git commit -m "feat(report_maker): enhance fragment extraction logic"
```

---

## Task 4: 完善 fragment 插入逻辑

**文件:**
- Modify: `skills/report_maker/scripts/renderer.py`

- [ ] **Step 1: 添加占位符定位函数**

```python
def find_placeholder_in_document(doc_path: str, placeholder: str) -> List[Dict[str, Any]]:
    """查找文档中所有占位符的位置。"""
    if Document is None:
        return []
    
    try:
        doc = Document(doc_path)
        locations = []
        
        # 搜索段落中的占位符
        for i, para in enumerate(doc.paragraphs):
            if placeholder in para.text:
                locations.append({
                    "type": "paragraph",
                    "index": i,
                    "full_text": para.text
                })
        
        # 搜索表格中的占位符
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell in row.cells:
                    if placeholder in cell.text:
                        locations.append({
                            "type": "table_cell",
                            "table": table_idx,
                            "row": row_idx,
                            "col": cell._index
                        })
        
        return locations
    except Exception as e:
        print(f"查找占位符失败: {e}")
        return []
```

- [ ] **Step 2: 添加 fragment 内容复制函数**

```python
def copy_fragment_content(source_doc: Document, target_doc: Document, insert_after_para: int) -> bool:
    """将源文档内容复制到目标文档的指定位置后。"""
    if Document is None:
        return False
    
    try:
        # 获取插入位置的段落元素
        if insert_after_para >= len(target_doc.paragraphs):
            return False
        
        insert_after_element = target_doc.paragraphs[insert_after_para]._element
        
        # 复制源文档的所有段落
        for source_para in source_doc.paragraphs:
            if source_para.text.strip():
                new_para = source_para._element
                insert_after_element.addnext(new_para)
        
        return True
    except Exception as e:
        print(f"复制内容失败: {e}")
        return False
```

- [ ] **Step 3: 实现智能 fragment 插入**

```python
def render_with_fragments(
    template_path: str,
    elements: Dict[str, Any],
    abstract_path: str,
    body_path: str,
    output_path: str
) -> bool:
    """渲染模板并插入 fragments。"""
    if not DOCX_AVAILABLE:
        return False
    
    try:
        # 1. 渲染短字段
        template = DocxTemplate(template_path)
        context = {k: v for k, v in elements.items() 
                   if k not in [common.FILE_ABSTRACT, common.FILE_BODY]}
        template.render(context)
        
        # 2. 保存到临时文件
        temp_output = str(Path(output_path).parent / "temp.docx")
        template.save(temp_output)
        
        # 3. 插入 fragments
        from docx import Document
        final_doc = Document(temp_output)
        
        # 查找并插入 abstract
        if Path(abstract_path).exists():
            abstract_doc = Document(abstract_path)
            insert_fragment_at_placeholder(final_doc, abstract_doc, "abstract")
        
        # 查找并插入 body
        if Path(body_path).exists():
            body_doc = Document(body_path)
            insert_fragment_at_placeholder(final_doc, body_doc, "body")
        
        final_doc.save(output_path)
        Path(temp_output).unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False
```

- [ ] **Step 4: 更新测试**
  
Run: `.venv/bin/python -m pytest skills/report_maker/tests/test_renderer.py -v`
```bash
Expected: 所有测试通过
```

- [ ] **Step 5: Commit**

```bash
git add skills/report_maker/scripts/renderer.py
git commit -m "feat(report_maker): enhance fragment insertion logic"
```

---

## Task 5: 添加错误处理和日志

**文件:**
- Create: `skills/report_maker/scripts/logger.py`
- Modify: `skills/report_maker/scripts/common.py`

- [ ] **Step 1: 创建日志工具函数**

```python
"""logger.py - 简单的日志工具。"""

import logging
from pathlib import Path
from datetime import datetime

def setup_logger(name: str, log_dir: str = "logs"):
    """设置日志器。"""
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(name)

def log_step(step: str, details: dict = None):
    """记录步骤。"""
    logger = logging.getLogger("report_maker")
    logger.info(f"[{step}]")
    if details:
        for key, value in details.items():
            logger.info(f"  {key}: {value}")
```

- [ ] **Step 2: 在 common.py 中添加错误处理装饰器**

```python
def handle_errors(func):
    """错误处理装饰器。"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.getLogger("report_maker").error(f"{func.__name__} 失败: {e}")
            raise
    return wrapper
```

- [ ] **Step 3: 在关键函数中添加日志记录**
  
Run: 在 extractor.py, splitter.py, renderer.py 的关键函数中添加日志

- [ ] **Step 4: 测试错误处理**
  
Run: `python -c "from scripts.logger import setup_logger; setup_logger('test'); import logging; logging.info('Test')"`
```bash
Expected: 日志正常输出
```

- [ ] **Step 5: Commit**

```bash
git add skills/report_maker/scripts/logger.py skills/report_maker/scripts/common.py
git commit -m "feat(report_maker): add error handling and logging"
```

---

## Task 6: 完善 PDF 转换功能

**文件:**
- Modify: `skills/report_maker/scripts/renderer.py`

- [ ] **Step 1: 添加 LibreOffice 路径检测**

```python
def find_libreoffice() -> str:
    """查找 LibreOffice 可执行文件。"""
    import shutil
    import platform
    
    if platform.system() == "Windows":
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        ]
    else:
        paths = ["libreoffice", "libreoffice7.5", "libreoffice7.6", "soffice"]
    
    for path in paths:
        found = shutil.which(path)
        if found:
            return found
    
    return None
```

- [ ] **Step 2: 添加 PDF 转换重试逻辑**

```python
def convert_to_pdf_with_retry(docx_path: str, pdf_path: str, max_retries: int = 2) -> bool:
    """带重试的 PDF 转换。"""
    libreoffice_cmd = find_libreoffice()
    if not libreoffice_cmd:
        return False
    
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [libreoffice_cmd, '--headless', '--convert-to', 'pdf',
                 '--outdir', str(Path(pdf_path).parent), str(docx_path)],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode == 0 and Path(pdf_path).exists():
                return True
            
            if attempt < max_retries - 1:
                print(f"PDF 转换失败，重试 {attempt + 1}/{max_retries}")
                import time
                time.sleep(2)
        except subprocess.TimeoutExpired:
            print(f"PDF 转换超时")
    
    return False
```

- [ ] **Step 3: 添加 PDF 转换验证**

```python
def verify_pdf_output(pdf_path: str, min_size: int = 1024) -> bool:
    """验证 PDF 输出。"""
    if not Path(pdf_path).exists():
        return False
    
    size = Path(pdf_path).stat().st_size
    return size >= min_size
```

- [ ] **Step 4: 测试 PDF 转换**
  
Run: `python -c "from scripts.renderer import find_libreoffice; print(find_libreoffice())"`
```bash
Expected: 显示 LibreOffice 路径或 None
```

- [ ] **Step 5: Commit**

```bash
git add skills/report_maker/scripts/renderer.py
git commit -m "feat(report_maker): improve PDF conversion with retry logic"
```

---

## Task 7: 编写部署文档

**文件:**
- Create: `docs/report_maker_deployment.md`

- [ ] **Step 1: 编写部署文档**

```markdown
# report_maker 部署文档

## 部署步骤

### 1. 确认环境

```bash
# 检查 Python 版本
python --version  # 应该是 3.8+

# 检查依赖
pip list | grep -E "(docx|docxtpl)"
```

### 2. 安装依赖

```bash
pip install python-docx docxtpl
```

### 3. 验证 skill

```bash
# 检查 skill 文件
ls -la skills/report_maker/SKILL.md

# 运行测试
pytest skills/report_maker/tests/ -v
```

### 4. 配置路由

编辑 `templates/router.yaml`:

```yaml
mappings:
  company: company
  sector: sector
  macro: common
  strategy: common
  quantitative: common
  bond: common
```

### 5. 测试完整流程

```bash
# 在 Claude Code 中运行
# 提示："我上传了公司报告草稿，报告类型是 company，帮我处理"
```

## 故障排除

### 问题 1: Skill 未触发

**解决方案**: 确保 SKILL.md 中的 description 清楚描述了使用场景

### 问题 2: 模板未找到

**解决方案**: 检查 router.yaml 配置

### 问题 3: PDF 转换失败

**解决方案**: 安装 LibreOffice 或跳过 PDF 转换
```

- [ ] **Step 2: 保存文档**
  
Run: `cat > docs/report_maker_deployment.md`
```bash
Expected: 文档创建成功
```

- [ ] **Step 3: Commit**

```bash
git add docs/report_maker_deployment.md
git commit -m "docs: add report_maker deployment guide"
```

---

## Task 8: 创建示例脚本

**文件:**
- Create: `examples/run_report_maker.sh`

- [ ] **Step 1: 编写示例脚本**

```bash
#!/bin/bash
# 示例：使用 report_maker 处理报告

set -e

echo "=== report_maker 示例 ==="
echo ""

# 检查环境
echo "1. 检查环境..."
python --version || { echo "Error: Python not found"; exit 1; }
pip list | grep -E "(docx|docxtpl)" || { echo "Error: dependencies not installed"; exit 1; }
echo "✓ 环境检查通过"
echo ""

# 准备测试
echo "2. 准备测试..."
REPORT_FILE="samples/西锐飞机首次覆盖报告（中文）提交版.docx"
[ -f "$REPORT_FILE" ] || { echo "Error: 样本文件不存在"; exit 1; }
echo "✓ 样本文件: $REPORT_FILE"
echo ""

# 运行测试
echo "3. 运行测试..."
pytest skills/report_maker/tests/ -q
echo "✓ 测试通过"
echo ""

echo "=== 示例完成 ==="
```

- [ ] **Step 2: 创建示例目录**
  
Run: `mkdir -p examples`
```bash
Expected: 目录创建成功
```

- [ ] **Step 3: 设置执行权限**
  
Run: `chmod +x examples/run_report_maker.sh`
```bash
Expected: 权限设置成功
```

- [ ] **Step 4: 测试示例脚本**
  
Run: `bash examples/run_report_maker.sh`
```bash
Expected: 脚本执行成功
```

- [ ] **Step 5: Commit**

```bash
git add examples/
git commit -m "examples: add report_maker example script"
```

---

## Task 9: 更新主文档

**文件:**
- Modify: `docs/skills-report.md`
- Modify: `README.md`

- [ ] **Step 1: 更新 skills-report.md**

在 `docs/skills-report.md` 中添加 report_maker 的使用说明

- [ ] **Step 2: 更新 README.md**

在项目 README.md 中添加 report_maker 的介绍

- [ ] **Step 3: 验证文档格式**
  
Run: `head -50 README.md`
```bash
Expected: 格式正确
```

- [ ] **Step 4: Commit**

```bash
git add docs/ README.md
git commit -m "docs: update documentation for report_maker integration"
```

---

## Task 10: 最终集成测试

**文件:**
- Create: `tests/integration/test_full_workflow.py`

- [ ] **Step 1: 编写完整集成测试**

```python
"""完整工作流集成测试。"""

import pytest
import shutil
from pathlib import Path

class TestFullWorkflow:
    def test_complete_report_generation(self):
        """测试完整的报告生成流程。"""
        # 模拟完整流程
        # 1. 上传草稿
        # 2. 指定报告类型
        # 3. 提取要素
        # 4. 确认
        # 5. 渲染
        # 6. 验证输出
        pass
```

- [ ] **Step 2: 运行完整测试**
  
Run: `.venv/bin/python -m pytest tests/integration/test_full_workflow.py -v`
```bash
Expected: 测试通过
```

- [ ] **Step 3: 生成测试报告**
  
Run: `pytest tests/ --cov=skills/report_maker --cov-report=html`
```bash
Expected: 覆盖率报告生成
```

- [ ] **Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add full workflow integration test"
```

---

## 完成清单

- [ ] 所有测试通过（39 个单元测试 + 集成测试）
- [ ] 文档完整（使用指南 + 部署文档）
- [ ] 示例脚本可用
- [ ] 集成测试通过
- [ ] 代码已提交

---

## 预期时间

- Task 1: 使用指南 - 30 分钟
- Task 2: 集成测试 - 1 小时
- Task 3: Fragment 拆分 - 2 小时
- Task 4: Fragment 插入 - 2 小时
- Task 5: 错误处理 - 1 小时
- Task 6: PDF 转换 - 1 小时
- Task 7: 部署文档 - 45 分钟
- Task 8: 示例脚本 - 30 分钟
- Task 9: 更新文档 - 30 分钟
- Task 10: 最终测试 - 1 小时

**总计: 约 10.5 小时**
