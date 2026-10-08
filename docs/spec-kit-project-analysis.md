# Spec Kit 项目技术文档

## 一、项目概述

### 1.1 项目定位

**Spec Kit** 是 GitHub 官方推出的**规范驱动开发（Spec-Driven Development, SDD）工具包**，旨在帮助开发者通过规范文档来构建高质量软件。它将传统的"代码优先"模式转变为"规范优先"——规范成为可执行的，直接生成可工作的实现而不是仅仅指导实现。

> **项目数据**：⭐ 78.7k Stars | 6.7k Forks | 650 Commits

### 1.2 核心理念

**SDD 的核心变革**：

| 传统模式 | SDD 模式 |
|---------|---------|
| 代码是真理 | 规范是真理 |
| 规范服务代码 | 代码服务规范 |
| PRD 是开发的附属品 | PRD 是生成的源头 |
| 代码即资产 | 规范即资产 |

### 1.3 核心价值

| 特性 | 描述 |
|------|------|
| **规范优先** | 规范成为可执行的艺术品 |
| **多代理支持** | 支持 20+ 种 AI 编码工具 |
| **模板驱动** | 结构化模板引导 LLM 行为 |
| **宪法约束** | 九条开发原则确保架构纪律 |
| **扩展系统** | 扩展和预设机制高度可定制 |

---

## 二、技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户/开发者                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Specify CLI                               │
│  specify init | specify check | extension | preset           │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ Constitution │  │   Spec      │  │  Extensions │
    │ (九条原则)   │  │   (规范)    │  │   (扩展)    │
    └─────────────┘  └─────────────┘  └─────────────┘
           │               │               │
           ▼               ▼               ▼
    ┌─────────────────────────────────────────────────────────┐
    │              AI Coding Agent                            │
    │  /speckit.constitution → /speckit.specify →          │
    │  /speckit.plan → /speckit.tasks → /speckit.implement │
    └─────────────────────────────────────────────────────────┘
