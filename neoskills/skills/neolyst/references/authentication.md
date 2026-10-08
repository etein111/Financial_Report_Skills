# 认证参考

## 获取 Client

所有接口需要已认证的 Supabase client。

```python
from skills.neolyst.scripts import connection

client = connection.get_client()
```

凭据文件（`user.json`、`session.json`）由 `get_client()` 自动管理，不提交到版本库。token 过期时自动刷新，全部失败时抛出 `ValueError`。

## 首次使用

当 `get_client()` 因缺少凭据抛出异常时：

1. 向用户索取 Neolyst 邮箱和密码
2. 调用 `get_client(email=..., password=...)` 完成登录
3. 登录成功后凭据自动保存，后续调用 `get_client()` 即可

```python
client = connection.get_client(email="user@neolyst.com", password="your_password")
```

## 凭据文件位置

凭据文件存放在 skill 根目录 `skills/neolyst/` 下：

| 文件 | 内容 | 用途 |
|------|------|------|
| `user.json` | `{ "email": "...", "password": "..." }` | 登录凭据，首次登录后自动生成 |
| `session.json` | `{ "access_token": "...", "refresh_token": "...", "expires_at": 1775813142 }` | 登录态，token 过期时自动刷新 |

需要切换账号或重置登录状态时，删除这两个文件后重新调用 `get_client(email=..., password=...)` 即可。

## 常见错误

| 错误信息 | 原因 | 处理方式 |
|----------|------|----------|
| `No valid session and no credentials provided` | 无可用 session 且未提供邮箱密码 | 向用户索取邮箱密码，调用 `get_client(email=..., password=...)` |
| `Authentication failed for 'xxx@...': ...` | 邮箱或密码错误 | 确认凭据是否正确，重新向用户索取 |
