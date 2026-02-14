# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 语言偏好

**所有对话、文档、代码注释、提交信息均使用中文。**

## 项目概览

本项目使用 **OpenSpec** 管理变更和规范。
- 当前采用极简配置：`openspec/config.yaml` 仅保留 `schema: spec-driven`
- 详细上下文与规则在重建稳定后再补充

## OpenSpec 常用命令

```bash
# 变更管理
openspec list                    # 查看所有变更
openspec new change <name>     # 创建新变更
openspec continue                # 继续当前变更

# 配置查看
openspec schema which           # 查看当前使用的 schema
```