```

### 2.2 核心命令体系

| 命令 | 功能 |
|------|------|
| `/speckit.constitution` | 创建项目治理原则和开发指南 |
| `/speckit.specify` | 定义要构建的内容（需求和用户故事） |
| `/speckit.plan` | 创建技术实现计划 |
| `/speckit.tasks` | 生成可执行任务列表 |
| `/speckit.implement` | 执行所有任务 |
| `/speckit.clarify` | 澄清不明确区域 |
| `/speckit.analyze` | 跨制品一致性分析 |

### 2.3 支持的 AI 代理

| 代理 | 状态 | 说明 |
|------|------|------|
| Claude Code | ✅ | |
| Claude Code | ✅ | |
| Gemini CLI | ✅ | |
| Codex CLI | ✅ | 需要 --ai-skills |
| Cursor | ✅ | |
| Windsurf | ✅ | |
| OpenCode | ✅ | |
| GitHub Copilot | ✅ | |
| Amp | ✅ | |
| Auggie | ✅ | |
| Kiro CLI | ✅ | |
| Qwen Code | ✅ | |
| Roo Code | ✅ | |
| Tabnine CLI | ✅ | |
| Mistral Vibe | ✅ | |
| Kimi Code | ✅ | |
| iFlow CLI | ✅ | |
| Pi Coding Agent | ✅ | |
| Antigravity | ✅ | 需要 --ai-skills |
| Trae | ✅ | |
| Generic | ✅ | 支持自定义代理 |

---

## 三、核心工作流详解

### 3.1 完整开发流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    规范驱动开发流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ 1. Constitution │ ← 创建项目治理原则                          │
│  │ /speckit.       │   (代码质量、测试标准、UX一致性)             │
│  │ constitution    │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                           │
│  │ 2. Specify      │ ← 定义需求                                  │
│  │ /speckit.      │   (WHAT & WHY，非 HOW)                    │
│  │ specify         │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                           │
│  │ 3. Plan         │ ← 技术实现计划                              │
│  │ /speckit.plan  │   (技术栈选择、架构决策)                    │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                           │
│  │ 4. Tasks        │ ← 生成任务列表                              │
│  │ /speckit.tasks │   (可执行的任务，带并行标记)                 │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                           │
│  │ 5. Implement    │ ← 执行实现                                  │
│  │ /speckit.      │   (按计划构建)                             │
│  │ implement       │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                           │
│  │ 6. Analyze      │ ← (可选) 一致性分析                        │
│  │ /speckit.      │   验证需求完整性和一致性                    │
│  │ analyze         │                                           │
│  └─────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 关键阶段详解

#### 3.2.1 Constitution（宪法阶段）

使用 `/speckit.constitution` 创建项目治理原则：

```
/speckit.constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements
```

**九条开发原则（Articles）**：

| Article | 原则 | 说明 |
|---------|------|------|
| I | Library-First | 每个功能必须从独立库开始 |
| II | CLI Interface | 每个库必须暴露 CLI 接口 |
| III | Test-First | 代码前必须先写测试（不可协商） |
| VII | Simplicity | 最多 3 个项目，无过度设计 |
| VIII | Anti-Abstraction | 直接使用框架，不过度抽象 |
| IX | Integration-First | 使用真实环境测试 |

#### 3.2.2 Specify（规范阶段）

使用 `/speckit.specify` 描述要构建的内容：

```
/speckit.specify Build an application that can help me organize my photos in separate photo albums. Albums are grouped by date and can be re-organized by dragging and dropping on the main page.
```

**关键约束**：
- ✅ 关注 WHAT（用户需要什么）和 WHY（为什么）
- ❌ 避免 HOW（如何实现）- 不指定技术栈、API、代码结构
- 标记 `[NEEDS CLARIFICATION]` 明确不确定性

**自动生成**：
- 分支创建（`specs/001-feature-name/`）
- Feature 编号
- 结构化规范模板

#### 3.2.3 Plan（计划阶段）

使用 `/speckit.plan` 创建技术实现计划：

```
/speckit.plan The application uses Vite with minimal number of libraries. Use vanilla HTML, CSS, and JavaScript as much as possible. Images are not uploaded anywhere and metadata is stored in a local SQLite database.
```

**Phase -1 预实现门控**：

```markdown
### Phase -1: Pre-Implementation Gates

#### Simplicity Gate (Article VII)
- [ ] Using ≤3 projects?
- [ ] No future-proofing?

#### Anti-Abstraction Gate (Article VIII)
- [ ] Using framework directly?
- [ ] Single model representation?

#### Integration-First Gate (Article IX)
- [ ] Contracts defined?
- [ ] Contract tests written?
```

#### 3.2.4 Tasks（任务阶段）

使用 `/speckit.tasks` 生成可执行任务列表：

- 读取 `plan.md`、`data-model.md`、`contracts/`、`research.md`
- 转换为具体任务
- 标记独立任务 `[P]`
- 输出 `tasks.md`

#### 3.2.5 Implement（执行阶段）

使用 `/speckit.implement` 执行所有任务：

**文件创建顺序**：
1. 创建 `contracts/` (API 规范)
2. 按顺序创建测试：contract → integration → e2e → unit
3. 创建源文件使测试通过

---

## 四、核心技术特性

### 4.1 模板驱动的质量保证

Spec Kit 的模板不仅自动化，还通过结构化约束引导 LLM 产生高质量输出：

| 约束机制 | 作用 |
|---------|------|
| **防止过早实现细节** | 强制保持 WHAT/WHY 与 HOW 分离 |
| **强制不确定性标记** | `[NEEDS CLARIFICATION]` 防止假设 |
| **结构化清单** | 作为规范的"单元测试" |
| **宪法合规门控** | Phase -1 强制架构原则 |
| **分层信息管理** | 保持计划可读，细节分离 |
| **测试优先** | 强制测试优先于实现 |
| **防止推测** | 禁止"可能需要"的功能 |

### 4.2 扩展系统（Extensions）

使用 **扩展** 添加新功能：

```bash
# 搜索可用扩展
specify extension search

