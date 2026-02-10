# Neolyst 实施计划

## 项目概述

**项目名称**: Neolyst - 投资研究报告管理系统
**开发周期**: 8-12 周（根据团队规模）
**团队配置建议**:
- 后端开发: 1人全职
- 前端开发: 1人全职
- 或者: 1-2名全栈开发人员

---

## 分阶段实施计划

### 🏗️ 阶段 1: 项目初始化和基础设施（Week 1-2）

**目标**: 搭建开发环境和基础设施

**时间**: 1-2 周

#### 1.1 项目初始化（2-3天）

- [ ] 创建 monorepo 项目结构
  ```
  neolyst/
  ├── backend/          # FastAPI 后端
  ├── frontend/         # Vue 3 前端
  ├── docs/             # 文档
  └── scripts/          # 工具脚本
  ```

- [ ] 后端初始化
  - 使用 `uv` 创建 FastAPI 项目
  - 配置 `pyproject.toml` 依赖
  - 配置开发环境（`.env.example`）

- [ ] 前端初始化
  - 使用 Vite 创建 Vue 3 + TypeScript 项目
  - 配置 Tailwind CSS（复用 prototype 配置）
  - 配置 Vue Router

- [ ] 配置开发工具
  - ESLint + Prettier（前端）
  - Black + Ruff + mypy（后端）
  - Git hooks（可选）

**交付物**:
- ✅ 可运行的前后端项目框架
- ✅ 开发环境配置文档

---

#### 1.2 数据库设计和 Supabase 配置（3-5天）

- [ ] 创建 Supabase 项目
  - 注册 Supabase 账号
  - 创建新项目
  - 获取数据库连接信息

- [ ] 编写数据库表结构 SQL
  - analyst 表
  - region 表
  - sector 表
  - coverage 表 + coverage_analyst 关联表
  - template 表
  - report 表 + report_analyst 关联表
  - report_version 表

- [ ] 创建 RLS 辅助函数
  ```sql
  CREATE OR REPLACE FUNCTION get_current_analyst_id()
  RETURNS UUID AS $$
    SELECT auth.uid()::UUID
  $$;

  CREATE OR REPLACE FUNCTION get_current_role()
  RETURNS TEXT AS $$
    SELECT auth.jwt()->>'app_metadata'->>'role'
  $$;
  ```

- [ ] 创建 RLS policies
  - report 表的 RLS policies（8个policy）
  - analyst 表的 RLS policies
  - coverage, sector, region, template 表的 RLS policies

- [ ] 插入初始数据
  - 预设 Region 数据
  - 示例 Sector 数据
  - 创建 Admin 账号

**交付物**:
- ✅ 完整的数据库 schema
- ✅ RLS policies 已部署并测试
- ✅ 可用的 Supabase 项目

---

#### 1.3 用户认证基础（2-3天）

- [ ] Supabase Auth 配置
  - 启用 Email + Password 认证
  - 配置 JWT settings

