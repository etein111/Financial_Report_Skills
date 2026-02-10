# 实施任务清单

## 1. 项目初始化和环境搭建

- [ ] 1.1 初始化项目结构(创建 monorepo: backend/ 和 frontend/)
- [ ] 1.2 后端: 使用 uv 初始化 FastAPI 项目
- [ ] 1.3 后端: 配置 Supabase 连接和认证
- [ ] 1.4 后端: 配置数据库迁移工具(Alembic)
- [ ] 1.5 前端: 使用 Vite 初始化 Vue 3 项目
- [ ] 1.6 前端: 配置 Element Plus UI 组件库
- [ ] 1.7 前端: 配置 Axios 和 API 请求拦截器
- [ ] 1.8 配置开发环境(.env 文件示例)

## 2. 数据库设计

- [ ] 2.1 编写数据库表结构 SQL 脚本
  - [ ] 2.1.1 analyst 表
  - [ ] 2.1.2 region 表
  - [ ] 2.1.3 sector 表
  - [ ] 2.1.4 coverage 表
  - [ ] 2.1.5 coverage_analyst 关联表
  - [ ] 2.1.6 template 表(报告模板 Word/Excel)
  - [ ] 2.1.7 report 表
  - [ ] 2.1.8 report_version 表
  - [ ] 2.1.9 report_analyst 关联表
- [ ] 2.2 创建数据库迁移
- [ ] 2.3 在 Supabase 中执行迁移
- [ ] 2.4 插入初始数据(预设 Region, 示例 Sector)

## 3. 后端 API 开发 - 基础数据管理

- [ ] 3.1 Analyst API
  - [ ] 3.1.1 GET /api/analysts - 获取列表(分页、搜索)
  - [ ] 3.1.2 POST /api/analysts - 创建(邮箱唯一性验证)
  - [ ] 3.1.3 GET /api/analysts/{id} - 获取详情
  - [ ] 3.1.4 PUT /api/analysts/{id} - 更新
  - [ ] 3.1.5 DELETE /api/analysts/{id} - 删除

- [ ] 3.2 Region API
  - [ ] 3.2.1 GET /api/regions - 获取列表
  - [ ] 3.2.2 POST /api/regions - 创建
  - [ ] 3.2.3 PUT /api/regions/{id} - 更新

- [ ] 3.3 Sector API
  - [ ] 3.3.1 GET /api/sectors - 获取树形结构
  - [ ] 3.3.2 POST /api/sectors - 创建(支持指定父级)
  - [ ] 3.3.3 PUT /api/sectors/{id} - 更新

- [ ] 3.4 Coverage API
  - [ ] 3.4.1 GET /api/coverage - 获取列表(分页、筛选)
  - [ ] 3.4.2 POST /api/coverage/check-duplicate - 检查 ticker 是否已被其他分析师覆盖
  - [ ] 3.4.3 POST /api/coverage - 创建(ticker+analyst 唯一性验证,支持重复 ticker 创建并记录审批)
  - [ ] 3.4.4 GET /api/coverage/{id} - 获取详情
  - [ ] 3.4.5 PUT /api/coverage/{id} - 更新

- [ ] 3.5 Template API (报告模板)
  - [ ] 3.5.1 GET /api/templates - 获取列表
  - [ ] 3.5.2 POST /api/templates - 上传模板(支持 Word 和 Excel)
  - [ ] 3.5.3 GET /api/templates/{id} - 下载模板
  - [ ] 3.5.4 PUT /api/templates/{id} - 更新模板

## 4. 后端 API 开发 - 报告管理

- [ ] 4.1 Report API
  - [ ] 4.1.1 GET /api/reports - 获取列表(分页、筛选、状态过滤)
  - [ ] 4.1.2 POST /api/reports - 创建报告(文件上传)
  - [ ] 4.1.3 GET /api/reports/{id} - 获取详情
  - [ ] 4.1.4 PUT /api/reports/{id} - 更新基本信息
  - [ ] 4.1.5 POST /api/reports/{id}/publish - 发布报告
  - [ ] 4.1.6 POST /api/reports/{id}/reject - 拒绝报告(软删除)

