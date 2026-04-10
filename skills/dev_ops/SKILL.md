---
name: dev_ops
description: "neoskills 项目的日常开发操作。当用户提到「启动本地数据库」「打开管理面板」「重置数据库」「导入测试数据」「推送到测试环境」「推送 schema」「更新 staging」「提交 github」「push github」「reset db」「seed data」「push staging」时使用此 skill。包括本地 Supabase 管理、测试数据导入、schema 推送、代码提交等操作。"
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

先检查 Supabase 是否在运行：

```bash
supabase status
```

然后打开浏览器：

```bash
# WSL 环境
explorer.exe "http://127.0.0.1:54323"

# macOS / Linux
open "http://127.0.0.1:54323"
```

Studio 地址固定为 `http://127.0.0.1:54323`。

---

### 2. 重置本地数据库 + 导入测试数据

**此操作会清空本地数据库，执行前必须向用户确认。**

两步依次执行，第二步依赖第一步：

```bash
# 步骤 1：重置数据库（自动执行 migrations + seed.sql）
supabase db reset

# 步骤 2：导入测试数据（不随 reset 自动加载）
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -f supabase/tests/test_data.sql
```

---

### 3. 推送 schema 变更到 staging 环境

**此操作会影响远程测试环境，执行前必须向用户确认。**

当前 staging 环境部署在 Zeabur，使用 `push_zeabur_com.py` 推送：

```bash
python3 skills/dev_ops/scripts/push_zeabur_com.py
```

---

### 4. 提交并推送到 GitHub

把工作区所有变更 commit 并 push 到 GitHub：

```bash
git add -A
git commit -m "<type>: <description>"
git push
```

提交信息格式：`<type>: <description>`，type 包括 feat、fix、refactor、docs、test、chore、perf、ci。

---

## 注意事项

- 使用中文与用户沟通
- 重置和推送是不可逆操作，执行前必须确认
- 本地数据库连接信息：`postgresql://postgres:postgres@127.0.0.1:54322/postgres`
