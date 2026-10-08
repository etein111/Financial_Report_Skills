# Get Shit Done (GSD) 项目技术文档

## 一、项目概述

### 1.1 项目定位

**Get Shit Done (GSD)** 是一个**轻量级但强大的元提示工程（meta-prompting）、上下文工程（context engineering）和规范驱动开发系统**，由 TÂCHES 开发，主要用于 Claude Code、OpenCode、Gemini CLI、Codex、Copilot 和 Antigravity 等 AI 编码工具。

该项目解决了 AI 编程中的核心问题：**上下文腐化（Context Rot）**—— 即随着 Claude 上下文窗口填满，代码质量逐渐下降的问题。

> **项目数据**：⭐ 36.5k Stars | 3k Forks | 1,205 Commits

### 1.2 核心理念

GSD 的核心理念与 Superpowers 不同：

| 特性 | 描述 |
|------|------|
| **轻量级** | 无企业级流程（Sprint、Story Points、Jira） |
| **开发者友好** | 复杂度在系统内，不在工作流中 |
| **上下文管理** | 解决上下文窗口耗尽导致的代码质量下降 |
| **多平台支持** | 主流 AI 编程工具均可使用 |

> **"我不是 50 人的软件公司。我不想演企业戏。我只是一个试图构建伟大产品的创意人。"** — TÂCHES

### 1.3 核心价值

| 特性 | 描述 |
|------|------|
| **上下文工程** | 智能管理上下文，防止质量降解 |
| **波次执行** | 并行执行独立任务，顺序执行依赖任务 |
| **原子提交** | 每个任务独立提交，便于追踪和回滚 |
| **垂直切片** | 端到端功能开发，并行度更高 |
| **快速模式** | 轻量级任务无需完整流程 |

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
│                   GSD Commands (入口)                        │
│  /gsd:new-project / gsd:plan-phase / gsd:execute-phase    │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  Research  │  │   Planner   │  │  Executor   │
    │  (4并行)   │  │   (验证)    │  │  (波次执行)  │
    └─────────────┘  └─────────────┘  └─────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Context Engineering Layer                  │
    │  PROJECT.md | REQUIREMENTS.md | ROADMAP.md | STATE.md  │
    │  .planning/research/ | {phase}-CONTEXT.md                │
    └─────────────────────────────────────────────────────────┘
```

### 2.2 核心文件结构

GSD 在项目中创建以下文件来管理上下文：

| 文件 | 作用 |
|------|------|
| `PROJECT.md` | 项目愿景，始终加载 |
| `REQUIREMENTS.md` | 范围化的 v1/v2 需求，可追踪到阶段 |
| `ROADMAP.md` | 进度追踪：要去哪里，已完成什么 |
| `STATE.md` | 决策、阻塞项、位置 — 跨会话记忆 |
| `{phase}-CONTEXT.md` | 实现偏好和决策 |
| `{phase}-RESEARCH.md` | 领域研究成果 |
| `{phase}-{N}-PLAN.md` | 原子任务计划（XML结构） |
| `{phase}-{N}-SUMMARY.md` | 执行结果和变更记录 |
| `{phase}-VERIFICATION.md` | 验证报告 |

---

## 三、核心工作流详解

### 3.1 完整开发流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ gsd:new-   │ → │ gsd:discuss │ → │ gsd:plan-  │ → │ gsd:execute │
│ project    │   │ -phase      │   │ phase       │   │ -phase      │
│            │   │             │   │             │   │             │
│ 初始化项目  │   │ 捕获偏好    │   │ 研究+计划   │   │ 波次执行    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────┐
                                               │ gsd:verify- │
                                               │ work        │
                                               │             │
                                               │ 人工验收    │
                                               └─────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────┐
                                               │ gsd:ship    │
                                               │ gsd:complete│
                                               │ -milestone  │
                                               └─────────────┘
```

### 3.2 关键阶段详解

#### 3.2.1 项目初始化 (`/gsd:new-project`)

```
用户描述想法 → 系统提问直到完全理解 → 并行研究 → 提取需求 → 创建路线图
```