- [ ] 4.2 Report File API
  - [ ] 4.2.1 POST /api/reports/{id}/word - 上传/更新 Word 文档
  - [ ] 4.2.2 POST /api/reports/{id}/model - 上传/更新 Excel Model
  - [ ] 4.2.3 GET /api/reports/{id}/word - 下载 Word 文档
  - [ ] 4.2.4 GET /api/reports/{id}/model - 下载 Excel Model

- [ ] 4.3 Report Version API
  - [ ] 4.3.1 GET /api/reports/{id}/versions - 获取版本历史
  - [ ] 4.3.2 GET /api/reports/{id}/versions/{version} - 获取特定版本详情
  - [ ] 4.3.3 POST /api/reports/{id}/versions/compare - 对比两个版本

- [ ] 4.4 Public API (对外接口)
  - [ ] 4.4.1 GET /api/public/published-reports - 获取已发布报告列表(支持 since 参数增量查询)
  - [ ] 4.4.2 生成带签名的文件下载 URL(Word 和 Model 文件)

## 5. 前端开发 - 桌面式界面基础

- [ ] 5.1 窗口系统核心组件
  - [ ] 5.1.1 WindowContainer.vue - 窗口容器(支持拖动、调整大小)
  - [ ] 5.1.2 WindowHeader.vue - 窗口标题栏(最小化、最大化、关闭按钮)
  - [ ] 5.1.3 WindowManager.vue - 窗口管理器(层级管理、焦点控制)

- [ ] 5.2 窗口状态管理 (Pinia Store)
  - [ ] 5.2.1 window.ts - 窗口状态管理(打开、关闭、最小化、最大化、层级)
  - [ ] 5.2.2 实现窗口快捷键(Alt+Tab 切换)

- [ ] 5.3 桌面环境
  - [ ] 5.3.1 Desktop.vue - 桌面主界面
  - [ ] 5.3.2 DesktopIcon.vue - 桌面图标卡片(图标 + 名称)
  - [ ] 5.3.3 Taskbar.vue - 任务栏(已打开窗口列表、系统托盘)
  - [ ] 5.3.4 配置桌面背景和布局

- [ ] 5.4 登录页面
  - [ ] 5.4.1 Login.vue - 登录表单
  - [ ] 5.4.2 登录后跳转到桌面

## 6. 前端开发 - 基础数据管理窗口

- [ ] 6.1 Analyst 管理窗口
  - [ ] 6.1.1 AnalystWindow.vue - 窗口化界面(列表、搜索、创建、编辑)
  - [ ] 6.1.2 AnalystForm.vue - 表单组件
  - [ ] 6.1.3 添加桌面图标卡片

- [ ] 6.2 Sector 管理窗口
  - [ ] 6.2.1 SectorWindow.vue - 窗口化界面(树形结构、展开/收起)
  - [ ] 6.2.2 SectorForm.vue - 表单组件(支持选择父级)
  - [ ] 6.2.3 添加桌面图标卡片

- [ ] 6.3 Region 管理窗口
  - [ ] 6.3.1 RegionWindow.vue - 窗口化界面(列表、创建、编辑)
  - [ ] 6.3.2 添加桌面图标卡片

- [ ] 6.4 Coverage 管理窗口
  - [ ] 6.4.1 CoverageWindow.vue - 窗口化界面(列表、筛选)
  - [ ] 6.4.2 CoverageForm.vue - 表单组件(支持多 Analyst 选择)
  - [ ] 6.4.3 DuplicateWarningDialog.vue - 重复 Ticker 警告对话框
  - [ ] 6.4.4 添加桌面图标卡片

- [ ] 6.5 Template 管理窗口(报告模板 Word/Excel)
  - [ ] 6.5.1 TemplateWindow.vue - 窗口化界面(列表、上传 Word/Excel、下载)
  - [ ] 6.5.2 添加桌面图标卡片

