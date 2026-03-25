# Report Upload Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个自动触发的报告上传、解析、审核工作流，包括：解析 Word → 提取字段 → 合规检查 → 内容校验 → 生成标准报告

**Architecture:** 采用模块化 Skill 架构，每个 Skill 独立负责一个功能模块，通过事件/消息解耦

**Tech Stack:** 
- python-docx (Word 解析)
- pandoc (Word → Markdown 转换)
- LLM (字段提取与校验)
- python-docx-template (报告生成)
- LibreOffice (Word → PDF)

---

## 1. 模块化 Skill 架构设计

### 1.1 Skill 目录结构

```
.opencode/
└── skills/
    ├── report-parser/              # Skill 1: 报告解析器
    │   ├── SKILL.md
    │   ├── parser.py               # python-docx 解析逻辑
    │   └── converter.py            # pandoc 转换逻辑
    ├── field-extractor/            # Skill 2: 字段提取器
    │   ├── SKILL.md
    │   └── extractor.py           # LLM 提取逻辑
    ├── compliance-checker/        # Skill 3: 合规检查器
    │   ├── SKILL.md
    │   ├── similarity.py           # 相似度检查
    │   ├── sfc_validator.py        # SFC 牌照验证
    │   ├── coverage_checker.py     # Coverage 检查
    │   └── rqc_checker.py          # RQC 触发检查
    ├── content-validator/         # Skill 4: 内容校验器
    │   ├── SKILL.md
    │   └── validator.py            # 排版校验
    ├── report-generator/           # Skill 5: 报告生成器
    │   ├── SKILL.md
    │   ├── generator.py           # Word 生成
    │   └── pdf_converter.py       # PDF 转换
    └── rule-manager/              # Skill 6: 规则管理器
        ├── SKILL.md
        └── manager.py             # 对话式规则更新
```

### 1.2 配置文件结构

```
.opencode/
├── config/
│   ├── schema.yaml                # 字段提取规则
│   ├── render_rules.yaml          # 排版校验规则
│   └── report_types.yaml          # 报告类型定义
└── templates/
    └── (报告模板文件)
```

### 1.3 Skill 接口定义

每个 Skill 定义标准接口：

```yaml
# SKILL.md 头部
---
name: [skill-name]
description: [功能描述]
triggers:
  - event: [触发事件]
    action: [执行动作]
dependencies:
  - skill: [依赖的 Skill]
inputs:
  - name: [输入字段]
    type: [类型]
    required: true/false
outputs:
  - name: [输出字段]
    type: [类型]
---
```

---

## 2. Task 分解

### Task 1: 创建 Skill 基础设施

**Files:**
- Create: `.opencode/skills/_base/SKILL.md`
- Create: `.opencode/config/schema.yaml`
- Create: `.opencode/config/render_rules.yaml`
- Create: `.opencode/config/report_types.yaml`

- [ ] **Step 1: 创建基础 Skill 模板**

```yaml
---
name: [skill-name]
description: [功能描述]
triggers:
  - event: report.uploaded
    action: parse
dependencies: []
inputs:
  - name: file_path
    type: string
    required: true
outputs:
  - name: result
    type: object
---
```

- [ ] **Step 2: 创建配置文件 - schema.yaml**

```yaml
# 字段提取规则 - 按报告类型分类
company:
  required_fields:
    - ticker
    - rating
    - target_price
    - region
    - sector
    - report_language
    - title
    - analysts
    - contact_person
    - investment_thesis
    - certificate
  extraction_prompts:
    ticker: "请提取报告中的股票代码，格式如 '700 HK'"
    rating: "请提取评级，如 'OUTPERFORM', 'NEUTRAL' 等"
    # ...
    
sector:
  required_fields:
    - region
    - sector
    - report_language
    - title
    - analysts
    - contact_person
    - investment_thesis
    - certificate
  # ...

company_flash:
  # ...

sector_flash:
  # ...

common:
  # Macro, Strategy, Quantitative, Bond
  required_fields:
    - region
    - report_language
    - title
    - analysts
    - contact_person
    - investment_thesis
    - certificate
  # ...
```

- [ ] **Step 3: 创建配置文件 - render_rules.yaml**

```yaml
# 排版校验规则
validation_rules:
  - name: table_spacing
    description: "表格间距检查"
    check: "表格与正文之间应有适当间距"
  - name: font_consistency
    description: "字体一致性检查"
    check: "正文应使用统一字体"
  - name: heading_hierarchy
    description: "标题层级检查"
    check: "标题应符合 hierarchy"
  # ...
```

- [ ] **Step 4: 创建配置文件 - report_types.yaml**

```yaml
# 报告类型自动识别规则
report_types:
  company:
    keywords: ["公司", "财报", "盈利", "业绩"]
    required_sections: ["公司概况", "财务分析"]
  sector:
    keywords: ["行业", "板块", "展望"]
    required_sections: ["行业分析"]
  company_flash:
    keywords: ["快讯", "动态"]
    length_limit: 500
  sector_flash:
    keywords: ["行业快讯"]
    length_limit: 500
  common:
    keywords: ["宏观", "策略", "量化", "债券"]
```

- [ ] **Step 5: Commit**

```bash
git add .opencode/skills/_base .opencode/config
git commit -m "feat: create skill infrastructure and config files"
```

