# neolyst

Neolyst Supabase 数据访问层。实现位置：`scripts/`。

## 开发与测试

### 连接配置

| 配置来源 | 用途 | 提交到版本库 |
|---------|------|------------|
| `neolyst.yaml` | 运行时默认连接（URL + anon_key） | 是（anon_key 是公开客户端 key） |
| `user.json` | 用户凭据（email + password） | 否 |
| `session.json` | 登录态（access_token + refresh_token） | 否 |

`neolyst.yaml` 当前可指向 staging。anon key 是公开客户端 key，不是密钥。

### 测试环境变量

本地测试必须设置以下环境变量，**不允许回落到 `neolyst.yaml` 默认值**：

```bash
export NEOLYST_TEST_URL="https://xxx.supabase.co"
export NEOLYST_TEST_ANON_KEY="eyJ..."
export NEOLYST_TEST_EMAIL="test@neolyst.com"
export NEOLYST_TEST_PASSWORD="xxx"
```

pytest 的 `conftest.py` 会将 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射为运行时的 `NEOLYST_URL` / `NEOLYST_ANON_KEY`。

## 模块依赖方向

依赖保持单向，`connection` 是基础设施层，不依赖任何业务模块：

```
connection  ←  storage, analyst, coverage, rpc
connection + storage  ←  template, draft_report
connection  ←  validators, submit_report
```
