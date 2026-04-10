---
name: dev_ops
description: "neoskills 项目的日常开发操作。当用户提到「启动本地数据库」「打开管理面板」「重置数据库」「导入测试数据」「推送到测试环境」「推送 schema」「reset db」「seed data」「push staging」时使用此 skill。包括本地 Supabase 管理、测试数据导入、schema 推送等操作。"
---

# dev_ops

neoskills 项目日常开发操作集合。

---

## 操作清单

### 1. 启动本地 Supabase

```bash
supabase start
```

启动后显示所有服务地址（Studio、API、数据库等）。

---

### 2. 打开 Studio 管理面板

先检查 Supabase 是否在运行：

```bash
supabase status
```

如果未运行，先执行操作 1 启动。然后打开浏览器：

```bash
# WSL 环境
explorer.exe "http://127.0.0.1:54323"

# macOS / Linux
open "http://127.0.0.1:54323"
```

Studio 地址固定为 `http://127.0.0.1:54323`。

---

### 3. 重置本地数据库 + 导入测试数据

**此操作会清空本地数据库，执行前必须向用户确认。**

两步依次执行，第二步依赖第一步：

```bash
# 步骤 1：重置数据库（自动执行 migrations + seed.sql）
supabase db reset

# 步骤 2：导入测试数据（不随 reset 自动加载）
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -f supabase/tests/test_data.sql
```

测试数据内容（`supabase/tests/test_data.sql`）：
- 5 个测试用户（admin / sa / analyst x3），密码统一 `Test1234!`
- 5 个分析师档案
- 6 个覆盖标的
- 7 份报告（覆盖 published / submitted / draft / rejected 四种状态）
- 7 个版本快照 + 14 条状态流转日志

---

### 4. 推送 schema 到测试环境

**此操作会影响远程测试环境，执行前必须向用户确认目标环境。**

```bash
# 推送到 Supabase Cloud
python supabase/push_supabase_com.py

# 推送到 Zeabur
python supabase/push_zeabur_com.py
```

执行时问用户：「推到哪个环境？Supabase Cloud 还是 Zeabur？」

---

## 注意事项

- 使用中文与用户沟通
- 重置和推送是不可逆操作，执行前必须确认
- 本地数据库连接信息：`postgresql://postgres:postgres@127.0.0.1:54322/postgres`