---

### Task 2: 实现 Report Parser Skill

**Files:**
- Create: `.opencode/skills/report-parser/SKILL.md`
- Create: `.opencode/skills/report-parser/parser.py`
- Create: `.opencode/skills/report-parser/converter.py`
- Test: `.opencode/skills/report-parser/test_parser.py`

- [ ] **Step 1: 创建 SKILL.md**

```yaml
---
name: report-parser
description: 解析 Word 文档，提取表格和段落，转换为 Markdown
triggers:
  - event: report.uploaded
    action: parse
dependencies: []
inputs:
  - name: file_path
    type: string
    required: true
outputs:
  - name: tables
    type: array
  - name: paragraphs
    type: array
  - name: markdown
    type: string
  - name: metadata
    type: object
---
```

- [ ] **Step 2: 实现 parser.py**

```python
"""报告解析器 - python-docx 解析 Word XML 结构"""
from docx import Document
from typing import Dict, List, Any
import tempfile
import os

class ReportParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = Document(file_path)
    
    def extract_tables(self) -> List[Dict[str, Any]]:
        """提取所有表格"""
        tables = []
        for idx, table in enumerate(self.doc.tables):
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(cells)
            tables.append({
                'index': idx,
                'rows': rows,
                'row_count': len(table.rows),
                'col_count': len(table.columns) if table.rows else 0
            })
        return tables
    
    def extract_paragraphs(self) -> List[Dict[str, str]]:
        """提取所有段落"""
        paragraphs = []
        for idx, para in enumerate(self.doc.paragraphs):
            if para.text.strip():
                paragraphs.append({
                    'index': idx,
                    'text': para.text.strip(),
                    'style': para.style.name if para.style else None
                })
        return paragraphs
    
    def extract_metadata(self) -> Dict[str, Any]:
        """提取文档元数据"""
        core_props = self.doc.core_properties
        return {
            'author': core_props.author,
            'title': core_props.title,
            'created': core_props.created.isoformat() if core_props.created else None,
            'modified': core_props.modified.isoformat() if core_props.modified else None
        }
    
    def parse(self) -> Dict[str, Any]:
        """执行完整解析"""
        return {
            'tables': self.extract_tables(),
            'paragraphs': self.extract_paragraphs(),
            'metadata': self.extract_metadata()
        }
```

- [ ] **Step 3: 实现 converter.py**

```python
"""Pandoc 转换器 - Word 转 Markdown"""
import subprocess
import tempfile
from typing import Optional

class PandocConverter:
    def __init__(self, pandoc_path: str = "pandoc"):
        self.pandoc_path = pandoc_path
    
    def docx_to_markdown(self, input_path: str, output_path: Optional[str] = None) -> str:
        """将 Word 转换为 Markdown"""
        if output_path is None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                output_path = f.name
        
        cmd = [
            self.pandoc_path,
            input_path,
            '-o', output_path,
            '--wrap=none'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Pandoc conversion failed: {result.stderr}")
        
        with open(output_path, 'r', encoding='utf-8') as f:
            return f.read()
```

- [ ] **Step 4: 创建测试文件**

```python
"""测试报告解析器"""
import pytest
from parser import ReportParser
from converter import PandocConverter

def test_extract_tables():
    """测试表格提取"""
    parser = ReportParser("samples/test_report.docx")
    tables = parser.extract_tables()
    assert len(tables) > 0

def test_docx_to_markdown():
    """测试 Pandoc 转换"""
    converter = PandocConverter()
    md = converter.docx_to_markdown("samples/test_report.docx")
    assert len(md) > 0
    assert "#" in md  # 应包含 Markdown 标题
```

- [ ] **Step 5: 运行测试验证**

```bash
cd .opencode/skills/report-parser
python -m pytest test_parser.py -v
```

- [ ] **Step 6: Commit**

```bash
git add .opencode/skills/report-parser
git commit -m "feat: implement report-parser skill"
```

---

### Task 3: 实现 Field Extractor Skill

**Files:**
- Create: `.opencode/skills/field-extractor/SKILL.md`
- Create: `.opencode/skills/field-extractor/extractor.py`
- Create: `.opencode/skills/field-extractor/type_detector.py`
- Test: `.opencode/skills/field-extractor/test_extractor.py`

- [ ] **Step 1: 创建 SKILL.md**

```yaml
---
name: field-extractor
description: 自动识别报告类型，提取结构化字段
triggers:
  - event: report.parsed
    action: extract
dependencies:
  - skill: report-parser
inputs:
  - name: markdown
    type: string
    required: true
  - name: tables
    type: array
    required: true
outputs:
  - name: report_type
    type: string
  - name: fields
    type: object
  - name: missing_fields
    type: array
---
```

- [ ] **Step 2: 实现 type_detector.py**

