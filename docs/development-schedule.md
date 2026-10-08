# NeoSpace 工作台插件系统 - 开发排期计划

**项目名称**: NeoSpace AI 工作台插件  
**项目类型**: AI 辅助金融报告管理系统  
**技术栈**: Next.js + Supabase + Claude Code (Skills)  
**文档版本**: v1.0  
**编制日期**: 2026-03-20

---

## 一、项目需求概述

### 1.1 项目背景

NeoSpace 是 Neolyst 研究报告管理平台的 AI 工作台插件系统，通过 AI Agent Skills 实现报告的自动化编辑与审核流程。

### 1.2 核心功能需求

基于 `platform_overview.pdf` 和 `report-skills.md` 以及 `neoskills/docs/` 下的文档，核心功能包括：

| 场景 | 功能描述 |
|------|---------|
| **场景一** | 报告模板的制作与维护（业务人员自主配置） |
| **场景二** | 分析师日常报告生成（草稿→标准报告） |

### 1.3 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    NeoSpace 工作台插件                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 Agent Skills 层                       │  │
│  │  template-admin | report-generator | data-maintenance │  │
│  └─────────────────────────────────────────────────────┘  │
│                            │                               │
│                            ▼                               │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Supabase Backend                       │  │
│  │    Auth | Postgres | RLS | PostgREST | Storage     │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 技术栈

| 层级 | 技术选型 |
|------|---------|
| 模板引擎 | python-docxtemplate (Jinja2) |
| 文档转换 | Pandoc + pypandoc |
| 结构化提取 | LLM + schema.yaml |
| 图表提取 | PyMuPDF (fitz) + LibreOffice |
| PDF转换 | libreoffice --headless |
| 数据格式 | YAML (业务友好) |

---

## 二、功能模块拆分

### 2.1 模块总览

```
NeoSpace Skills
├── skills/
│   ├── template-admin/          # 技能1: 模板配置管家
│   │   ├── upload-handler       # 上传标准样本
│   │   ├── schema-generator     # 生成提取规则
│   │   ├── template-validator   # 模板验证
│   │   └── workspace-manager   # 工作区管理
│   │
│   ├── report-generator/        # 技能2: 通用研报生成器
│   │   ├── report-parser        # 草稿解析
│   │   ├── element-extractor    # 要素提取
│   │   ├── template-renderer    # 模板渲染
│   │   ├── chart-generator      # 图表生成
│   │   └── file-converter       # 格式转换
│   │
│   └── common/                  # 通用技能
│       ├── yaml-manager         # YAML文件管理
│       ├── llm-client           # LLM调用
│       └── file-manager         # 文件操作
```

### 2.2 详细功能清单

---

## 三、开发阶段规划

### 阶段一：基础设施搭建 (Week 1-2)

**目标**: 搭建项目骨架和核心基础设施

| 序号 | 任务 | 描述 | 预估工时 | 优先级 |
|------|------|------|---------|--------|
| 1.1 | 项目初始化 | 创建项目结构，配置环境 | 1d | P0 |
| 1.2 | 目录结构设计 | 按照 skills/workspace/reports 划分 | 0.5d | P0 |
| 1.3 | YAML管理模块 | 实现 elements.yaml/schema.yaml 读写 | 2d | P0 |
| 1.4 | LLM 客户端封装 | 统一调用接口，支持多模型 | 1.5d | P0 |
| 1.5 | 文件操作模块 | 上传/下载/转换封装 | 2d | P0 |
| 1.6 | 基础工具脚本 | Python 依赖环境搭建 | 1d | P1 |

**交付物**:
- [ ] 项目目录结构
- [ ] YAML 解析/写入工具
- [ ] LLM 调用封装
- [ ] 文件处理基础模块

---

### 阶段二：模板管理技能 (Week 3-4)

**目标**: 实现模板制作与维护功能

| 序号 | 任务 | 描述 | 预估工时 | 优先级 |
|------|------|------|---------|--------|
| 2.1 | 样本上传处理 | 接收 Word + elements.yaml 上传 | 1d | P0 |
| 2.2 | Word 解析引擎 | 解析文档结构，提取占位符 | 2d | P0 |
| 2.3 | Schema 生成器 | 从样本生成/更新 schema.yaml | 2d | P0 |
| 2.4 | 模板验证器 | 闭环验证（生成→比对） | 1.5d | P1 |
| 2.5 | 对话式规则修改 | 自然语言指令解析与执行 | 2d | P1 |
| 2.6 | 模板更新机制 | 上传新版 Word 覆盖模板 | 1d | P2 |

**交付物**:
- [ ] template-admin 技能
- [ ] 模板解析与验证流程
- [ ] schema.yaml 自动生成

---

### 阶段三：报告生成技能 (Week 5-7)

**目标**: 实现草稿到标准报告的生成

