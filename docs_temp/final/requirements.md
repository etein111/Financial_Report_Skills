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
   AI自动解析并生成报告保存在Neolyst-DB，Editor核对修改。
3. 确认入库
   Editor处理好报告，会自动在Neolyst-DB，状态标记为"待审核"。

### 审批发布(todo)

1. 自动初筛
   SA 登录工作台调用审核功能，系统高亮合规风险点。
2. 人工决断
   SA 确认后下达发布指令。
3. 异步发布
   系统修改 Neolyst-DB 状态为"已发布"，独立进程侦测后自动同步至 Neoport-DB。

## 报告字段矩阵

| 字段 | company | company_flash | sector | sector_flash | macro, strategy, quantitative, bond |
|------|:---:|:---:|:---:|:---:|:---:|
| Report language | ✅ | ✅ | ✅ | ✅ | ✅ |
| Report title | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analyst | ✅ | ✅ | ✅ | ✅ | ✅ |
| Investment thesis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ticker | ✅ | ✅ | | | |
| Rating | ✅ | | | | |
| Target price | ✅ | | | | |
| Region | | | ✅ | ✅ | ✅ |
| Sector | | | ✅ | ✅ | |

- 所有报告类型都需要 language、title、analyst、investment thesis。
- 公司类报告（company、company_flash）需要 ticker。
- company 还需要 rating 和 target price。
- 非公司类报告都需要 region。
- 行业类报告（sector、sector_flash）还需要 sector。

## 报告提交规则

- 报告类型必须有对应的有效模板。
- 所有报告类型提交时必须有 Report Word 文件；company 类型还必须有 Model 文件。
- 公司类报告（company、company_flash）提交时必须满足 Coverage 关联（Ticker + Analyst 关系存在）。
- 提交前必须确认 Certificate 条款。

## Certificate 条款

分析师提交报告时必须声明已遵守以下合规条款：

1. members of my household and I have not traded any financial interest in the subject company since I started the coverage nor currently hold any financial interest in the subject company (including, without limitation, any securities, option, right, warrant, future, long or short position;
2. I did not receive any compensation from the subject company in the previous 12 months;
3. I have not served as an officer, director or employee of the subject company;
4. none of my household serve as an officer of the subject company;
5. I comply with the Group Compliance Policy with regards to gifts and entertainment in dealing with subject companies and investors;
6. this research report contains no material non-public information.

## Contact Person

- 初期由 Admin 替分析师提交报告，数据库中报告的 owner 记录的是 Admin。
- Contact Person 用于标注实际的报告负责人。
- 报告发布后，Neoreport 系统向 Contact Person 发送最终版报告。
- 此做法后续可能调整。

## 报告状态机

- 报告 owner 模型：谁创建归谁，owner 不可转移。
- `draft` 状态可编辑，其他状态不可编辑。
- 允许流转：`draft → submitted → published`、`submitted → rejected → draft`
- 禁止：跨级跳转和逆向回写（如 `published → draft`）
- SA/Admin 可审批通过、拒绝（rejected → draft）。
- Reject 必须填写 Note，无 Note 阻断状态流转。
- 发布时必须记录发布人和时间快照，其他状态流转不可修改。

### 报告版本

- 报告版本服务于编辑过程。
- 每次内容保存必须追加新版本。

### 状态历史

- 状态历史服务于审计报告流程。
- 状态流转必须记录状态日志，并记录动作对应版本号。

## 角色权限

### 管理员（Admin）

- 管理基础数据（区域、分析师、行业）
- 管理 Coverage
- 管理模板及模板文件
- 操作所有报告，不可删除

### 合规人员（SA）

- 查看基础数据、Coverage、模板
- 查看已提交、已发布、已退回的报告及文件
- 审批和退回报告

### 分析师（Analyst）

- 查看基础数据、Coverage、模板
- 新增 Coverage
- 创建、编辑、提交自己的报告
- 操作自己的报告文件

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

