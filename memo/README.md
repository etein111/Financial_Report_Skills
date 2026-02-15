# Memo 机制（会话备忘）

本目录用于保存"跨会话上下文"，帮助快速恢复背景、阻塞点与下一步动作。

## 文件职责

| 文件 | 内容 |
|------|------|
| `TODO.md` | 未完成任务的上下文、阻塞点、下一步动作 |

## 使用规范

### 什么时候写 TODO.md

- 有明确的下一步行动
- 需要跨会话保持的任务上下文
- 当前遇到的阻塞点

### 不适合写入 memo 的内容

- 已稳定的长期约束：应迁移到 `docs/DECISIONS.md` / `docs/LOGIC.md` / `docs/UI.md`
- OpenSpec change 的正式规范：应在 `openspec/changes/<change>/`
- 账号口令、PAT、DB 密码等密钥：禁止写入
- **经验积累**：使用 `/instinct-import` 导入到 instinct 系统（见下方）

## 经验积累（Instinct 系统）

解决问题的经验、踩过的坑应导入到 instinct 系统，而非写在 TODO.md 里。

**导入方式**：
1. 创建 YAML 格式的 instinct 文件（见 `~/.claude/homunculus/instincts/inherited/` 现有文件作为模板）
2. 运行 `/instinct-import <文件路径>`

**查看已积累的经验**：`/instinct-status`

## 更新日志

| 日期 | 内容 |
|------|------|
| 2026-02-15 | 经验积累迁移到 instinct 系统 |
| 2026-02-15 | 初始结构 |