```python
"""报告类型自动识别器"""
import yaml
from typing import Dict, List, Optional

class ReportTypeDetector:
    def __init__(self, config_path: str = ".opencode/config/report_types.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def detect(self, markdown: str, tables: List[Dict]) -> str:
        """根据内容特征自动识别报告类型"""
        text = markdown.lower()
        
        scores = {}
        for report_type, rules in self.config['report_types'].items():
            score = 0
            # 关键词匹配
            for keyword in rules.get('keywords', []):
                if keyword.lower() in text:
                    score += 1
            # 字数限制检查 (for flash)
            if 'length_limit' in rules:
                word_count = len(text.split())
                if word_count <= rules['length_limit']:
                    score += 1
            
            scores[report_type] = score
        
        # 返回最高分类型
        best_type = max(scores, key=scores.get)
        if scores[best_type] == 0:
            return 'common'  # 默认类型
        
        return best_type
```

- [ ] **Step 3: 实现 extractor.py**

```python
"""字段提取器 - 基于 LLM"""
import yaml
from typing import Dict, List, Any, Optional

class FieldExtractor:
    def __init__(self, schema_path: str = ".opencode/config/schema.yaml", llm_client=None):
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = yaml.safe_load(f)
        self.llm = llm_client
    
    def extract(self, markdown: str, tables: List[Dict], report_type: str) -> Dict[str, Any]:
        """提取字段"""
        # 构建 prompt
        prompt = self._build_prompt(markdown, tables, report_type)
        
        # 调用 LLM
        response = self.llm.chat(prompt)
        
        # 解析结果
        fields = self._parse_response(response)
        
        # 检查必填字段
        required = self.schema[report_type].get('required_fields', [])
        missing = [f for f in required if f not in fields or not fields[f]]
        
        return {
            'report_type': report_type,
            'fields': fields,
            'missing_fields': missing
        }
    
    def _build_prompt(self, markdown: str, tables: List[Dict], report_type: str) -> str:
        """构建提取 prompt"""
        schema = self.schema[report_type]
        prompts = schema.get('extraction_prompts', {})
        
        prompt = f"""请从以下报告中提取字段信息。

报告类型: {report_type}

需要提取的字段:
"""
        for field, desc in prompts.items():
            prompt += f"- {field}: {desc}\n"
        
        prompt += f"\n报告内容:\n{markdown[:5000]}\n"  # 截断避免超长
        
        if tables:
            prompt += f"\n表格数据:\n{str(tables[:3])}\n"  # 只取前3个表格
        
        prompt += "\n请以 JSON 格式输出提取的字段。"
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        import json
        import re
        
        # 尝试提取 JSON
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
        
        return {}
```

- [ ] **Step 4: 创建测试文件**

```python
"""测试字段提取器"""
import pytest
from type_detector import ReportTypeDetector
from extractor import FieldExtractor

def test_detect_report_type():
    """测试报告类型识别"""
    detector = ReportTypeDetector()
    markdown = "这是关于腾讯控股的深度分析报告..."
    result = detector.detect(markdown, [])
    assert result == 'company'

def test_extract_fields():
    """测试字段提取"""
    extractor = FieldExtractor()
    # Mock LLM response
    extractor.llm = MockLLM()
    
    result = extractor.extract("markdown content", [], "company")
    assert 'fields' in result
    assert 'missing_fields' in result
```

- [ ] **Step 5: 运行测试验证**

```bash
cd .opencode/skills/field-extractor
python -m pytest test_extractor.py -v
```

- [ ] **Step 6: Commit**

```bash
git add .opencode/skills/field-extractor
git commit -m "feat: implement field-extractor skill"
```

---

### Task 4: 实现 Compliance Checker Skill

**Files:**
- Create: `.opencode/skills/compliance-checker/SKILL.md`
- Create: `.opencode/skills/compliance-checker/similarity.py`
- Create: `.opencode/skills/compliance-checker/sfc_validator.py`
- Create: `.opencode/skills/compliance-checker/coverage_checker.py`
- Create: `.opencode/skills/compliance-checker/rqc_checker.py`
- Create: `.opencode/skills/compliance-checker/checker.py`
- Test: `.opencode/skills/compliance-checker/test_checker.py`

- [ ] **Step 1: 创建 SKILL.md**

```yaml
---
name: compliance-checker
description: 执行合规检查：相似度、SFC、Coverage、RQC
triggers:
  - event: fields.extracted
    action: check
dependencies:
  - skill: field-extractor
inputs:
  - name: fields
    type: object
    required: true
  - name: report_id
    type: string
    required: true
outputs:
  - name: checks
    type: object
  - name: warnings
    type: array
  - name: needs_attention
    type: array
---
```

- [ ] **Step 2: 实现 similarity.py**

```python
"""文件相似度检查"""
import os
from typing import Optional
from Levenshtein import distance as levenshtein_distance

class SimilarityChecker:
    THRESHOLD = 0.6  # 60%
    
    def __init__(self, reports_dir: str = ".opencode/workspace/reports"):
        self.reports_dir = reports_dir
    
    def check(self, current_filename: str, report_id: str) -> Dict[str, Any]:
        """检查文件相似度"""
        # 获取上一版本文件名
        prev_file = self._get_previous_version(report_id)
        
        if not prev_file:
            return {'has_previous': False}
        
        # 计算相似度
        similarity = self._calculate_similarity(current_filename, prev_file)
        
        return {
            'has_previous': True,
            'previous_file': prev_file,
            'current_file': current_filename,
            'similarity': similarity,
            'is_suspicious': similarity < self.THRESHOLD,
            'warning': f"文件相似度 {similarity:.1%}，疑似提交错误" if similarity < self.THRESHOLD else None
        }
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算相似度: 1 - 莱文斯坦距离 / 最大字符串长度"""
        if not s1 or not s2:
            return 0.0
        
        max_len = max(len(s1), len(s2))
        dist = levenshtein_distance(s1, s2)
        
        return 1 - (dist / max_len)
    
    def _get_previous_version(self, report_id: str) -> Optional[str]:
        """获取上一版本文件名"""
        # 从数据库/存储获取
        # 简化实现
        return None
```

