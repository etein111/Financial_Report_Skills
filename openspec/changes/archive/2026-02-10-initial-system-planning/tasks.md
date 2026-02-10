# 实施任务清单

## 1. 项目初始化和环境搭建

- [ ] 1.1 初始化项目结构(创建 monorepo: backend/ 和 frontend/)
- [ ] 1.2 后端: 使用 uv 初始化 FastAPI 项目
- [ ] 1.3 后端: 配置 Supabase 连接和认证
- [ ] 1.4 后端: 配置数据库迁移工具(Alembic)
- [ ] 1.5 前端: 使用 Vite 初始化 Vue 3 项目
- [ ] 1.6 前端: 配置 Tailwind CSS（与prototype保持一致）
- [ ] 1.7 前端: 配置 Axios 和 API 请求拦截器
- [ ] 1.8 配置开发环境(.env 文件示例)

## 2. 数据库设计

- [ ] 2.1 编写数据库表结构 SQL 脚本
  - [ ] 2.1.1 analyst 表(添加 role 字段到 Supabase Auth，不放在 analyst 表中)
  - [ ] 2.1.2 region 表
  - [ ] 2.1.3 sector 表
  - [ ] 2.1.4 coverage 表
  - [ ] 2.1.5 coverage_analyst 关联表
  - [ ] 2.1.6 template 表(报告模板 Word/Excel)
  - [ ] 2.1.7 report 表(添加工作流字段: status, submitted_at, submitted_by, published_at, published_by, rejected_at, rejected_by, rejection_reason)
  - [ ] 2.1.8 report_version 表
  - [ ] 2.1.9 report_analyst 关联表
- [ ] 2.2 创建 RLS 辅助函数
  - [ ] 2.2.1 get_current_analyst_id() - 从 JWT 提取 analyst_id
  - [ ] 2.2.2 get_current_role() - 从 JWT 提取 role
- [ ] 2.3 创建 RLS policies
  - [ ] 2.3.1 report 表的 RLS policies（根据角色控制读写权限）
  - [ ] 2.3.2 analyst 表的 RLS policies（Admin only）
  - [ ] 2.3.3 coverage, sector, region, template 表的 RLS policies
- [ ] 2.4 创建数据库迁移
- [ ] 2.5 在 Supabase 中执行迁移
- [ ] 2.6 插入初始数据(预设 Region, 示例 Sector, Admin 账号)
- [ ] 2.7 测试 RLS policies（确保权限正确）

## 3. 用户认证和权限系统

- [ ] 3.1 Supabase Auth 集成
  - [ ] 3.1.1 配置 Supabase Auth 项目
  - [ ] 3.1.2 实现 JWT Token 验证中间件
  - [ ] 3.1.3 实现登录 API (/api/auth/login)
  - [ ] 3.1.4 实现登出 API (/api/auth/logout)
  - [ ] 3.1.5 实现获取当前用户 API (/api/auth/me)

- [ ] 3.2 Supabase RLS (Row Level Security) 实现
  - [ ] 3.2.1 在数据库表上启用 RLS (analyst, report, coverage, sector, region, template)
  - [ ] 3.2.2 创建辅助函数 (get_current_analyst_id, get_current_role)
  - [ ] 3.2.3 定义三种角色 (analyst, sa, admin) 在 user_metadata 和 app_metadata 中
  - [ ] 3.2.4 为 report 表创建 RLS policies
    - [ ] 3.2.4.1 Analyst 只能查看自己的报告
    - [ ] 3.2.4.2 SA/Admin 可以查看所有报告
    - [ ] 3.2.4.3 Analyst 只能插入自己的报告
    - [ ] 3.2.4.4 Admin 可以为任何 Analyst 插入报告
    - [ ] 3.2.4.5 Analyst 只能更新自己的草稿报告
    - [ ] 3.2.4.6 Admin 可以更新任何报告
    - [ ] 3.2.4.7 SA 不能更新报告（没有 policy）
    - [ ] 3.2.4.8 SA/Admin 可以审核报告（更新状态为 published/rejected）
  - [ ] 3.2.5 为基础数据表创建 RLS policies
    - [ ] 3.2.5.1 Analyst 表：Admin 可管理，所有用户可查看
    - [ ] 3.2.5.2 Coverage/Sector/Region/Template 表：所有用户可查看，Admin 可修改
  - [ ] 3.2.6 测试 RLS policies（每种角色单独测试）

