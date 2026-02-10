## Context

Neolyst 项目目前是一个空仓库,只有原型 HTML 文件和 OpenSpec 规划文档。需要建立标准化的开发环境来支持后续的系统实施。

**约束条件:**
- 后端使用 Python + FastAPI
- 必须使用 Supabase 作为后端服务(认证、数据库、存储)
- 前端界面风格必须匹配现有的 prototype 设计
- 所有开发文档和注释使用中文

## Goals / Non-Goals

**Goals:**
- 建立可运行的开发环境,开发者可以快速启动后端和前端
- 配置统一的工具链(uv for Python, npm for JavaScript)
- 准备好 Supabase 集成的基础配置
- 提供清晰的环境配置文档

**Non-Goals:**
- 不包含具体的业务逻辑实现
- 不包含数据库表结构设计(属于下一个变更)
- 不包含认证系统实现(属于后续变更)
- 不包含生产环境部署配置

## Decisions

### Decision 1: 使用 uv 作为 Python 工具链

**选择:** uv (替代 pip + venv)

**理由:**
- 极快的依赖解析和安装速度(比 pip 快 10-100 倍)
- 统一管理虚拟环境和依赖,无需手动管理 venv
- 内置锁文件支持(`uv.lock`),确保团队依赖一致
- 兼容标准的 pyproject.toml 格式

**替代方案:**
- pip + venv: 速度慢,操作繁琐
- poetry: 较重,有兼容性问题

### Decision 2: 使用 Vite + Vue 3

**选择:** Vite 作为前端构建工具

**理由:**
- 极快的开发服务器启动速度(基于 ESM)
- 原生支持 TypeScript
- 丰富的插件生态
- 与 prototype 使用的 CDN 版本 Tailwind 兼容

**替代方案:**
- webpack: 配置复杂,启动慢
- Vue CLI: 基于 webpack,不如 Vite 快

### Decision 3: Tailwind CSS 配置保留原型的设计

**选择:** 从 prototype 复制 Tailwind 配置到前端项目

**理由:**
- 保持视觉一致性
- 原型的颜色和字体设置已经验证可行
- 减少设计调整工作

**实施:**
- 复制 `prototype/index.html` 中的 Tailwind 配置
- 提取颜色定义(zinc 色系)和字体配置(Inter + JetBrains Mono)

### Decision 4: Monorepo 结构

**选择:** backend/ 和 frontend/ 在同一个仓库

**理由:**
- 简化版本管理(前后端同步发布)
- 便于代码共享和统一工具配置
- 适合中小型项目(预计 1-5 人团队)

**替代方案:**
- 分离仓库: 增加复杂度,对小项目不必要

### Decision 5: 环境变量管理

**选择:** `.env.example` + `.gitignore`

**理由:**
- `.env.example` 作为模板提交到 git,指导开发者配置
- `.env` 文件包含真实密钥,不提交
- Supabase URL 和 key 需要每个开发者单独配置

**风险:** 开发者可能忘记配置 `.env` 导致启动失败
**缓解:** 在文档中明确说明步骤,启动脚本检查必要变量

## Risks / Trade-offs

**Risk 1:** uv 仍较新,生态可能不如 pip 成熟
**Mitigation:** uv 完全兼容 PyPI,可以使用任何 pip 包

**Risk 2:** 开发者可能不熟悉 uv 或 Vite
**Mitigation:** 提供详细的 README 和常用命令说明

**Trade-off:** 前端暂时不实现登录页面(保留原型作为参考)
**Reason:** 登录功能依赖认证系统,属于后续变更

## Migration Plan

不适用(这是初始项目设置,无迁移场景)

## Open Questions

无(所有技术决策已明确)
