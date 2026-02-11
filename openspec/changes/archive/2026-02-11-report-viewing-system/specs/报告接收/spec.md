## ADDED Requirements

### Requirement: 接收外部报告推送

系统 SHALL 提供 API 接收来自外部系统发布的报告。

#### Scenario: 接收报告基本信息
- **WHEN** 外部系统调用 POST /api/v1/reports 接口
- **THEN** 系统必须验证请求的 API 密钥
- **AND** 系统必须解析请求体中的报告基本信息（title, summary, analysts, ticker, sector, region, publish_date 等）
- **AND** 系统必须将报告信息存储到 Report 表
- **AND** 系统必须返回创建成功的响应，包含报告 ID

#### Scenario: 接收报告附件文件
- **WHEN** 外部系统在创建报告时上传附件文件
- **THEN** 系统必须将文件存储到本地文件系统
- **AND** 系统必须在 ReportFile 表中记录文件元数据（file_name, file_path, file_size, file_type）
- **AND** 系统必须关联文件到对应的报告

#### Scenario: 增量同步已发布的报告
- **WHEN** 外部系统调用 GET /api/v1/reports/sync 接口并传递 since 参数
- **THEN** 系统必须返回 publish_date 大于 since 时间戳的所有已发布报告
- **AND** 返回数据必须包含报告基本信息和附件下载链接

### Requirement: 报告数据存储

系统 SHALL 将接收到的报告数据持久化存储到数据库。

#### Scenario: 报告基本信息存储
- **WHEN** 系统接收到报告推送
- **THEN** 系统必须在 Report 表中创建一条记录
- **AND** 记录必须包含所有必填字段（title, summary, analysts, ticker, sector, region, status, publish_date 等）
- **AND** status 字段必须设置为 'published'

#### Scenario: 报告附件存储
- **WHEN** 报告包含附件文件
- **THEN** 系统必须将文件保存到 {storage_path}/reports/{report_id}/ 目录
- **AND** 文件名必须保持原始名称
- **AND** 系统必须在 ReportFile 表中记录文件路径

### Requirement: API 安全验证

系统 SHALL 验证外部系统调用 API 的权限。

#### Scenario: API 密钥验证
- **WHEN** 外部系统调用报告接收 API
- **THEN** 系统必须验证请求头中的 X-API-Key
- **AND** 验证失败时必须返回 401 Unauthorized 错误
- **AND** 验证成功时必须继续处理请求

#### Scenario: 请求速率限制
- **WHEN** 外部系统频繁调用 API
- **THEN** 系统必须实施速率限制（如：每分钟最多 100 次请求）
- **AND** 超过限制时必须返回 429 Too Many Requests 错误

### Requirement: 错误处理

系统 SHALL 正确处理报告接收过程中的各种错误情况。

#### Scenario: 重复报告处理
- **WHEN** 外部系统推送已存在的报告（通过 external_id 判断）
- **THEN** 系统必须返回 409 Conflict 错误
- **AND** 错误信息必须包含已存在报告的 ID

#### Scenario: 无效数据处理
- **WHEN** 外部系统推送的数据缺少必填字段
- **THEN** 系统必须返回 400 Bad Request 错误
- **AND** 错误信息必须明确指出缺少的字段

#### Scenario: 文件上传失败处理
- **WHEN** 文件上传过程中发生错误
- **THEN** 系统必须返回 500 Internal Server Error 错误
- **AND** 系统必须记录详细的错误日志
- **AND** 如果报告记录已创建，系统必须回滚该记录