## 7. 前端开发 - 报告管理窗口

- [ ] 7.1 报告列表窗口
  - [ ] 7.1.1 ReportListWindow.vue - 窗口化界面(列表、筛选、状态切换)
  - [ ] 7.1.2 状态标签切换(未发布/已发布/已拒绝)
  - [ ] 7.1.3 添加桌面图标卡片

- [ ] 7.2 报告创建窗口
  - [ ] 7.2.1 ReportCreateWindow.vue - 窗口化界面(动态表单)
  - [ ] 7.2.2 动态表单(根据报告类型显示不同字段)
  - [ ] 7.2.3 文件上传组件(Word + Excel)
  - [ ] 7.2.4 表单验证
  - [ ] 7.2.5 添加桌面图标卡片

- [ ] 7.3 报告编辑窗口
  - [ ] 7.3.1 ReportEditWindow.vue - 窗口化界面
  - [ ] 7.3.2 基本信息编辑组件
  - [ ] 7.3.3 文件重新上传组件
  - [ ] 7.3.4 发布/拒绝操作按钮

- [ ] 7.4 版本历史窗口
  - [ ] 7.4.1 ReportVersionsWindow.vue - 窗口化界面
  - [ ] 7.4.2 版本列表组件
  - [ ] 7.4.3 版本详情查看组件
  - [ ] 7.4.4 版本对比组件
  - [ ] 7.4.5 添加桌面图标卡片

## 8. 版本管理实现

- [ ] 8.1 后端: 实现版本创建逻辑
  - [ ] 8.1.1 监听基本信息修改,创建版本记录
  - [ ] 8.1.2 监听文件上传,创建版本记录
  - [ ] 8.1.3 生成基本信息 JSONB snapshot

- [ ] 8.2 前端: 实现版本历史展示
  - [ ] 8.2.1 版本列表组件
  - [ ] 8.2.2 版本详情组件
  - [ ] 8.2.3 版本对比组件

## 9. 认证和权限

- [ ] 9.1 后端: 集成 Supabase Auth
  - [ ] 9.1.1 JWT Token 验证中间件
  - [ ] 9.1.2 登录 API (/api/auth/login)
  - [ ] 9.1.3 登出 API (/api/auth/logout)
  - [ ] 9.1.4 获取当前用户 API (/api/auth/me)

- [ ] 9.2 前端: 实现登录功能
  - [ ] 9.2.1 Login.vue (已包含在 5.4 中)
  - [ ] 9.2.2 Token 存储和自动续期
  - [ ] 9.2.3 Axios 请求拦截器(添加 Authorization header)

## 10. 测试和验证

- [ ] 10.1 后端单元测试
  - [ ] 10.1.1 测试 Analyst API
  - [ ] 10.1.2 测试 Report API
  - [ ] 10.1.3 测试版本管理逻辑

- [ ] 10.2 前端测试
  - [ ] 10.2.1 组件测试
  - [ ] 10.2.2 窗口系统测试
  - [ ] 10.2.3 E2E 测试

- [ ] 10.3 集成测试
  - [ ] 10.3.1 测试完整的报告创建流程
  - [ ] 10.3.2 测试版本管理流程
  - [ ] 10.3.3 测试发布和拒绝流程
  - [ ] 10.3.4 测试窗口系统交互

## 11. 部署和文档

- [ ] 11.1 后端部署准备
  - [ ] 11.1.1 Dockerfile
  - [ ] 11.1.2 环境变量配置

- [ ] 11.2 前端部署准备
  - [ ] 11.2.1 生产环境构建配置
  - [ ] 11.2.2 静态资源配置

- [ ] 11.3 编写项目文档
  - [ ] 11.3.1 更新 README.md
  - [ ] 11.3.2 API 文档(使用 FastAPI 自动生成的 Swagger UI)
  - [ ] 11.3.3 部署文档
  - [ ] 11.3.4 开发环境搭建文档
  - [ ] 11.3.5 窗口系统使用指南
