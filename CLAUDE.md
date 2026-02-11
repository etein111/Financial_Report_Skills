# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概览

本项目使用 **OpenSpec** 管理变更和规范。
- **完整配置**: `openspec/config.yaml`（技术栈、规范）
- OpenSpec AI 会自动读取并注入到提示中

## OpenSpec 常用命令

```bash
# 变更管理
openspec list                    # 查看所有变更
openspec new change <name>     # 创建新变更
openspec continue                # 继续当前变更

# 配置查看
openspec schema which           # 查看当前使用的 schema
```

**遇到问题？** 查看 `openspec/config.yaml` 获取完整上下文。