# 安装扩展
specify extension add <extension-name>
```

扩展可添加：
- Jira 集成
- 代码审查
- V-Model 测试可追溯性
- 项目健康诊断

### 4.3 预设系统（Presets）

使用 **预设** 自定义工作流：

```bash
# 搜索可用预设
specify preset search

# 安装预设
specify preset add <preset-name>
```

预设可实现：
- 合规导向的规范格式
- 领域特定术语
- 组织标准
- 工作流本地化（如海盗语言示例）

### 4.4 优先级加载

```
⬆ 最高优先级
  项目本地覆盖 (.specify/templates/overrides/)
预设 (.specify/presets/<preset-id>/templates/)
扩展 (.specify/extensions/<ext-id>/templates/)
核心 (.specify/templates/)
⬇ 最低优先级
```

---

## 五、安装与配置

### 5.1 安装 Specify CLI

#### 方式 1：持久安装（推荐）

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# 创建新项目
specify init <PROJECT_NAME>

# 或在现有项目中初始化
specify init . --ai claude
```

#### 方式 2：一次性使用

```bash
# 创建新项目
uvx --from git+https://github.com/github/spec-kit.git specify init <PROJECT_NAME>

# 或在现有项目中初始化
uvx --from git+https://github.com/github/spec-kit.git specify init . --ai claude
```

### 5.2 前置条件

- Linux/macOS/Windows
- 支持的 AI 编码代理
- uv（包管理）
- Python 3.11+
- Git

### 5.3 常用命令示例

```bash
# 基础项目初始化
specify init my-project

# 使用特定 AI 助手
specify init my-project --ai claude
specify init my-project --ai cursor-agent
specify init my-project --ai windsurf
specify init my-project --ai codex --ai-skills

# 在当前目录初始化
specify init . --ai copilot

# 强制合并到非空目录
specify init . --force --ai copilot

# 跳过 Git 初始化
specify init my-project --ai gemini --no-git

# 检查系统需求
specify check
```

---

## 六、与同类项目对比

### 6.1 架构差异对比

| 特性 | Spec Kit | Superpowers | GSD | Ralph |
|------|----------|-------------|-----|-------|
| **核心理念** | 规范优先，宪法约束 | 工程纪律优先 | 轻量级效率 | PRD 循环执行 |
| **规范形式** | 结构化模板 + 宪法 | 设计文档 | 阶段计划 | 用户故事 |
| **执行模式** | 任务列表执行 | 子代理评审 | 波次执行 | 迭代循环 |
| **质量保障** | 宪法门控 + 测试优先 | 强制 TDD | 验证步骤 | typecheck+tests |
| **支持代理** | 20+ 种 | 少数 | 少数 | Amp/Claude |
| **扩展性** | 扩展+预设 | 技能系统 | 无 | 无 |

### 6.2 理念差异可视化

```
Spec Kit:
┌─────────────────────────────────────────────┐
│  Constitution (9 Articles)                 │
│  ↓                                         │
│  Specify → Plan → Tasks → Implement        │
│  ↓                                         │
│  Phase -1 Gates (宪法门控)                  │
└─────────────────────────────────────────────┘

Superpowers:
┌─────────────────────────────────────────────┐
│  Skills (TDD, Debugging, Review)           │
│  ↓                                         │
│  Brainstorm → Plan → Execute → Review     │
│  ↓                                         │
│  强制 RED-GREEN-REFACTOR                   │
└─────────────────────────────────────────────┘

GSD:
┌─────────────────────────────────────────────┐
│  Context Engineering (文档)                 │
│  ↓                                         │
│  Discuss → Plan → Execute → Verify         │
│  ↓                                         │
│  Wave Execution (波次执行)                   │
└─────────────────────────────────────────────┘

Ralph:
┌─────────────────────────────────────────────┐
│  PRD (User Stories)                        │
│  ↓                                         │
│  Loop: Pick → Implement → Check → Commit  │
│  ↓                                         │
│  Fresh Context Each Iteration               │
└─────────────────────────────────────────────┘
```

