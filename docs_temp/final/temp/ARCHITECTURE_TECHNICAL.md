

### 4.2 报告标题生成规则

| 场景 | 格式 |
|------|------|
| 首次覆盖 | `{公司名} ({Ticker}): 首次覆盖: {标题}` |
| 评级变动，目标价不变 | `{公司名} ({Ticker}): {标题}—{动作}{评级}` |
| 评级+目标价变动 | `{公司名} ({Ticker}): {标题}—{动作}{评级}; {TP动作}{TP变动}%` |
| 仅目标价变动 | `{公司名} ({Ticker}): {标题}—维持{评级}; {TP动作}{TP变动}%` |
| 评级和目标价都不变 | `{公司名} ({Ticker}): {标题}—维持{评级}` |
| 中英文版 | `公司中文简称 ({Ticker}): 中文标题—动作 (English Title — Action)` |

## 5. 业务流程

### 5.1 报告创建流程

```
上传文件 → 字段检查 → 文件检查 → 相似度检查 → SFC 检查
→ Coverage 检查 → 标题生成 → 提交报告 → RQC/首席审批 → 发布
```

### 5.2 模板制作流程

1. 上传标准样本 + schema.yaml
2. 系统自动构建模板并验证
3. 对话式修改提取规则和模板
4. 确认后生效

## 6. 存储架构

### 6.1 模板文件

- Bucket：模板专用
- 路径：以 `template.template_file_path` 和 `template.schema_file_path` 为准（非 report_type 推导）
- 读取：所有已认证用户
- 写入：仅 Admin
- 多个 report_type 可引用同一路径共用模板资产

### 6.2 报告文件

- Bucket：reports 专用
- 目录：`{report_id}/`
- 命名：`{report_id}_{version_no3}_{label}_{ts}.{ext}`
  - version_no3：三位版本号（001、002…）
  - label：report / pdf / model
  - ts：UTC `YYYYMMDDTHHMMSSZ`

### 6.3 报告文件权限

- 读取：owner / Admin / SA（SA 仅 submitted|published|rejected）
- 写入：owner / Admin

## 7. 权限与安全

### 7.1 角色

| 角色 | 权限范围 |
|------|----------|
| Admin | 全部操作（用户/区域/分析师/Coverage/Sector/模板/报告/审批） |
| SA | 审批 submitted 报告；可见 submitted/published/rejected |
| Analyst | 创建/编辑/提交自己的报告；新增 Coverage |

### 7.2 认证

- 会话：SSR cookies（`@supabase/ssr`）
- 鉴权事实源：`getUser()`
- 角色事实源：JWT 角色字段（遵循 DECISIONS.md D-003）
- 路由门禁：proxy.ts（未登录 → /login，无权限 → /403）

## 8. 目录结构

```
neoskills/
├── docs/
│   ├── README.md
│   ├── agent-req.md
│   ├── report-skills.md
│   └── neolyst/
│       ├── ARCHITECTURE.md
│       ├── DATA_MODEL.md
│       └── REQUIREMENTS.md
├── samples/                   # 研究报告示例
└── CLAUDE.md
```

报告文件命名：
- 中文：`公司全称 日期.docx`
- 英文：`Ticker 日期.docx`

## 9. 关键技术实现

### 9.1 模板引擎

python-docx-template (Jinja2) 渲染短文本到 Word 占位符。`{{company_name}}`、`{{rating}}` 等。

重复部分用循环：`{% for analyst in analysts %}{{ analyst.name }}{% endfor %}`

### 9.2 文档格式转换

- Word → Markdown：Pandoc (pypandoc)，剥离格式生成纯净文本
- Markdown → Word：Pandoc + Subdoc 机制，保留层级结构不破坏主模板版式

### 9.3 复杂图表提取

LibreOffice 静默转 PDF → PyMuPDF 解析坐标 → 高清截图裁剪 → 存入 assets/

避免 Word 表格转 HTML/Markdown 的格式崩坏，保证 100% 视觉保真。

### 9.4 文件相似度检测

相似度 = `1 - 莱文斯坦距离 / 最大字符串长度`。阈值 60%。

### 9.5 SFC 牌照验证

从 https://apps.sfc.hk/publicregWeb/searchByName 查询，自动填充。重名时人工确认。

## 10. 附录

### 10.1 Certificate 英文条款

报告提交前必须展示并勾选确认：

1. members of my household and I have not traded any financial interest in the subject company since I started the coverage nor currently hold any financial interest in the subject company (including, without limitation, any securities, option, right, warrant, future, long or short position)
2. I did not receive any compensation from the subject company in the previous 12 months
3. I have not served as an officer, director or employee of the subject company
4. none of my household serve as an officer of the subject company
5. I comply with the Group Compliance Policy with regards to gifts and entertainment in dealing with subject companies and investors
6. this research report contains no material non-public information

### 10.2 RQC 触发条件

- 首次覆盖
- 评级变动
- 目标价变动 ≥ 30%