- [ ] 3.3 账号管理功能
  - [ ] 3.3.1 Analyst 创建时自动创建 Supabase Auth 账号
  - [ ] 3.3.2 实现默认密码生成和邮件通知
  - [ ] 3.3.3 实现密码重置功能（使用 Supabase Auth Admin API）
  - [ ] 3.3.4 实现账号启用/禁用功能（同步更新 Supabase Auth）

- [ ] 3.4 前端认证和权限
  - [ ] 3.4.1 实现登录页面
  - [ ] 3.4.2 Token 存储和自动续期
  - [ ] 3.4.3 Axios 请求拦截器（添加 Authorization header）
  - [ ] 3.4.4 权限检查函数库 (can.editReport, can.viewReport 等，仅用于 UI 控制)
  - [ ] 3.4.5 路由守卫（基于角色控制页面访问）

## 4. 后端 API 开发 - 基础数据管理

- [ ] 4.1 Analyst API (Admin only)
  - [ ] 4.1.1 GET /api/analysts - 获取列表(分页、搜索)
  - [ ] 4.1.2 GET /api/analysts/check-email - 检查邮箱是否可用(检查 analyst 表和 Supabase Auth)
  - [ ] 4.1.3 POST /api/analysts - 创建(邮箱唯一性验证,自动创建 Supabase Auth 账号)
  - [ ] 4.1.4 GET /api/analysts/{id} - 获取详情
  - [ ] 4.1.5 PUT /api/analysts/{id} - 更新(同步更新 Auth 邮箱)
  - [ ] 4.1.6 POST /api/analysts/{id}/reset-password - 重置密码
  - [ ] 4.1.7 PUT /api/analysts/{id}/toggle-status - 启用/禁用账号

- [ ] 4.2 Region API
  - [ ] 4.2.1 GET /api/regions - 获取列表
  - [ ] 4.2.2 POST /api/regions - 创建
  - [ ] 4.2.3 PUT /api/regions/{id} - 更新

- [ ] 4.3 Sector API
  - [ ] 4.3.1 GET /api/sectors - 获取树形结构
  - [ ] 4.3.2 POST /api/sectors - 创建(支持指定父级)
  - [ ] 4.3.3 PUT /api/sectors/{id} - 更新

- [ ] 4.4 Coverage API
  - [ ] 4.4.1 GET /api/coverage - 获取列表(分页、筛选)
  - [ ] 4.4.2 POST /api/coverage/check-duplicate - 检查 ticker 是否已被其他分析师覆盖
  - [ ] 4.4.3 POST /api/coverage - 创建(ticker+analyst 唯一性验证,支持重复 ticker 创建并记录审批)
  - [ ] 4.4.4 GET /api/coverage/{id} - 获取详情
  - [ ] 4.4.5 PUT /api/coverage/{id} - 更新

- [ ] 4.5 Template API (所有用户可查看，Admin 可管理)
  - [ ] 4.5.1 GET /api/templates - 获取列表(所有用户)
  - [ ] 4.5.2 GET /api/templates/{id} - 下载模板(所有用户)
  - [ ] 4.5.3 POST /api/templates - 上传模板(Admin only)
  - [ ] 4.5.4 PUT /api/templates/{id} - 更新模板(Admin only)
  - [ ] 4.5.5 DELETE /api/templates/{id} - 删除模板(Admin only)

## 5. 后端 API 开发 - 报告管理

- [ ] 5.1 Report API (权限由 RLS 自动控制)
  - [ ] 5.1.1 GET /api/reports - 获取列表(RLS 自动根据角色过滤: Analyst 只看自己的, SA/Admin 看所有)
  - [ ] 5.1.2 POST /api/reports - 创建报告(Analyst 为自己创建, Admin 可为其他 Analyst 创建, RLS 检查权限)
  - [ ] 5.1.3 GET /api/reports/{id} - 获取详情(RLS 检查权限)
  - [ ] 5.1.4 PUT /api/reports/{id} - 更新基本信息(RLS 检查: Analyst 可编辑自己的报告(包括已提交), Admin 可编辑任何, SA 不能编辑)
  - [ ] 5.1.5 POST /api/reports/{id}/submit - 提交审核(Analyst only, RLS 检查拥有权限, 草稿→已提交)
  - [ ] 5.1.6 POST /api/reports/{id}/reedit - 重新编辑(Analyst only, RLS 检查拥有权限, 已拒绝→草稿, 清除拒绝信息)