**创建文件**：`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `.planning/research/`

#### 3.2.2 阶段讨论 (`/gsd:discuss-phase N`)

这是**塑造实现方式**的关键步骤。系统分析阶段并识别灰色区域：

- **可视化功能** → 布局、密度、交互、空状态
- **API/CLI** → 响应格式、标志、错误处理、详细程度
- **内容系统** → 结构、语气、深度、流程
- **组织任务** → 分组标准、命名、重复、异常

输出 `CONTEXT.md` 直接供研究者和规划者使用。

#### 3.2.3 阶段规划 (`/gsd:plan-phase N`)

```
并行研究 → 创建原子计划 → 验证计划
```

- 每个计划足够小，可在全新上下文窗口中执行
- 200k tokens 纯用于实现，无累积垃圾

**创建文件**：`{phase_num}-RESEARCH.md`, `{phase_num}-{N}-PLAN.md`

#### 3.2.4 阶段执行 (`/gsd:execute-phase N`)

**波次执行机制**：

```
┌─────────────────────────────────────────────────────────────────┐
│  WAVE 1 (并行)          WAVE 2 (并行)          WAVE 3 (顺序)   │
│  ┌─────────┐ ┌─────────┐    ┌─────────┐ ┌─────────┐            │
│  │ Plan 01 │ │ Plan 02 │ →  │ Plan 03 │ │ Plan 04 │ →  Plan 05  │
│  │ User    │ │ Product │    │ Orders  │ │ Cart    │            │
│  │ Model   │ │ Model   │    │ API     │ │ API     │            │
│  └─────────┘ └─────────┘    └─────────┘ └─────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**关键设计**：
- 独立计划 → 同波次 → 并行运行
- 依赖计划 → 后续波次 → 等待依赖
- 文件冲突 → 顺序执行

**"垂直切片"优于"水平分层"**：
- 垂直切片（Plan 01: 端到端用户功能）→ 并行度更高
- 水平分层（Plan 01: 所有模型, Plan 02: 所有API）→ 并行度低

#### 3.2.5 验证工作 (`/gsd:verify-work N`)

**这是确认功能真正工作的步骤**：

1. 提取可测试的交付物
2. 逐个引导验证："能登录吗？"
3. 自动诊断失败 → 生成调试代理找根因
4. 创建验证过的修复计划 → 准备重新执行

如果一切通过，进入下一阶段。如果有问题，直接运行 `/gsd:execute-phase` 执行修复计划，无需手动调试。

#### 3.2.6 快速模式 (`/gsd:quick`)

**适用于不需要完整规划的临时任务**：

```
/gsd:quick
> "Add dark mode toggle to settings"
```

- 相同质量的 Planner + Executor
- 跳过可选步骤（无研究、无计划检查、无验证器）
- 独立追踪，存于 `.planning/quick/`

**可用标志**：
- `--discuss` — 轻量级讨论
- `--research` — 聚焦研究
- `--full` — 启用计划检查 + 验证

---

## 四、核心技术特性

### 4.1 上下文工程（Context Engineering）

**解决核心问题**：Claude 代码质量随上下文窗口填满而下降

**GSD 方案**：
- 文件大小限制，基于 Claude 质量降级阈值
- 主会话上下文保持在 30-40%
- 工作在全新子代理上下文中完成

### 4.2 XML 提示格式化

每个计划都是结构化 XML，为 Claude 优化：

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>
    Use jose for JWT (not jsonwebtoken - CommonJS issues).
    Validate credentials against users table.
    Return httpOnly cookie on success.
  </action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200 + Set-Cookie</verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</task>