| 序号 | 任务 | 描述 | 预估工时 | 优先级 |
|------|------|------|---------|--------|
| 3.1 | 草稿解析 | Word → Markdown 转换 | 1.5d | P0 |
| 3.2 | 报告类型识别 | 自动识别 company/sector/common | 1d | P0 |
| 3.3 | 要素提取 | LLM 从 Markdown 提取字段 | 2d | P0 |
| 3.4 | 要素确认 UI | 对话式展示与修改 | 1d | P1 |
| 3.5 | 短数据渲染 | elements.yaml → 占位符填充 | 1.5d | P0 |
| 3.6 | 长文本渲染 | body.md → Word 正文 | 2d | P0 |
| 3.7 | 图表提取 | PDF 坐标裁剪法 | 2d | P1 |
| 3.8 | PDF 导出 | Word → PDF 转换 | 1d | P2 |

**交付物**:
- [ ] report-generator 技能
- [ ] 完整报告生成流程
- [ ] Word/PDF 双格式输出

---

### 阶段四：检查与审批 (Week 8-9)

**目标**: 实现报告检查和审批流程

| 序号 | 任务 | 描述 | 预估工时 | 优先级 |
|------|------|------|---------|--------|
| 4.1 | 字段完整性检查 | 按报告类型检查必填字段 | 1.5d | P0 |
| 4.2 | 文件齐全检查 | Word/Model 文件验证 | 1d | P0 |
| 4.3 | 文件相似度检查 | 莱文斯坦距离算法 | 1d | P1 |
| 4.4 | SFC 署名验证 | 爬虫 + 手动确认 | 1.5d | P1 |
| 4.5 | Coverage 审批 | 检查/创建 Coverage | 1d | P1 |
| 4.6 | RQC 触发判断 | 首次覆盖/评级变动/目标价≥30% | 1d | P1 |

**交付物**:
- [ ] 完整检查技能集
- [ ] 审批流程触发器

---

### 阶段五：高级功能 (Week 10-12)

**目标**: 实现高级自动化功能

| 序号 | 任务 | 描述 | 预估工时 | 优先级 |
|------|------|------|---------|--------|
| 5.1 | 标题自动生成 | 业务规则引擎 | 1.5d | P1 |
| 5.2 | 股价图生成 | 市场数据 → 图表 | 2d | P1 |
| 5.3 | StockList 检查 | 公司识别 + 披露生成 | 3d | P2 |
| 5.4 | 自动翻译 | 多语言支持 | 2d | P2 |
| 5.5 | 自动审核 | AI 合规检查 | 2d | P2 |

**交付物**:
- [ ] 标题生成器
- [ ] 图表生成模块
- [ ] StockList 处理流程

---

## 四、任务详细说明

### 4.1 Phase 1: 基础设施 (Week 1-2)

#### 1.1 项目初始化
```
创建目录结构：
/agent_workspace/
├── /skills/
│   ├── /template-admin/
│   │   └── SKILL.md
│   └── /report-generator/
│       ├── SKILL.md
│       ├── /scripts/
│       └── /templates/
│           └── router.json
├── /workspace/
│   ├── /reports/           # 用户数据区
│   └── /templates/          # 模板备份
└── /config/
    └── settings.yaml
```

#### 1.3 YAML 管理模块
```python
# elements.yaml 结构
company: "西锐飞机"
ticker: "TXCAV US"
rating: "OUTPERFORM"
target_price: 45
region: "China"
sector: "Aerospace"
analysts:
  - name: "张三"
    email: "zhangsan@example.com"
    sfc: "AAA123456"

# schema.yaml 结构
company:
  description: "请提取报告覆盖的公司名称"
  type: "string"
  required: true
rating:
  description: "请提取评级（OUTPERFORM/NEUTRAL/UNDERPERFORM）"
  type: "enum"
  options: ["OUTPERFORM", "NEUTRAL", "UNDERPERPERFORM"]
  required: true
```

#### 1.4 LLM 客户端
```python
class LLMClient:
    def __init__(self, provider="openai"):
        self.provider = provider
    
    def extract_elements(self, markdown: str, schema: dict) -> dict:
        """从Markdown提取要素"""
        pass
    
    def generate_schema(self, sample_text: str) -> dict:
        """从样本生成提取规则"""
        pass
```

---

### 4.2 Phase 2: 模板管理 (Week 3-4)

#### 2.1 样本上传处理
```python
class SampleUploader:
    """处理标准样本上传"""
    
    def process(self, word_file: Path, elements_yaml: Path) -> dict:
        # 1. 解析 Word 文档
        # 2. 识别占位符 {{xxx}}
        # 3. 生成模板占位符列表
        # 4. 验证 elements.yaml 完整性
        pass
```

#### 2.2 Word 解析引擎
```python
class WordParser:
    """解析 Word 文档结构"""
    
    def extract_placeholders(self, docx_path: Path) -> List[str]:
        """提取所有占位符 {{xxx}}"""
        pass
    
    def extract_tables(self, docx_path: Path) -> List[Table]:
        """提取所有表格及位置"""
        pass
    
    def extract_images(self, docx_path: Path) -> List[Image]:
        """提取所有图片"""
        pass
```

#### 2.3 Schema 生成器
```python
class SchemaGenerator:
    """从样本自动生成/更新 schema.yaml"""
    
    def generate(self, docx_path: Path) -> dict:
        """基于文档内容生成提取规则"""
        pass
    
    def update(self, new_field: str, description: str) -> dict:
        """对话式更新提取规则"""
        pass
```

