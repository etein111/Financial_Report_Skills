# Template Maker Skill

分析师报告模板自动生成工具。

## 概述

Template Maker 是一个 neoskills skill，用于自动化创建和维护分析师报告模板。它能够分析 Word 文档结构，生成标准的模板文件，并维护路由配置。

## 功能特性

- **自动分析**: 分析 Word 文档结构，识别表格和段落
- **Schema 生成**: 自动生成字段 schema.yaml
- **模板创建**: 生成可用于 Jinja2 渲染的 template.docx
- **路由管理**: 自动更新 router.yaml 配置
- **模板验证**: 验证模板与 elements 的兼容性

## 安装

```bash
pip install -r scripts/requirements.txt
```

依赖：
- python-docx: Word 文档处理
- docxtpl: Word 模板渲染
- PyYAML: YAML 配置文件处理

## 快速开始

### 1. 创建新模板

```python
from skills.template_maker.scripts.core import TemplateMaker
from pathlib import Path

# 初始化
maker = TemplateMaker(project_root=Path.cwd())

# 创建模板
result = maker.create_template(
    name="西锐飞机首次覆盖",
    word_path=Path("samples/西锐飞机首次覆盖报告.docx"),
    elements_path=Path("samples/西锐飞机 elements.yaml")
)

print(result)
# {'status': 'success', 'template_dir': '...', 'fields_count': 10}
```

### 2. 验证模板

```python
from skills.template_maker.scripts.validator import TemplateValidator

validator = TemplateValidator()
success, message = validator.validate(
    template_path=Path("templates/西锐飞机首次覆盖/template.docx"),
    elements_path=Path("samples/西锐飞机 elements.yaml")
)
```

### 3. 管理路由

```python
from skills.template_maker.scripts.router_mgr import RouterManager

router = RouterManager(Path("templates/router.yaml"))
router.add_mapping("company", "西锐飞机首次覆盖")
router.remove_mapping("company", "旧模板")
```

## 目录结构

```
skills/template_maker/
├── SKILL.md             # Skill 定义文件
├── README.md            # 本文档
└── scripts/             # 代码模块
    ├── __init__.py
    ├── core.py              # 核心编排器
    ├── parser.py            # Word 文档分析器
    ├── schema_gen.py        # Schema 生成器
    ├── template_builder.py  # 模板构建器
    ├── router_mgr.py        # 路由管理器
    ├── validator.py         # 模板验证器
    ├── utils.py             # 工具函数
    └── requirements.txt
```

## 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定模块测试
pytest tests/test_core.py -v

# 查看覆盖率
pytest tests/ --cov=skills/template_maker/scripts --cov-report=html
```

## 配置文件

### router.yaml

模板路由配置：

```yaml
mappings:
  company:
    - 西锐飞机首次覆盖
    - 其他公司报告
  industry:
    - 航空行业报告
```

### meta.yaml

模板元数据：

```yaml
name: 西锐飞机首次覆盖
display_name: 西锐飞机首次覆盖报告模板
version: 1.0.0
status: active
sample_source: /path/to/sample.docx
```

### schema.yaml

字段 schema 定义：

```yaml
name: 西锐飞机首次覆盖
display_name: 西锐飞机首次覆盖报告模板
version: 1.0.0
fields:
  company:
    type: string
    format: 西锐飞机
    description: 公司名称
    required: true
  ticker:
    type: string
    format: 2507.HK
    description: 股票代码
    required: true
```

## 开发指南

### 添加新模块

1. 在 `skills/template_maker/scripts/` 创建新模块
2. 在 `tests/` 创建对应测试文件
3. 保持 80%+ 测试覆盖率
4. 运行 `pytest` 验证

### 代码风格

- 遵循 PEP 8
- 使用类型注解
- 编写文档字符串
- 保持函数简短（<50 行）

## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可

MIT License