- [ ] **Step 3: 实现 sfc_validator.py**

```python
"""SFC 牌照验证"""
import requests
from typing import Dict, Any, Optional
import re

class SFCValidator:
    SFC_SEARCH_URL = "https://apps.sfc.hk/publicregWeb/searchByName"
    
    def __init__(self, cache: Optional[Dict] = None):
        self.cache = cache or {}
    
    def validate(self, analyst_name: str, sfc_number: Optional[str] = None) -> Dict[str, Any]:
        """验证 SFC 牌照"""
        # 如果提供了 SFC 号码，直接验证
        if sfc_number:
            return self._verify_sfc(analyst_name, sfc_number)
        
        # 否则搜索获取
        return self._search_sfc(analyst_name)
    
    def _verify_sfc(self, name: str, sfc: str) -> Dict[str, Any]:
        """验证 SFC 号码"""
        # 实际实现需要调用 SFC API 或网页爬取
        # 这里简化处理
        valid = self._check_sfc_validity(sfc)
        
        return {
            'analyst_name': name,
            'sfc_number': sfc,
            'is_valid': valid,
            'warning': None if valid else f"SFC 牌照 {sfc} 无效，请确认"
        }
    
    def _search_sfc(self, name: str) -> Dict[str, Any]:
        """搜索 SFC 牌照"""
        # 实现网页搜索逻辑
        # 返回匹配结果
        return {
            'analyst_name': name,
            'found': False,
            'warning': f"未找到 {name} 的 SFC 牌照，请手动确认"
        }
    
    def _check_sfc_validity(self, sfc: str) -> bool:
        """检查牌照有效性"""
        # SFC 格式: 通常是 8 位数字
        return bool(re.match(r'^\d{8}$', sfc))
```

- [ ] **Step 4: 实现 coverage_checker.py**

```python
"""Coverage 检查"""
from typing import Dict, Any, Optional

class CoverageChecker:
    def __init__(self, db_client=None):
        self.db = db_client
    
    def check(self, ticker: str) -> Dict[str, Any]:
        """检查 Coverage 是否存在"""
        if not ticker:
            return {'exists': False, 'warning': '无 ticker 信息'}
        
        # 查询数据库
        coverage = self._query_coverage(ticker)
        
        if coverage:
            return {
                'exists': True,
                'coverage_id': coverage['id'],
                'ticker': ticker,
                'warning': None
            }
        
        return {
            'exists': False,
            'ticker': ticker,
            'warning': f'新 Coverage [{ticker}] 需要添加到系统'
        }
    
    def _query_coverage(self, ticker: str) -> Optional[Dict]:
        """查询 Coverage"""
        # 实现数据库查询
        return None
```

- [ ] **Step 5: 实现 rqc_checker.py**

```python
"""RQC 触发检查"""
from typing import Dict, Any, Optional

class RQCChecker:
    TP_CHANGE_THRESHOLD = 0.30  # 30%
    
    def __init__(self, db_client=None):
        self.db = db_client
    
    def check(self, ticker: str, current_target_price: float) -> Dict[str, Any]:
        """检查是否触发 RQC"""
        if not ticker or not current_target_price:
            return {'needs_rqc': False, 'reason': '无目标价信息'}
        
        # 获取上次报告的目标价
        prev_tp = self._get_previous_target_price(ticker)
        
        if prev_tp is None:
            # 首次覆盖，触发 RQC
            return {
                'needs_rqc': True,
                'reason': '首次覆盖',
                'warning': '首次覆盖需要 RQC 审批'
            }
        
        # 计算变动幅度
        change = abs(current_target_price - prev_tp) / prev_tp
        
        if change >= self.TP_CHANGE_THRESHOLD:
            return {
                'needs_rqc': True,
                'reason': f'目标价变动 {change:.1%}',
                'previous_tp': prev_tp,
                'current_tp': current_target_price,
                'change': change,
                'warning': f'目标价变动 {change:.1%}，超过 30% 阈值，需要 RQC 审批'
            }
        
        # 检查评级变动
        prev_rating = self._get_previous_rating(ticker)
        if prev_rating:
            return {
                'needs_rqc': True,
                'reason': '评级变动',
                'warning': '评级变动需要 RQC 审批'
            }
        
        return {
            'needs_rqc': False,
            'reason': '无触发条件'
        }
    
    def _get_previous_target_price(self, ticker: str) -> Optional[float]:
        """获取上次目标价"""
        return None
    
    def _get_previous_rating(self, ticker: str) -> Optional[str]:
        """获取上次评级"""
        return None
```

- [ ] **Step 6: 实现 checker.py**

