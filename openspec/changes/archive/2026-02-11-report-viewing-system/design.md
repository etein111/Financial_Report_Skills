# 系统设计文档

## Context

这是投资研究报告查看系统，是一个独立的 Web 应用，为授权用户提供报告查看功能，并通过自动化 Job 将报告外发给订阅用户。系统与报告管理系统分离，拥有独立的用户体系和数据存储。

## Goals / Non-Goals

**Goals:**
- 提供独立的用户认证系统（Analyst、Admin 两种角色）
- 接收来自报告管理系统的已发布报告
- 为用户提供报告列表和详情查看功能
- 实现邮件外发功能（支持普通用户、Wind、同花顺三种格式）
- 提供 Admin 管理界面（邮箱配置、订阅管理、发送记录查看）

**Non-Goals:**
- 报告创建和编辑功能（属于报告管理系统）
- 移动端支持（第一版本仅桌面端）
- FTP 和 API 外发（后续版本扩展）

## Decisions

### Decision 1: 系统架构

**选择:** 独立的单体应用 + 后台 Job 服务

**架构图:**
```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3 SPA)                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │  Login  │  │ Reports │  │ Detail  │  │  Admin Pages    │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Auth Module  │  │Report Module │  │ Distribution API │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Admin Module │  │ Receive API  │  │ Job Scheduler    │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │    │   Supabase   │    │ File Storage │
│  (Database)  │    │    (Auth)    │    │    (Local)   │
└──────────────┘    └──────────────┘    └──────────────┘
```

**理由:**
- 系统规模适中，单体架构足够满足需求
- 与报告管理系统完全隔离，便于独立部署和维护
- 后台 Job 与 API 服务在同一进程内运行，简化部署

### Decision 2: 技术栈选择

**选择:** FastAPI + Vue 3 + Supabase Auth + PostgreSQL + APScheduler

**理由:**
- **FastAPI**: 与报告管理系统保持一致，便于代码复用和团队熟悉
- **Vue 3**: 与报告管理系统保持一致
- **Supabase Auth**: 使用独立的 Supabase 项目，与报告管理系统的用户体系隔离
- **PostgreSQL**: 使用独立的数据库，与报告管理系统数据隔离
- **APScheduler**: Python 原生 Job 调度库，轻量且功能足够

### Decision 3: 数据库设计

**表结构设计:**

```sql
-- 用户表（与 Supabase Auth 关联）
users
- id: UUID (PK, 与 Supabase Auth user.id 一致)
- email: VARCHAR (unique)
- full_name: VARCHAR
- role: VARCHAR ('analyst', 'admin')
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

-- 邮箱配置表
email_configs
- id: UUID (PK)
- name: VARCHAR (配置名称)
- host: VARCHAR (SMTP 服务器地址)
- port: INTEGER (SMTP 端口)
- username: VARCHAR
- password: VARCHAR (加密存储)
- use_tls: BOOLEAN
- is_active: BOOLEAN
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

-- 订阅表
subscriptions
- id: UUID (PK)
- email: VARCHAR (订阅邮箱)
- subscription_type: VARCHAR ('general', 'wind', 'ths')
- institution: VARCHAR (研究机构简称)
- email_config_id: UUID (FK -> email_configs)
- is_active: BOOLEAN
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

-- 报告表（从报告管理系统同步）
reports
- id: UUID (PK)
- report_id: UUID (报告管理系统中的 reports_id)
- institution: VARCHAR (研究机构简称后续支持多个研究机构, unique)
- title: VARCHAR
- summary: TEXT
- report_type: VARCHAR ('Company', 'Sector', 'Macro', 'Strategy', 'Quantitative', 'Bond')
- analyst_names: JSONB (作者姓名列表)
- analyst_ids: JSONB (作者 ID 列表)
- coverage_id: UUID (nullable, 公司覆盖)
- coverage_name: VARCHAR (nullable)
- ticker: VARCHAR (nullable)
- sector_id: UUID (nullable)
- sector_name: VARCHAR (nullable)
- region_id: UUID (nullable)
- region_name: VARCHAR (nullable)
- rating: VARCHAR (nullable)
- target_price: DECIMAL (nullable)
- publish_date: DATE
- status: VARCHAR ('published')
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

-- 报告附件表
report_files
- id: UUID (PK)
- report_id: UUID (FK -> reports)
- file_name: VARCHAR
- file_path: VARCHAR (本地存储路径)
- file_type: VARCHAR ('pdf', 'word', 'excel')
- file_size: BIGINT
- created_at: TIMESTAMP

-- 外发记录表
distribution_logs
- id: UUID (PK)
- report_id: UUID (FK -> reports)
- subscription_id: UUID (FK -> subscriptions)
- status: VARCHAR ('pending', 'success', 'failed')
- error_message: TEXT (nullable)
- retry_count: INTEGER (default 0)
- sent_at: TIMESTAMP (nullable)
- created_at: TIMESTAMP
```

### Decision 4: API 设计

**认证相关:**
- `POST /api/v1/auth/login` - 登录（由 Supabase 处理）
- `POST /api/v1/auth/logout` - 登出
- `GET /api/v1/auth/me` - 获取当前用户信息