- [ ] 5.2 Report File API
  - [ ] 5.2.1 POST /api/reports/{id}/word - 上传/更新 Word 文档
  - [ ] 5.2.2 POST /api/reports/{id}/model - 上传/更新 Excel Model
  - [ ] 5.2.3 GET /api/reports/{id}/word - 下载 Word 文档
  - [ ] 5.2.4 GET /api/reports/{id}/model - 下载 Excel Model

- [ ] 5.3 Report Version API
  - [ ] 5.3.1 GET /api/reports/{id}/versions - 获取版本历史
  - [ ] 5.3.2 GET /api/reports/{id}/versions/{version} - 获取特定版本详情
  - [ ] 5.3.3 POST /api/reports/{id}/versions/compare - 对比两个版本

## 6. 后端 API 开发 - 报告审核

- [ ] 6.1 Report Review API (SA and Admin only)
  - [ ] 6.1.1 GET /api/reports/submitted - 获取待审核报告列表
  - [ ] 6.1.2 GET /api/reports/review/stats - 获取审核统计(待审核数、今日已审核等)
  - [ ] 6.1.3 POST /api/reports/{id}/approve - 批准发布(已提交→已发布)
  - [ ] 6.1.4 POST /api/reports/{id}/reject - 拒绝发布(已提交→已拒绝, 需要理由)
  - [ ] 6.1.5 GET /api/reports/{id}/review-history - 查看审核历史

- [ ] 6.2 邮件通知系统
  - [ ] 6.2.1 实现账号创建通知邮件
  - [ ] 6.2.2 实现报告批准通知邮件
  - [ ] 6.2.3 实现报告拒绝通知邮件(包含拒绝理由)
  - [ ] 6.2.4 配置 SMTP 或使用 Supabase 邮件服务

- [ ] 6.3 批量审核操作(可选)
  - [ ] 6.3.1 POST /api/reports/batch-approve - 批量批准
  - [ ] 6.3.2 POST /api/reports/batch-reject - 批量拒绝

## 7. 后端 API 开发 - 对外接口

- [ ] 7.1 Public API (无需认证)
  - [ ] 7.1.1 GET /api/public/published-reports - 获取已发布报告列表(支持 since 参数增量查询)
  - [ ] 7.1.2 生成带签名的文件下载 URL(Word 和 Model 文件)

## 8. 前端开发 - 多页面基础架构

- [ ] 8.1 登录页面
  - [ ] 8.1.1 Login.vue - 登录表单(粒子效果背景)
  - [ ] 8.1.2 登录后跳转到桌面

- [ ] 8.2 桌面主页
  - [ ] 8.2.1 Desktop.vue - 桌面主界面
  - [ ] 8.2.2 功能卡片分组(报告功能组 + 基础数据管理组)
  - [ ] 8.2.3 基于角色显示不同功能卡片
  - [ ] 8.2.4 顶部导航栏(Logo, 用户信息, 登出按钮)

- [ ] 8.3 页面路由
  - [ ] 8.3.1 配置 Vue Router
  - [ ] 8.3.2 实现路由守卫(权限检查)
  - [ ] 8.3.3 所有功能页在新标签页打开(target="_blank")

## 9. 前端开发 - 报告管理页面

- [ ] 9.1 报告列表页面
  - [ ] 9.1.1 ReportsPage.vue - 列表页面(独立 URL)
  - [ ] 9.1.2 基于角色显示不同报告(Analyst 只能看自己的)
  - [ ] 9.1.3 状态筛选(草稿/已提交/已发布/已拒绝)
  - [ ] 9.1.4 报告卡片显示(标题、类型、状态、时间)
  - [ ] 9.1.5 操作按钮(编辑: Analyst 草稿+已提交, 提交审核: Analyst 草稿, 查看: 所有)

