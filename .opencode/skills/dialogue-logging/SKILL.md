---
name: dialogue-logging
description: Use when user wants to track evolving requirements, decision-making process, or multiple options presented during conversation
---

# Dialogue Logging

## Overview

Automatically track and summarize the conversation flow, including user needs evolution and AI-provided choices. Creates a persistent record of decisions made.

## When to Use

- User says "记录" (record), "追踪" (track), "总结" (summarize)
- User's requirements change or evolve over multiple messages
- You present multiple options/choices for user to choose from
- User asks "我之前说了什么" (what did I say before) or similar
- Project involves iterative refinement where previous decisions matter

## Core Pattern

### 1. Track Initial Request

When conversation starts or new task begins, note:
- User's original goal
- Context provided
- Constraints mentioned

### 2. Log Evolution

When user modifies requirements:
- What changed from previous request?
- Why did they change? (if stated)
- Previous approach being abandoned

### 3. Document Choices

When presenting options, ALWAYS log with context:
选项记录
背景: [为什么需要做这个选择，问题的背景]
- 选项A: [方案描述] → 用户决策: chosen/rejected/pending [简要原因]
- 选项B: [方案描述] → 用户决策: chosen/rejected/pending [简要原因]

### 4. Summary Output

When user asks for summary, provide plain text only (no code blocks):

对话摘要

原始需求
[用户最初的需求]

需求演变
1. [第一个变化] - [原因]
2. [第二个变化] - [原因]

决策记录
- [选项1]: chosen/rejected - [原因]
- [选项2]: chosen/rejected - [原因]

当前状态
[用户当前想要完成的事情]

## Quick Reference

| Trigger | Action |
|---------|--------|
| New task begins | Log initial request |
| Requirement changes | Note evolution |
| Present options | Log each option with → |
| User makes decision | Mark option as chosen/rejected |
| "总结" / "summary" | Generate structured summary |

## Common Mistakes

- **Not logging options**: Always track what you presented, even if user didn't choose explicitly
- **Forgetting context**: Initial requirements matter for later understanding
- **No decision markers**: Mark each option as chosen/rejected/pending
- **Skipping "why"**: If user explains why they changed something, record it

## Implementation

### Session Isolation

每个独立的话题/项目使用独立的日志文件，文件放在项目根目录的 .opencode/logs/ 文件夹下。

日志文件命名格式：session名称_日期.md，例如 neoskills-yc_2026-03-24.md

如何确定session名称：
1. 如果用户明确指定了session名称 → 使用用户指定的名称
2. 否则使用项目目录名 + 当天日期
3. 如果是跨多天的连续对话 → 使用同一个session名称直到用户明确新建

示例：
- 用户说"继续刚才的那个" → 加载最近的同名session
- 用户说"新开一个话题" → 创建新session

### Multi-Round Summarization

核心设计：日志持久化到文件，支持跨session累积

1. 每次总结时：
   - 先读取该session已有的日志文件
   - 在已有内容基础上追加新内容
   - 重新写入完整日志

2. 日志文件结构（纯文字）：

Session: [session名称]
创建时间: [时间]
最后更新: [时间]

原始需求
[用户最初的需求]

需求演变
第1轮 (时间)
- [变化1描述]
- [变化2描述]

第2轮 (时间)
- [新增变化]

决策记录
- [选项1]: chosen/rejected - [时间] - [原因]
- [选项2]: chosen/rejected - [时间] - [原因]

交互摘要
消息1 (时间)
背景/上下文: [这段对话发生的背景，比如正在讨论什么问题]
User: [用户完整消息的要点]
AI: [AI的关键回应，包含提供的选项、解释的方案等]
影响: [这次交互带来的变化或决策]

消息2 (时间)
背景/上下文: [这段对话发生的背景]
User: [用户完整消息的要点]
AI: [AI的关键回应]
影响: [这次交互带来的变化或决策]

当前状态
[最新一轮用户想要完成的事情]

3. 增量更新规则：
   - 需求演变：追加到"需求演变"部分，标记轮次和时间
   - 决策记录：追加新决策，标记时间
   - 交互摘要：每3-5轮对话做一次增量摘要，避免过长
   - 当前状态：每次更新

### 文件存储位置

项目根目录/.opencode/logs/
  - neoskills-yc_2026-03-24.md
  - project-x_2026-03-20.md

### 工具使用

使用 Write 工具创建/更新日志文件，使用 Read 工具读取历史内容。

工作流程：
1. 对话开始 → 检查是否存在已有session → 如有则加载
2. 对话过程中 → 维护内存中的当前session结构
3. 用户要求总结 → 读取历史文件 → 合并新内容 → 写入更新
4. 用户说"新建session" → 使用新的session名称创建文件
