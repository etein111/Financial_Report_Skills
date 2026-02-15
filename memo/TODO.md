# TODO - 2026-02-15

## 待完成：阶段 7 验收

Change: `openspec/changes/auth-and-users-mvp`

**剩余任务**：
- [ ] 7.1 认证闭环验收（登录/登出/会话刷新/忘记密码/回调）
- [ ] 7.2 权限验收（Admin/SA/Analyst 三角色访问控制）
- [ ] 7.3 禁用账号验收（被 ban 用户无法登录/访问）
- [ ] 7.4 路由保护验收（未登录访问 /desktop /users -> /login）
- [ ] DoD：`/opsx:verify`

**验收方式**：
```powershell
cd web && corepack pnpm dev
```
- 访问 http://localhost:3000/login
- 登录凭证：`jiang_jiahong@qq.com` / `Admin123`

**验收清单**：
- 未登录访问 `/desktop`、`/users` -> 跳 `/login`
- Admin 登录 -> `/desktop` 可见 Users 卡片；打开 `/users` 正常
- SA/Analyst 登录 -> `/desktop` 不显示 Users 卡；直接访问 `/users` -> `/403`
- Ban 用户后：该用户无法继续登录/访问受保护路由

完成后执行：
```powershell
openspec verify --change auth-and-users-mvp
```
