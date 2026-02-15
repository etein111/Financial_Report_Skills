# Testing & Verification

目标：让“测试/验收/诊断”可重复、可清理、不污染目录、不对云端数据造成不可控副作用。

## 临时文件（统一目录）

- 所有测试/验收产生的临时文件，只允许写到仓库根目录 `temp/`。
- `temp/` 已在 `.gitignore` 忽略，允许直接整目录删除清理。
- 建议子目录（不新增新的顶层目录）：
  - `temp/verify/`：验收输出
  - `temp/e2e/`：端到端测试工件
  - `temp/logs/`：本地日志

规范：
- 输出文件名带时间戳，避免覆盖：`<tool>-<yyyyMMdd-HHmmss>.<ext>`
- 任何脚本不得在源码目录写入 `*.out`、`*.log`、`*.tmp` 等文件。

## 脚本放置

- Web 侧验收/诊断脚本：`web/scripts/verify/*`
- Supabase 运维脚本：`supabase/scripts/*`

说明：
- 仓库根目录不再放 `scripts/`，避免和“日常 job”含义混淆。

## 云端库副作用控制

默认原则：
- 能用 **只读** 验证就只读（例如查询 RLS policy、读取配置）。
- 需要写入验证时，优先选择：
  - 事务内执行并 `ROLLBACK`
  - 或者创建带 `__test__` 前缀的临时数据，并确保 `finally` 清理

当前脚本策略：
- `web/scripts/verify/verify-db-admin-and-rls.mjs`
  - 默认 Admin 幂等检查在事务内执行并回滚
  - RLS 写入验证也在事务内执行并回滚
- `web/scripts/verify/verify-auth-and-rls.mjs`
  - 属于“全链路验收”（依赖 Auth 正常），会创建临时 Auth 用户并在 `finally` 尝试删除
  - 若云端 Auth 异常，可能无法完成清理，需谨慎使用

## 常用命令（验收）

DB 直连验收（不依赖 Docker/psql）：
```powershell
cd web
node scripts/verify/verify-db-admin-and-rls.mjs
```

Auth 故障诊断（直连 Postgres）：
```powershell
cd web
node scripts/verify/diagnose-auth-500.mjs
```

