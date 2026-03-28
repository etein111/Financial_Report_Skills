# NeoSkills 服务器部署指南

## 概述

本指南说明如何在 Linux 服务器上部署 NeoSkills + OpenCode + FileBrowser，实现：
1. **Skill 自然语言激活** - 说"做研报"即可触发报告生成
2. **Web 文件管理** - FileBrowser 提供文件上传/下载
3. **用户目录隔离** - 每个用户有独立的 input/output 目录

---

## 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Linux Server                           │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   OpenCode      │    │         FileBrowser            │ │
│  │   (AI 对话)     │    │   (文件管理 :8080)              │ │
│  │   :3000         │    │                                 │ │
│  │                 │    │   /data/{username}/input/        │ │
│  │                 │    │   /data/{username}/output/       │ │
│  └─────────────────┘    └─────────────────────────────────┘ │
│                                                              │
│  /data/                                                     │
│  ├── user_alice/                                            │
│  │   ├── input/   ← 上传草稿                               │
│  │   └── output/  ← 生成报告                               │
│  ├── user_bob/                                             │
│  │   ├── input/                                           │
│  │   └── output/                                          │
│  └── filebrowser/                                          │
│      └── filebrowser.db                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: 上传部署脚本到服务器

从本项目 `docs/deploy/` 目录获取以下文件：

- `deploy-server.sh` - 主部署脚本
- `init-user-dirs.sh` - 用户目录初始化脚本

上传到服务器的 `/opt/neoskills/` 目录：

```bash
scp deploy-server.sh init-user-dirs.sh user@your-server:/opt/neoskills/
ssh user@your-server
cd /opt/neoskills
chmod +x deploy-server.sh init-user-dirs.sh
```

---

## Step 2: 执行部署

```bash
sudo /opt/neoskills/deploy-server.sh
```

输出示例：
```
[INFO] 创建目录结构...
[INFO] 检查 Docker...
Docker version 28.x.x
[INFO] 清理旧容器...
[INFO] 启动 FileBrowser...
[INFO] FileBrowser 启动成功！

=============================================================================
                      部署完成！
=============================================================================

访问地址：
  FileBrowser: http://192.168.1.100:8080

默认管理员账号：
  用户名: admin
  密码: admin
```

---

## Step 3: 配置 FileBrowser 多用户

### 3.1 登录 FileBrowser

访问 `http://your-server:8080`，使用默认账号登录：
- 用户名: `admin`
- 密码: `admin`

### 3.2 修改管理员密码

登录后右上角 Settings → Profile → Change Password

### 3.3 创建业务人员账号

1. Settings → Users → New User
2. 填写用户名（建议与 OpenCode 用户名一致，如 `alice`）
3. 设置密码
4. 权限设置：
   - Scope: `/data/alice` （只允许访问自己的目录）
   - Permissions: `upload`, `download`, `delete`, `rename`

### 3.4 创建用户目录

在服务器上执行：

```bash
sudo /opt/neoskills/init-user-dirs.sh alice
sudo /opt/neoskills/init-user-dirs.sh bob
```

---

## Step 4: 配置 OpenCode

### 4.1 复制配置到 OpenCode 配置目录

```bash
# 将 opencode.json 复制到 OpenCode 配置目录
cp /opt/neoskills/opencode.json ~/.opencode/config.json

# 将 skills 链接到 OpenCode
ln -sf /opt/neoskills/.claude/skills ~/.opencode/skills
```

### 4.2 OpenCode 配置说明

`opencode.json` 内容：

```json
{
  "skillsDir": ".claude/skills",
  "workingDirectory": "/data/{username}",
  "allowedDirectories": [
    "/data/{username}/input",
    "/data/{username}/output",
    "skills",
    "templates",
    "samples"
  ]
}
```

**注意**：`{username}` 需要根据实际登录用户动态替换。你可能需要：
- 使用环境变量 `OPENCODE_USERNAME`
- 或在启动 OpenCode 时指定用户参数

---

## Step 5: 业务人员操作流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 打开 FileBrowser (http://your-server:8080)              │
│    → 用自己的账号登录 (如 alice)                             │
│    → 进入 "input" 文件夹                                     │
│    → 上传报告草稿 .docx 文件                                │
├─────────────────────────────────────────────────────────────┤
│ 2. 打开 OpenCode Web (http://your-server:3000)              │
│    → 对话框输入："帮我做研报"                               │
│    → AI 自动识别 skill，读取 input/ 最新文件                │
│    → 生成报告保存到 output/ 目录                            │
│    → 告知完成或返回文件路径                                 │
├─────────────────────────────────────────────────────────────┤
│ 3. 回到 FileBrowser                                         │
│    → 进入 "output" 文件夹                                   │
│    → 下载生成的报告文件                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
/data/
├── filebrowser/
│   └── filebrowser.db         # FileBrowser 数据库
├── alice/                     # 用户 alice 的目录
│   ├── input/                # 上传文件
│   └── output/               # 输出文件
├── bob/                      # 用户 bob 的目录
│   ├── input/
│   └── output/
└── neoskills/                # NeoSkills 代码
    ├── skills/
    ├── templates/
    └── samples/
```

---

## 故障排除

### FileBrowser 无法启动

```bash
# 查看日志
docker logs filebrowser

# 检查端口占用
netstat -tlnp | grep 8080
```

### 权限问题

```bash
# 修改目录所有者
sudo chown -R 1000:1000 /data/alice

# 或使用 ACL
sudo setfacl -R -m u:1000:rwx /data/alice
```

### OpenCode 无法读取用户目录

检查 OpenCode 启动用户和目录权限：
```bash
ls -la /data/alice/
```

---

## 注意事项

1. **防火墙**：确保 8080 和 3000 端口对外开放
2. **数据备份**：定期备份 `/data/filebrowser/filebrowser.db`
3. **安全建议**：
   - 首次登录后立即修改 admin 密码
   - 为每个业务人员创建独立账号
   - 考虑启用 HTTPS（通过 Nginx 反向代理）
