## ADDED Requirements

### Requirement: 邮箱配置管理

系统 SHALL 支持管理员配置外发邮箱的 SMTP 设置。

#### Scenario: 创建邮箱配置
- **WHEN** Admin 用户创建新的邮箱配置
- **THEN** 系统必须验证配置的完整性（host、port、username、password）
- **AND** 系统必须测试 SMTP 连接是否可用
- **AND** 验证通过后系统必须将配置存储到 EmailConfig 表
- **AND** 密码必须加密存储

#### Scenario: 更新邮箱配置
- **WHEN** Admin 用户更新现有的邮箱配置
- **THEN** 系统必须验证新配置的完整性
- **AND** 系统必须测试 SMTP 连接
- **AND** 系统必须更新 EmailConfig 表中的记录

#### Scenario: 删除邮箱配置
- **WHEN** Admin 用户删除邮箱配置
- **THEN** 系统必须检查是否有正在使用的订阅引用该配置
- **AND** 如果有引用，系统必须提示无法删除
- **AND** 如果没有引用，系统必须删除该配置

### Requirement: 用户订阅管理

系统 SHALL 支持管理员配置用户的报告订阅。

#### Scenario: 创建用户订阅
- **WHEN** Admin 用户创建新的订阅
- **THEN** 系统必须记录订阅用户的邮箱
- **AND** 系统必须标识订阅类型（subscription_type: 'general'）
- **AND** 系统必须将订阅信息存储到 Subscription 表
- **AND** 系统必须使用对应的普通用户邮件模板

#### Scenario: 创建 Wind/同花顺订阅
- **WHEN** Admin 用户创建 Wind 或同花顺订阅
- **THEN** 系统必须标识订阅类型（subscription_type: 'wind' 或 'ths'）
- **AND** 系统必须记录目标邮箱地址（Wind/同花顺指定的接收邮箱）
- **AND** 系统必须将订阅信息存储到 Subscription 表
- **AND** 系统必须使用对应的邮件格式模板

#### Scenario: 更新用户订阅
- **WHEN** Admin 用户更新现有订阅
- **THEN** 系统必须允许修改订阅邮箱和订阅类型（subscription_type: 'general'、'wind' 或 'ths'）
- **AND** 系统必须更新 Subscription 表中的记录

#### Scenario: 删除用户订阅
- **WHEN** Admin 用户删除订阅
- **THEN** 系统必须从 Subscription 表中删除该订阅 （Subscription中添加是否可用状态，删除订阅使用逻辑删除）
- **AND** 后续的邮件外发任务不再向该用户发送邮件

### Requirement: 报告邮件外发

系统 SHALL 通过 Job 定时任务将报告外发给订阅用户。

#### Scenario: 匹配订阅条件的外发
- **WHEN** 新报告被推送到系统
- **THEN** 系统必须查找所有可用的订阅用户（必须根据 report 表的 institution 关联 subscriptions 表的 institution）
- **AND** 系统必须为每个匹配的订阅创建外发任务
- **AND** 外发任务必须使用订阅关联的邮箱配置

#### Scenario: 邮件发送
- **WHEN** 外发任务执行时
- **THEN** 系统必须根据订阅类型选择对应的邮件模板（普通用户/Wind/同花顺）
- **AND** 系统必须使用配置的 SMTP 服务器发送邮件
- **AND** 邮件必须附带报告 PDF 附件文件

#### Scenario: 发送失败重试
- **WHEN** 邮件发送失败
- **THEN** 系统必须将 DistributionLog 状态设为 'failed'
- **AND** 系统必须记录失败原因
- **AND** 系统必须在 5 分钟后自动重试
- **AND** 最多重试 3 次

### Requirement: 发送记录监控

系统 SHALL 记录所有邮件外发的状态供管理员查看。

#### Scenario: 记录发送成功
- **WHEN** 邮件发送成功
- **THEN** 系统必须在 DistributionLog 表中创建记录
- **AND** 记录必须包含：report_id、subscription_id、status='success'、sent_at
- **AND** 系统必须关联 Subscription 和 Report

#### Scenario: 记录发送失败
- **WHEN** 邮件发送失败
- **THEN** 系统必须在 DistributionLog 表中创建记录
- **AND** 记录必须包含：report_id、subscription_id、status='failed'、error_message、retry_count
- **AND** retry_count 必须递增

#### Scenario: Admin 查看发送记录
- **WHEN** Admin 用户访问发送记录页面
- **THEN** 系统必须显示所有 DistributionLog 记录
- **AND** 记录必须按发送时间倒序排列
- **AND** 系统必须支持按状态、报告、订阅筛选
- **AND** 系统必须显示失败原因和重试次数

### Requirement: 邮件模板

系统 SHALL 使用预定义的邮件模板发送外发邮件。

#### Scenario: 普通用户邮件模板
- **WHEN** 系统发送给普通订阅用户
- **THEN** 邮件主题格式必须为报告标题
- **AND** 邮件正文必须包含报告摘要
- **AND** 邮件必须附带报告 PDF 附件

#### Scenario: Wind 邮件模板
- **WHEN** 系统发送给 Wind 订阅
- **THEN** 邮件主题格式必须符合 Wind 规范：报告来源*报告类别*报告标题*报告日期*报告作者
- **AND** 邮件主题根据不同报告分类特点，举例如下：
- **AND** 1、东亚前海证券*公司研究*光华科技（002741.SZ）：PCB 化学品龙头，电池回收打开新增长*20220305*李子卓
- **AND** 2、东亚前海证券*行业研究*商贸零售行业周报：疫情持续供求疲软，零售展现业绩韧性*20220406*倪华
- **AND** 3、东亚前海证券*策略研究*4月金股组合*20220401*段小虎,贺燕青,李子卓,倪华,汪玲
- **AND** 报告来源为研究机构简称
- **AND** 报告类型为 report_type
- **AND** 报告日期格式为 YYYYMMDD
- **AND** 报告作者多个作者用,号分割
- **AND** 邮件正文必须包含报告摘要
- **AND** 邮件必须附带报告 PDF 附件

#### Scenario: 同花顺邮件模板
- **WHEN** 系统发送给同花顺订阅
- **THEN** 邮件主题格式必须符合同花顺规范：
- **AND** Company报告格式：报告来源*个股研究*股票简称*作者*报告撰写时间*标题
- **AND** Sector报告格式：报告来源*行业研究*行业名称*作者*报告撰写时间*标题
- **AND** 其他报告格式：报告来源*报告类型*作者*报告撰写时间*标题
- **AND** 报告来源为研究机构简称
- **AND** 其他报告格式中的报告类型为 report_type
- **AND** 作者为报告第一作者（分析师）
- **AND** 报告撰写时间格式为 YYYY-MM-DD
- **AND** 邮件正文必须包含报告摘要
- **AND** 邮件必须附带报告 PDF 附件