- [ ] 实现认证 API
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`

- [ ] 前端登录页面
  - Login.vue（复用 prototype 设计）
  - 粒子效果背景
  - Token 存储和自动续期

**交付物**:
- ✅ 可用的登录功能
- ✅ JWT 认证中间件

---

### 📊 阶段 2: 基础数据管理（Week 3-4）

**目标**: 实现所有基础数据的 CRUD 功能

**时间**: 1-2 周

#### 2.1 后端 API 开发（5-7天）

**Analyst API** (Admin only):
- [ ] GET /api/analysts - 列表（分页、搜索）
- [ ] GET /api/analysts/check-email - 邮箱重复检查
- [ ] POST /api/analysts - 创建（自动创建 Supabase Auth 账号）
- [ ] GET /api/analysts/{id} - 详情
- [ ] PUT /api/analysts/{id} - 更新
- [ ] POST /api/analysts/{id}/reset-password - 重置密码
- [ ] PUT /api/analysts/{id}/toggle-status - 启用/禁用

**Region API**:
- [ ] GET /api/regions
- [ ] POST /api/regions
- [ ] PUT /api/regions/{id}

**Sector API**:
- [ ] GET /api/sectors - 树形结构
- [ ] POST /api/sectors - 支持父级
- [ ] PUT /api/sectors/{id}

**Coverage API**:
- [ ] GET /api/coverage - 分页、筛选
- [ ] POST /api/coverage/check-duplicate - Ticker 重复检查
- [ ] POST /api/coverage - 创建（支持重复 ticker）
- [ ] GET /api/coverage/{id}
- [ ] PUT /api/coverage/{id}

**Template API**:
- [ ] GET /api/templates - 所有用户可查看
- [ ] GET /api/templates/{id} - 下载模板
- [ ] POST /api/templates - 上传（Admin only）
- [ ] PUT /api/templates/{id} - 更新（Admin only）
- [ ] DELETE /api/templates/{id} - 删除（Admin only）

**交付物**:
- ✅ 5个模块的完整 CRUD API
- ✅ API 文档（Swagger UI）

---

#### 2.2 前端页面开发（5-7天）

- [ ] 桌面主页
  - Desktop.vue（复用 prototype 设计）
  - 功能卡片分组
  - 基于角色显示卡片
  - 顶部导航栏

- [ ] Analyst 管理页面（Admin only）
  - 列表显示
  - 创建/编辑表单
  - 重置密码功能
  - 启用/禁用功能

- [ ] Sector 管理页面
  - 树形结构显示
  - 创建/编辑表单（支持选择父级）

- [ ] Region 管理页面
  - 列表显示
  - 创建/编辑表单

- [ ] Coverage 管理页面
  - 列表显示（筛选）
  - 创建/编辑表单（支持多 Analyst 选择）
  - 重复 Ticker 警告对话框

- [ ] Template 管理页面
  - 模板卡片网格（所有用户可查看）
  - 下载功能（所有用户可用）
  - 上传/编辑/删除（Admin only）

**交付物**:
- ✅ 5个功能页面
- ✅ 桌面主页

---

### 📝 阶段 3: 报告管理核心功能（Week 5-7）

**目标**: 实现报告创建、编辑、版本管理

**时间**: 2-3 周

#### 3.1 后端 API 开发（7-10天）

**Report API**:
- [ ] GET /api/reports - 列表（RLS 自动过滤）
- [ ] POST /api/reports - 创建
- [ ] GET /api/reports/{id} - 详情
- [ ] PUT /api/reports/{id} - 更新基本信息
- [ ] POST /api/reports/{id}/submit - 提交审核
- [ ] POST /api/reports/{id}/reedit - 重新编辑

**Report File API**:
- [ ] POST /api/reports/{id}/word - 上传/更新 Word
- [ ] POST /api/reports/{id}/model - 上传/更新 Excel
- [ ] GET /api/reports/{id}/word - 下载 Word
- [ ] GET /api/reports/{id}/model - 下载 Excel

**Report Version API**:
- [ ] GET /api/reports/{id}/versions - 版本历史
- [ ] GET /api/reports/{id}/versions/{version} - 特定版本详情
- [ ] POST /api/reports/{id}/versions/compare - 版本对比

**版本管理逻辑**:
- [ ] 监听基本信息修改，创建版本记录
- [ ] 监听文件上传，创建版本记录
- [ ] 生成基本信息 JSONB snapshot

**交付物**:
- ✅ 报告管理完整 API
- ✅ 版本管理功能

---

#### 3.2 前端页面开发（7-10天）

- [ ] 报告列表页面
  - ReportsPage.vue
  - 基于角色显示不同报告
  - 状态筛选（草稿/已提交/已发布/已拒绝）
  - 报告卡片显示
  - 操作按钮

- [ ] 新建报告页面
  - NewReportPage.vue
  - 动态表单（根据报告类型显示不同字段）
  - Admin 特有功能："Create for Analyst" 选择器
  - 文件上传组件（Word + Excel）
  - 保存草稿按钮

- [ ] 报告编辑页面
  - ReportEditPage.vue
  - 基本信息编辑
  - 文件重新上传
  - 提交审核按钮（Analyst only，草稿状态）
  - 权限控制

- [ ] 版本历史页面
  - ReportVersionsPage.vue
  - 版本列表组件
  - 版本详情查看
  - 版本对比组件

**交付物**:
- ✅ 4个报告管理页面
- ✅ 版本历史功能

---

### ✅ 阶段 4: 报告审核和工作流（Week 8-9）

**目标**: 实现审核功能和完整工作流

**时间**: 1-2 周

#### 4.1 后端 API 开发（3-5天）

**Report Review API** (SA and Admin only):
- [ ] GET /api/reports/submitted - 待审核列表
- [ ] GET /api/reports/review/stats - 审核统计
- [ ] POST /api/reports/{id}/approve - 批准发布
- [ ] POST /api/reports/{id}/reject - 拒绝发布
- [ ] GET /api/reports/{id}/review-history - 审核历史

**邮件通知系统**:
- [ ] 配置 SMTP 或 Supabase 邮件服务
- [ ] 账号创建通知邮件
- [ ] 报告批准通知邮件
- [ ] 报告拒绝通知邮件（含拒绝理由）

**交付物**:
- ✅ 审核功能 API
- ✅ 邮件通知系统

---

#### 4.2 前端页面开发（3-5天）

- [ ] 报告审核列表页面（SA and Admin only）
  - ReportReviewPage.vue
  - 待审核报告列表
  - 审核统计信息卡片
  - 筛选功能
  - 高亮显示等待时间较长的报告

- [ ] 报告审核详情页面（SA and Admin only）
  - ReportReviewDetailPage.vue
  - 显示完整报告信息
  - Word 文档预览或下载
  - Excel Model 下载
  - 批准/拒绝按钮
  - 拒绝理由对话框

**交付物**:
- ✅ 审核功能页面
- ✅ 拒绝理由对话框组件

---

### 🌐 阶段 5: 对外接口（Week 10）

**目标**: 提供外部系统查询接口

**时间**: 3-5天

- [ ] Public API (无需认证)
  - GET /api/public/published-reports - 增量查询
  - 生成带签名的文件下载 URL

**交付物**:
- ✅ 对外 API
- ✅ API 使用文档

---

### 🧪 阶段 6: 测试和验证（Week 11-12）

**目标**: 全面测试，确保质量

**时间**: 1-2 周

#### 6.1 后端单元测试

- [ ] Supabase Auth 集成测试
- [ ] RLS policies 测试（每种角色）
- [ ] Analyst API 测试
- [ ] Report API 测试
- [ ] Report Review API 测试
- [ ] 版本管理逻辑测试
- [ ] 工作流状态流转测试

#### 6.2 前端测试

- [ ] 组件测试
- [ ] 权限控制测试
- [ ] E2E 测试（关键流程）

#### 6.3 集成测试

- [ ] 完整的报告创建流程（Analyst）
- [ ] Admin 替 Analyst 创建报告
- [ ] 报告提交流程
- [ ] SA 审核流程（批准和拒绝）
- [ ] 版本管理流程
- [ ] 权限隔离测试
- [ ] 邮件通知测试

#### 6.4 安全测试

- [ ] RLS 安全测试
- [ ] SQL 注入测试
- [ ] 权限提升攻击测试
- [ ] 性能测试（RLS 影响）

#### 6.5 用户验收测试

- [ ] Analyst 角色完整流程
- [ ] SA 角色完整流程
- [ ] Admin 角色完整流程

**交付物**:
- ✅ 测试报告
- ✅ 已知问题列表

---

### 🚀 阶段 7: 部署和文档（Week 12）

**目标**: 部署上线，完善文档

**时间**: 3-5天

- [ ] 后端部署准备
  - Dockerfile
  - 环境变量配置
  - 配置 Supabase 生产环境

- [ ] 前端部署准备
  - 生产环境构建配置
  - 静态资源配置

- [ ] 编写项目文档
  - 更新 README.md
  - API 文档（Swagger UI）
  - 部署文档
  - 开发环境搭建文档
  - 用户手册（三种角色）
  - 权限和角色说明文档
  - 工作流程图

**交付物**:
- ✅ 部署的应用
- ✅ 完整的项目文档

---

## 时间线和里程碑

```
Week 1-2:  ━━━━━━━━━━━━━━━━━━━━━━━━ 阶段1: 基础设施
           ├─ 项目初始化 ✅
           ├─ 数据库设计和 Supabase 配置 ✅
           └─ 用户认证基础 ✅