```python
"""合规检查器 - 整合所有检查"""
from typing import Dict, Any, List
from similarity import SimilarityChecker
from sfc_validator import SFCValidator
from coverage_checker import CoverageChecker
from rqc_checker import RQCChecker

class ComplianceChecker:
    def __init__(self):
        self.similarity = SimilarityChecker()
        self.sfc = SFCValidator()
        self.coverage = CoverageChecker()
        self.rqc = RQCChecker()
    
    def check_all(self, fields: Dict, report_id: str, filename: str) -> Dict[str, Any]:
        """执行所有合规检查"""
        results = {}
        warnings = []
        needs_attention = []
        
        # 1. 相似度检查
        sim_result = self.similarity.check(filename, report_id)
        results['similarity'] = sim_result
        if sim_result.get('warning'):
            warnings.append(sim_result['warning'])
            needs_attention.append('similarity')
        
        # 2. SFC 验证 (对所有分析师)
        analysts = fields.get('analysts', [])
        sfc_results = []
        for analyst in analysts:
            sfc_result = self.sfc.validate(
                analyst.get('name'),
                analyst.get('sfc')
            )
            sfc_results.append(sfc_result)
            if sfc_result.get('warning'):
                warnings.append(sfc_result['warning'])
                needs_attention.append('sfc')
        results['sfc'] = sfc_results
        
        # 3. Coverage 检查
        ticker = fields.get('ticker')
        cov_result = self.coverage.check(ticker)
        results['coverage'] = cov_result
        if cov_result.get('warning'):
            warnings.append(cov_result['warning'])
            needs_attention.append('coverage')
        
        # 4. RQC 检查
        tp = fields.get('target_price')
        if tp:
            try:
                tp = float(tp)
                rqc_result = self.rqc.check(ticker, tp)
                results['rqc'] = rqc_result
                if rqc_result.get('warning'):
                    warnings.append(rqc_result['warning'])
                    needs_attention.append('rqc')
            except (ValueError, TypeError):
                pass
        
        return {
            'checks': results,
            'warnings': warnings,
            'needs_attention': list(set(needs_attention))
        }
```

- [ ] **Step 7: 创建测试文件**

```python
"""测试合规检查器"""
import pytest
from similarity import SimilarityChecker
from sfc_validator import SFCValidator

def test_similarity_calculation():
    """测试相似度计算"""
    checker = SimilarityChecker()
    sim = checker._calculate_similarity("报告A.docx", "报告A_修改.docx")
    assert sim > 0.6

def test_sfc_validation():
    """测试 SFC 验证"""
    validator = SFCValidator()
    result = validator.validate("张三", "12345678")
    assert 'is_valid' in result
```

- [ ] **Step 8: 运行测试验证**

```bash
cd .opencode/skills/compliance-checker
python -m pytest test_checker.py -v
```

- [ ] **Step 9: Commit**

```bash
git add .opencode/skills/compliance-checker
git commit -m "feat: implement compliance-checker skill"
```

---

### Task 5: 实现 Content Validator Skill

**Files:**
- Create: `.opencode/skills/content-validator/SKILL.md`
- Create: `.opencode/skills/content-validator/validator.py`
- Test: `.opencode/skills/content-validator/test_validator.py`

- [ ] **Step 1: 创建 SKILL.md**

```yaml
---
name: content-validator
description: 校验报告内容排版，对比 render_rules
triggers:
  - event: compliance.checked
    action: validate
dependencies:
  - skill: compliance-checker
inputs:
  - name: markdown
    type: string
  - name: tables
    type: array
outputs:
  - name: validation_results
    type: array
  - name: issues
    type: array
---
```

- [ ] **Step 2: 实现 validator.py**

```python
"""内容校验器"""
import yaml
from typing import Dict, List, Any

class ContentValidator:
    def __init__(self, rules_path: str = ".opencode/config/render_rules.yaml"):
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
    
    def validate(self, markdown: str, tables: List[Dict]) -> Dict[str, Any]:
        """执行内容校验"""
        issues = []
        
        # 1. 检查标题层级
        heading_issues = self._check_heading_hierarchy(markdown)
        issues.extend(heading_issues)
        
        # 2. 检查表格格式
        table_issues = self._check_tables(tables)
        issues.extend(table_issues)
        
        # 3. 检查字体/格式
        # (需要更复杂的实现)
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'issue_count': len(issues)
        }
    
    def _check_heading_hierarchy(self, markdown: str) -> List[Dict]:
        """检查标题层级"""
        issues = []
        lines = markdown.split('\n')
        prev_level = 0
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                if level > prev_level + 1:
                    issues.append({
                        'type': 'heading_hierarchy',
                        'line': i + 1,
                        'message': f'标题层级跳跃: {prev_level} -> {level}'
                    })
                prev_level = level
        
        return issues
    
    def _check_tables(self, tables: List[Dict]) -> List[Dict]:
        """检查表格格式"""
        issues = []
        
        for table in tables:
            # 检查是否有空表格
            if not table.get('rows'):
                issues.append({
                    'type': 'empty_table',
                    'table_index': table.get('index'),
                    'message': '发现空表格'
                })
            
            # 检查跨行跨列
            # (需要更复杂的实现)
        
        return issues
```

- [ ] **Step 3: 创建测试文件**

