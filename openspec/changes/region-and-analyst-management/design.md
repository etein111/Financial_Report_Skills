# Regions 与 Analyst Info 管理设计

## 1. 数据模型（以现有迁移为准）

- `region`：地区字典（name/code 唯一）
- `analyst`：业务分析师信息（email 唯一，`region_id` 外键，`ON DELETE SET NULL`）

迁移参考：
- `supabase/migrations/20260214094418_auth_and_user_management_baseline.sql`

系统预置 Region：
- China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US

解耦原则：
- `analyst` 为业务信息表，创建/删除 Analyst 信息不自动创建/删除 Auth Users。
- Analyst 业务数据通过 email 与未来业务逻辑关联，不做外键强绑定到 Auth 用户。

## 2. 权限与安全（功能权限 + RLS 兜底）

功能权限（应用层）：
- Regions / Analyst Info 页面与写操作：Admin-only

数据权限（RLS，数据库层兜底）：
- `region`/`analyst`：认证可读
- 写操作：仅 Admin（以 JWT `app_metadata.role` 判定）

补充：
- 本阶段不做字段脱敏（例如 `analyst.email` 不做部分隐藏）。

## 3. 页面与路由

页面：
- `/regions`（Admin-only）
- `/analyst-info`（Admin-only）

导航：
- Desktop 增加两张卡片（Admin-only 显示），点击新标签页打开

## 4. 列表与分页（统一规则）

- 默认 `created_at DESC`
- 超过 15 条分页
- 每页固定 15 条

## 5. CRUD 交互建议（保持简单）

Regions：
- Create/Edit 用同一套表单（modal 或独立页二选一，建议 modal 以减少路由复杂度）
- Delete 必须二次确认
- 删除 Region 时不做关联阻断；若被 Analyst 引用，按数据库策略 `ON DELETE SET NULL` 自动置空关联。

Analyst Info：
- Create/Edit 表单字段：full_name、chinese_name、email、region、is_active
- 创建必填字段：`full_name`、`email`、`region`
- 列表支持按 `full_name`、`chinese_name`、`email` 搜索
- Delete 必须二次确认

失败提示：
- 唯一性冲突（name/code/email）必须能在 UI 上明确定位到字段或给出明确报错文案

---

# 补充内容（待审核后合并）

## 6. 设计基线（继承自 auth-and-users-mvp）

本 change 遵循 `auth-and-users-mvp` 建立的设计基线：

- 应用入口：Next.js 为唯一应用入口
- 交互：Server-first（Server Components + Server Actions）
- 写操作：使用 Server Actions
- UI 语言：英文
- 时间展示：Asia/Shanghai（UTC+8）
- 工具链：`pnpm` + 项目本地 `node_modules`
- 安全：`SUPABASE_SERVICE_ROLE_KEY` 仅服务端可用
- Supabase 能力边界：不使用 Edge Functions / Realtime / Storage

## 7. 文件结构

```text
web/
├── app/
│   ├── regions/
│   │   └── page.tsx              # Regions 列表页（Admin-only）
│   └── analyst-info/
│       └── page.tsx              # Analyst Info 列表页（Admin-only）
│
├── features/
│   ├── regions/
│   │   ├── index.ts              # 公共入口
│   │   ├── actions.ts            # Server Actions（CRUD）
│   │   ├── repo/
│   │   │   └── regions-repo.ts   # 数据访问层（server-only）
│   │   └── components/
│   │       ├── regions-page.tsx       # 服务端页面组件
│   │       ├── regions-page-client.tsx # 客户端交互组件
│   │       └── region-form.tsx        # 创建/编辑表单
│   │
│   └── analysts/
│       ├── index.ts
│       ├── actions.ts
│       ├── repo/
│       │   └── analysts-repo.ts
│       └── components/
│           ├── analysts-page.tsx
│           ├── analysts-page-client.tsx
│           └── analyst-form.tsx
│
└── domain/
    └── schemas/
        ├── region.ts             # Zod schema for Region
        └── analyst.ts            # Zod schema for Analyst
```

## 8. Server Actions 设计

### Regions Actions