Week 3-4:                    ━━━━━━━━━━━━━━━ 阶段2: 基础数据管理
                             ├─ 后端 API ✅
                             └─ 前端页面 ✅

Week 5-7:                                  ━━━━━━━━━━━━━━━━━━━ 阶段3: 报告管理
                                              ├─ 后端 API ✅
                                              └─ 前端页面 ✅

Week 8-9:                                                    ━━━━ 阶段4: 审核和工作流
                                                                 ├─ 后端 API ✅
                                                                 └─ 前端页面 ✅

Week 10:                                                               ━ 阶段5: 对外接口
                                                                        └─ Public API ✅

Week 11-12:                                                                  ━━━ 阶段6: 测试和验证
                                                                              ├─ 单元测试 ✅
                                                                              ├─ 集成测试 ✅
                                                                              └─ 安全测试 ✅

Week 12:                                                                             ━ 阶段7: 部署和文档
                                                                                      ├─ 部署 ✅
                                                                                      └─ 文档 ✅
```

---

## 资源配置建议

### 方案 A: 2人团队（推荐）

| 角色 | 人数 | 主要工作 |
|------|------|---------|
| 后端开发 | 1 | 阶段1-5的后端开发 |
| 前端开发 | 1 | 阶段1-5的前端开发 |
| **总计** | **2人** | **8-12周** |

**工作方式**:
- Week 1-2: 两人合作搭建基础设施
- Week 3-9: 后端和前端并行开发，API优先
- Week 10-12: 集中测试和部署

### 方案 B: 1-2人全栈团队

| 角色 | 人数 | 主要工作 |
|------|------|---------|
| 全栈开发 | 1-2 | 所有工作 |
| **总计** | **1-2人** | **10-14周** |

---

## 关键里程碑

1. **Week 2 结束**: 基础设施完成，可以登录
2. **Week 4 结束**: 所有基础数据管理功能可用
3. **Week 7 结束**: 报告创建和编辑功能可用（核心功能）
4. **Week 9 结束**: 审核和工作流完成（完整系统）
5. **Week 11 结束**: 测试完成
6. **Week 12 结束**: 部署上线

---

## 风险和应对

### 风险 1: Supabase RLS 性能问题

**应对**:
- 阶段1进行性能测试
- 如果性能不足，考虑缓存优化

### 风险 2: 前后端并行开发依赖问题

**应对**:
- 先定义好 API 契约（OpenAPI 规范）
- 使用 Mock 数据开发前端
- 后端优先开发 API

### 风险 3: 版本管理实现复杂

**应对**:
- 简化版本对比功能（只做基本信息对比）
- 优先实现版本列表和详情查看

### 风险 4: 时间估算不准确

**应对**:
- 每周进行进度review
- 及时调整计划
- 必要时削减非核心功能

---

## 可削减的功能（时间紧张时）

如果时间不足，可以考虑**暂缓**以下功能：

- ⏸️ 批量审核操作（阶段4）
- ⏸️ 版本对比功能（阶段3）
- ⏸️ Analyst 历史报告统计（阶段4）
- ⏸️ 对外接口API（阶段5）- 可以后期加

---

## 每日工作建议

### Standup（每日站会）

每天15分钟，团队成员分享：
1. 昨天完成了什么
2. 今天计划做什么
3. 遇到什么阻碍

### Weekly Review（每周回顾）

每周五下午，团队回顾：
1. 本周完成了什么
2. 下周计划做什么
3. 是否需要调整计划

---

## 开发工具和工作流

### 代码仓库

```
main         - 生产分支
develop      - 开发分支
feature/*    - 功能分支
```

### 工作流

1. 从 `develop` 创建功能分支
2. 开发完成后提交 Pull Request
3. Code Review（如果有多人）
4. 合并到 `develop`
5. 定期合并 `develop` 到 `main`

### 推荐工具

- **项目管理**: GitHub Issues / Projects
- **文档**: Markdown（已包含在 repo）
- **API 文档**: FastAPI Swagger UI
- **测试**: pytest（后端）+ Vitest（前端）
- **代码质量**: Black + Ruff（后端）+ ESLint + Prettier（前端）

---

## 总结

这个实施计划将 OpenSpec 任务清单组织成7个阶段，每个阶段有明确的目标、时间估算和交付物。

**关键成功因素**:
1. ✅ 严格遵循 OpenSpec 文档
2. ✅ 每个阶段完成后有可演示的功能
3. ✅ 及时沟通和调整
4. ✅ 重视测试和安全

**预期成果**:
- 一个完整的投资研究报告管理系统
- 支持三角色权限管理
- 完整的报告审核工作流
- 版本管理功能
- 可部署到生产环境

祝开发顺利！🚀
