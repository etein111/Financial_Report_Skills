# 实施任务列表

## 后端基础设施

- [ ] 创建后端项目结构
  - [ ] 初始化 FastAPI 项目（使用 uv）
  - [ ] 配置 pyproject.toml 依赖
  - [ ] 创建目录结构（api, models, services, jobs, core）
  - [ ] 配置环境变量模板（.env.example）

- [ ] 配置数据库连接
  - [ ] 创建 PostgreSQL 数据库
  - [ ] 配置 SQLAlchemy 连接
  - [ ] 创建数据库迁移脚本（Alembic）

- [ ] 配置 Supabase Auth
  - [ ] 创建独立的 Supabase 项目
  - [ ] 配置认证提供者（邮箱密码登录）
  - [ ] 创建 Supabase 客户端封装

## 数据库模型

- [ ] 创建 User 模型
  - [ ] 定义表结构和字段
  - [ ] 与 Supabase Auth 用户关联

- [ ] 创建 EmailConfig 模型
  - [ ] 定义表结构和字段
  - [ ] 实现密码加密存储

- [ ] 创建 Subscription 模型
  - [ ] 定义表结构和字段
  - [ ] 支持 subscription_type（general, wind, ths）

- [ ] 创建 Report 模型
  - [ ] 定义表结构和字段
  - [ ] 支持 JSONB 字段（analyst_names, analyst_ids, coverage_ids）

- [ ] 创建 ReportFile 模型
  - [ ] 定义表结构和字段
  - [ ] 与 Report 关联

- [ ] 创建 DistributionLog 模型
  - [ ] 定义表结构和字段
  - [ ] 记录发送状态和重试次数

## 认证模块

- [ ] 实现认证 API
  - [ ] POST /api/v1/auth/logout - 登出
  - [ ] GET /api/v1/auth/me - 获取当前用户信息

- [ ] 实现认证中间件
  - [ ] JWT Token 验证
  - [ ] 用户角色提取

- [ ] 实现权限控制
  - [ ] Analyst 权限检查装饰器
  - [ ] Admin 权限检查装饰器

## 报告接收模块

- [ ] 实现报告接收 API
  - [ ] POST /api/v1/reports/receive - 接收报告推送
  - [ ] API Key 认证
  - [ ] 请求速率限制

- [ ] 实现报告存储服务
  - [ ] 报告基本信息存储
  - [ ] 附件文件存储（本地文件系统）
  - [ ] 重复报告检测（通过 external_id）

- [ ] 实现增量同步 API
  - [ ] GET /api/v1/reports/sync - 按时间戳查询
  - [ ] 返回报告列表和附件下载链接

## 报告查询模块

- [ ] 实现报告列表 API
  - [ ] GET /api/v1/reports - 分页查询
  - [ ] 支持 Analyst 只看自己的报告
  - [ ] 支持 Admin 看所有报告
  - [ ] 支持筛选（coverage, sector, date, search）

- [ ] 实现报告详情 API
  - [ ] GET /api/v1/reports/{id} - 获取详情
  - [ ] 权限检查（Analyst 只能访问自己的报告）

- [ ] 实现文件下载 API
  - [ ] GET /api/v1/reports/{id}/files/{file_id}/download
  - [ ] 权限验证
  - [ ] 文件流式下载

## Admin - 邮箱配置模块

- [ ] 实现邮箱配置 CRUD API
  - [ ] GET /api/v1/admin/email-configs - 列表
  - [ ] POST /api/v1/admin/email-configs - 创建
  - [ ] PUT /api/v1/admin/email-configs/{id} - 更新
  - [ ] DELETE /api/v1/admin/email-configs/{id} - 删除

- [ ] 实现邮箱配置测试 API
  - [ ] POST /api/v1/admin/email-configs/{id}/test
  - [ ] SMTP 连接测试
  - [ ] 发送测试邮件

## Admin - 订阅管理模块

- [ ] 实现订阅 CRUD API
  - [ ] GET /api/v1/admin/subscriptions - 列表
  - [ ] POST /api/v1/admin/subscriptions - 创建
  - [ ] PUT /api/v1/admin/subscriptions/{id} - 更新
  - [ ] DELETE /api/v1/admin/subscriptions/{id} - 删除

- [ ] 实现订阅业务逻辑
  - [ ] 支持选择订阅类型（general, wind, ths）
  - [ ] 输入机构简称
  - [ ] 输入订阅邮箱
  - [ ] 关联邮箱配置

## Admin - 发送记录模块

- [ ] 实现发送记录查询 API
  - [ ] GET /api/v1/admin/distribution-logs - 列表
  - [ ] 支持筛选（status, report, subscription）
  - [ ] 分页查询