```python
"""测试内容校验器"""
import pytest
from validator import ContentValidator

def test_heading_hierarchy():
    """测试标题层级检查"""
    validator = ContentValidator()
    markdown = """# 主标题
## 二级标题
### 三级标题
#### 四级标题
## 另一个二级标题
"""
    result = validator.validate(markdown, [])
    assert result['passed'] == True

def test_empty_table():
    """测试空表格检查"""
    validator = ContentValidator()
    tables = [{'index': 0, 'rows': []}]
    result = validator.validate("", tables)
    assert result['issue_count'] > 0
```

- [ ] **Step 4: 运行测试验证**

```bash
cd .opencode/skills/content-validator
python -m pytest test_validator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add .opencode/skills/content-validator
git commit -m "feat: implement content-validator skill"
```

---

### Task 6: 实现 Report Generator Skill

**Files:**
- Create: `.opencode/skills/report-generator/SKILL.md`
- Create: `.opencode/skills/report-generator/generator.py`
- Create: `.opencode/skills/report-generator/pdf_converter.py`
- Test: `.opencode/skills/report-generator/test_generator.py`

- [ ] **Step 1: 创建 SKILL.md**

```yaml
---
name: report-generator
description: 生成标准格式 Word 报告和 PDF
triggers:
  - event: content.validated
    action: generate
dependencies:
  - skill: content-validator
inputs:
  - name: fields
    type: object
    required: true
  - name: report_type
    type: string
    required: true
  - name: markdown
    type: string
  - name: issues
    type: array
outputs:
  - name: word_file
    type: string
  - name: pdf_file
    type: string
  - name: issues_summary
    type: string
---
```

- [ ] **Step 2: 实现 generator.py**

```python
"""报告生成器 - python-docx-template"""
from docxtpl import DocxTemplate
from typing import Dict, Any, Optional
import os

class ReportGenerator:
    def __init__(self, templates_dir: str = ".opencode/templates"):
        self.templates_dir = templates_dir
    
    def generate(self, fields: Dict, report_type: str, 
                 markdown: str, output_dir: str) -> Dict[str, Any]:
        """生成标准报告"""
        # 1. 加载模板
        template = self._load_template(report_type)
        
        # 2. 准备数据
        context = self._prepare_context(fields, markdown)
        
        # 3. 渲染 Word
        word_path = os.path.join(output_dir, 'output_standard.docx')
        template.render(context)
        template.save(word_path)
        
        # 4. 转换为 PDF
        pdf_path = self._convert_to_pdf(word_path, output_dir)
        
        # 5. 生成问题清单
        issues_summary = self._generate_issues_summary(fields.get('issues', []))
        
        return {
            'word_file': word_path,
            'pdf_file': pdf_path,
            'issues_summary': issues_summary
        }
    
    def _load_template(self, report_type: str) -> DocxTemplate:
        """加载对应模板"""
        template_path = os.path.join(
            self.templates_dir,
            f'{report_type}_template.docx'
        )
        return DocxTemplate(template_path)
    
    def _prepare_context(self, fields: Dict, markdown: str) -> Dict:
        """准备渲染上下文"""
        # 提取正文和摘要
        abstract = self._extract_abstract(markdown)
        body = self._extract_body(markdown)
        
        return {
            'company': fields.get('company_name'),
            'ticker': fields.get('ticker'),
            'rating': fields.get('rating'),
            'target_price': fields.get('target_price'),
            'report_date': fields.get('report_date'),
            'title': fields.get('title'),
            'analysts': fields.get('analysts', []),
            'abstract': abstract,
            'body': body,
            # ... 其他字段
        }
    
    def _extract_abstract(self, markdown: str) -> str:
        """提取摘要"""
        # 简单实现：取第一个标题前的内容
        lines = markdown.split('\n')
        abstract_lines = []
        for line in lines:
            if line.startswith('#'):
                break
            abstract_lines.append(line)
        return '\n'.join(abstract_lines)
    
    def _extract_body(self, markdown: str) -> str:
        """提取正文"""
        # 简单实现：取标题后的内容
        lines = markdown.split('\n')
        body_lines = []
        in_body = False
        for line in lines:
            if line.startswith('#'):
                in_body = True
                continue
            if in_body:
                body_lines.append(line)
        return '\n'.join(body_lines)
    
    def _convert_to_pdf(self, word_path: str, output_dir: str) -> str:
        """Word 转 PDF"""
        # 使用 LibreOffice
        import subprocess
        pdf_path = word_path.replace('.docx', '.pdf')
        
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            word_path
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        return pdf_path
    
    def _generate_issues_summary(self, issues: list) -> str:
        """生成问题清单"""
        if not issues:
            return "无问题"
        
        summary = "## 待确认事项\n\n"
        for issue in issues:
            summary += f"- {issue}\n"
        
        return summary
```

- [ ] **Step 3: 实现 pdf_converter.py**

```python
"""PDF 转换器"""
import subprocess
import os

class PDFConverter:
    def __init__(self, libreoffice_path: str = "libreoffice"):
        self.libreoffice = libreoffice_path
    
    def convert(self, input_path: str, output_dir: str) -> str:
        """转换 Word 到 PDF"""
        cmd = [
            self.libreoffice,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"PDF conversion failed: {result.stderr}")
        
        return input_path.replace('.docx', '.pdf')
```