- [ ] 9.2 新建报告页面
  - [ ] 9.2.1 NewReportPage.vue - 创建报告页面
  - [ ] 9.2.2 动态表单(根据报告类型显示不同字段)
  - [ ] 9.2.3 Admin 特有功能: "Create for Analyst" 选择器
  - [ ] 9.2.4 文件上传组件(Word + Excel)
  - [ ] 9.2.5 表单验证
  - [ ] 9.2.6 保存草稿按钮

- [ ] 9.3 报告编辑页面
  - [ ] 9.3.1 ReportEditPage.vue - 编辑报告页面
  - [ ] 9.3.2 基本信息编辑组件
  - [ ] 9.3.3 文件重新上传组件
  - [ ] 9.3.4 提交审核按钮(Analyst only, 草稿状态)
  - [ ] 9.3.5 权限控制(Analyst 可编辑自己的报告(包括已提交), SA 不能编辑, Admin 可编辑所有)

- [ ] 9.4 版本历史页面
  - [ ] 9.4.1 ReportVersionsPage.vue - 版本历史页面
  - [ ] 9.4.2 版本列表组件
  - [ ] 9.4.3 版本详情查看组件
  - [ ] 9.4.4 版本对比组件

## 10. 前端开发 - 报告审核页面

- [ ] 10.1 报告审核列表页面(SA and Admin only)
  - [ ] 10.1.1 ReportReviewPage.vue - 审核列表页面
  - [ ] 10.1.2 待审核报告列表(状态为"已提交")
  - [ ] 10.1.3 审核统计信息卡片(待审核数、今日已审核等)
  - [ ] 10.1.4 筛选功能(报告类型、Analyst、提交时间)
  - [ ] 10.1.5 高亮显示等待时间较长的报告

- [ ] 10.2 报告审核详情页面(SA and Admin only)
  - [ ] 10.2.1 ReportReviewDetailPage.vue - 审核详情页面
  - [ ] 10.2.2 显示完整报告信息
  - [ ] 10.2.3 Word 文档预览或下载
  - [ ] 10.2.4 Excel Model 下载
  - [ ] 10.2.5 显示 Analyst 历史报告统计(可选)
  - [ ] 10.2.6 批准发布按钮
  - [ ] 10.2.7 拒绝发布按钮(弹出理由输入对话框)

- [ ] 10.3 拒绝理由对话框
  - [ ] 10.3.1 RejectionReasonDialog.vue - 拒绝理由输入对话框
  - [ ] 10.3.2 预设拒绝理由选项
  - [ ] 10.3.3 自定义理由输入
  - [ ] 10.3.4 确认和取消按钮

## 11. 前端开发 - 基础数据管理页面

- [ ] 11.1 Analyst 管理页面(Admin only)
  - [ ] 11.1.1 AnalystsPage.vue - Analyst 管理页面
  - [ ] 11.1.2 列表显示(搜索、创建、编辑)
  - [ ] 11.1.3 AnalystForm.vue - 表单组件(包含角色选择)
  - [ ] 11.1.4 重置密码功能
  - [ ] 11.1.5 启用/禁用账号功能

- [ ] 11.2 Sector 管理页面
  - [ ] 11.2.1 SectorsPage.vue - Sector 管理页面
  - [ ] 11.2.2 树形结构显示(展开/收起)
  - [ ] 11.2.3 SectorForm.vue - 表单组件(支持选择父级)

- [ ] 11.3 Region 管理页面
  - [ ] 11.3.1 RegionsPage.vue - Region 管理页面
  - [ ] 11.3.2 列表显示(创建、编辑)

- [ ] 11.4 Coverage 管理页面
  - [ ] 11.4.1 CoveragePage.vue - Coverage 管理页面
  - [ ] 11.4.2 列表显示(筛选)
  - [ ] 11.4.3 CoverageForm.vue - 表单组件(支持多 Analyst 选择)
  - [ ] 11.4.4 DuplicateWarningDialog.vue - 重复 Ticker 警告对话框

