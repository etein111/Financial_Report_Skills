# Skill 拆分最佳实践：来自社区的共识

> 整理时间：2026-04-16
> 来源：Anthropic 官方文档 + 社区经验

---

## 1. Anthropic "Building Effective AI Agents"

**核心原则：从最简方案开始。**

### Workflow vs Agent 的区别

| 维度 | Workflow | Agent |
|------|----------|-------|
| 控制流 | 预定义路径 | LLM 自主决策 |
| 适合场景 | 步骤确定、可枚举 | 开放式、需自主判断 |
| 可预测性 | 高 | 低 |
| 成本 | 低 | 高 |

**判断标准：** 如果能用 workflow 解决，不要上 agent。

### 5 种编排模式（从简到复杂）

1. **Prompt Chaining** — 串行管道，每步输出是下步输入
2. **Routing** — 分类 → 分发到不同处理分支
3. **Parallelization** — 分段/投票，多路并发后聚合
4. **Orchestrator-Workers** — 中心调度，动态分配子任务
5. **Evaluator-Optimizer** — 生成 → 评估 → 循环改进

### 3 条铁律

1. **简单性** — 能用最简方案就不加复杂度
2. **透明性** — Agent 的每一步决策必须可追溯
3. **ACI（Agent-Computer Interface）设计** — 工具接口要为 LLM 优化，不是为人优化

---

## 2. Anthropic "Writing Effective Tools for Agents"

**核心观点：合并工具，而非拆碎工具。**

### 4 条原则

1. **Right granularity（恰当粒度）**
   - 太粗：Agent 无法精确控制
   - 太细：Agent 需要多步编排，增加出错概率
   - **经验法则：合并相关操作为一个工具，用参数区分行为**

2. **Namespacing for boundaries（命名空间划定边界）**
   - 用工具名前缀表示领域边界
   - 例：`report_check__similarity`、`report_check__sfc_verify`

3. **Return meaningful context（返回有意义的上下文）**
   - 工具返回值要包含 Agent 做下一步决策所需的信息
   - 不要只返回 "success" / "error"
   - 要返回结构化结果，让 Agent 能直接判断

4. **Optimize for token efficiency（优化 token 效率）**
   - 返回值精简，去掉 Agent 不需要的字段
   - 大文档用摘要，不要全文灌入上下文

### 关键引述

> "Instead of `list_users`, `list_events`, `create_event` → `schedule_event`"
>
> 少数精心设计的高影响力工具 > 大量细粒度工具

---

## 3. Anthropic "Skill Authoring Best Practices"

### 核心原则：Concise is key

- SKILL.md 控制在 **500 行以内**
- 超过则加层级，用 references/ 子目录按需加载
- 每一层只加载当前需要的上下文（Progressive Disclosure）

### Degrees of Freedom（自由度分级）

| 自由度 | 描述 | 适用场景 |
|--------|------|----------|
| Low | 固定流程，参数化执行 | 数据转换、格式化 |
| Medium | 有分支判断，但路径有限 | 审核流程、条件处理 |
| High | 开放式，Agent 自主规划 | 研究分析、创意写作 |

**Skill 设计要根据自由度级别调整约束强度：**
- Low freedom → 严格步骤定义
- High freedom → 目标 + 原则，少约束

### 评估驱动开发（Evaluation-Driven）

1. 先写 test prompts
2. 跑 with_skill vs without_skill 对比
3. 量化评估 + 人工评审
4. 迭代改进

### Claude A/B 迭代法

- 同一任务，两个版本的 Skill 对比
- 关注：准确率、token 消耗、耗时
- 胜者成为新 baseline

### Progressive Disclosure（渐进式加载）

```
skill-name/
├── SKILL.md              ← 始终加载（< 500 行）
├── references/            ← 按需加载
│   ├── domain-a.md
│   └── domain-b.md
└── scripts/               ← 可执行，无需加载到上下文
    └── helper.py
```

---

## 4. 社区反模式（Anti-patterns）

### 反模式 1: Tool Overload（工具过载）

- **症状：** Agent 面对几十个工具，频繁选错或遗漏
- **原因：** 工具粒度过细，描述重叠
- **解法：** 合并相关工具，用参数区分

### 反模式 2: Over-decomposition（过度拆分）

- **症状：** 一个任务需要 5+ 个 Skill 串联
- **原因：** 迷信"单一职责"，忽略了编排成本
- **解法：** 评估端到端路径长度，> 3 步考虑合并

### 反模式 3: Overlapping Descriptions（描述重叠）

- **症状：** 多个 Skill 的 description 有重叠关键词
- **原因：** Skill 触发条件不够精确
- **解法：** description 明确写入触发条件和排除条件

### 反模式 4: Telephone Game（传话游戏）

- **症状：** 多 Skill 串联时，上下文逐步丢失/变形
- **原因：** 每个 Skill 只看到上一步输出，丢失原始意图
- **解法：** 减少串联层级；必要时传递原始上下文

### 反模式 5: God Skill（万能技能）

- **症状：** 一个 Skill 做所有事，SKILL.md 超过 1000 行
- **原因：** 拒绝拆分的另一个极端
- **解法：** 拆分为核心流程 + references/ 按需加载

---

## 5. 修订后的拆分方案

### 原始方案 vs 修订方案

| 原始方案（4 个新 Skill） | 修订方案（2 个新 Skill） | 修订理由 |
|--------------------------|--------------------------|----------|
| report_checker | report_checker（合并 SFC） | SFC 验证是文件检查的自然延伸 |
| sfc_verifier | ↑ 合并到 report_checker | 独立 Skill 粒度过细 |
| chart_generator | → report_maker 内部模块 | 图表生成是报告渲染的一部分 |
| compliance | compliance | StockList + RQC 属于合规领域 |
| title_generator | → report_maker 内部模块 | 标题生成是报告组装的一部分 |

### 修订后的架构

```
已有 Skill                    新建 Skill
─────────                     ──────────
report_maker                  report_checker
├── 字段提取（已有）           ├── 文件相似度检查
├── 模板渲染（已有）           ├── SFC 验证（合并）
├── 图表生成（新增模块）       ├── 格式完整性检查
└── 标题生成（新增模块）       └── 报告提交前校验

neolyst                       compliance
├── 报告生命周期               ├── StockList 合规检查
├── 覆盖率查询                 └── RQC 触发与记录
└── 分析师/模板管理

template_maker
├── 模板创建
└── 模板维护
```

### 端到端路径验证

**生成报告：** 用户请求 → report_maker → neolyst → 完成（2 步）

**检查报告：** 用户请求 → report_checker → 完成（1 步）

**合规检查：** 用户请求 → compliance → neolyst → 完成（2 步）

**最大路径 ≤ 2 步，满足社区共识的 "≤ 3 步" 原则。**

---

## 6. 待确认的开放问题

1. **标题生成** — 独立 Skill 还是 report_maker 内部模块？（倾向后者）
2. **行情数据源** — chart_generator 的市场数据从哪获取？
3. **SFC 验证方式** — 是网页抓取还是 API？
4. **StockList 交互** — 合规部门系统接口是什么？
5. **report_checker 触发** — 自动触发还是用户手动？

---

## 参考来源

- [Anthropic Skill Authoring Best Practices](https://platform.claude.com/docs/skills/best-practices)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
