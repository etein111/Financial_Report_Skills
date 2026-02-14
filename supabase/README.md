# Supabase

数据库配置与版本管理。

## 目录结构

```
supabase/
├─ config.toml       # 本地 Supabase 配置
├─ migrations/       # 数据库迁移（版本控制）
├─ seed/             # 种子数据
└─ .temp/            # CLI 临时文件（不提交）
```

### migrations/

数据库 schema 变更的版本控制。每个迁移是一个 SQL 文件，按时间戳命名：

```
migrations/
├─ 20260213165658_init_default_admin.sql
└─ 20260214094418_auth_and_user_management_baseline.sql
```

**命名规则**：`YYYYMMDDHHMMSS_description.sql`

**执行顺序**：按文件名时间戳升序执行。

### seed/

初始化/测试数据。迁移执行后可选择加载：

```
seed/
└─ regions.sql       # Region 基础数据
```

### config.toml

本地 Supabase 实例配置：
- 认证设置（site_url, redirect_urls）
- 数据库配置
- 服务端口等

---

## 常用命令

在项目根目录执行：

```bash
# 启动本地 Supabase
pnpm supabase:start

# 查看本地实例状态
pnpm supabase status

# 停止本地 Supabase
pnpm supabase:stop

# 推送迁移到本地实例
pnpm supabase:db:push

# 预览推送（不实际执行）
pnpm supabase:db:push:dry-run

# 生成迁移文件（基于当前 schema 差异）
pnpm supabase db diff -p --schema public > migrations/xxx_description.sql
```

---

## 版本管理流程

### 1. 开发新功能需要改 schema

```bash
# 1. 启动本地 Supabase
pnpm supabase:start

# 2. 在本地实例中修改 schema（通过 SQL 或 Dashboard）

# 3. 生成迁移文件
pnpm supabase db diff -p --schema public > migrations/YYYYMMDDHHMMSS_description.sql

# 4. 检查生成的 SQL，确认无误后提交
git add migrations/
git commit -m "Add xxx migration"
```

### 2. 应用迁移

```bash
# 推送到本地实例
pnpm supabase:db:push

# 或推送到远程（需配置 project ref）
pnpm exec supabase db push --linked
```

### 3. 重置本地数据库

```bash
# 重置到最新迁移状态
pnpm exec supabase db reset
```

---

## 注意事项

1. **迁移文件一旦提交不应修改**：如需修正，创建新的迁移文件
2. **seed 数据不自动执行**：需要手动加载或通过脚本执行
3. **.temp/ 不提交**：在 `.gitignore` 中已忽略
4. **生产环境操作**：推送前务必先 `--dry-run` 检查

---

## 相关链接

- [Supabase CLI 文档](https://supabase.com/docs/reference/cli)
- [本地开发指南](https://supabase.com/docs/guides/local-development)
