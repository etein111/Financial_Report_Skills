# template-maker 设计文档

**日期**: 2026-03-24
**状态**: 设计中
**版本**: 1.0

---

## 1. 概述

### 1.1 目标

`template-maker` 是分析师报告自动化系统的核心技能之一，负责：
- 从标准 Word 样本创建可复用的报告模板
- 通过自然语言维护模板和提取规则
- 管理报告类型到模板的路由映射

### 1.2 设计原则

- **业务友好**：YAML 格式简洁，业务人员可读
- **对话式交互**：零学习成本，通过自然语言完成所有操作
- **职责单一**：只负责模板资产，不处理单篇报告

---

## 2. 核心功能与边界

### 2.1 职责（做什么）

| 功能 | 描述 |
|------|------|
| 创建新模板 | 解析 Word 样本 + elements.yaml，生成模板资产 |
| 维护模板 | 通过对话添加/删除字段，同步更新 schema 和模板 |
| 管理路由 | 维护 router.yaml（报告类型 → 模板名映射） |
| 验证模板 | 执行最小渲染测试，确保模板可用 |

### 2.2 边界（不做什么）

- 不处理单篇报告（不写入 `/reports/`）
- 不直接修改已存在的报告目录
- 不负责最终的报告渲染（由 `report-maker` 负责）

---

## 3. 目录结构

```
neoskills/
├── skills/
│   └── template-maker/
│       ├── SKILL.md              # Skill 定义文件
│       ├── __init__.py
│       ├── core.py               # 核心逻辑
│       ├── parser.py             # Word 解析器
│       ├── validator.py          # 模板验证器
│       └── utils.py              # 工具函数
│
├── templates/                    # 由 template-maker 写入
│   ├── router.yaml               # 路由配置
│   └── common/                   # 模板目录（按模板名组织）
│       ├── schema.yaml           # 提取规则
│       ├── template.docx         # 排版模板
│       └── meta.yaml             # 元数据
│
└── samples/                      # 用户样本文件（只读）
    └── 西锐飞机首次覆盖报告（中文）提交版 elements.yaml
```

---

## 4. 核心数据结构

### 4.1 schema.yaml（提取规则）

**极简设计，只保留必要属性：**

```yaml
# schema.yaml
fields:
  report_date:
    description: 报告日期
    format: "21 Oct 2025"  # 日 月 年

  company:
    description: 公司名称
    format: "西锐飞机"  # 中英文全称

  ticker:
    description: 股票代码
    format: "700.HK"  # 或 "VRT US"

  title:
    description: 报告标题
    # 无固定格式，省略 format

  rating:
    description: 评级
    format: "优于大市"  # 中文或英文

  target_price:
    description: 目标价
    format: "11.12美元（对应港币86.72元）"

  current_price:
    description: 现价
    format: "340.80"

  market_cap:
    description: 市值
    format: "10000亿港元"
```

**字段说明：**
- `name`: 字段标识符
- `description`: 字段含义，帮助 AI 理解
- `format`: 格式示例（可选），告诉 AI 提取标准

**设计原则：**
- 不需要 `format` 的字段可以省略
- 不包含必填校验（`required`），这是运行时逻辑
- 不包含版本信息，由 git 管理

### 4.2 router.yaml（路由配置）

```yaml
# 报告类型 → 模板名映射
mappings:
  company: common
  company_flash: common
  sector: common
  sector_flash: common
  macro: common
  strategy: common
  quantitative: common
  bond: common
```

### 4.3 meta.yaml（模板元数据）

```yaml
name: common
display_name: 通用模板
version: 1.0.0
status: active
created_at: "2026-03-24"
updated_at: "2026-03-24"
sample_source: "西锐飞机首次覆盖报告（中文）提交版.docx"
```

---

## 5. 交互流程

### 5.1 创建新模板

```
用户: /template-maker

系统: 好的，我来帮你创建模板。请提供以下信息：
1. 模板名称是什么？（如：common）

用户: common

系统: 好的，模板名称是 common。
2. Word 样本文件在哪里？

用户: /mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx

系统: 收到。正在解析样本文件...
   [使用 python-docx 读取文档结构]

3. elements.yaml 文件在哪里？

用户: /mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告 elements.yaml

系统: 收到。正在分析字段定义...
   [读取 elements.yaml]
   [生成 schema.yaml]
   [生成 template.docx]
   [生成 meta.yaml]
   [更新 router.yaml]

✅ 模板创建成功！
   - 模板目录：/mnt/c/_code/neoskills/templates/common/
   - 字段数量：15
   - 已更新路由配置

是否要进行验证测试？
```

### 5.2 维护模板（添加字段）

```
用户: 给 common 模板添加一个"风险提示"字段

系统: 好的，我来添加"风险提示"字段。

   请提供以下信息：
   1. 这个字段的格式要求是什么？

用户: 就是一段文字，放在附录前面

系统: 好的，我会：
   1. 在 schema.yaml 中添加 risk_warning 字段
   2. 在 template.docx 附录前插入占位符

   [生成变更预览]
   + risk_warning:
   +   description: 风险提示
   +   format: "文本段落"

确认应用这些变更吗？

用户: 确认

系统: ✅ 变更已应用。是否进行验证测试？
```

---

## 6. 技术实现要点

### 6.1 核心依赖

| 库 | 用途 |
|----|------|
| `python-docx` | Word 文档结构解析 |
| `python-docx-template` | Jinja2 模板占位符处理 |

### 6.2 LLM 能力复用

- **不调用外部 API**：直接复用 Claude Code 会话的 LLM 能力
- **文档解析**：使用 Read 工具读取 Word 样本
- **智能分析**：LLM 分析文档结构，识别动态内容区域

### 6.3 Word 处理流程

```
Word 样本 → python-docx 解析 → 识别动态内容 → 生成 Jinja2 占位符 → template.docx
                    ↓
              同时生成 schema.yaml（LLM 辅助）
```

---

## 7. 开发计划

### 7.1 第一阶段（MVP）

- [ ] 创建基础项目结构
- [ ] 实现对话式交互（创建模板）
- [ ] 实现 Word 样本解析
- [ ] 生成 schema.yaml
- [ ] 生成 template.docx
- [ ] 更新 router.yaml

### 7.2 第二阶段（增强）

- [ ] 实现字段添加/删除功能
- [ ] 实现模板验证测试
- [ ] 支持模板切换
- [ ] 错误处理和提示优化

---

## 8. 测试基准

**使用标准样本文件进行测试：**
- `/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx`
- `/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版 elements.yaml`

---

## 9. 附录：设计决策记录

### 9.1 为什么 schema 这么简单？

**决策**：只保留 `name`、`description`、`format` 三个属性

**理由**：
1. **不包含 `required`**：提取规则应该只关注"提取什么"，校验是运行时逻辑
2. **不包含版本信息**：git 已有版本管理
3. **不包含 `type`**：第一版不需要强类型，后期可扩展
4. **`format` 独立**：结构化清晰，比嵌入 description 更易理解和维护

### 9.2 为什么选择对话式交互？

**决策**：`/template-maker` 触发，所有参数通过对话询问

**理由**：
1. 零学习成本，业务人员无需记忆命令参数
2. 自然语言引导，按需填写
3. 符合"业务人员自主配置"的目标

### 9.3 为什么使用 python-docx + python-docx-template？

**决策**：职责分离，两个库配合使用

**理由**：
1. `python-docx` 负责文档结构解析（识别表格、段落）
2. `python-docx-template` 负责模板占位符（基于 Jinja2）
3. 与 `report-maker` 技术栈保持一致
4. 成熟稳定，文档完善
