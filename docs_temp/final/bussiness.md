# 业务

## 业务角色

* 分析师（Analyst）
  在微信里发送草稿和指令给编辑，后期直接与 AI Agent 协作。
* 合规人员（SA）
  在工作台查看系统初筛结果，完成审批和发布。
* 编辑（Editor）
  通过工作台与AI写作前期负责手动操作和教系统规则，后期负责维护系统和处理异常。
  初期平台没有设置这个角色，只有一个编辑，用SA的身份操作。
  后面进展快的话可以一步到位，直接过渡到分析师直接接入AI工作台自助工作，编辑只是AI的监督者，可能不需要这个角色。
* 系统管理员 (Admin)
  拥有所有平台权限，包括管理用户权限、行业分类等基础设置等。
* 买方机构（Customer）
  在外部发布系统查看报告。

## 核心工作流(todo)

### 报告编辑(todo)

1. 任务接收
   分析师通过微信发送草稿与指令。
2. AI 预处理
   AI自动解析并生成报告保存在neolyst-db，Editor核对修改。
3. 确认入库
   Editor处理好报告，会自动在neolyst-db，状态标记为"待审核"。

### 审批发布(todo)

1. 自动初筛
   SA 登录工作台调用审核功能，系统高亮合规风险点。
2. 人工决断
   SA 确认后下达发布指令。
3. 异步发布
   系统修改 neolyst-db 状态为"已发布"，独立进程侦测后自动同步至 neoport-db。

## RLS 矩阵(todo)

| 表 | Admin | SA | Analyst |
|----|-------|----|---------|
| region / analyst / sector | R/W | R | R |
| coverage | R/W | R | R + INSERT |
| coverage_analyst | R/W | R | R + INSERT |
| template | R/W | R | R |
| report | 全量 R/W（无 DELETE） | R（submitted/published/rejected） | R/W（仅 owner，draft/submitted） |
| report_version | R + INSERT | R（submitted/published/rejected） | R + INSERT（仅 owner） |
| report_analyst | 全量 R/W | R（submitted/published/rejected） | R/W（仅 owner） |
| report_status_log | R + INSERT | R + INSERT（审批与退回） | R + INSERT（仅 owner submit） |

## 报告状态机(todo)

允许流转：`draft → submitted → published`、`submitted → rejected → draft`
禁止：跨级跳转和逆向回写（如 `published → draft`）

## 报告字段矩阵(todo)

| 字段 | company | sector | company_flash | sector_flash | common |
|------|:-------:|:------:|:-------------:|:------------:|:------:|
| Ticker | ✅ | | ✅ | | |
| Rating | ✅ | | | | |
| Target price | ✅ | | | | |
| Region | | ✅ | | ✅ | ✅ |
| Sector | | ✅ | | ✅ | |
| Report language | ✅ | ✅ | ✅ | ✅ | ✅ |
| Report title | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analyst | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contact Person | ✅ | ✅ | ✅ | ✅ | ✅ |
| Investment thesis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Certificate | ✅ | ✅ | ✅ | ✅ | ✅ |


## Domain Model(todo)

### Domain

* user
* coverage
* template
* report
* analyst
* ticker
* sector
* region

### Relationship(todo)

