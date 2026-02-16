# Docs

这是一组“跨目录、长期有效”的项目规范与约定。面向人和 AI 工具共同阅读。

约定：
- `docs/README.md` 是唯一入口与索引。
- `docs/` 下除 `README.md` 外的文件：彼此不相互引用；每个文件只负责一类事情。

建议阅读顺序：
1. `docs/REQUIREMENTS.md`：项目级需求全貌（按主题组织，非按 change 时间顺序）
2. `docs/ARCHITECTURE.md`：项目级架构全貌（按主题组织，非按 change 时间顺序）
3. `docs/DECISIONS.md`：跨后续功能的关键约束/约定（从 design/proposal 收敛而来）
4. `docs/TESTING.md`：测试与验收规范（尤其是临时文件目录 `temp/`）
5. `docs/LOGIC.md`：Web 逻辑与分层硬约定（优先级最高）
6. `docs/UI.md`：Web UI 组件规范

子系统文档：
- Web（Next.js）：`web/README.md`、`docs/LOGIC.md`、`docs/UI.md`
- Tests：`tests/README.md`
- Supabase：`supabase/README.md`
- 变更（OpenSpec）：`openspec/`

## Web (Next.js)

Next.js 应用，系统前端界面。

详细说明：`web/README.md`

### 目录结构

```text
web/                      # 交付代码
├─ app/                   # Next.js App Router
├─ components/            # React 组件
├─ domain/                # 业务类型与规则
├─ features/              # 业务功能模块
├─ lib/                   # 基础设施
└─ .env                   # 环境变量（提交到仓库）
```

### Web 规范文档

- 逻辑处理规范：`docs/LOGIC.md`
- UI 组件规范：`docs/UI.md`
- 测试规范：`docs/TESTING.md`
