# Ralph 项目技术文档

## 一、项目概述

### 1.1 项目定位

**Ralph** 是一个**自主 AI 代理循环系统**，基于 Geoffrey Huntley 提出的 Ralph 模式开发。它让 AI 编码工具（ Amp 或 Claude Code ）循环运行，直到所有 PRD（产品需求文档）项目完成。

其核心创新在于：**每次迭代都是全新的 AI 实例，拥有干净的上下文**，通过 git 历史、`progress.txt` 和 `prd.json` 实现记忆持久化。

> **项目数据**：⭐ 13.3k Stars | 1.4k Forks | 20 Commits

### 1.2 核心理念

| 特性 | 描述 |
|------|------|
| **自主循环** | 自动化执行，直到所有用户故事完成 |
| **全新上下文** | 每次迭代都是fresh instance，防止上下文腐化 |
| **小任务优先** | 每个PRD项足够小，可在一个上下文窗口内完成 |
| **记忆持久化** | 通过 git、progress.txt、prd.json 跨迭代传递信息 |

### 1.3 核心价值

| 特性 | 描述 |
|------|------|
| **自动化** | 无需人工干预，AI 自主完成需求 |
| **可追溯** | 每次迭代有记录，git 历史可回溯 |
| **质量保障** | 类型检查、测试、CI 必须通过 |
| **学习机制** | AGENTS.md 更新，持续改进 |

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
│                    PRD 需求文档                               │
│              (tasks/prd-[feature-name].md)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Ralph Skill 转换                                 │
│                    prd.json                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Ralph Loop (ralph.sh)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  迭代 N: 全新 AI 实例 (Amp/Claude Code)                ││
│  │  1. 选取最高优先级 passes=false 的故事                 ││
│  │  2. 实现该故事                                        ││
│  │  3. 运行质量检查 (typecheck, tests)                   ││
│  │  4. 通过则提交，更新 prd.json passes=true             ││
│  │  5. 追加学习到 progress.txt                           ││
│  │  6. 更新 AGENTS.md                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                           │                                  │
│                           ▼                                  │
│              (所有故事 passes=true 或达到最大迭代)            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心文件结构

| 文件 | 作用 |
|------|------|
| `ralph.sh` | Bash 循环脚本，生成全新 AI 实例 |
| `prompt.md` | Amp 的提示模板 |
| `CLAUDE.md` | Claude Code 的提示模板 |
| `prd.json` | 用户故事列表，带 passes 状态 |
| `prd.json.example` | PRD 格式示例 |
| `progress.txt` | 追加式学习记录 |
| `skills/prd/` | PRD 生成技能 |
| `skills/ralph/` | PRD 转 JSON 技能 |
| `AGENTS.md` | 跨迭代的代码库知识 |

### 2.3 PRD.json 结构

```json
{
  "project": "MyApp",
  "branchName": "ralph/task-priority",
  "description": "Task Priority System - Add priority levels to tasks",
  "userStories": [
    {
      "id": "US-001",
      "title": "Add priority field to database",
      "description": "As a developer...",
      "acceptanceCriteria": [
        "Add priority column to tasks table...",
        "Generate and run migration successfully",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## 三、核心工作流详解

### 3.1 完整执行流程

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 创建 PRD                                            │
│ /prd skill: 创建详细需求文档                                │
│ → tasks/prd-[feature-name].md                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 转换为 Ralph 格式                                   │
│ /ralph skill: 转换 PRD 为 JSON                              │
│ → prd.json                                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 运行 Ralph Loop                                     │
│ ./scripts/ralph/ralph.sh [max_iterations]                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ FOR 迭代 in 1..max_iterations:                      │   │
│  │   1. 全新 AI 实例 (clean context)                   │   │
│  │   2. 选取最高优先级 passes=false 的故事             │   │
│  │   3. 实现该故事                                     │   │
│  │   4. typecheck + tests                              │   │
│  │   5. [通过] → git commit + passes=true             │   │
│  │   6. [失败] → 记录到 notes                         │   │
│  │   7. 更新 progress.txt                              │   │
│  │   8. 更新 AGENTS.md                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│              所有故事 passes=true → 输出 COMPLETE            │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 关键执行步骤

#### 3.2.1 创建 PRD

使用 PRD skill 生成详细需求文档：

```
Load the prd skill and create a PRD for [your feature description]
```

回答澄清问题，skill 保存输出到 `tasks/prd-[feature-name].md`。

#### 3.2.2 转换为 Ralph 格式

将 Markdown PRD 转换为 JSON 格式：

```
Load the ralph skill and convert tasks/prd-[feature-name].md to prd.json
```

创建 `prd.json`，包含为自主执行结构化的用户故事。

#### 3.2.3 运行 Ralph

```bash
# 使用 Amp (默认)
./scripts/ralph/ralph.sh [max_iterations]

