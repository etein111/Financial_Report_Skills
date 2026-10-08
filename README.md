# Financial Report Skills

金融报告相关的技能与工具集。本仓库汇总了两个项目及其文档，各自保留了原有提交历史。

## 目录结构

| 目录 | 说明 | 来源 |
|---|---|---|
| `neolyst/` | Next.js Web 应用（`next.config.js`、`web/`、`prototype/`、`supabase/`） | 原 `neolyst` 仓库 `main` 分支 |
| `neoskills/` | Python 技能库（`skills/`、`templates/`、`samples/`、`supabase/`） | 原 `neoskills` 仓库 `main` 分支 |
| `docs/` | 项目分析与调研文档 | 本仓库新增 |

两个子项目通过 `git subtree` 方式合并，各自完整的提交历史均保留：

```bash
git log --oneline -- neoskills/   # 查看 neoskills 的历史
git log --oneline -- neolyst/     # 查看 neolyst 的历史
```

## 分支

`neoskills` 原有的其余分支也一并保留：

- `main` — 当前主干，`neolyst/` 与 `neoskills/` 以子目录形式组织
- `feature/neolyst-report`
- `refactor/code-cleanup`

> 注意：后两个分支保留的是合并前的原始目录结构（内容位于仓库根目录），
> 与 `main` 的子目录布局不同。

## 本地开发

两个子项目相互独立，各自安装依赖：

```bash
# neoskills (Python)
cd neoskills && uv sync

# neolyst (Node.js)
cd neolyst && npm install
```

各子项目的详细说明见其目录下的 `README.md` / `CLAUDE.md` / `AGENTS.md`。
