---
name: template-maker
description: 创建和维护分析师报告模板。当用户需要创建新模板、分析 Word 文档结构生成 schema、维护现有模板字段或验证模板时使用此 skill。支持对话式参数收集和自动检测 elements.yaml 配置文件
---

# template-maker

创建和维护分析师报告模板。

## 工作流程

当用户请求创建或维护模板时，按以下步骤执行：

### 步骤 1: 收集必要信息

对话式询问以下信息：

1. **模板名称**（必需）
   - 示例："西锐飞机首次覆盖"、"航空行业报告"
   - 提示："请输入模板名称"

2. **Word 样本文件路径**（必需）
   - 示例：`samples/西锐飞机首次覆盖报告.docx`
   - 验证文件存在性
   - 提示："请提供 Word 样本文件路径"

3. **elements.yaml 文件路径**（可选）
   - 如果不提供，系统将自动检测：
     - `<word_dir>/<word_name> elements.yaml`
     - `<word_dir>/<word_name>_elements.yaml`
     - `<word_dir>/elements.yaml`
   - 提示："请输入 elements.yaml 路径（留空自动检测）"

### 步骤 2: 执行创建

使用 `scripts/invoke.py` 执行模板创建：

```bash
cd /mnt/c/_code/neoskills
python3 skills/template-maker/scripts/invoke.py \
  --name "模板名称" \
  --word "path/to/sample.docx" \
  --elements "path/to/elements.yaml"
```

或使用对话式模式：

```bash
python3 skills/template-maker/scripts/invoke.py
```

### 步骤 3: 验证结果

成功后会创建以下文件结构：

```
templates/
├── router.yaml           # 自动更新路由配置
└── <模板名>/
    ├── meta.yaml         # 模板元数据
    ├── schema.yaml       # 字段 schema
    └── template.docx     # Word 模板文件
```

## 使用示例

### 示例 1: 创建新模板

用户：`创建一个西锐飞机首次覆盖的模板`

流程：
1. 询问模板名称 → "西锐飞机首次覆盖"
2. 询问 Word 文件 → `samples/西锐飞机首次覆盖报告.docx`
3. 询问 elements.yaml → 用户留空（自动检测）
4. 执行创建
5. 报告结果

### 示例 2: 命令行调用

```bash
python3 skills/template-maker/scripts/invoke.py \
  --name "西锐飞机首次覆盖" \
  --word "samples/西锐飞机首次覆盖报告.docx"
```

## 技术细节

### schema.yaml 结构

生成的 schema.yaml 包含三部分：

```yaml
name: 模板名称
display_name: 模板显示名称
version: 1.0.0
fields:
  company:
    description: 公司名称
    format: 西锐飞机
  ticker:
    description: 股票代码
    format: 2507.HK

extraction_rules:
  abstract:
    description: 报告摘要部分
    scope: 从报告开头到第一个一级标题之前
    hints:
      - 通常包含投资亮点、核心观点
      - 长度约 200-500 字
  body:
    description: 报告正文部分
    scope: 从第一个一级标题之后到报告结尾
    hints:
      - 包含各章节详细内容
      - 可能包含表格、图表引用
```

注意：`extraction_rules` 供 report-maker skill 使用，定义如何从草稿中抽取摘要和正文。

### 自动检测逻辑

系统按以下顺序查找 `elements.yaml`：

1. `<word_name> elements.yaml`
2. `<word_name>_elements.yaml`
3. `elements.yaml`（同目录）

### 代码模块

- `scripts/core.py`: 核心编排器 TemplateMaker
- `scripts/invoke.py`: CLI 调用入口
- `scripts/parser.py`: Word 文档分析器
- `scripts/schema_gen.py`: Schema 生成器（包含 extraction_rules）
- `scripts/router_mgr.py`: 路由管理器
- `scripts/validator.py`: 模板验证器
- `scripts/utils.py`: 工具函数

### 依赖安装

```bash
pip install -r skills/template-maker/scripts/requirements.txt
```

## 模板目录结构

```
templates/
├── router.yaml           # 路由配置
└── <模板名>/
    ├── meta.yaml         # 模板元数据
    ├── schema.yaml       # 字段 schema
    └── template.docx     # Word 模板文件
```

## elements.yaml 格式

```yaml
company: 西锐飞机
ticker: 2507.HK
target_price: 15.0
rating: 买入
```

## 生成的 schema.yaml 格式

```yaml
name: 模板名称
display_name: 模板显示名称
version: 1.0.0
fields:
  company:
    type: string
    format: 西锐飞机
    description: 公司名称
  ticker:
    type: string
    format: 2507.HK
    description: 股票代码
```

## 模块说明

本 skill 的代码模块位于 `scripts/` 目录：

- `scripts/parser.py`: Word 文档结构分析器
- `scripts/schema_gen.py`: Schema 生成器
- `scripts/template_builder.py`: 模板构建器
- `scripts/router_mgr.py`: 路由管理器
- `scripts/validator.py`: 模板验证器
- `scripts/core.py`: 核心编排器
- `scripts/utils.py`: 工具函数