---

## 七、优势分析

### 7.1 核心优势

| 优势 | 说明 |
|------|------|
| **规范即代码** | 消除规范与实现之间的鸿沟 |
| **宪法约束** | 九条原则确保架构纪律 |
| **多代理支持** | 20+ 种 AI 工具兼容 |
| **模板质量** | 结构化约束引导高质量输出 |
| **扩展系统** | 高度可定制 |
| **企业就绪** | 支持组织约束和合规要求 |
| **测试优先** | 强制先写测试再写代码 |

### 7.2 设计亮点

1. **九条规定** — 从库优先到 CLI 接口，从测试优先到反抽象
2. **Phase -1 门控** — 实现前强制检查架构原则
3. **模板约束** — 防止 LLM "作弊"，强制不确定性标记
4. **扩展+预设** — 插件化架构，高度灵活

---

## 八、劣势与挑战

| 挑战 | 说明 |
|------|------|
| **学习曲线** | 需要理解宪法九条规定和模板系统 |
| **复杂性** | 比 GSD/Ralph 更重的流程 |
| **模板依赖** | 输出质量依赖模板设计 |
| **灵活性** | 严格流程可能限制探索性开发 |
| **工具依赖** | 需要安装 Specify CLI |

---

## 九、应用场景

### 9.1 最佳适用场景

| 场景 | 为什么适合 |
|------|-----------|
| **企业级开发** | 宪法约束确保架构一致性 |
| **规范导向团队** | 规范即真理，代码服务规范 |
| **多技术栈** | 20+ 代理支持 |
| **合规项目** | 预设系统可强制合规要求 |
| **大型系统** | Phase -1 门控防止过度设计 |
| **测试优先** | 强制 TDD (Article III) |

### 9.2 不适用场景

- 快速原型探索（流程过于严格）
- 简单一次性任务
- 无测试基础设施的项目
- 探索性/实验性开发

---

## 十、社区示例

### 10.1 绿场项目示例

| 示例 | 技术栈 | 说明 |
|------|--------|------|
| .NET CLI 工具 | .NET | 从零构建时区工具 |
| Spring Boot + React | Spring Boot, React, PostgreSQL | LLM 性能分析平台 |
| Go/React Dashboard | Go, React | NASA Hermes 扩展 |

### 10.2 存量项目示例

| 示例 | 规模 | 说明 |
|------|------|------|
| ASP.NET CMS 扩展 | ~307k 行 | 扩展现有 CMS |
| Jakarta EE 运行时 | ~420k 行 | 多模块 Java 项目 |
| Go/React Dashboard | NASA 系统 | 终端驱动开发 |

---

## 十一、总结

Spec Kit 是 **GitHub 官方的规范驱动开发框架**，代表了 AI 辅助编程的"官方"方法论。

> **"规格成为可执行的，直接生成可工作的实现，而不是仅仅指导实现"**

其核心特点：
- **规范即源代码** — 消除规范与实现的鸿沟
- **宪法约束** — 九条原则确保架构纪律
- **模板驱动** — 结构化约束引导 LLM 行为
- **多代理支持** — 20+ 种 AI 工具兼容
- **扩展系统** — 高度可定制的插件架构

对于追求**规范优先**、需要**企业级架构约束**、希望保持**多技术栈兼容**的团队，Spec Kit 提供了一套经过 GitHub 官方验证的解决方案。

---

**参考资源**：
- 官网：https://github.com/github/spec-kit
- 文档：https://github.github.io/spec-kit/
- 视频概述：https://www.youtube.com/watch?v=a9eR1xsfvHg
- 交互式流程图：https://snarktank.github.io/ralph/
