# Neolyst validate_draft 当前版本校验设计

## 背景

当前 `neolyst` skill 的接口如下：

- `validate_draft(client, report_id, version_no)`
- `submit_report(client, report_id, version_no)`
- `public.submit_report(p_report_id, p_version_no)`

这组接口把“要提交哪个版本”的决定权交给调用方。但在现有数据模型里，`report.current_version_no` 已经是报告当前版本的唯一事实源。继续要求调用方传 `version_no`，会带来两个问题：

1. 调用方需要额外维护一个本不该由它决定的参数。
2. 校验和提交可能针对不同版本，形成接口语义不一致。

本次设计的目标是把“当前版本”的定义统一收回到服务端状态，不再由调用方显式传入版本号。

## 设计结论

本次采用以下约束：

- `validate_draft` 去掉 `version_no` 入参，只校验 `report.current_version_no` 指向的当前版本。
- `submit_report` 去掉 `version_no` 入参，只提交当前版本。
- `public.submit_report` RPC 去掉 `p_version_no`，由数据库侧读取 `report.current_version_no`。
- `submit_report` 不再在 Python 侧自动调用 `validate_draft`。
- 仓内直接硬切换，不保留兼容层。

## 接口契约

### Python: validate_draft

```python
validate_draft(client, report_id: str) -> {"report_id": str, "version_no": int}
```

语义：

- 读取 `report` 记录。
- 使用 `report.current_version_no` 作为唯一校验目标版本。
- 校验通过后返回真实校验版本号，便于调用方记录和展示。

### Python: submit_report

```python
submit_report(client, report_id: str) -> {"report_id": str, "version_no": int, "status": "submitted"}
```

语义：

- Python 侧不再先调 `validate_draft`。
- 直接调用 `public.submit_report(p_report_id)`。
- 返回值中的 `version_no` 由 RPC 返回真实提交版本。

### Supabase RPC: submit_report

```sql
public.submit_report(p_report_id uuid)
returns table(report_id uuid, version_no integer, status text)
```

语义：

- 在 RPC 内部读取 `report.current_version_no`。
- 将该版本号写入 `report_status_log.version_no`。
- 返回真实提交版本号。

## 详细行为

### validate_draft 的处理流程

1. 查询 `report.id = report_id`，读取：
   - `status`
   - `current_version_no`
   - 当前已有的业务字段
2. 若报告不存在，直接抛出 `报告不存在: {report_id}`。
3. 若 `status` 不在 `draft` / `rejected`，沿用现有报错语义。
4. 若 `current_version_no <= 0`，抛出 `报告当前没有可校验版本`。
5. 使用 `report_id + current_version_no` 查询 `report_version`。
6. 若当前版本不存在，报 `当前版本 v{n} 不存在`。
7. 继续执行现有全量校验：
   - Word / PDF 路径
   - 必填字段
   - 分析师列表
   - `contact_person`
   - 分析师存在且启用
   - `coverage_id`
   - `sector_id`
   - `region_code`
8. 若存在多个问题，继续一次性汇总抛出。
9. 通过后返回 `{"report_id": report_id, "version_no": current_version_no}`。

### submit_report RPC 的处理流程

1. 查询 `report.id = p_report_id`。
2. 若报告不存在，抛错。
3. 若 `status` 不在 `draft` / `rejected`，抛错。
4. 读取 `current_version_no`。
5. 若 `current_version_no <= 0`，抛错，禁止提交没有实际版本的报告。
6. 校验 `report_version(report_id, current_version_no)` 存在。
7. 若不存在，抛错，禁止写入悬空状态日志。
8. 更新 `report.status = 'submitted'`。
9. 写入 `report_status_log.version_no = current_version_no`。
10. 返回 `{report_id, version_no: current_version_no, status: 'submitted'}`。

## 错误模型

### validate_draft

保留“字段类错误一次性汇总”的行为，但新增两个当前版本相关错误：

- `报告当前没有可校验版本`
- `当前版本 v{n} 不存在`

### submit_report

`submit_report` 不负责完整字段校验，只负责状态流转的最低一致性保护。RPC 侧至少保证：

- 报告存在
- 状态允许提交
- `current_version_no > 0`
- 当前版本记录存在

这意味着：

- `validate_draft` 仍然是显式预检接口。
- 若调用方跳过 `validate_draft`，`submit_report` 仍可能提交字段不完整但状态合法的报告。

这是本次明确接受的边界，不在本次调整中把完整校验下沉到 RPC。

## 改动范围

### 代码

- `skills/neolyst/scripts/validators.py`
- `skills/neolyst/scripts/submit_report.py`
- `supabase/migrations/*submit_report*`

### 测试

- `skills/neolyst/tests/test_validators.py`
- `skills/neolyst/tests/test_submit_report.py`

新增或调整的重点场景：

- `validate_draft` 只传 `report_id`
- `current_version_no = 0`
- `current_version_no > 0` 但对应 `report_version` 缺失
- `submit_report` 返回的 `version_no` 来自当前版本

### 文档

- `skills/neolyst/SKILL.md`
- 仓内所有 `validate_draft(report_id, version_no)` / `submit_report(report_id, version_no)` 相关设计文档与集成文档

说明：

- `SKILL.md` 后续实现阶段必须按仓库规范使用 `skill-creator` 修改，不手工编辑。

## 不在本次范围内

- 不调整 `save_draft_report` 的版本生成逻辑。
- 不调整文件存储路径规则。
- 不把 `validate_draft` 的完整校验逻辑下沉到 RPC。
- 不提供旧接口兼容层。

## 实施顺序

1. 修改 `public.submit_report` RPC 签名和内部版本定位逻辑。
2. 修改 Python `submit_report(client, report_id)` 包装层。
3. 修改 `validate_draft(client, report_id)`。
4. 修改测试。
5. 修改 `SKILL.md` 和相关文档。

## 兼容性结论

这是一次破坏性接口调整，仓内统一硬切换：

- 删除所有 `validate_draft(report_id, version_no)` 调用。
- 删除所有 `submit_report(report_id, version_no)` 调用。
- 以后“当前版本”的唯一事实源是 `report.current_version_no`。