**报告接收（外部系统调用）:**
- `POST /api/v1/reports/receive` - 接收报告推送
- `GET /api/v1/reports/sync` - 增量同步已发布报告

**报告查询:**
- `GET /api/v1/reports` - 获取报告列表（支持分页、筛选）
- `GET /api/v1/reports/{id}` - 获取报告详情
- `GET /api/v1/reports/{id}/files/{file_id}/download` - 下载附件

**Admin - 邮箱配置:**
- `GET /api/v1/admin/email-configs` - 获取邮箱配置列表
- `POST /api/v1/admin/email-configs` - 创建邮箱配置
- `PUT /api/v1/admin/email-configs/{id}` - 更新邮箱配置
- `DELETE /api/v1/admin/email-configs/{id}` - 删除邮箱配置
- `POST /api/v1/admin/email-configs/{id}/test` - 测试邮箱配置

**Admin - 订阅管理:**
- `GET /api/v1/admin/subscriptions` - 获取订阅列表
- `POST /api/v1/admin/subscriptions` - 创建订阅
- `PUT /api/v1/admin/subscriptions/{id}` - 更新订阅
- `DELETE /api/v1/admin/subscriptions/{id}` - 删除订阅

**Admin - 发送记录:**
- `GET /api/v1/admin/distribution-logs` - 获取发送记录列表
- `POST /api/v1/admin/distribution-logs/{id}/retry` - 手动重试发送

### Decision 5: 文件存储设计

**选择:** 本地文件系统存储

**目录结构:**
```
storage/
├── reports/
│   ├── {report_id}/
│   │   ├── {filename}.pdf
│   │   ├── {filename}.docx
│   │   └── {filename}.xlsx
```

**理由:**
- 第一版本数据量不大，本地存储足够
- 避免引入额外的存储服务复杂性
- 后续可迁移到 Supabase Storage 或 S3

### Decision 6: Job 调度设计

**选择:** APScheduler + 后台线程

**Job 类型:**
1. **报告外发 Job** - 新报告发布后触发邮件发送
2. **失败重试 Job** - 定期检查失败的外发记录并重试

**实现方式:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# 新报告触发外发
@scheduler.scheduled_job('interval', minutes=5)
async def process_new_reports():
    # 检查未处理的报告，创建外发任务
    pass

# 失败重试
@scheduler.scheduled_job('interval', minutes=5)
async def retry_failed_distributions():
    # 重试失败的发送（最多3次）
    pass
```

### Decision 7: 邮件模板设计

**模板类型:**

1. **普通用户模板**
```
Subject: {report_title}
Body:

Summary:
{summary}

Best regards,
Research report system
```

2. **Wind 模板**
```
Subject: [报告来源*报告类别*报告标题*报告日期*报告作者]
Body:
[Wind 指定格式的正文内容]
包含 Wind 要求的元数据字段
```

3. **同花顺模板**
```
Subject: 【报告来源*报告类型*作者*报告撰写时间*标题】
Body:
[同花顺指定格式的正文内容]
包含同花顺要求的元数据字段
```

### Decision 8: 安全设计

**API 安全:**
- 报告接收 API 使用 API Key 认证
- 用户 API 使用 Supabase JWT 认证
- Admin API 检查用户角色

**权限控制:**
- Analyst 只能查询 `analyst_names` 包含自己 name 的报告
- Admin 可以查询所有报告
- 前端路由根据角色动态显示/隐藏菜单

**数据安全:**
- 邮箱密码加密存储（使用 Fernet 对称加密）
- 文件下载链接包含签名验证
- API 请求日志记录

### Decision 9: 前端架构

**页面结构:**
```
/
├── /login              - 登录页
├── /reports            - 报告列表
├── /reports/:id        - 报告详情
└── /admin              - Admin 管理页（需要 admin 角色）
    ├── /admin/email-configs    - 邮箱配置
    ├── /admin/subscriptions    - 订阅管理
    └── /admin/distribution-logs - 发送记录
```

**组件复用:**
- 参照 `prototype/login.html` 实现登录页
- 参照 `prototype/reports.html` 实现报告列表页
- 使用 Tailwind CSS 保持样式一致

## Implementation Notes

1. **项目结构:**
```
backend-report-viewing/
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── reports.py
│   │   ├── admin/
│   │   │   ├── email_configs.py
│   │   │   ├── subscriptions.py
│   │   │   └── distribution_logs.py
│   │   └── receive.py
│   ├── models/
│   │   ├── user.py
│   │   ├── report.py
│   │   ├── subscription.py
│   │   └── distribution_log.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── report_service.py
│   │   ├── email_service.py
│   │   └── distribution_service.py
│   ├── jobs/
│   │   ├── scheduler.py
│   │   └── distribution_job.py
│   └── core/
│       ├── config.py
│       ├── security.py
│       └── database.py
├── tests/
├── pyproject.toml
└── .env

frontend-report-viewing/
├── src/
│   ├── views/
│   ├── components/
│   ├── router/
│   ├── stores/
│   ├── api/
│   └── assets/
├── package.json
└── vite.config.ts
```

2. **环境变量:**
```
# Supabase (独立项目)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Database
DATABASE_URL=

# Storage
STORAGE_PATH=

# API Security
API_KEY=

# Email encryption key
FERNET_KEY=
```
