# Memo 机制（会话备忘）

本目录用于保存“跨会话上下文”，帮助下次启动 Codex 快速恢复背景、阻塞点与下一步动作。

## 什么时候写 memo

适合写入 memo 的内容：
- 云端阻塞排障过程与关键结论（例如 Supabase Auth 500 的现象、已排除项、下一步）
- 大段推理后的取舍（为什么不用 A，用 B；暂时性 workaround）
- 影响后续开发但还没稳定到可以写进 `docs/DECISIONS.md` 的约定

不适合写入 memo 的内容：
- 已稳定的长期约束：应迁移到 `docs/DECISIONS.md` / `docs/LOGIC.md` / `docs/UI.md`
- OpenSpec change 的正式规范：应在 `openspec/changes/<change>/proposal.md`、`design.md`、`tasks.md`、`specs/**`
- 账号口令、PAT、DB 密码等任何密钥：禁止写入（只放本机 `supabase/*.token`，并确保已被 `.gitignore` 忽略）

## 文件命名与结构

命名：`YYYY-MM-DD-<topic>.md`（例如 `2026-02-15-supabase-auth-500.md`）

建议结构：
- 背景/现象
- 已验证的事实（带命令或脚本路径）
- 排除项（为什么不是 X）
- 下一步（可执行步骤清单）
- 关联链接（指向 `memo/TODO.md`、相关脚本、相关 OpenSpec 文件路径）

## 场景入口（需要时再加入上下文）


推荐入口：
- 下一步行动清单：`memo/TODO.md`
- OpenSpec 变更相关（拆分/取舍/上下文）：`memo/openspec-*.md`
- 子系统排障（例如 Supabase/Auth）：`memo/supabase-*.md`

`memo/TODO.md` 只保留“下一步要做什么”，较长背景/排障细节放到对应的 `memo/*.md` 再从 TODO 链接过去。
