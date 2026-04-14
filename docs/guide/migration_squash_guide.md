# 迁移文件合并（Squash）操作指南

将多个开发阶段积累的迁移文件合并为一个，减少文件数量、加速 `db reset`，同时保证数据库状态不变。

## 前置条件

- 所有待合并的迁移**未推送到远端环境**。已推送的迁移禁止 squash，只能新建增量迁移。
- 本地 Supabase 服务运行正常（`supabase start`）。
- 当前迁移文件所在分支已提交或有备份。

## 操作步骤

### 第一步：确认迁移状态

```bash
# 确认本地服务可用
supabase status

# 用原始迁移 rebuild，确保当前状态正确
supabase db reset
```

如果 reset 报错，先修复问题再继续。

### 第二步：导出当前 schema

```bash
supabase db dump --local --schema public > /tmp/squashed.sql
```

`--schema public` 只导出 `public` schema 下的对象（表、函数、触发器、索引、策略、COMMENT）。

### 第三步：补充数据库级配置

`pg_dump` 不导出数据库级配置（如 timezone）。需要从原始迁移文件中提取并手动补回。

当前项目的数据库级配置位于 `000_bootstrap.sql`：

```sql
alter database postgres set timezone to 'Asia/Shanghai';
```

把该行插入 squash 文件最前面：

```bash
# 在导出文件开头插入时区配置
sed -i '1i\alter database postgres set timezone to '\''Asia/Shanghai'\'';' /tmp/squashed.sql
```

操作者必须在合并前**通读所有原始迁移文件**，收集所有非 schema 对象（`ALTER DATABASE`、`ALTER ROLE`、`CREATE EXTENSION` 等），逐条确认已补回。

### 第四步：替换迁移文件

```bash
# 1. 备份原始迁移文件
cp -r supabase/migrations /tmp/migrations_backup

# 2. 删除旧迁移文件
rm supabase/migrations/*.sql

# 3. 创建新迁移文件
supabase migration new squashed_schema

# 4. 写入导出内容
cp /tmp/squashed.sql supabase/migrations/<新生成的文件名>.sql
```

### 第五步：验证

验证分三层，全部通过才算完成。

#### 5.1 db diff 验证（快速）

原理：用原始迁移构建的数据库状态还在，对比它与新迁移文件的差异。

```bash
supabase db diff --schema public
```

- **无输出** = 一致，通过。
- **有输出** = squash 丢失了内容，根据提示补回。

> 注意：第三步已删除旧迁移文件，此时数据库是旧迁移构建的状态，迁移文件是新 squash 的。`db diff` 比对的正是这两者的差异。

#### 5.2 双 dump 对比（完整）

用同一份 dump 工具、同样的参数，分别 dump 原始和 squash 后的数据库，做文本 diff。

```bash
# A. 用原始迁移 reset 并 dump
cp -r /tmp/migrations_backup/* supabase/migrations/
supabase db reset
supabase db dump --local --schema public > /tmp/schema_original.sql

# B. 用 squash 迁移 reset 并 dump
rm supabase/migrations/*.sql
cp /tmp/squashed.sql supabase/migrations/<squash文件名>.sql
supabase db reset
supabase db dump --local --schema public > /tmp/schema_squashed.sql

# C. 对比
diff /tmp/schema_original.sql /tmp/schema_squashed.sql
```

- **零差异** = 完全一致。
- **有差异** = 检查差异内容并修正。

#### 5.3 数据库级配置验证

```bash
# 查询当前数据库时区设置
supabase db reset
psql "$(supabase status 2>/dev/null | grep 'DB URL' | awk '{print $NF}')" \
  -c "SELECT name, setting FROM pg_settings WHERE name = 'TimeZone';"
```

确认输出为 `Asia/Shanghai`。如果有其他数据库级配置，同理逐一查询确认。

#### 5.4 seed 数据验证（如适用）

```bash
supabase db reset
# 查询 seed 表确认数据完整
psql "$(supabase status 2>/dev/null | grep 'DB URL' | awk '{print $NF}')" \
  -c "SELECT count(*) FROM analyst;"
```

### 第六步：清理备份

验证全部通过后：

```bash
rm -rf /tmp/migrations_backup
rm /tmp/squashed.sql /tmp/schema_original.sql /tmp/schema_squashed.sql
```

## 回滚方案

如果验证不通过且无法快速修复：

```bash
# 恢复原始迁移文件
rm -rf supabase/migrations
cp -r /tmp/migrations_backup supabase/migrations
supabase db reset
```

## 检查清单

| 检查项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| 表/列/约束/索引 | `db diff` + 双 dump | 零差异 |
| 函数/触发器 | `db diff` + 双 dump | 零差异 |
| RLS Policy | `db diff` + 双 dump | 零差异 |
| COMMENT ON | 双 dump | 零差异 |
| 数据库级配置（timezone） | `pg_settings` 查询 | 值一致 |
| seed 数据 | 查表计数 | 行数一致 |
