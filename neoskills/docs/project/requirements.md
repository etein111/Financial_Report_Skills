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

## 报告编辑自动化流程

系统在报告编辑阶段按以下顺序执行自动化步骤：

* 接受原始报告
  分析师发送原始报告过来

* 提取报告要素、摘要和正文
  AI自动从 Word 内容中提取，报告要素即报告的核心字段

* 文件齐全性检查
  所有报告类型必须有 Word 文件，company 类型还必须有 Model 文件。

* Coverage 关联检查
  检查 Coverage 关联是否已存在（见报告提交规则）。

* 必填字段检查
  自动从报告内容提取必填字段（见报告字段矩阵）。缺失字段提示补齐。提取完成后在 Neolyst-DB 新建草稿报告。

* 实时股价图生成
  从市场数据库取出 ticker 数据生成图表。股价走势图：最近一年股票收盘价与指数收盘价的涨跌幅，起点固定为 100，后续按日涨跌幅累乘。Volume 柱状图：股票 Volume 数据。

* 报告标题生成
  根据评级变动场景自动生成报告标题（见报告标题规则）。

* 报告生成
  将报告要素、摘要和正文按模板生成报告。创建报告草稿。

* Model 一致性检查
  自动提取报告中的数据（如盈利预测）与 Model 比对，不一致则提示修改。

* SFC 牌照检查
  查询 SFC 牌照信息并自动填充到报告中。报告署名分析师无 SFC 牌照时阻断提交。

* StockList 合规检查
  检查报告中提到的公司是否在 StockList 内（见 StockList 合规检查）。

* RQC/首席审批
  所有报告必须经过首席审批。满足以下条件之一额外触发 RQC：首次覆盖、评级变动、目标价变动 ≥ 30%。审批不通过则退回 draft。

* 提交报告
  以上检查通过后，提交报告以待合规审核。

## 报告审批自动化流程

* 自动初筛
  系统自动检查合规风险点，有问题提示 SA。

* SA 人工判定
  合规责任由 SA 承担，最终判定必须由 SA 亲自做出，不可由 AI 代劳。不合规则 reject 报告，重新走报告编辑流程。

* 发布
  SA 判定合规后发布报告，状态改为 published。后台每日自动同步至 Neoport-DB。

## 报告标题规则

Company 报告标题根据评级变动场景自动生成：

| 场景 | 格式 | 示例 |
|------|------|------|
| 首次覆盖 | `{公司名} ({Ticker}): 首次覆盖: {标题}` | Vertiv (VRT US)：首次覆盖：报告标题 |
| 评级变动，目标价不变 | `{公司名} ({Ticker}): {标题}—{动作}{评级}` | Vertiv (VRT US)：报告标题—上调至优于大市 |
| 评级+目标价变动 | `{公司名} ({Ticker}): {标题}—{动作}{评级}; {TP动作}{TP变动}%` | Vertiv (VRT US)：报告标题—上调至优于大市; 上调目标价24% |
| 仅目标价变动 | `{公司名} ({Ticker}): {标题}—维持{评级}; {TP动作}{TP变动}%` | Vertiv (VRT US)：报告标题—维持优于大市; 上调目标价24% |
| 评级和目标价都不变 | `{公司名} ({Ticker}): {标题}—维持{评级}` | Vertiv (VRT US)：报告标题—维持优于大市 |
| 有英文版标题 | `公司中文简称 ({Ticker}): 中文标题—动作评级; TP动作 (English Title — Action & TP)` | 腾讯控股 (700 HK)：报告标题—上调至优于大市; 上调目标价24%（Tencent：English Title—Maintain OP & Raise TP by 24%） |

## 报告类型

| 报告类型 | 说明 | 模板 |
|---------|------|------|
| `company` | 公司覆盖报告（首次覆盖、深度分析等） | company |
| `sector` | 行业研究报告 | sector |
| `company_flash` | 公司快讯 | company_flash |
| `sector_flash` | 行业快讯 | sector_flash |
| `macro` | 宏观报告 | macro |
| `strategy` | 策略报告 | macro |
| `quantitative` | 量化报告 | macro |
| `bond` | 债券报告 | macro |

macro、strategy、quantitative、bond 共用 macro 模板。

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

## StockList 合规检查

分析师发布研报时，如果报告涉及的公司与分析师所在机构存在利益关系，有操纵市场嫌疑，不能发布。

StockList 记录机构与哪些公司存在利益关系。发布前必须检查报告中提到的所有公司是否在 StockList 内：
- 涉及上市公司：不能发布。
- 涉及非上市公司：可能不能发布（待与业务确认）。

xn 系统的处理方式：对报告脱敏后提取所有公司，匹配上市公司 code，生成 stock list 发给合规部门获取利益披露信息，有披露内容则贴到报告附录。

## SFC 牌照规则

- 报告署名分析师必须有 SFC 牌照，无 SFC 禁止发布。提交时自动检查，无 SFC 阻断提交。
- 从 SFC 官网（https://apps.sfc.hk/publicregWeb/searchByName）查询牌照信息并自动填充，遇重名等特殊情况与人确认。

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