- [ ] 11.5 Template 管理页面(所有用户可查看和下载，Admin 可管理)
  - [ ] 11.5.1 TemplatesPage.vue - 模板页面
  - [ ] 11.5.2 模板卡片网格显示(所有用户可查看)
  - [ ] 11.5.3 下载模板功能(所有用户可用)
  - [ ] 11.5.4 上传 Word/Excel 模板(Admin only)
  - [ ] 11.5.5 编辑和删除模板(Admin only)

## 12. 版本管理实现

- [ ] 12.1 后端: 实现版本创建逻辑
  - [ ] 12.1.1 监听基本信息修改,创建版本记录
  - [ ] 12.1.2 监听文件上传,创建版本记录
  - [ ] 12.1.3 生成基本信息 JSONB snapshot

- [ ] 12.2 前端: 实现版本历史展示
  - [ ] 12.2.1 版本列表组件
  - [ ] 12.2.2 版本详情组件
  - [ ] 12.2.3 版本对比组件

## 13. 测试和验证

- [ ] 13.1 后端单元测试
  - [ ] 13.1.1 测试 Supabase Auth 集成（登录、登出、获取用户）
  - [ ] 13.1.2 测试 RLS policies（每种角色分别测试）
    - [ ] 13.1.2.1 测试 Analyst 角色的 RLS 权限
    - [ ] 13.1.2.2 测试 SA 角色的 RLS 权限
    - [ ] 13.1.2.3 测试 Admin 角色的 RLS 权限
    - [ ] 13.1.2.4 测试权限隔离（Analyst 不能访问他人数据）
  - [ ] 13.1.3 测试 Analyst API
  - [ ] 13.1.4 测试 Report API（各种角色权限）
  - [ ] 13.1.5 测试 Report Review API
  - [ ] 13.1.6 测试版本管理逻辑
  - [ ] 13.1.7 测试工作流状态流转

- [ ] 13.2 前端测试
  - [ ] 13.2.1 组件测试
  - [ ] 13.2.2 权限控制测试（UI 显示/隐藏）
  - [ ] 13.2.3 E2E 测试

- [ ] 13.3 集成测试
  - [ ] 13.3.1 测试完整的报告创建流程（Analyst）
  - [ ] 13.3.2 测试 Admin 替 Analyst 创建报告
  - [ ] 13.3.3 测试报告提交流程
  - [ ] 13.3.4 测试 SA 审核流程（批准和拒绝）
  - [ ] 13.3.5 测试版本管理流程
  - [ ] 13.3.6 测试权限隔离（RLS 保证，Analyst 不能看他人报告）
  - [ ] 13.3.7 测试邮件通知
  - [ ] 13.3.8 测试 RLS 绕过攻击（确保应用层漏洞不影响数据安全）

- [ ] 13.4 RLS 安全测试
  - [ ] 13.4.1 测试直接数据库访问（使用不同角色的 JWT）
  - [ ] 13.4.2 测试 SQL 注入（RLS 应该有效防护）
  - [ ] 13.4.3 测试权限提升攻击
  - [ ] 13.4.4 性能测试（RLS 对查询性能的影响）

- [ ] 13.5 用户验收测试
  - [ ] 13.5.1 测试 Analyst 角色完整流程
  - [ ] 13.5.2 测试 SA 角色完整流程
  - [ ] 13.5.3 测试 Admin 角色完整流程

## 14. 部署和文档

- [ ] 14.1 后端部署准备
  - [ ] 14.1.1 Dockerfile
  - [ ] 14.1.2 环境变量配置
  - [ ] 14.1.3 配置 Supabase 生产环境

- [ ] 14.2 前端部署准备
  - [ ] 14.2.1 生产环境构建配置
  - [ ] 14.2.2 静态资源配置

- [ ] 14.3 编写项目文档
  - [ ] 14.3.1 更新 README.md
  - [ ] 14.3.2 API 文档(使用 FastAPI 自动生成的 Swagger UI)
  - [ ] 14.3.3 部署文档
  - [ ] 14.3.4 开发环境搭建文档
  - [ ] 14.3.5 用户手册(Analyst/SA/Admin 三种角色)
  - [ ] 14.3.6 权限和角色说明文档
  - [ ] 14.3.7 工作流程图(草稿→已提交→已发布/已拒绝)
