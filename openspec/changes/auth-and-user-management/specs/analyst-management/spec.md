# Analyst 信息管理规范

## ADDED Requirements

### Requirement: 系统提供 Analyst 业务数据模型

系统 SHALL 提供 Analyst（分析师）业务数据模型，支持存储基本信息、关联 Region、SFC 编号等。

**重要：** 本规范与用户账号系统完全解耦。Analyst 信息管理 **不创建或修改用户账号**，只管理 Analyst 数据记录。

---

## 数据模型

### Requirement: Analyst 表结构

系统 SHALL 创建 analyst 表存储 Analyst 信息。

#### Scenario: Analyst 表结构

- **WHEN** 查看 analyst 表结构
- **THEN** 表包含以下字段：
  - `id`: UUID 主键
  - `full_name`: VARCHAR 英文全名（必填）
  - `chinese_name`: VARCHAR 中文名（可选）
  - `email`: VARCHAR 邮箱（必填，唯一）
  - `suffix`: VARCHAR 后缀（如 "CFA", "CPA"）
  - `region_id`: UUID 外键，关联 region 表（可选）
  - `sfc`: VARCHAR SFC 编号（可选）
  - `is_active`: BOOLEAN 是否启用（默认 true）
  - `created_at`: TIMESTAMP 创建时间
  - `updated_at`: TIMESTAMP 更新时间

#### Scenario: 外键关系

- **WHEN** Analyst 关联 Region
- **THEN** analyst.region_id 外键关联到 region.id
- **AND** 删除 Region 时，analyst.region_id 设为 NULL（ON DELETE SET NULL）

---

## API 设计

### Requirement: Analyst 信息 CRUD API

系统 SHALL 提供完整的 Analyst 信息 CRUD API。

#### Scenario: 获取 Analyst 列表

- **WHEN** Admin 用户已登录
- **THEN** 可以调用 GET /api/analyst-info
- **AND** API 返回所有 Analyst 信息
- **AND** 数据按 created_at 倒序排列
- **AND** 支持通过 query 参数搜索（按 full_name 或 email）

**API 端点：** `GET /api/analyst-info`

**查询参数：**
- `search`: 搜索关键词（可选）
- `page`: 页码（可选，默认 1）
- `limit`: 每页数量（可选，默认 20）