---

### 4.3 Phase 3: 报告生成 (Week 5-7)

#### 3.1 草稿解析流程
```
Word 草稿 
  → Pandoc 转换 → 纯净 Markdown
  → LLM 提取 → 结构化要素 (elements.yaml)
  → 用户确认 → 确认要素
  → 模板渲染 → 标准 Word/PDF
```

#### 3.5 模板渲染
```python
class TemplateRenderer:
    """使用 python-docxtemplate 渲染"""
    
    def render_short_data(self, template: Path, elements: dict) -> bytes:
        """渲染短数据（标题、评级等）"""
        pass
    
    def render_long_content(self, template: Path, body_md: Path) -> bytes:
        """渲染长文本（正文）使用 Subdoc"""
        pass
```

#### 3.7 图表提取
```python
class ChartExtractor:
    """PDF 坐标裁剪法提取复杂图表"""
    
    def extract_table_as_image(self, pdf_path: Path, page: int, rect: tuple) -> bytes:
        """从 PDF 指定坐标裁剪表格"""
        pass
    
    def extract_chart_as_image(self, pdf_path: Path, page: int, rect: tuple) -> bytes:
        """从 PDF 指定坐标裁剪图表"""
        pass
```

---

### 4.4 Phase 4: 检查与审批 (Week 8-9)

#### 4.1 字段完整性检查
```python
class FieldChecker:
    """按报告类型检查必填字段"""
    
    REQUIRED_FIELDS = {
        "company": ["ticker", "rating", "target_price", "analysts"],
        "sector": ["region", "sector"],
        "common": ["region", "report_language", "title"],
        "company_flash": ["ticker"],
        "sector_flash": ["region", "sector"]
    }
    
    def check(self, report_type: str, elements: dict) -> CheckResult:
        pass
```

#### 4.3 文件相似度检查
```python
def similarity(s1: str, s2: str) -> float:
    """1 - 莱文斯坦距离 / 最大字符串长度"""
    distance = levenshtein(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1 - (distance / max_len)
```

---

### 4.5 Phase 5: 高级功能 (Week 10-12)

#### 5.1 标题自动生成
```python
def generate_title(company: str, ticker: str, report_type: str, 
                   rating_change: str, tp_change: float) -> str:
    """业务规则引擎"""
    if report_type == "first_coverage":
        return f"{company} ({ticker}): 首次覆盖: {title}"
    elif rating_change and tp_change:
        return f"{company} ({ticker}): {title}—{action}{rating}; {tp_action}{tp_change}%"
    # ... 更多规则见 CLAUDE.md
```

#### 5.2 股价图生成
```python
class StockChartGenerator:
    """生成股价走势图"""
    
    def generate_price_chart(self, ticker: str, days: int = 365) -> bytes:
        """生成涨跌幅走势图（起点100）"""
        pass
    
    def generate_volume_chart(self, ticker: str, days: int = 365) -> bytes:
        """生成 Volume 柱状图"""
        pass
```

---

## 五、里程碑定义

| 里程碑 | 完成时间 | 验收标准 |
|--------|---------|---------|
| M1: 基础设施 | Week 2 结束 | 项目可运行，YAML/文件模块可用 |
| M2: 模板管理 | Week 4 结束 | 可上传样本，生成 schema |
| M3: 报告生成 | Week 7 结束 | 完整流程：草稿→标准报告 |
| M4: 检查审批 | Week 9 结束 | 字段检查、SFC验证、审批流 |
| M5: 高级功能 | Week 12 结束 | 标题生成、图表、StockList |

---

## 六、技术依赖矩阵

| 任务 | 依赖项 | 前置任务 |
|------|--------|---------|
| 2.1 样本上传 | 1.5 文件操作 | 1.x |
| 2.2 Word解析 | 1.3 YAML管理 | 1.x |
| 3.1 草稿解析 | 1.4 LLM客户端 | 1.x |
| 3.3 要素提取 | 3.1 + 2.3 | 3.1, 2.3 |
| 3.5 模板渲染 | 2.2 | 2.2 |
| 4.1 字段检查 | 3.3 | 3.3 |
| 5.2 股价图 | 3.x 完成 | M3 |

---

## 七、风险与预案

| 风险 | 影响 | 预案 |
|------|------|------|
| LLM 调用不稳定 | 提取失败 | 增加重试机制，支持手动确认 |
| Word 格式复杂 | 解析不完整 | 分阶段处理，支持模板约定 |
| 图表提取失败 | 信息丢失 | 降级为文本描述 |
| 多人协作冲突 | 数据覆盖 | 使用 workspace 隔离 |

---

## 八、开发检查清单

### 每周检查项
- [ ] 代码符合项目规范
- [ ] 单元测试覆盖新功能
- [ ] 更新相关文档
- [ ] 与其他模块集成测试

### 发布检查项
- [ ] 所有 P0 功能测试通过
- [ ] P1 功能基本可用
- [ ] 文档更新完毕
- [ ] 无阻塞性问题

---

**文档结束**

下一步行动：确认排期 → 开始 Phase 1 开发