# 使用 Claude Code
./scripts/ralph/ralph.sh --tool claude [max_iterations]
```

默认 10 次迭代。Ralph 会：
1. 创建功能分支（从 PRD 的 `branchName`）
2. 选取最高优先级且 `passes: false` 的故事
3. 实现该单一故事
4. 运行质量检查（typecheck, tests）
5. 如果检查通过则提交
6. 更新 `prd.json` 标记故事为 `passes: true`
7. 追加学习到 `progress.txt`
8. 重复直到所有故事通过或达到最大迭代

---

## 四、核心技术特性

### 4.1 全新上下文机制

**每次迭代都是全新的 AI 实例**，这是 Ralph 的核心创新：

| 记忆载体 | 作用 |
|---------|------|
| Git 历史 | 之前迭代的提交记录 |
| progress.txt | 学习成果和上下文 |
| prd.json | 哪些故事已完成 |

**优势**：
- 避免上下文窗口耗尽导致的代码质量下降
- 无需复杂的上下文管理
- 每次迭代都是"从零开始"但有完整上下文

### 4.2 小任务原则

**每个 PRD 项应该足够小**，可以在一个上下文窗口内完成。

合适的任务大小：
- 添加数据库列和迁移
- 在现有页面添加 UI 组件
- 使用新逻辑更新服务器 action
- 在列表中添加筛选下拉框

**过大的任务（需要拆分）**：
- "构建整个仪表板"
- "添加身份验证"
- "重构 API"

### 4.3 AGENTS.md 更新

每次迭代后，Ralph 更新相关 `AGENTS.md` 文件的学习内容。这是关键，因为 AI 编码工具会自动读取这些文件，未来迭代（和未来的人类开发者）可以从发现的模式、陷阱和约定中受益。

**AGENTS.md 应包含**：
- 发现的模式（"此代码库使用 X 做 Y"）
- 陷阱（"更改 W 时不要忘记更新 Z"）
- 有用的上下文（"设置面板在组件 X 中"）

### 4.4 反馈循环

Ralph 依赖于反馈循环：
- **Typecheck** 捕获类型错误
- **Tests** 验证行为
- **CI** 必须保持绿色（坏代码会在迭代中累积）

### 4.5 UI 故事浏览器验证

前端故事必须在验收标准中包含"使用 dev-browser skill 在浏览器中验证"。Ralph 将使用 dev-browser skill 导航到页面、与 UI 交互并确认更改有效。

---

## 五、安装与配置

### 5.1 前置条件

- 已安装并认证的 AI 编码工具：
  - [Amp CLI](https://ampcode.com)（默认）
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- 已安装 `jq`（macOS: `brew install jq`）
- Git 仓库

### 5.2 安装方式

#### 方式 1: 复制到项目

```bash
# 从项目根目录
mkdir -p scripts/ralph
cp /path/to/ralph/ralph.sh scripts/ralph/

# 复制适合你的 AI 工具的提示模板：
cp /path/to/ralph/prompt.md scripts/ralph/prompt.md    # For Amp
# OR
cp /path/to/ralph/CLAUDE.md scripts/ralph/CLAUDE.md    # For Claude Code

