# Session Notes: 2026-03-24

## 概述

本 session 完成 **template-maker skill** 的开发、标准化重构和功能增强，包括：
- 完整的设计和实施（前一个 session）
- 符合 Anthropic Agent Skills Open Standard 的重构
- 添加调用接口和抽取规则支持
- 项目编码规范更新

---

## 一、核心设计决策

### 1.1 架构模式：混合模式

**提示词负责**：
- 分析 Word 文档结构
- 生成 schema.yaml 内容
- 识别动态内容区域

**代码负责**：
- 文件 I/O（读写、替换）
- 占位符替换
- 验证测试

### 1.2 Schema 极简设计

只保留三个属性：
```yaml
fields:
  report_date:
    description: 报告日期
    format: "21 Oct 2025"
```

**不包含**：
- `required` - 运行时校验逻辑
- `type` - 第一版不需要强类型
- `version` - git 已管理
- `default` - 可在模板层面处理

### 1.3 对话式交互

```
用户: /template-maker
系统: 模板名称是什么？
用户: 西锐飞机首次覆盖
系统: Word 样本在哪里？
用户: ./samples/sample.docx
系统: elements.yaml 在哪里？[自动检测]
```

### 1.4 elements.yaml 自动检测约定

**优先级顺序**：
1. `<word_name> elements.yaml`
2. `<word_name>_elements.yaml`
3. 目录下的 `elements.yaml`

### 1.5 报告三部分结构

根据 `docs/skills-report.md`，报告包含：
- **elements** - 结构化字段（公司名、股票代码等）
- **abstract** - 摘要部分
- **body** - 正文部分

**schema.yaml 新增 extraction_rules**：
```yaml
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

---

## 二、Skills 职责划分

### 2.1 template-maker 职责

**负责目录**：`templates/`

**职责**：
- 创建和维护 `template.docx`（正式排版模板）
- 生成和维护 `schema.yaml`（提取规则 + extraction_rules）
- 维护 `meta.yaml`（模板元数据）
- 维护 `router.yaml`（路由配置）
- 执行模板验证测试

**不负责**：
- 处理单篇报告
- 写入 `reports/` 目录

### 2.2 report-maker 职责

**负责目录**：`reports/`

**职责**：
- 接收草稿、识别报告类型
- 抽取 `elements.yaml`、`abstract.docx`、`body.docx`
- 两阶段流程：抽取与确认 → 渲染与输出
- 生成 `output.docx` 和 `output.pdf`

**不负责**：
- 修改正式模板
- 写入 `templates/` 目录

---

## 三、Anthropic Skills 标准化

### 3.1 SKILL.md 格式要求

**必需的 YAML frontmatter**：
```yaml
---
name: template-maker
description: 创建和维护分析师报告模板...
---
```

**description 字段要求**：
- 包含 skill 的功能说明
- 包含使用场景和触发条件
- 不要在 body 中重复"when to use"

### 3.2 标准 Skill 目录结构

```
skill-name/
├── SKILL.md              # 必需，在根目录
└── scripts/              # 代码目录
    ├── core.py
    ├── parser.py
    └── ...
```

**不应包含**：
- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md

### 3.3 开发规范

**新增到 AGENTS.md**：
```markdown
### Skills 开发

- **严格遵循 Anthropic Agent Skills Open Standard**
  官方文档：https://agentskills.io/home

- **使用 skill-creator skill 开发**
  - 创建或修改 skill 前，必须先调用 skill-creator
  - 使用 init_skill.py 初始化
  - 使用 package_skill.py 验证和打包
```

---

## 四、技术实现

### 4.1 代码模块

```
skills/template_maker/
├── SKILL.md              # Skill 定义（含 YAML frontmatter）
└── scripts/
    ├── __init__.py
    ├── core.py           # 核心编排器 TemplateMaker
    ├── invoke.py         # CLI 调用入口
    ├── parser.py         # Word 文档分析器
    ├── schema_gen.py     # Schema 生成器（含 extraction_rules）
    ├── template_builder.py
    ├── router_mgr.py
    ├── validator.py
    ├── utils.py          # 含 find_elements_yaml()
    └── requirements.txt
```

### 4.2 调用接口

**CLI 入口** (`scripts/invoke.py`)：

对话式模式：
```bash
python3 skills/template_maker/scripts/invoke.py
```

命令行模式：
```bash
python3 skills/template_maker/scripts/invoke.py \
  --name "西锐飞机首次覆盖" \
  --word "samples/sample.docx"
