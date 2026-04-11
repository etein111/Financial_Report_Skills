# 认证参考

## 获取 Client

所有接口需要已认证的 Supabase client。

```python
from skills.neolyst.scripts import connection

client = connection.get_client()
```

## 配置文件（随 skill 发布，非敏感，已提交到仓库）

`skills/neolyst/neolyst.yaml` — 运行时默认 Supabase 连接配置：

```yaml
supabase_url: "https://neolyst.zeabur.app"  # 当前仓库默认指向 staging
anon_key: "eyJhbG..."                       # Supabase anon/publishable key（非密钥）
```

anon key 是公开的客户端 key，不是敏感信息，可以安全提交到版本库。`neolyst.yaml` 是运行时默认配置，不保证指向本地环境。

## 凭据文件（本地保存，不提交）

`skills/neolyst/user.json` — 用户登录凭据：

```json
{
  "email": "user@example.com",
  "password": "..."
}
```

`skills/neolyst/session.json` — 当前登录 session：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_at": 1712345678
}
```

## 首次使用

当 `skills/neolyst/user.json` 不存在时，说明用户尚未登录过。此时：

1. 告知用户需要 Neolyst 账号凭据（邮箱 + 密码）
2. 向用户请求邮箱和密码
3. 调用 `get_client(email=..., password=...)` 完成首次登录
4. 登录成功后凭据自动保存到 `user.json`，session 自动保存到 `session.json`

```python
client = connection.get_client(email="user@neolyst.com", password="your_password")
```

## Session 自动管理

`get_client` 的完整认证顺序：

1. 读取 `session.json`，用 `access_token` 恢复 session
2. token 过期时自动用 `refresh_token` 刷新，回写 `session.json`
3. refresh 失败时用 `user.json` 里的 `email + password` 重新登录，回写 `session.json`
4. 以上均失败 → 抛出 `ValueError`，向用户索取邮箱和密码后重新调用 `get_client(email=..., password=...)`

access token 有效期约 1 小时，refresh token 随之轮换。长时间不用后需要重新登录属于正常现象。

## 测试连接约束

本地测试不得依赖 `neolyst.yaml` 的默认值。测试环境强制把：

- `NEOLYST_TEST_URL` 映射到 `NEOLYST_URL`
- `NEOLYST_TEST_ANON_KEY` 映射到 `NEOLYST_ANON_KEY`

本地联调还需要显式提供：

- `NEOLYST_TEST_EMAIL`
- `NEOLYST_TEST_PASSWORD`

测试连接目标必须通过环境变量声明，禁止回落到 staging 配置。
