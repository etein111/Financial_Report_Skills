# 设计文档搬运判定规则

本文档定义从设计文档（`docs/skills_neolyst_design.md`）向代码和 README 搬运内容时的判定原则。

## 总原则

任何具体问题，只要 Claude Code 可以通过查看代码、代码注释和数据库对象（含 SQL comment）准确回答，就不需要进文档，可以从设计文档中直接删除。

## 判定流程

对设计文档中的每条信息，依次执行两步判定。

### 第一步：核对代码是否已反映

依次检查以下四处，任何一处已包含该信息则不需要重复搬运：

1. **Python 代码 + docstring** — 函数签名、模块 docstring、函数 docstring
2. **Supabase SQL + comment** — RPC 定义、RLS policy、`comment on function`
3. **`references/interfaces.md`** — 接口参考文档
4. **`SKILL.md`** — AI skill 入口

### 第二步：按归属判断去处

经第一步筛选后，剩余信息按以下规则分配：

**放代码 docstring（贴着实现单元）：**

- 函数自身的行为、约束、边界——"做什么、怎么做、有什么限制"
- 只对阅读/修改/调用该函数的人有意义
- 代码变了这段话也要变
- 依据：`principles/DOCSTR.md`

**放 README（子系统级、跨模块）：**

- 子系统级、跨模块、跨文件的说明
- 脱离目录地图就不容易快速看懂的内容
- 单个函数重写后仍然成立
- 如：模块依赖方向、环境配置、开发测试方法
- 依据：`principles/DOCUMENT_README.md`

**直接删除：**

- 设计决策的"为什么"（业务背景、设计动机）——代码不承载这个
- 从函数签名和实现可直接推断的机械事实
- 已在 `references/interfaces.md` 或 `SKILL.md` 中完整覆盖的调用约定

## 典型判例

| 情况 | 处理 | 原因 |
|------|------|------|
| 函数签名、参数、返回值 | 删除 | 代码自解释 |
| 模块级职责（一句话） | 删除 | 模块 docstring 已有 |
| 模块间依赖方向 | → README | 跨模块，代码 import 可推断但没有显式声明规则 |
| Storage 路径格式约定 | → docstring | 贴着 storage.py 的约束 |
| 函数执行步骤（3-5 步） | 删除 | 代码读下来就是这些步骤 |
| 调用约定"先调 A 再调 B" | 删除 | `references/interfaces.md` 已写 |
| 业务场景"什么时候用" | 删除 | 设计动机，代码不承载 |
| RLS policy 名称和设计 | 删除 | SQL 侧注释已有 |
| 环境变量和测试配置 | → README | 开发者上手需要，跨文件 |