```

### 4.3 SchemaGenerator 更新

**方法签名变更**：
```python
def generate(self, elements: Dict[str, Any], template_name: str = "") -> Dict[str, Any]
```

**新增 extraction_rules 生成**：
```python
def _get_extraction_rules(self) -> Dict[str, Any]:
    return {
        "abstract": {
            "description": "报告摘要部分",
            "scope": "从报告开头到第一个一级标题之前",
            "hints": [...]
        },
        "body": {...}
    }
```

---

## 五、关键 Git 提交

### 5.1 主要提交记录

| 提交 | 说明 |
|------|------|
| 773b6b8 | feat: 在 schema.yaml 中添加抽取规则，支持摘要和正文处理 |
| 5994cc7 | fix: 从 SKILL.md 移除职责边界说明 |
| 24182cb | feat: 添加 template-maker skill 调用接口 |
| a3e587a | chore: 添加本地 skill 安装目录到 gitignore |
| 15efa5b | fix: 删除 template-maker skill 中不符合规范的 README.md |
| 974d10b | chore: 删除测试残留的模板数据 |
| 0767b13 | refactor: 重构 template-maker skill 为标准 skill 结构 |
| adca9f6 | docs: 添加 Skills 开发标准到 AGENTS.md |
| 6c4338a | Merge feature/template-maker into main |

### 5.2 删除的测试数据

删除了 `templates/` 下的测试模板：
- `template_1/`, `template_2/`
- `test_template/`, `test_template_auto/`

**原因**：pytest 测试时创建的临时数据，不应在正式目录

---

## 六、项目配置更新

### 6.1 AGENTS.md 新增

```markdown
### Skills 开发

- **严格遵循 Anthropic Agent Skills Open Standard**
  - 官方文档：https://agentskills.io/home
  - 官方仓库：https://github.com/anthropics/skills
  - 完整指南：https://resources.anthropic.com/.../Building-Skill-for-Claude.pdf

- **使用 skill-creator skill 开发**
  - 创建或修改 skill 前必须先调用 skill-creator
  - 使用 init_skill.py 初始化目录结构
  - 使用 package_skill.py 验证和打包
```

### 6.2 .gitignore 更新

```bash
# Test templates (ignore test-only templates, not real ones)
templates/test_*/
templates/template_[0-9]*/

# Local skill installation
~/.claude/skills/
```

---

## 七、下一步

### 7.1 待办事项

- [ ] 推送到远程 `git push origin main`
- [ ] 开发 **report-maker** skill（新 session）

### 7.2 Report-Maker 关键点

**参考文档**：`docs/skills-report.md`

**两阶段流程**：
1. 抽取与确认（等待 Editor 检查）
2. 渲染与输出（生成最终文档）

**关键决策**（待确认）：
- 对话式交互方式
- 两阶段暂停的实现
- 草稿解析复杂度
- LLM 辅助程度

---

## 八、参考文档

| 文档 | 路径 | 用途 |
|------|------|------|
| 系统设计 | `docs/skills-report.md` | 主文档，需求和设计 |
| 设计文档 | `docs/skills-template-maker-design.md` | template-maker 设计 |
| 实施计划 | `docs/superpowers/plans/2026-03-24-template-maker.md` | 实施步骤 |
| 编码规范 | `AGENTS.md` | Python 编码原则 + Skills 开发标准 |
| Skills 标准 | https://agentskills.io/home | Anthropic Agent Skills Open Standard |

---

## 九、经验总结

### 9.1 做得好的地方

1. **遵循标准**：使用 skill-creator 指导开发
2. **代码重构**：从非标准结构重构为标准结构
3. **职责清晰**：明确两个 skills 的边界
4. **测试清理**：删除测试残留数据

### 9.2 教训

1. **先读文档再动手**
   - 没有认真读 `docs/skills-report.md` 就开始实现
   - 导致后来才发现职责边界问题

2. **文档层级理解**
   - 系统架构设计 → 项目级文档（docs/skills-report.md）
   - 单个 skill 使用方法 → SKILL.md
   - 不应混淆

3. **验证标准**
   - 实现后再检查是否符合标准，浪费时间
   - 应该在开始前确认标准要求

---

## Session 统计

- **日期**: 2026-03-24
- **持续时间**: 约 4.5 小时（两个 session）
- **完成内容**:
  - 1 个完整 skill (template-maker)
  - 符合 Anthropic Agent Skills Open Standard
  - 支持报告三部分结构（elements + abstract + body）
  - CLI 调用接口
  - 项目编码规范更新
- **Git 提交**: 20+ 个提交
