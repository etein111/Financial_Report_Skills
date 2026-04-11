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