**响应示例：**
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "items": [
      {
        "id": "uuid",
        "full_name": "John Doe",
        "chinese_name": "张三",
        "email": "john.doe@example.com",
        "suffix": "CFA",
        "region_id": "uuid",
        "region_name": "China",
        "sfc": "ABC123",
        "is_active": true,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

---

### Requirement: 创建 Analyst 信息

系统 SHALL 支持创建新的 Analyst 信息记录。

#### Scenario: 创建 Analyst 信息

- **WHEN** Admin 用户已登录
- **AND** 访问 Analyst 信息管理页面
- **AND** 点击 "Create Analyst" 按钮
- **THEN** 显示创建表单
- **AND** 填写表单字段：
  - Full Name（英文全名，必填）
  - Chinese Name（中文名，可选）
  - Email（邮箱，必填，唯一性检查）
  - Suffix（后缀，如 "CFA"）
  - Region（下拉选择，从 Region 表获取）
  - SFC License No.（SFC 编号，可选）
- **AND** 点击 "Submit" 提交表单
- **THEN** 前端调用 POST /api/analyst-info
- **AND** 后端验证邮箱唯一性
- **AND** 创建 analyst 表记录（**不创建 Auth 用户**）
- **AND** 返回成功提示

**API 端点：** `POST /api/analyst-info`

**请求体：**
```json
{
  "full_name": "John Doe",
  "chinese_name": "张三",
  "email": "john.doe@example.com",
  "suffix": "CFA",
  "region_id": "uuid",
  "sfc": "ABC123",
  "is_active": true
}
```

**成功响应：**
```json
{
  "success": true,
  "message": "创建成功",
  "data": { /* 创建的 Analyst 对象 */ }
}
```

**错误响应：**
```json
{
  "success": false,
  "message": "创建失败",
  "error": "Email already exists"
}
```

**注意：** 创建 Analyst 信息**不会**：
- ❌ 创建 Supabase Auth 用户
- ❌ 生成随机密码
- ❌ 发送欢迎邮件
- ✅ 只创建 analyst 表记录

---

### Requirement: 更新 Analyst 信息

系统 SHALL 支持更新已有的 Analyst 信息。

#### Scenario: 更新 Analyst 信息

- **WHEN** Admin 用户已登录
- **AND** 访问 Analyst 信息管理页面
- **AND** 在列表中点击某个 Analyst 的 "Edit" 按钮
- **THEN** 显示编辑表单（预填充现有数据）
- **AND** Admin 可以修改除 email 外的所有字段
- **AND** 点击 "Update" 提交表单
- **THEN** 前端调用 PUT /api/analyst-info/{id}

**API 端点：** `PUT /api/analyst-info/{id}`

**请求体：**
```json
{
  "full_name": "John Doe",
  "chinese_name": "张三",
  "email": "john.doe@example.com",  // 不可修改（用于唯一性标识）
  "suffix": "CFA",
  "region_id": "uuid",
  "sfc": "ABC123",
  "is_active": true
}
```

**成功响应：**
```json
{
  "success": true,
  "message": "更新成功",
  "data": { /* 更新后的 Analyst 对象 */ }
}
```

---

### Requirement: 删除 Analyst 信息

系统 SHALL 支持删除不需要的 Analyst 信息记录。

#### Scenario: 删除 Analyst 信息

- **WHEN** Admin 用户已登录
- **AND** 访问 Analyst 信息管理页面
- **AND** 在列表中点击某个 Analyst 的 "Delete" 按钮
- **THEN** 显示确认对话框：**"确定要删除该 Analyst 的信息吗？此操作将删除 Analyst 数据，但不影响用户账号。"**
- **AND** 用户确认删除
- **THEN** 前端调用 DELETE /api/analyst-info/{id}

**API 端点：** `DELETE /api/analyst-info/{id}`

**成功响应：**
```json
{
  "success": true,
  "message": "删除成功",
  "data": { "id": "uuid" }
}
```

**注意：** 删除 Analyst 信息**不会**：
- ❌ 删除 Supabase Auth 用户
- ❌ 从 analyst 表删除用户
- ✅ 只删除 analyst 表记录

---

## 前端页面规范

### Requirement: Analyst 信息管理页面

系统 SHALL 提供完整的管理页面。

#### Scenario: 页面布局

- **WHEN** Admin 用户访问 `/analyst-info`
- **THEN** 显示 Analyst 信息管理页面
- **AND** 页面包含：
  - 顶部导航栏（标题 + "Back to Desktop" 链接）
  - 搜索框（按 full_name 或 email）
  - Analyst 信息列表（表格形式）
  - "Create Analyst" 按钮（Admin only）

#### Scenario: 列表展示

- **WHEN** 页面加载或搜索
- **THEN** 显示 Analyst 信息列表
- **AND** 列表包含以下列：
  - Full Name（英文全名）
  - Chinese Name（中文名）
  - Email
  - Region（地区名称）
  - SFC No.（SFC 编号）
  - Status（状态）
  - 操作列（Edit, Delete 按钮）

#### Scenario: 创建表单

- **WHEN** Admin 点击 "Create Analyst"
- **THEN** 显示创建表单对话框
- **AND** 表单包含以下字段：
  - Full Name 输入框（必填，验证格式）
  - Chinese Name 输入框（可选）
  - Email 输入框（必填，验证格式和唯一性）
  - Region 下拉选择（从 Region 表获取）
  - SFC License No. 输入框（可选）
  - Submit 按钮
- **AND** 前端实时验证邮箱唯一性（调用 POST /api/analyst-info/check-email）

#### Scenario: 编辑表单

- **WHEN** Admin 点击某个 Analyst 的 "Edit" 按钮
- **THEN** 显示编辑表单对话框（预填充现有数据）
- **AND** 表单包含所有字段（Email 不可修改，用于唯一性标识）
- **AND** "Update" 提交后显示成功提示

#### Scenario: 删除确认

- **WHEN** Admin 点击某个 Analyst 的 "Delete" 按钮
- **THEN** 显示确认对话框
- **AND** 确认信息：**"确定要删除该 Analyst 的信息吗？此操作将删除 Analyst 数据，但不影响用户账号。"**
- **AND** 确认后调用 DELETE API
- **AND** 成功后刷新列表并显示成功提示

---

## 权限控制

### Requirement: 只有 Admin 可以访问

系统 SHALL 限制只有 Admin 用户可以访问 Analyst 信息管理功能。

#### Scenario: 访问控制

- **WHEN** 用户尝试访问 `/analyst-info`
- **THEN** 系统检查用户角色
- **AND** 如果不是 Admin
- **THEN** 返回 403 Forbidden
- **AND** 显示权限不足提示

#### Scenario: UI 隐藏

- **WHEN** 用户不是 Admin
- **THEN** "Analyst Info" 卡片在桌面主页隐藏
- **AND** 路由守卫阻止访问

---

## 数据验证

### Requirement: 邮箱唯一性检查

系统 SHALL 在创建和更新 Analyst 信息时验证邮箱唯一性。

#### Scenario: 创建时检查

- **WHEN** Admin 提交创建表单
- **THEN** 前端调用 POST /api/analyst-info/check-email
- **AND** 提供 email 参数
- **THEN** 后端查询 analyst 表
- **AND** 如果 email 已存在
- **THEN** 返回 `{"exists": true}`
- **AND** 前端显示错误提示："该邮箱已被使用"

#### Scenario: 更新时检查

- **WHEN** Admin 提交编辑表单
- **THEN** 前端调用 POST /api/analyst-info/check-email
- **AND** 提供 email 参数和当前 analyst id（排除自己）
- **THEN** 后端查询 analyst 表
- **AND** 如果 email 已被其他 Analyst 使用
- **THEN** 返回 `{"exists": true}`
- **AND** 前端显示错误提示："该邮箱已被其他 Analyst 使用"

**注意：** 更新自己的记录时不需要检查（因为 email 未改变）

---

## 搜索功能

### Requirement: 支持搜索

系统 SHALL 支持按 full_name 或 email 搜索 Analyst 信息。

#### Scenario: 搜索 Analyst

- **WHEN** Admin 在搜索框输入关键词
- **AND** 触发搜索（实时或点击搜索按钮）
- **THEN** 前端调用 GET /api/analyst-info?search={keyword}
- **THEN** 后端使用 SQL LIKE 查询
- **AND** 返回匹配的结果
- **AND** 前端显示过滤后的列表

**SQL 实现：**
```sql
SELECT * FROM analyst
WHERE full_name ILIKE '%' || chinese_name ILIKE '%' || email ILIKE '%'
ORDER BY created_at DESC;
```

---

## 用户账号与 Analyst 信息解耦说明

### Requirement: 完全解耦设计

系统 SHALL 将用户账号管理和 Analyst 信息管理完全解耦为两个独立功能。

**用户管理（/api/users）：**
- 创建 Supabase Auth 用户
- 管理用户账号（创建、编辑、删除）
- 修改密码、修改角色
- 启用/禁用账号
- **目的：** 系统认证和权限控制

**Analyst 信息管理（/api/analyst-info）：**
- 创建 Analyst 数据记录（analyst 表）
- 管理 Analyst 信息（创建、编辑、删除）
- 关联 Region
- 记录 SFC 编号等
- **目的：** Analyst 数据记录，与认证系统解耦

**关键区别：**
- Analyst 信息管理**不创建或修改用户账号**
- Analyst 信息管理**不包含密码、角色等认证相关功能**
- email 字段在两个系统中独立存在（user_metadata 和 analyst 表）

**隐式关联规则（为未来报告功能预留）：**
- 当 User Auth 的 email 与 Analyst 的 email **一致时**，系统认为是**同一人**
- **当前阶段（auth-and-user-management）：** 只有 Admin 可以访问 Analyst 信息管理，SA/Analyst 不需要
- **未来报告功能：** Analyst 登录后可以查看/编辑自己的报告，报告表的 `contact_person` 字段关联到 analyst.email
- **不使用外键关联**，通过 email 字符串匹配实现逻辑关联
- 示例：Analyst `john.doe@example.com` 登录后，只能看到 `contact_person = 'john.doe@example.com'` 的报告

**好处：**
- ✅ 职责清晰，易于维护
- ✅ Analyst 数据可以独立存在（不需要登录账号的 Analyst 也能有记录）
- ✅ 避免数据同步问题
- ✅ 通过 email 一致性即可建立用户与 Analyst 信息的关联