chmod +x scripts/ralph/ralph.sh
```

#### 方式 2: 全局安装 Skills (Amp)

```bash
cp -r skills/prd ~/.config/amp/skills/
cp -r skills/ralph ~/.config/amp/skills/
```

#### 方式 3: Claude Code 市场

```bash
/plugin marketplace add snarktank/ralph
/plugin install ralph-skills@ralph-marketplace
```

### 5.3 配置 Amp Auto-Handoff（推荐）

添加到 `~/.config/amp/settings.json`：

```json
{
  "amp.experimental.autoHandoff": { "context": 90 }
}
```

这允许在上下文填满时自动切换，使 Ralph 能够处理超出单个上下文窗口的大型故事。

---

## 六、与同类项目对比

### 6.1 Ralph vs Superpowers vs GSD

| 特性 | Ralph | Superpowers | GSD |
|------|-------|-------------|-----|
| **核心理念** | 自主循环执行 | 工程纪律优先 | 轻量级效率优先 |
| **上下文** | 每次迭代全新实例 | 技能系统触发 | 文档工程管理 |
| **任务来源** | PRD 用户故事 | 设计文档 | 阶段计划 |
| **执行模式** | 单故事迭代 | 子代理+两阶段评审 | 波次执行 |
| **停止条件** | passes=true 或达到最大迭代 | 人工确认 | 人工验收 |
| **学习机制** | AGENTS.md 更新 | 技能系统 | 上下文文档 |

### 6.2 架构差异可视化

```
Ralph:
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│iter1│→│iter2│→│iter3│→│iter4│ 全新实例 × N
└─────┘ └─────┘ └─────┘ └─────┘

Superpowers:
┌─────────────────────────────────┐
│      单个会话 + 技能触发          │
│  brainstorming → TDD → review  │
└─────────────────────────────────┘

GSD:
┌─────────────────────────────────┐
│      文档工程 + 波次执行          │
│  discuss → plan → execute      │
└─────────────────────────────────┘
```

---

## 七、优势分析

### 7.1 核心优势

| 优势 | 说明 |
|------|------|
| **防止上下文腐化** | 每次迭代全新实例，质量稳定 |
| **自主执行** | 无需人工持续干预 |
| **小任务原则** | 确保任务可完成，减少失败 |
| **学习积累** | AGENTS.md 持续改进代码库知识 |
| **简单直接** | 纯 Bash 脚本，易于理解和修改 |
| **Git 友好** | 每次提交可追溯，git bisect 可用 |

### 7.2 设计亮点

1. **全新上下文** — 解决 AI 长对话质量下降问题
2. **小任务优先** — 确保可完成性，减少半成品
3. **反馈循环** — typecheck + tests + CI 保障质量
4. **AGENTS.md** — 跨迭代知识积累

---

## 八、劣势与挑战

| 挑战 | 说明 |
|------|------|
| **任务拆分要求** | 需要人工将大需求拆分为小故事 |
| **无动态规划** | 不如 GSD 的波次执行灵活 |
| **质量检查依赖** | 需要完善的 typecheck + tests |
| **迭代开销** | 每次全新启动可能有重复工作 |
| **上下文限制** | 不如 Superpowers 的技能系统丰富 |

---

## 九、应用场景

### 9.1 最佳适用场景

| 场景 | 为什么适合 |
|------|-----------|
| **大型重构** | 小任务拆分，自主循环完成 |
| **批量功能开发** | PRD 驱动，自动化执行 |
| **CI/CD 集成** | 可完全无人值守运行 |
| **遗留系统改造** | AGENTS.md 积累知识 |
| **简单 CRUD 开发** | 标准化流程，效率高 |

### 9.2 不适用场景

- 需要动态规划的场景（不如 GSD 灵活）
- 复杂设计决策（需要人工持续参与）
- 无完善测试的项目（无法保证质量）
- 探索性/实验性开发

---

## 十、总结

Ralph 是 **AI 辅助编程领域的"任务循环执行"框架**。与 Superpowers 和 GSD 的理念不同：

> **"让 AI 自己循环执行，直到所有 PRD 故事完成"**

其核心特点：
- **全新上下文** — 每次迭代都是 fresh instance
- **小任务原则** — 确保可完成性
- **自主执行** — 减少人工干预
- **学习积累** — AGENTS.md 持续改进

对于需要**批量完成 PRD 需求**、希望**自动化执行**的团队，Ralph 提供了一套简单有效的解决方案。

---

**参考资源**：
- 官网：https://github.com/snarktank/ralph
- 原始模式：https://ghuntley.com/ralph/
- 交互式流程图：https://snarktank.github.io/ralph/
- 作者文章：https://x.com/ryancarson/status/2008548371712135632