- [ ] **Step 4: 创建测试文件**

```python
"""测试报告生成器"""
import pytest
from generator import ReportGenerator

def test_extract_abstract():
    """测试摘要提取"""
    generator = ReportGenerator()
    markdown = """这是摘要内容第一段
这是摘要内容第二段

# 正文标题
正文内容
"""
    abstract = generator._extract_abstract(markdown)
    assert "摘要内容" in abstract
    assert "正文标题" not in abstract
```

- [ ] **Step 5: 运行测试验证**

```bash
cd .opencode/skills/report-generator
python -m pytest test_generator.py -v
```

- [ ] **Step 6: Commit**

```bash
git add .opencode/skills/report-generator
git commit -m "feat: implement report-generator skill"
```

---

### Task 7: 实现 Rule Manager Skill

**Files:**
- Create: `.opencode/skills/rule-manager/SKILL.md`
- Create: `.opencode/skills/rule-manager/manager.py`
- Test: `.opencode/skills/rule-manager/test_manager.py`

- [ ] **Step 1: 创建 SKILL.md**

```yaml
---
name: rule-manager
description: 对话式规则管理，更新 schema.yaml
triggers:
  - event: user.feedback
    action: update
dependencies: []
inputs:
  - name: feedback
    type: string
    required: true
  - name: current_schema
    type: object
outputs:
  - name: updated
    type: boolean
  - name: changes
    type: array
  - name: prompt_for_template
    type: string
---
```

- [ ] **Step 2: 实现 manager.py**

```python
"""规则管理器 - 对话式更新"""
import yaml
from typing import Dict, List, Any

class RuleManager:
    def __init__(self, schema_path: str = ".opencode/config/schema.yaml"):
        self.schema_path = schema_path
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = yaml.safe_load(f)
    
    def update_from_feedback(self, feedback: str) -> Dict[str, Any]:
        """根据反馈更新规则"""
        changes = []
        
        # 解析反馈
        # 示例: "以后提取宏观报告时，增加一个'风险提示'字段"
        
        if "增加" in feedback and "字段" in feedback:
            # 提取字段名
            field_info = self._parse_add_field(feedback)
            if field_info:
                # 添加字段到 schema
                self._add_field(field_info)
                changes.append(f"添加字段: {field_info['name']}")
        
        if "修改" in feedback and "字段" in feedback:
            # 修改字段
            field_info = self._parse_modify_field(feedback)
            if field_info:
                self._modify_field(field_info)
                changes.append(f"修改字段: {field_info['name']}")
        
        # 保存更新
        if changes:
            self._save_schema()
        
        # 生成模板更新提示
        prompt = self._generate_template_prompt(changes)
        
        return {
            'updated': len(changes) > 0,
            'changes': changes,
            'prompt_for_template': prompt
        }
    
    def _parse_add_field(self, feedback: str) -> Dict[str, Any]:
        """解析添加字段反馈"""
        # 简单实现：提取引号内的内容
        import re
        match = re.search(r'["\']([^"\']+)["\']', feedback)
        if match:
            field_name = match.group(1)
            # 尝试推断字段类型
            return {
                'name': field_name,
                'description': f'从反馈中提取: {field_name}'
            }
        return None
    
    def _parse_modify_field(self, feedback: str) -> Dict[str, Any]:
        """解析修改字段反馈"""
        return self._parse_add_field(feedback)
    
    def _add_field(self, field_info: Dict):
        """添加字段到 schema"""
        # 添加到 common 类型（默认）
        if 'common' not in self.schema:
            self.schema['common'] = {}
        if 'required_fields' not in self.schema['common']:
            self.schema['common']['required_fields'] = []
        if 'extraction_prompts' not in self.schema['common']:
            self.schema['common']['extraction_prompts'] = {}
        
        self.schema['common']['required_fields'].append(field_info['name'])
        self.schema['common']['extraction_prompts'][field_info['name']] = field_info['description']
    
    def _modify_field(self, field_info: Dict):
        """修改字段"""
        # 实现修改逻辑
        pass
    
    def _save_schema(self):
        """保存 schema"""
        with open(self.schema_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.schema, f, allow_unicode=True)
    
    def _generate_template_prompt(self, changes: List[str]) -> str:
        """生成模板更新提示"""
        if not changes:
            return ""
        
        prompt = "已更新提取规则。\n\n"
        for change in changes:
            prompt += f"- {change}\n"
        
        prompt += "\n请下载当前的排版模板，在您希望显示新字段的段落输入占位符，然后上传修改后的模板。"
        
        return prompt
```

- [ ] **Step 3: 创建测试文件**

```python
"""测试规则管理器"""
import pytest
from manager import RuleManager

def test_parse_add_field():
    """测试解析添加字段反馈"""
    manager = RuleManager()
    result = manager._parse_add_field('增加"风险提示"字段')
    assert result['name'] == '风险提示'

def test_update_from_feedback():
    """测试根据反馈更新规则"""
    manager = RuleManager()
    result = manager.update_from_feedback('增加"风险提示"字段')
    assert result['updated'] == True
    assert 'risk_warning' in str(result['changes'])
```

- [ ] **Step 4: 运行测试验证**

```bash
cd .opencode/skills/rule-manager
python -m pytest test_manager.py -v
```