- [ ] 实现手动重试 API
  - [ ] POST /api/v1/admin/distribution-logs/{id}/retry
  - [ ] 检查重试次数限制

## 邮件外发模块

- [ ] 实现邮件发送服务
  - [ ] SMTP 客户端封装
  - [ ] 邮件构建（主题、正文、附件）

- [ ] 实现邮件模板
  - [ ] 普通用户邮件模板
  - [ ] Wind 邮件模板
  - [ ] 同花顺邮件模板

- [ ] 实现外发服务
  - [ ] 根据订阅类型选择模板
  - [ ] 匹配订阅条件
  - [ ] 发送邮件
  - [ ] 记录发送日志

## Job 调度模块

- [ ] 配置 APScheduler
  - [ ] 创建调度器实例
  - [ ] 应用启动时启动调度器

- [ ] 实现报告外发 Job
  - [ ] 检查新发布的报告
  - [ ] 创建外发任务
  - [ ] 执行邮件发送

- [ ] 实现失败重试 Job
  - [ ] 检查失败的发送记录
  - [ ] 重试次数检查（最多 3 次）
  - [ ] 执行重试

## 前端基础设施

- [ ] 创建前端项目结构
  - [ ] 初始化 Vue 3 + Vite 项目
  - [ ] 配置 Tailwind CSS
  - [ ] 配置路由（Vue Router）
  - [ ] 配置状态管理（Pinia）

- [ ] 配置 API 客户端
  - [ ] Axios 封装
  - [ ] 请求拦截器（添加 Token）
  - [ ] 响应拦截器（错误处理）

- [ ] 配置认证状态
  - [ ] 用户状态管理
  - [ ] Token 存储（localStorage）
  - [ ] 自动刷新 Token

## 前端 - 登录页

- [ ] 实现登录页面
  - [ ] 参照 prototype/login.html 原型设计
  - [ ] 登录表单（邮箱、密码）
  - [ ] 登录按钮和加载状态
  - [ ] 错误提示

- [ ] 实现登录逻辑
  - [ ] 调用 Supabase Auth API
  - [ ] 保存 Token
  - [ ] 跳转到报告列表

## 前端 - 报告列表页

- [ ] 实现报告列表页面
  - [ ] 参照 prototype/reports.html 原型设计
  - [ ] 报告卡片列表
  - [ ] 分页控件

- [ ] 实现筛选功能
  - [ ] 按报告类型筛选（默认所有类型）
  - [ ] 关键词搜索

- [ ] 实现导航
  - [ ] 点击报告进入详情页
  - [ ] 保持筛选状态（URL 参数）

## 前端 - 报告详情页

- [ ] 实现报告详情页面
  - [ ] 显示报告基本信息
  - [ ] 显示报告摘要（富文本）
  - [ ] 显示附件列表

- [ ] 实现文件下载
  - [ ] 下载按钮
  - [ ] 下载进度显示

- [ ] 实现导航
  - [ ] 返回列表（保持筛选条件）

## 前端 - Admin 管理页

- [ ] 实现邮箱配置页面
  - [ ] 配置列表
  - [ ] 创建/编辑表单
  - [ ] 测试连接功能
  - [ ] 删除确认

- [ ] 实现订阅管理页面
  - [ ] 订阅列表
  - [ ] 创建/编辑表单（选择订阅类型、选择邮箱配置、输入订阅邮箱）
  - [ ] 删除确认

- [ ] 实现发送记录页面
  - [ ] 记录列表（状态、失败原因、重试次数）
  - [ ] 筛选功能
  - [ ] 手动重试按钮

## 前端 - 导航和布局

- [ ] 实现导航栏
  - [ ] Logo
  - [ ] 用户信息显示
  - [ ] 登出按钮
  - [ ] Admin 管理菜单（仅 Admin 可见）

- [ ] 实现路由守卫
  - [ ] 未登录重定向到登录页
  - [ ] Admin 页面角色检查

## 测试

- [ ] 后端单元测试
  - [ ] 认证模块测试
  - [ ] 报告查询测试
  - [ ] 权限控制测试

- [ ] 后端集成测试
  - [ ] API 端点测试
  - [ ] 数据库操作测试

- [ ] 前端组件测试
  - [ ] 登录组件测试
  - [ ] 报告列表组件测试

## 部署

- [ ] 配置生产环境
  - [ ] 环境变量配置
  - [ ] 数据库迁移
  - [ ] 静态文件构建

- [ ] 部署后端服务
  - [ ] 配置 WSGI/ASGI 服务器
  - [ ] 配置反向代理

- [ ] 部署前端服务
  - [ ] 构建生产版本
  - [ ] 配置静态文件服务