```

### 4.3 多代理编排

| 阶段 | 编排器 | 代理 |
|------|--------|------|
| Research | 协调、呈现 | 4个并行研究者调查技术栈、功能、架构、陷阱 |
| Planning | 验证、迭代 | 规划器创建计划，检查器验证，循环直到通过 |
| Execution | 分组为波次、追踪 | 执行者并行实现，每人全新 200k 上下文 |
| Verification | 呈现结果、路由 | 验证器检查代码库目标，调试者诊断失败 |

### 4.4 原子 Git 提交

每个任务完成后立即独立提交：

```bash
abc123f docs(08-02): complete user registration plan
def456g feat(08-02): add email confirmation flow
hij789k feat(08-02): implement password hashing
lmn012o feat(08-02): create registration endpoint
```

**优势**：
- Git bisect 可精确找到失败任务
- 每个任务可独立回滚
- 为未来会话提供清晰历史

---

## 五、安装与配置

### 5.1 安装

```bash
npx get-shit-done-cc@latest
```

安装程序提示选择：
1. **Runtime** — Claude Code、OpenCode、Gemini、Codex、Copilot、Antigravity 或全部
2. **Location** — Global（所有项目）或 Local（当前项目）

### 5.2 验证安装

```
Claude Code / Gemini: /gsd:help
OpenCode: /gsd-help
Codex: $gsd-help
Copilot: /gsd:help
Antigravity: /gsd:help
```

### 5.3 推荐：跳过权限模式

```bash
claude --dangerously-skip-permissions
```

> 停止批准 `date` 和 `git commit` 50 次会破坏目的。

### 5.4 模型配置

| Profile | Planning | Execution | Verification |
|---------|----------|-----------|--------------|
| `quality` | Opus | Opus | Sonnet |
| `balanced` (默认) | Opus | Sonnet | Sonnet |
| `budget` | Sonnet | Sonnet | Haiku |
| `inherit` | 继承 | 继承 | 继承 |

---

## 六、命令参考

### 6.1 核心工作流

| 命令 | 功能 |
|------|------|
| `/gsd:new-project [--auto]` | 完整初始化：提问 → 研究 → 需求 → 路线图 |
| `/gsd:discuss-phase [N] [--auto]` | 捕获实现决策 |
| `/gsd:plan-phase [N] [--auto]` | 研究 + 计划 + 验证 |
| `/gsd:execute-phase <N>` | 波次执行所有计划 |
| `/gsd:verify-work [N]` | 人工验收测试 |
| `/gsd:ship [N] [--draft]` | 从验证工作创建 PR |
| `/gsd:next` | 自动进入下一步 |
| `/gsd:complete-milestone` | 归档里程碑，标记发布 |
| `/gsd:new-milestone [name]` | 启动下一版本 |

### 6.2 导航与工具

| 命令 | 功能 |
|------|------|
| `/gsd:progress` | 我在哪里？下一步是什么？ |
| `/gsd:help` | 显示所有命令 |
| `/gsd:quick [--full]` | 快速执行临时任务 |
| `/gsd:map-codebase [area]` | 分析现有代码库 |
| `/gsd:add-todo [desc]` | 捕获想法供后续 |
| `/gsd:debug [desc]` | 系统化调试 |

---

## 七、优势分析

### 7.1 核心优势

| 优势 | 说明 |
|------|------|
| **上下文管理** | 解决上下文腐化问题，保持代码质量稳定 |
| **波次执行** | 智能并行/顺序切换，最大化效率 |
| **原子提交** | 每次任务独立提交，可精确追踪和回滚 |
| **轻量级** | 无企业流程，复杂度在系统内 |
| **多平台** | 支持 6 种主流 AI 编程工具 |
| **快速模式** | 临时任务无需完整流程 |

### 7.2 设计亮点

1. **垂直切片优先** — 端到端功能开发，并行度更高
2. **全新上下文执行** — 200k tokens 纯用于实现
3. **验证内置** — 每个计划自带验证步骤
4. **自动诊断** — 失败时自动生成调试代理

---

## 八、劣势与挑战

| 挑战 | 说明 |
|------|------|
| **学习曲线** | 需要理解完整的工作流程和命令 |
| **上下文开销** | 多文件管理需要维护大量上下文文档 |
| **平台差异** | 不同平台安装方式不同 |
| **自动化风险** | 跳过权限模式存在安全隐患 |
| **模型依赖** | 不同模型配置影响质量和成本 |

---

## 九、应用场景

### 9.1 最佳适用场景

| 场景 | 为什么适合 |
|------|-----------|
| **个人开发者** | 无企业流程，直接构建 |
| **快速原型** | 快速模式适合临时任务 |
| **复杂系统** | 波次执行 + 上下文管理 |
| **AI 辅助团队** | 原子提交 + 验证内置 |
| **遗留项目** | `/gsd:map-codebase` 分析现有代码 |

### 9.2 不适用场景

- 简单一次性脚本（流程过于复杂）
- 完全不允许 AI 自动化的环境
- 需要严格审计流程的企业项目

---

## 十、与 Superpowers 对比

| 特性 | Superpowers | GSD |
|------|-------------|-----|
| **核心理念** | 工程纪律优先 | 轻量级、效率优先 |
| **工作流** | 技能自动触发 | 命令驱动 |
| **TDD** | 强制 RED-GREEN-REFACTOR | 建议验证步骤 |
| **调试** | 4阶段系统化调试 | 失败自动诊断 |
| **执行模式** | 子代理 + 两阶段评审 | 波次执行 |
| **提交策略** | 每个任务原子提交 | 每个任务原子提交 |
| **上下文** | 技能系统 | 文档工程 |
| **复杂度** | 中等 | 轻量 |

---

## 十一、总结

Get Shit Done 是 **AI 辅助编程领域的轻量级效率框架**。与 Superpowers 的"工程纪律优先"理念不同，GSD 强调：

> **"复杂性在系统内，不在工作流中"**

它通过：
- **上下文工程** 解决 AI 代码质量下降问题
- **波次执行** 最大化并行效率
- **原子提交** 确保可追踪性
- **垂直切片** 提升并行度

对于追求效率、希望保持轻量工作流的个人开发者和小型团队，GSD 提供了一套经过验证的解决方案。

---

**参考资源**：
- 官网：https://github.com/gsd-build/get-shit-done
- Discord 社区：https://discord.gg/gsd
- Twitter：https://x.com/gsd_foundation
