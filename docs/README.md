# Docs

项目规范与约定的唯一入口。面向人和 AI 工具共同阅读。


## 核心文档（按优先级阅读）

| 优先级 | 文档 | 说明 |
|--------|------|------|
| 1 | `docs/REQUIREMENTS.md` | 系统需求全貌 |
| 2 | `docs/ARCHITECTURE.md` | 项目架构规范 |
| 3 | `docs/DECISIONS.md` | 长期约束与约定 |
| 4 | `docs/TESTING.md` | 测试规范（临时文件放 `temp/`） |
| 5 | `docs/LOGIC.md` | Web 分层约定（**优先级最高**） |
| 6 | `docs/UI.md` | UI 组件规范 |

---

## 开发流程原则

### 必须遵守的文档

开发时必须理解并遵守以上 6 个核心文档。

### 交付边界原则

**核心：`web/` 目录只包含交付代码**

```
web/                     # 交付代码：app/, components/, domain/, features/, lib/
tests/                   # 所有测试代码（E2E、验收脚本）
supabase/scripts/        # 数据库开发脚本
docs/                    # 项目文档
scripts/                 # 开发/运维脚本
temp/                    # 临时输出（不提交）
```

**典型场景：**

| 场景 | 应放位置 | 禁止 |
|------|---------|------|
| 测试脚本 | `tests/e2e/` 或 `tests/scripts/` | `web/scripts/` |
| 数据库验证脚本 | `supabase/scripts/` | `web/scripts/` |
| 新功能模块 | `web/features/<name>/` | - |
| UI 组件 | `web/components/` 或 `web/features/<name>/components/` | - |
| 临时测试文件 | `temp/` | 任何源码目录 |

---

## 子系统文档

| 子系统 | 文档 |
|--------|------|
| Web (Next.js) | `web/README.md`、`docs/LOGIC.md`、`docs/UI.md`、`docs/FRONTEND_VISUAL_CONSISTENCY.md` |
| Tests | `tests/README.md` |
| Supabase | `supabase/README.md` |
| 变更管理 | `openspec/` |

---

## 约定

- `docs/README.md` 是唯一入口与索引
- `docs/` 下其他文件彼此不相互引用，每个文件只负责一类事情
