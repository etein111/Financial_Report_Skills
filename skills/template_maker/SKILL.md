# template-maker

创建和维护分析师报告模板。

## 功能

template-maker skill 可以自动创建和维护分析师报告模板，包括：
- 分析 Word 文档结构
- 生成模板 schema.yaml
- 创建 template.docx 模板文件
- 维护 router.yaml 路由配置
- 验证模板可用性

## 用法

### 创建新模板

```
/template-maker
```

然后按提示提供：
1. 模板名称（如：西锐飞机首次覆盖）
2. Word 样本文件路径
3. elements.yaml 文件路径（可选，系统会自动检测同目录）

### 维护模板

```
给 <模板名> 添加一个 <字段名> 字段
```

示例：
```
给 西锐飞机首次覆盖 添加一个 target_price 字段
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

- `parser.py`: Word 文档结构分析器
- `schema_gen.py`: Schema 生成器
- `template_builder.py`: 模板构建器
- `router_mgr.py`: 路由管理器
- `validator.py`: 模板验证器
- `core.py`: 核心编排器
- `utils.py`: 工具函数
