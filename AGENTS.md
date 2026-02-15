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

## 沟通原则
- 当需要向用户提问以澄清需求或做决策时，必须同时给出：我的推荐选项（默认）、关键考量/取舍、以及不确定时可采用的默认决策，避免只抛问题。

## 开发流程原则

1. **开发前先阅读规范**：开始任何开发任务前，先阅读 `docs/README.md`（入口）、`docs/DECISIONS.md`（长期约束）、`docs/TESTING.md`（测试规范），并以 `docs/LOGIC.md` + `docs/UI.md` 作为 Web 侧强约定（冲突以 `docs/LOGIC.md` 为准）。
2. **修改前先审核**：修改代码前，先审核目标文件是否符合现有规范；不符合则先清理。
3. **先清理再新增**：清理代码、测试跑通后，再添加新需求；避免在不稳定的代码上叠加新功能。 

## 会话备忘
- 若要继续"auth-and-user-management 拆分为 3 个 change"的工作，请先阅读 `memo/openspec-auth-and-user-management-split.md` 恢复上下文。

## 工作机制（上下文沉淀）

- 每次会话结束前：更新 `memo/TODO.md`（只写"未完成事项 + 下一步可执行动作"，避免长篇叙事）。
- 若有较长排障/取舍推理：在 `memo/` 里补一份 memo，并在 `memo/TODO.md` 里链接它。
- **经验积累**：解决的问题、踩过的坑应使用 `/instinct-import` 导入到 instinct 系统，而非写在 TODO.md 里。
- 历史兼容：如果仓库存在 `MEMO.md`，按旧约定先读取再删除（不要新增 `MEMO.md`，改用 `memo/`）。

### Instinct 系统

经验积累通过 instinct 系统管理，支持跨会话、跨项目复用：
- `/instinct-status`：查看已积累的经验
- `/instinct-import <文件>`：导入新的经验
- `/instinct-export`：导出经验供分享
