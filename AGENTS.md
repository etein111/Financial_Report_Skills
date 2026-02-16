# AGENTS.md

## 语言偏好
- 默认使用中文与用户沟通，思考过程回显也使用中文。
- 产出的文档、说明、计划与总结默认使用中文。
- 仅在用户明确要求英文（或其他语言）时切换语言。

## 编码与终端
- 编码目标：仓库内文本文件尽量统一为 UTF-8（需要 PowerShell 5.1 兼容时，`.ps1` 可保留 BOM）。
- PowerShell 输出：优先设置 UTF-8（例如 `[Console]::OutputEncoding=[System.Text.Encoding]::UTF8`）。
- 读取文件：默认不强制 `-Encoding`；只有出现乱码/解析异常时才显式指定编码或转为 UTF-8。
- 写入文件：尽量保持原文件编码；如需转码，先说明并一次性完成，避免零散转码造成 diff 噪音。

## 项目概览

本项目使用 **OpenSpec** 管理变更和规范。
- 当前采用极简配置：`openspec/config.yaml` 仅保留 `schema: spec-driven`
- 详细上下文与规则在重建稳定后再补充

## OpenSpec 常用命令

```bash
# 变更管理
openspec list                    # 查看所有变更
openspec new change <name>       # 创建新变更
openspec continue                # 继续当前变更

# 配置查看
openspec schema which            # 查看当前使用的 schema
```

## OpenSpec Change 规范

### Proposal 文档规范

每个 change 的 `proposal.md` 必须包含以下内容：

**1. 权限模型（必须包含）**

所有涉及角色和权限的 change 必须提供两个完整的权限矩阵：

- **角色功能权限矩阵**：描述各角色（Admin、SA、Analyst 等）对每个功能模块的访问权限
  - 功能模块包括：认证与会话、用户管理、业务数据管理、Desktop 入口等
  - 权限标识：✅（允许）、❌（禁止）

- **角色数据表权限矩阵（RLS）**：描述各角色对数据库表的读写权限
  - 包括所有相关数据表：auth.users、业务表等
  - 权限维度：SELECT、INSERT、UPDATE、DELETE
  - 说明 RLS 策略如何基于 JWT `app_metadata.role` 判定

**2. 文档结构要求**

- 三大块结构：目标与背景 → 需求 → 设计约束与规范
- 内容内聚：相关内容集中，避免分散
- 符合阅读顺序：从"为什么"到"做什么"到"怎么做"
- 需求与设计分离：不要混在一起

**3. 设计文档规范**

`design.md` 应包含：
- 设计基线与架构原则（技术栈、Supabase 能力边界）
- 数据模型设计（表结构、关系、约束）
- 权限与安全设计（功能权限、数据权限）
- 页面与交互设计（路由、列表、CRUD 流程）
- 技术实现方案（文件结构、Repository 模式、Server Actions 接口）
- 示例代码精简：只保留接口签名，不放完整实现

## 沟通原则
- 当需要向用户提问以澄清需求或做决策时，必须同时给出：我的推荐选项（默认）、关键考量/取舍、以及不确定时可采用的默认决策，避免只抛问题。

## 开发流程原则

### 标准工作流

```
收到任务 → 阅读规范 → 按规范执行 → 验证清单 → 交付
```

### 1. 开发前先阅读规范

开始任何开发任务前，必须阅读：
- `docs/README.md`（文档入口）
- `docs/DECISIONS.md`（长期约束）
- `docs/TESTING.md`（测试规范）
- `docs/LOGIC.md`（Web 侧强约定，优先级最高）
- `docs/UI.md`（UI 组件规范）

**规范优先级：`docs/LOGIC.md` > 其他规范**

### 2. 交付边界原则（最重要）

**核心原则：`web/` 目录只包含交付代码**

```
web/                     # 只包含：app/, components/, domain/, features/, lib/
tests/                   # 所有测试代码（E2E、验收脚本）
supabase/scripts/        # 数据库开发脚本
docs/                    # 项目文档
scripts/                 # 开发/运维脚本
temp/                    # 临时输出（不提交）
```

**典型场景：**

| 场景 | 应放位置 | 禁止 |
|------|---------|------|
| 创建测试脚本 | `tests/e2e/` 或 `tests/scripts/` | `web/scripts/` |
| 创建数据库验证脚本 | `supabase/scripts/` | `web/scripts/` |
| 创建新功能模块 | `web/features/<name>/` | - |
| 创建 UI 组件 | `web/components/` 或 `web/features/<name>/components/` | - |
| 创建临时测试文件 | `temp/` | 任何源码目录 |

### 3. 修改前先审核

修改代码前，先审核目标文件是否符合现有规范；不符合则先清理。

### 4. 先清理再新增

清理代码、测试跑通后，再添加新需求；避免在不稳定的代码上叠加新功能。

### 5. 验证清单

实施任何变更前，确认：
- [ ] 已阅读相关规范文档
- [ ] 代码放在正确的目录（web/ 只放交付代码）
- [ ] 触库逻辑只在 `features/*/repo/*`
- [ ] 页面层只 import `features/<name>`，不直连 repo
- [ ] 测试代码不在 web/ 目录 

## 经验积累（Instinct 系统）

经验积累通过 **Instinct 系统**管理，支持跨会话、跨项目复用：
- `/instinct-status`：查看已积累的经验
- `/instinct-import <文件>`：导入新的经验
- `/instinct-export`：导出经验供分享
