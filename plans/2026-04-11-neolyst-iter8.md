# Neolyst Iter 8: report_maker + template_maker 接入实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `report_maker` 与 `template_maker` 接入 `neolyst`，形成“模板发布到 Neolyst、运行时从 Neolyst 取模板、报告生成后保存 draft 到 Neolyst”的完整闭环。

**Architecture:**
- `report_maker` 新增一层 `neolyst` 适配模块，负责解析模板、组装 draft payload、调用 analyst / coverage / draft 相关接口；现有渲染逻辑尽量保留。
- `template_maker` 保留本地模板制作流程，但发布与复用改走 `neolyst.upsert_template` / `neolyst.reuse_template`；`router.yaml` 退出运行时事实源，只允许作为迁移期辅助或直接移除。
- 自动化测试只新增 `report_maker` 最小集成链路；`template_maker` 以手工联调验证为主。

**Tech Stack:** Python 3.14, pytest, python-docx, docxtpl, supabase-py, YAML

**已确认的设计决策：**
- `report_maker` 运行时模板来源改为 `neolyst.resolve_template(report_type, language)`
- `report_maker` 调用 `resolve_template` 时，下载目标目录必须显式限定在项目根目录内的 `templates/` 子目录，不能落到项目外路径
- `report_maker` 生成 Word/PDF 后调用 `save_draft_report`，默认不自动 `submit_report`
- `report_maker` 需要接入 `resolve_analyst_by_email`、`resolve_coverage`、`list_coverage_history`、`create_coverage`
- `template_maker` 发布主模板走 `upsert_template`，共享模板走 `reuse_template`
- `router.yaml` 不再作为运行时事实源
- `router.py` 本轮直接删除，`invoke.py` 中现有的 router 读取、展示和写回逻辑统一改写
- 本轮只给 `report_maker` 增加自动化集成测试，不新增 `template_maker` 自动化测试

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/report_maker/scripts/common.py` | 修改 | 替换本地 router 取模板逻辑 |
| `skills/report_maker/scripts/neolyst_adapter.py` | 新建 | `neolyst` 适配层：模板解析、draft 组装、coverage/analyst 调用 |
| `skills/report_maker/SKILL.md` | 修改 | 运行时模板与 draft 流程改写为 `neolyst` 版本 |
| `skills/report_maker/tests/integration/test_neolyst_integration.py` | 新建 | 最小集成链路测试 |
| `skills/template_maker/scripts/invoke.py` | 修改 | 模板发布改走 `neolyst` |
| `skills/template_maker/scripts/neolyst_publish.py` | 新建 | 模板发布与复用辅助函数 |
| `skills/template_maker/SKILL.md` | 修改 | 运行时事实源与发布流程改写 |
| `skills/template_maker/scripts/router.py` | 删除 | 移除 router 读写能力与运行时职责 |
| `plans/2026-04-07-neolyst-skill-roadmap.md` | 修改 | Iter 8 状态回写 |

## 背景与约束

- 当前 `report_maker` 仍通过 [`get_template_name`](/mnt/c/_code/neoskills/skills/report_maker/scripts/common.py) 读取本地 `templates/router.yaml`，与目标架构不符
- 当前 `template_maker` 在 [`invoke.py`](/mnt/c/_code/neoskills/skills/template_maker/scripts/invoke.py) 中仍会写入 `router.yaml`
- 当前 [`skills/template_maker/scripts/invoke.py`](/mnt/c/_code/neoskills/skills/template_maker/scripts/invoke.py) 既在 `_confirm_report_type_mapping()` 中读取 `router.yaml` 展示现有映射，也在创建完成后写回 `router.yaml`，router 依赖已经深入主路径
- 当前两个 skill 中都没有任何 `neolyst` 调用
- 按仓库规范，修改 `SKILL.md` 时必须使用 `skill-creator`
- 本轮不扩展 `template_maker` 自动化测试，只做手工发布验证

## Task 1: 为 `report_maker` 建立 `neolyst` 适配层

**Files:**
- Modify: `skills/report_maker/scripts/common.py`
- Create: `skills/report_maker/scripts/neolyst_adapter.py`

- [ ] **Step 1: 先写 `report_maker` 集成测试骨架**

Create:
- `skills/report_maker/tests/integration/test_neolyst_integration.py`

覆盖范围：
- 通过 `neolyst.upsert_template` 发布测试模板
- 通过 `neolyst.resolve_template` 拉取模板到项目内 `templates/` 子目录
- 使用现有渲染逻辑生成 Word/PDF
- 组装最小 draft payload 并调用 `save_draft_report`
- 断言返回 `report_id` / `version_no` / `status = draft`

- [ ] **Step 2: 运行测试，确认先因适配层缺失而失败**

Run:
```bash
uv run pytest skills/report_maker/tests/integration/test_neolyst_integration.py -q
```

Expected:
- FAIL，报缺少 `neolyst_adapter.py` 或缺少适配函数

- [ ] **Step 3: 创建 `neolyst_adapter.py` 最小实现**

职责：
- 获取 `neolyst` client
- 封装 `resolve_template`
- 统一约束模板下载目标目录，确保始终落在项目根目录内的 `templates/` 子目录；不得把运行时模板下载到项目外路径
- 将 `elements + 输出文件路径 + 业务补充字段` 组装成 `save_draft_report` 所需扁平 payload
- 提供与 `docs/skills_neolyst_design.md` 对齐的辅助函数，命名保持和 `neolyst` 契约一致：
  - `resolve_analyst_by_email`
  - `resolve_coverage`
  - `create_coverage`
  - `list_coverage_history`
  - `save_draft_report`
- 如需减少上层重复组装，可额外提供纯适配层内部函数，例如 `build_draft_payload`；不要用 `resolve_or_create_coverage`、`save_report_draft` 这类会掩盖 `neolyst` 正式契约的命名

- [ ] **Step 4: 在 `common.py` 中替换本地 router 依赖**

要求：
- 弱化或删除 `get_template_name()` 的运行时职责
- 新增面向 `neolyst` 的模板解析入口，避免 `report_maker` 再去读 `templates/router.yaml`

- [ ] **Step 5: 跑新增测试与现有关键测试**

Run:
```bash
uv run pytest skills/report_maker/tests/integration/test_neolyst_integration.py -q
uv run pytest skills/report_maker/tests/test_common.py -q
```

Expected:
- 新增集成测试通过
- `test_common.py` 中与 router 强耦合的旧断言已被更新

## Task 2: 改写 `report_maker` 工作流说明，接入 analyst / coverage / draft

**Files:**
- Modify: `skills/report_maker/SKILL.md`

- [ ] **Step 1: 用 `skill-creator` 更新模板来源说明**

要求：
- 将“本地 `templates/` 作为运行时模板来源”改为“调用 `neolyst.resolve_template`”
- 保留本地模板目录仅作为制作阶段概念，不再作为运行时事实源
- 明确运行时模板虽然通过 `neolyst` 下载，但下载目标仍必须位于项目根目录内的 `templates/` 子目录，以满足“禁止访问项目外路径”
- 明确删除或改写 1.2 节“模板映射”表，不能再保留 `company -> company`、`strategy / quantitative / bond -> common` 这类硬编码运行时映射
- 同步删除或改写“使用模板: templates/.../”这类把本地模板目录写成运行时来源的示例

- [ ] **Step 2: 用 `skill-creator` 更新 draft 流程说明**

要求：
- 增加 `report_language`、`contact_person`、`analysts`、`author_order`、`coverage_id` 的确认与补齐要求
- 增加 `save_draft_report` 步骤
- 增加 `validate_draft` 作为提交前入口
- 明确默认不自动执行 `submit_report`

- [ ] **Step 3: 运行 grep 验证**

Run:
```bash
rg -n "resolve_template|resolve_analyst_by_email|resolve_coverage|create_coverage|save_draft_report|validate_draft|submit_report|router.yaml|templates/|模板映射|common" skills/report_maker/SKILL.md
```

Expected:
- `resolve_template` / `save_draft_report` / `validate_draft` 出现
- `resolve_analyst_by_email` / `resolve_coverage` / `create_coverage` 的运行时调用语义已写入
- 不再把 `router.yaml` 或本地 `templates/` 写成运行时事实源
- 不再保留“模板映射”表或 `common` 这类本地运行时模板映射文案

## Task 3: 为 `template_maker` 增加发布与复用能力

**Files:**
- Create: `skills/template_maker/scripts/neolyst_publish.py`
- Modify: `skills/template_maker/scripts/invoke.py`

- [ ] **Step 1: 创建模板发布辅助模块**

职责：
- 获取 `neolyst` client
- 封装 `publish_template(report_type, language, template_local_path, schema_local_path)`
- 封装 `reuse_template_for(report_type, language, same_as_report_type)`

- [ ] **Step 2: 改写 `invoke.py` 的输出阶段**

要求：
- 模板本地生成成功后，允许直接发布到 `neolyst`
- 删除“更新 `router.yaml`”这一步的运行时职责
- 重写 `_confirm_report_type_mapping()`：不再读取 `router.yaml` 展示现有映射，只保留“本次发布到哪个 `report_type` / language”所需的显式输入确认
- `invoke.py` 中不再 import `router` 模块，也不再生成或返回 `router.yaml`

- [ ] **Step 3: 手工验证发布链路**

Run:
```bash
uv run python skills/template_maker/scripts/invoke.py --name company --word <sample.docx> --elements <elements.yaml> --auto-confirm
uv run python - <<'PY'
from skills.neolyst.scripts import connection, template
client = connection.get_client()
print(template.resolve_template(client, "company", "en"))
PY
```

Expected:
- 本地模板生成成功
- `resolve_template("company", "en")` 能返回已发布模板路径

## Task 4: 改写 `template_maker` 文档并处理 `router.yaml`

**Files:**
- Modify: `skills/template_maker/SKILL.md`
- Delete: `skills/template_maker/scripts/router.py`

- [ ] **Step 1: 用 `skill-creator` 更新 `template_maker/SKILL.md`**

要求：
- 删除“运行时通过 `router.yaml` 映射模板”的表述
- 增加 `upsert_template` / `reuse_template` 发布流程
- 明确本地模板目录仍保留为制作阶段工作目录

- [ ] **Step 2: 删除 `router.py` 并完成代码同步**

要求：
- 删除 `skills/template_maker/scripts/router.py`
- 删除 `invoke.py` 中对 `load_router`、`update_mapping`、`save_router`、`get_all_router_mappings` 的 import 与调用
- 将报告类型确认逻辑改成不依赖 `router.yaml` 的显式交互或参数输入
- 若需要保留旧 router 数据，只能在迁移脚本或一次性说明中处理，不得继续留在主执行路径

- [ ] **Step 3: 验证 `template_maker` 代码中不再把 `router.yaml` 当运行时事实源**

Run:
```bash
rg -n "router.yaml|load_router|save_router|get_all_router_mappings|update_mapping" skills/template_maker
```

Expected:
- `skills/template_maker` 主路径中不再依赖这些调用
- `router.py` 已删除，或仅剩明确标注为迁移脚本的非主路径代码

## Task 5: 回写 roadmap 并做最小联调验收

**Files:**
- Modify: `plans/2026-04-07-neolyst-skill-roadmap.md`

- [ ] **Step 1: 更新 roadmap 中 Iter 8 状态**

要求：
- 实施开始后改为“进行中”
- 完成后改为“已完成”

- [ ] **Step 2: 跑最小验收命令**

Run:
```bash
uv run pytest skills/report_maker/tests/integration/test_neolyst_integration.py -q
uv run pytest skills/neolyst/tests -q
```

Expected:
- `report_maker` 新增集成测试通过
- `neolyst` 原测试集不回归

## 完成标准

- [ ] `report_maker` 运行时模板来源改为 `neolyst.resolve_template`
- [ ] `report_maker` 能将生成结果保存为 `neolyst` draft
- [ ] `template_maker` 能将本地模板发布到 `neolyst`
- [ ] `router.yaml` 不再承担运行时事实源职责
- [ ] 新增 `report_maker` 最小集成测试通过
