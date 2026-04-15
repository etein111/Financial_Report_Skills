# Supabase 数据准备清单

本文档说明测试 neolyst 集成功能所需的 Supabase 数据准备。

---

## 一、必须准备的数据

### 1. analyst 表（分析师）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | UUID | ✅ | 主键 |
| `email` | text | ✅ | 唯一键，大小写不敏感，内部统一 lowercase/strip |
| `english_name` | text | ✅ | 英文姓名 |
| `chinese_name` | text | ❌ | 中文姓名 |
| `suffix` | text | ❌ | 姓名后缀/头衔 |
| `sfc` | text | ❌ | 证券期货从业资格编号 |
| `region_code` | text | ❌ | 所属区域编码 |
| `is_active` | boolean | ✅ | 是否在职，默认 true |

**测试数据示例：**

```sql
INSERT INTO analyst (id, email, english_name, chinese_name, is_active) VALUES
  ('a1111111-1111-1111-1111-111111111111', 'zhangsan@example.com', 'Zhang San', '张三', true),
  ('a2222222-2222-2222-2222-222222222222', 'lisi@example.com', 'Li Si', '李四', true),
  ('a3333333-3333-3333-3333-333333333333', 'wangwu@example.com', 'Wang Wu', '王五', true);
```

---

### 2. report_template 表（模板）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | text | ✅ | 主键，格式 `{report_type}_{language}`，如 `company_en` |
| `report_type` | text | ✅ | 报告类型，如 `company`、`macro`、`sector` |
| `language` | text | ✅ | 语言代码，如 `en`、`zh` |
| `template_file_path` | text | ✅ | Storage 中的 Word 模板路径（上传后填充） |
| `schema_file_path` | text | ❌ | Storage 中的 schema.yaml 路径 |
| `is_published` | boolean | ✅ | 是否已发布 |

**报告类型枚举值：**

- `company` — 公司报告
- `company_flash` — 公司快讯
- `sector` — 行业报告
- `macro` — 宏观报告
- `strategy` — 策略报告
- `quantitative` — 量化报告
- `bond` — 债券报告
- `flash` — 快讯（通用）

**测试数据示例：**

```sql
INSERT INTO report_template (id, report_type, language, template_file_path, schema_file_path, is_published) VALUES
  ('company_en', 'company', 'en', 'templates/company/en/template.docx', 'templates/company/en/schema.yaml', true),
  ('company_zh', 'company', 'zh', 'templates/company/zh/template.docx', 'templates/company/zh/schema.yaml', true),
  ('macro_en', 'macro', 'en', 'templates/macro/en/template.docx', 'templates/macro/en/schema.yaml', true),
  ('macro_zh', 'macro', 'zh', 'templates/macro/zh/template.docx', 'templates/macro/zh/schema.yaml', true);
```

**注意：** `template_file_path` 和 `schema_file_path` 仅为字符串路径，实际文件需上传到 Supabase Storage。

---

### 3. Storage Bucket（文件存储）

模板文件需上传到 Supabase Storage，bucket 名称由 `get_template_storage_paths` RPC 确定。

**测试步骤：**

1. 准备本地模板文件（Word `.docx` 和 `schema.yaml`）
2. 调用 `neolyst.template.upsert_template()` 自动上传，或手动上传到 Storage

**手动上传示例（通过 Supabase Dashboard）：**

- Bucket: `report-templates`（名称由后端 RPC 决定）
- 路径示例: `templates/company/en/template.docx`
- 路径示例: `templates/company/en/schema.yaml`

---

## 二、公司类报告额外数据

### 4. coverage 表（覆盖范围）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | UUID | ✅ | 主键 |
| `ticker` | text | ✅ | 股票代码，唯一约束（与 analyst_email 组合） |
| `english_name` | text | ✅ | 公司英文名 |
| `chinese_name` | text | ❌ | 公司中文名 |
| `sector_id` | UUID | ❌ | 所属行业 ID（关联 sector 表） |
| `isin` | text | ❌ | ISIN 码 |
| `country_of_domicile` | text | ❌ | 注册国家/地区 |

**测试数据示例：**