```ts
// features/regions/actions.ts

// 列表查询（支持分页、搜索）
export async function listRegionsAction(params: {
  page: number;
  query: string | null;
}): Promise<Result<{ items: Region[]; total: number; page: number; totalPages: number }>>

// 创建 Region
export async function createRegionAction(data: {
  name: string;
  code: string;
}): Promise<Result<Region>>

// 更新 Region
export async function updateRegionAction(id: string, data: {
  name?: string;
  code?: string;
}): Promise<Result<Region>>

// 删除 Region
export async function deleteRegionAction(id: string): Promise<Result<null>>
```

### Analysts Actions

```ts
// features/analysts/actions.ts

// 列表查询（支持分页、搜索）
export async function listAnalystsAction(params: {
  page: number;
  query: string | null;
}): Promise<Result<{ items: Analyst[]; total: number; page: number; totalPages: number }>>

// 创建 Analyst
export async function createAnalystAction(data: {
  full_name: string;
  chinese_name?: string;
  email: string;
  region_id: string;
  suffix?: string;
  sfc?: string;
}): Promise<Result<Analyst>>

// 更新 Analyst
export async function updateAnalystAction(id: string, data: Partial<{
  full_name: string;
  chinese_name: string;
  email: string;
  region_id: string;
  suffix: string;
  sfc: string;
  is_active: boolean;
}>): Promise<Result<Analyst>>

// 删除 Analyst
export async function deleteAnalystAction(id: string): Promise<Result<null>>

// 获取所有 Regions（用于下拉选择）
export async function getRegionsForSelectAction(): Promise<Result<Region[]>>
```

## 9. 错误处理

### 唯一性冲突

```ts
// 识别 Supabase 唯一性错误并返回字段级提示
function handleUniqueError(error: PostgrestError): string {
  if (error.code === '23505') {
    if (error.message.includes('region_name_unique')) {
      return 'Region name already exists';
    }
    if (error.message.includes('region_code_unique')) {
      return 'Region code already exists';
    }
    if (error.message.includes('analyst_email_unique')) {
      return 'Email already exists';
    }
  }
  return 'An unexpected error occurred';
}
```

### 删除关联检查

- Region 删除：不做阻断，依赖数据库 `ON DELETE SET NULL`
- Analyst 删除：当前无关联表，直接删除

## 10. Desktop 卡片更新

在 `features/desktop/components/desktop-page-client.tsx` 中增加两个 Admin-only 卡片：

```tsx
// Admin-only 卡片
const adminCards = [
  { key: 'regions', title: 'Regions', href: '/regions', permission: 'Admin only' },
  { key: 'analyst-info', title: 'Analyst Info', href: '/analyst-info', permission: 'Admin only' },
];

// 渲染时检查用户角色
{userRole === 'admin' && (
  <div className="card-group">
    <h2>Data Management</h2>
    {adminCards.map(card => (
      <DesktopCard key={card.key} {...card} />
    ))}
  </div>
)}
```

## 11. Zod Schemas

```ts
// domain/schemas/region.ts
import { z } from 'zod';

export const regionSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  code: z.string().min(1, 'Code is required').max(10),
});

export const regionUpdateSchema = regionSchema.partial();

// domain/schemas/analyst.ts
import { z } from 'zod';

export const analystSchema = z.object({
  full_name: z.string().min(1, 'Full name is required').max(200),
  chinese_name: z.string().max(100).optional(),
  email: z.string().email('Invalid email address'),
  region_id: z.string().uuid('Region is required'),
  suffix: z.string().max(50).optional(),
  sfc: z.string().max(50).optional(),
});

export const analystUpdateSchema = analystSchema.partial();

export const analystCreateSchema = analystSchema.required({
  full_name: true,
  email: true,
  region_id: true,
});
```

## 12. 测试验收要点

### 功能测试
- [ ] Regions CRUD 全流程
- [ ] Analyst Info CRUD 全流程
- [ ] 唯一性冲突错误提示
- [ ] 分页功能（超过 15 条）
- [ ] 搜索功能
- [ ] Region 删除后 Analyst 的 region_id 置空

### 权限测试
- [ ] Admin 可访问所有页面和操作
- [ ] SA/Analyst 无法访问 `/regions` 和 `/analyst-info`
- [ ] 非 Admin 直接访问 URL 被重定向到 `/403`
- [ ] Desktop 卡片按角色显示/隐藏

### RLS 验证
- [ ] 认证用户可读取 region/analyst 数据
- [ ] 非 Admin 用户无法写入（通过 Server Action 层面 + RLS 双重校验）