- [ ] **Step 5: Commit**

```bash
git add .opencode/skills/rule-manager
git commit -m "feat: implement rule-manager skill"
```

---

### Task 8: 工作流编排

**Files:**
- Create: `.opencode/skills/workflow.yaml`
- Create: `.opencode/skills/orchestrator.py`
- Test: `.opencode/skills/test_workflow.py`

- [ ] **Step 1: 创建 workflow.yaml**

```yaml
# 工作流编排配置
name: report-upload-workflow
version: "1.0"

triggers:
  - event: report.uploaded
    source: user

stages:
  - name: parse
    skill: report-parser
    on_success: extract
    
  - name: extract
    skill: field-extractor
    on_success: check
    on_failure: notify_missing_fields
    
  - name: check
    skill: compliance-checker
    parallel: true
    on_success: validate
    
  - name: validate
    skill: content-validator
    on_success: generate
    
  - name: generate
    skill: report-generator
    on_success: complete
    
notifications:
  - on_complete:
      - channel: user
        message: "报告处理完成"
  - on_warning:
      - channel: user
        message: "发现 {issue_count} 个待确认事项"
```

- [ ] **Step 2: 实现 orchestrator.py**

```python
"""工作流编排器"""
from typing import Dict, Any, List, Optional
import yaml

class WorkflowOrchestrator:
    def __init__(self, workflow_config: str = ".opencode/skills/workflow.yaml"):
        with open(workflow_config, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.skills = {}
    
    def register_skill(self, name: str, skill_instance):
        """注册 Skill"""
        self.skills[name] = skill_instance
    
    async def execute(self, trigger: str, context: Dict) -> Dict[str, Any]:
        """执行工作流"""
        # 查找触发器对应的流程
        for stage in self.config['stages']:
            result = await self._execute_stage(stage, context)
            
            if result.get('failed'):
                # 处理失败
                if 'on_failure' in stage:
                    await self._execute_stage(
                        {'skill': stage['on_failure']}, 
                        context
                    )
                break
            
            # 更新上下文
            context.update(result)
            
            # 检查是否需要并行执行
            if stage.get('parallel'):
                results = await self._execute_parallel(stage, context)
                context.update({'parallel_results': results})
        
        return context
    
    async def _execute_stage(self, stage: Dict, context: Dict) -> Dict:
        """执行单个阶段"""
        skill_name = stage['skill']
        skill = self.skills.get(skill_name)
        
        if not skill:
            return {'failed': True, 'error': f'Skill {skill_name} not found'}
        
        # 执行 skill
        result = await skill.execute(context)
        
        return result
    
    async def _execute_parallel(self, stage: Dict, context: Dict) -> List[Dict]:
        """并行执行检查"""
        # 实现并行执行逻辑
        return []
```

- [ ] **Step 3: 创建集成测试**

```python
"""工作流集成测试"""
import pytest
from orchestrator import WorkflowOrchestrator

@pytest.mark.asyncio
async def test_full_workflow():
    """测试完整工作流"""
    orchestrator = WorkflowOrchestrator()
    
    # 注册 skills
    # orchestrator.register_skill('report-parser', ...)
    
    # 执行工作流
    context = {
        'file_path': 'samples/test_report.docx',
        'filename': 'test_report.docx'
    }
    
    result = await orchestrator.execute('report.uploaded', context)
    
    assert 'word_file' in result
    assert 'pdf_file' in result
```

- [ ] **Step 4: 运行测试验证**

```bash
python -m pytest test_workflow.py -v
```

- [ ] **Step 5: Commit**

```bash
git add .opencode/skills/workflow.yaml .opencode/skills/orchestrator.py
git commit -m "feat: add workflow orchestration"
```

---

## 3. 执行顺序

建议按以下顺序执行：

1. **Task 1**: 创建 Skill 基础设施（配置和基础模板）
2. **Task 2**: Report Parser（最早需要的基础模块）
3. **Task 3**: Field Extractor（依赖 Parser 输出）
4. **Task 4**: Compliance Checker（依赖 Extractor 输出）
5. **Task 5**: Content Validator（依赖 Checker 输出）
6. **Task 6**: Report Generator（依赖所有上游输出）
7. **Task 7**: Rule Manager（独立模块，对话式反馈）
8. **Task 8**: 工作流编排（整合所有模块）

---

## 4. 依赖关系图

```
User Upload
    │
    ▼
┌─────────────┐
│  Parser     │ ─────────────┐
└─────────────┘              │
    │                        │
    ▼                        │
┌─────────────┐              │
│ Extractor   │ ─────────────┼────────────┐
└─────────────┘              │            │
    │                        ▼            ▼
    │                 ┌─────────────┐ ┌─────────────┐
    │                 │ Compliance  │ │   Rules     │
    │                 │  Checker    │ │  Manager    │
    │                 └─────────────┘ └─────────────┘
    │                        │            │
    ▼                        ▼            │
┌─────────────┐              │            │
│  Content    │ ◄────────────┘            │
│  Validator  │                           │
└─────────────┘                           │
    │                                     │
    ▼                                     │
┌─────────────┐                           │
│  Generator  │ ◄─────────────────────────┘
└─────────────┘
    │
    ▼
   PDF
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-24-report-upload-workflow.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