```sql
INSERT INTO coverage (id, ticker, english_name, chinese_name, sector_id, isin, country_of_domicile) VALUES
  ('c1111111-1111-1111-1111-111111111111', '2507.HK', 'Cirrus Aircraft', '西锐飞机', NULL, 'US1234567890', 'US'),
  ('c2222222-2222-2222-2222-222222222222', '9988.HK', 'Alibaba Group', '阿里巴巴', NULL, 'US0169Y10895', 'CN');
```

### 5. coverage_analyst 表（覆盖范围-分析师关联）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `coverage_id` | UUID | ✅ | 关联 coverage.id |
| `analyst_email` | text | ✅ | 关联 analyst.email |
| `author_order` | integer | ✅ | 作者顺序，1 代表 1 作 |
| `is_primary` | boolean | ❌ | 是否为主要分析师 |

**测试数据示例：**

```sql
INSERT INTO coverage_analyst (coverage_id, analyst_email, author_order, is_primary) VALUES
  ('c1111111-1111-1111-1111-111111111111', 'zhangsan@example.com', 1, true),
  ('c1111111-1111-1111-1111-111111111111', 'lisi@example.com', 2, false),
  ('c2222222-2222-2222-2222-222222222222', 'zhangsan@example.com', 1, true);
```

---

## 三、行业类报告额外数据

### 6. sector 表（行业）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | UUID | ✅ | 主键 |
| `name` | text | ✅ | 行业名称 |
| `region_code` | text | ❌ | 区域代码 |

**测试数据示例：**

```sql
INSERT INTO sector (id, name, region_code) VALUES
  ('s1111111-1111-1111-1111-111111111111', 'Technology', 'US'),
  ('s2222222-2222-2222-2222-222222222222', '金融', 'CN');
```

### 7. region 表（区域）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | text | ✅ | 主键，区域代码 |
| `name` | text | ✅ | 区域名称 |
| `name_zh` | text | ❌ | 中文名称 |

**测试数据示例：**

```sql
INSERT INTO region (code, name, name_zh) VALUES
  ('US', 'United States', '美国'),
  ('CN', 'China', '中国'),
  ('HK', 'Hong Kong', '香港');
```

---

## 四、RPC 函数权限

确保已认证用户有权调用以下 RPC：

| RPC 函数 | 所需权限 |
|---------|---------|
| `get_template_storage_paths` | 读取模板路径 |
| `upsert_template_record` | 插入/更新模板记录 |
| `reuse_template` | 建立模板复用关系 |
| `upsert_report` | 创建/更新报告 |
| `validate_report` | 校验报告 |
| `submit_report` | 提交报告 |
| `resolve_coverage` | 查询 coverage |
| `create_coverage` | 创建 coverage（可选） |
| `generate_upload_path` | 生成上传路径 |
| `update_report_doc_paths` | 更新报告文件路径 |
| `update_model_path` | 更新模型文件路径 |

---

## 五、环境变量

确保本地环境或 CI 环境设置了以下环境变量：

```bash
# Supabase 连接
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
# 或使用 anon key（需 RLS 策略允许）
SUPABASE_ANON_KEY=your-anon-key
```

---

## 六、最小测试数据集快速检查清单

- [ ] `analyst` 表至少有 1 条活跃分析师记录（测试 `resolve_analyst_by_email`）
- [ ] `analyst` 表至少有 2 条活跃分析师记录（测试多人作者）
- [ ] `report_template` 表有 `company_en` 和 `macro_en` 两条记录
- [ ] 对应的模板文件已上传到 Storage
- [ ] 若测试公司报告：`coverage` 表有对应 ticker 的记录，`coverage_analyst` 关联正确
- [ ] 若测试行业报告：`sector` 表有记录

---

## 七、常见错误排查

### 错误：`模板不存在: report_type='company', language='en'`

**原因：** `report_template` 表中没有对应 `report_type + language` 的记录。

**解决：** 插入记录，并上传模板文件到 Storage。

---

### 错误：`分析师未找到：zhangsan@example.com`

**原因：** `analyst` 表中没有该邮箱记录，或 `is_active=false`。

**解决：** 插入分析师记录，确保 `is_active=true`。

---

### 错误：`Coverage 未命中`

**原因：** `coverage` 表中没有 `(ticker, 1作分析师邮箱)` 的匹配记录。

**解决：** 插入 coverage 和 coverage_analyst 记录。
