# Agent Req

## 目标与定位

工作台的自动化逻辑，实现AI自动编辑和审核的工作，包括：研报模板的自动刷新，自动翻译，评级变动需要主管审,以及各种合规检查，诸如stocklist等。

尽量把逻辑拆成独立Agent Skills的方式实现，即把各种自动化逻辑分类成不同的skill，彼此相对独立，通过流程编排进行触发，编排要可以修改定制。

## 报告类型

系统支持以下报告类型（全部使用小写）：

| 报告类型 | 说明 |
|---------|------|
| `company` | 公司覆盖报告（首次覆盖、深度分析等） |
| `sector` | 行业研究报告 |
| `company_flash` | 公司快讯报告 |
| `sector_flash` | 行业快讯报告 |
| `macro` | 宏观报告（通常共用 common 模板） |
| `strategy` | 策略报告（通常共用 common 模板） |
| `quantitative` | 量化报告（通常共用 common 模板） |
| `bond` | 债券报告（通常共用 common 模板） |

**注意**：`macro`、`strategy`、`quantitative`、`bond` 四种报告类型通常共用 `common` 模板。

## Capabilities

### 检查报告基本信息

- 检查报告类型（`company`、`sector`、`macro`、`strategy`、`quantitative`、`bond`、`company_flash`、`sector_flash`）所需的字段是否都填了。
- 自动从原始报告提取要素，要素如果不齐，需要提示补齐。

#### 报告字段矩阵（提交态必填）

提取字段示例如下：

- Ticker: 700 HK
- Rating: OUTPERFORM
- Target price：500
- Region: China
- Sector：Internet
- Report language:
- Report title：表格第6行1列
- Analystysts ：分析师名字、邮箱（多个分析师都要提取）
- Contact Person：工作台输入或neolyst选择
- Investment thesis：报告首页表格 第9行2列，可能第二页也有，需要人工干预
- Certificate（checkbox）：工作台确认？

### 检查文件是否齐全

- 所有的报告必须有word文件
- Company报告必须有Model文件。

### 检查报告里面的数据是否和model一致（优先级低）

- 工作台自动提取报告中的数据（比如盈利预测）是否和model完全一致，如果不一致要提示人修改。

### 检查文件相似度，防止提交错文件

- 可比对文件名相似度，与上一版最新文件名比对。主要是防止提交错文件，或确认是否是下载最新版本进行修改，以防中间版本修改内容丢失
- 文件相似度阈值：相似度 <60% 提示。文件相似度对比用的一个算法叫1-莱茵斯坦距离/最大字符串长度，用最新上传文件对比上一个版本最新文件。

### 保存报告基本信息

- 自动从原始报告中提取要素。
- 缺少的要素与人沟通补齐。
- 自动在neolyst新建报告（草稿状态）。

### 检查Sector是否存在

- 如果不存在，提醒人。

### Sector选择及新建（优先级低）

- 分为一级行业，二级行业
- 系统已存在部分行业可供选择，如不满足分析师需要，可添加一级或二级行业，需分析师提供新建行业信息，如一级/二级、中/英文行业名称

### Coverage审批

- 检查报告的Coverage是否已经存在，不存在的话提示在neolyst里添加。

### Company报告标题自动生成

- 如首次覆盖：Vertiv (VRT US)：首次覆盖：报告标题xxxx。
- 如调整评级目标价未变动：Vertiv (VRT US)：报告标题xxxx—上调至优于大市
- 如调整评级目标价变动：Vertiv (VRT US)：报告标题xxxx—上调至优于大市; 上调目标价24%
- 如未调评级目标价变动：Vertiv (VRT US)：报告标题xxxx—维持优于大市; 上调目标价24%
- 如未调评级目标价未变动：Vertiv (VRT US)：报告标题xxxx—维持优于大市
- 如有英文版标题：公司中文简称 (VRT US)：报告中文标题—上调至优于大市; 上调目标价24%（Vertiv：英文标题—Maintain OP & Raise TP by 24%）

### StockList（优先级低）

- 识别报告内涉及所有公司，匹对code，生成stock list，发送给合规部门，等待合规部门回复excel，run disclosure生成披露，如有披露内容贴到报告附录中。
- 具体业务和操作步骤：先将报告做脱敏处理（隐藏报告中，评级、目标价、以及一些敏感词），再把报告发给大模型获取所有公司list，匹配code后（根据所有上市公司code匹配，未找到的code的为非上市公司），最终生成stock list发给合规，合规回复excel（利益披露信息），run disclosure生成披露文字，如有披露内容贴到报告附录中。

### 核对分析师与 SFC 署名

- 可从这个网址里查询SFC牌照：https://apps.sfc.hk/publicregWeb/searchByName
- 获取SFC牌照自动填充到report中。
- 遇重名等特殊情况，与人沟通确认
- 报告署名Analyst必须有SFC，否则禁止发布，最好是提交时自动检查，没有sfc不能submit，免得提交后不能发布最后还要终止重新上传。

### 提取报告摘要和正文

- 可以自动从word内容中提取报告的摘要和正文

### 生成股价图

- 在市场数据库中取出ticker的数据，生成股价图，用于生成报告。
- 股票走势图：最近一年股票收盘价 和 指数收盘价 的涨跌幅，股价图中数据为股票涨跌幅和对应市场的大盘涨跌幅走势图。按照起点为100来计算，如果一年前也就是走势图第一天的数据固定为100，第二天股票涨了10%，第二天的数据就是100+100*10%=110，以此类推计算一年的数据
- 股票Volume柱状图：股票的Volume数据刷新的柱状图

### 生成报告（先只做公司报告）

#### Company:

- 报告日期：表格[Table_Main]，第3行1列，无需数据库字段，填充数据为当前日期，格式：4 Feb 2026
- 公司+股票代码：表格[Table_Main]，第5行1列，coverage表english_full_name、chinese_short_name、ticker
  - 格式：中文报告：腾讯控股 Tencent Holdings(700 HK)，英文报告：Tencent Holdings(700 HK)，Ticker保存report表ticker字段, coverage表id关联保存到report表coverage_id
- 标题：表格[Table_Main]，第5行1列，report表title字段，填充数据由分析师输入，中文和英文换行区分
- 首页左侧数据：
  - 评级调整 ：表格[Table_Info]，第2行1列， 填充数据查询上一次报告Rating和本次Rating对比后的结果，无需数据库字段
  - 评级：表格[Table_Info]，第4行2列，填充数据为分析师输入，保存report表rating字段
  - 现价：表格[Table_Info]，第5行2列，填充数据股票最新收盘价，股票行情数据，无需保存到报告表
  - 目标价：表格[Table_Info]，第6行2列，填充数据为分析师输入，保存report表target price字段
  - 市值：表格[Table_Info]，第7行2列，填充数据获取股票行情数据，无需保存到报告表
  - 发行股票数目：表格[Table_Info]，第8行2列，填充数据获取股票行情数据，无需保存到报告表
  - 1年股价最高最低值：表格[Table_Info]，第9行2列，填充数据获取股票行情数据，无需保存到报告表
  - Note：Current Price 340.80 is the close price on 2 Feb 2026（固定格式说明现价的日期是哪一天），表格[Table_Info]，第10行1列，填充数据获取股票行情数据，无需保存到报告，格式如：Note：Current Price {close_price} is the close price on {date}
  - 股价行情走势图，表格[Table_Info]，第12行1列，填充数据从股票行情表和指数行情表获取数据画图，无需保存到报告表
  - 股票Volume柱状图，表格[Table_Info]，第13行1列，填充数据从股票行情表获取画图，无需保存到报告表
- 分析师 ：表格[Table_Author]，从第2行1列开始，填充数据依次为分析师, SFC编号，第3行1列为分析师邮箱，依次往后排列，超过4个往下一行，最多支持8个分析师，填充后如下：

![image.png](image.png)

- 页眉：表格[Table_header1]，第2行1列，填充数据Company + Code，和上面2是一样，第2行2列，填充数据为评级调整，和上面4一样，无需保存到报告
- 页脚：日期和页码自动刷新，不用管
- 附录（所有报告都一样），表格[Table_disclaimer]，第4行1列，无需保存到报告表
  - 数据填充查询报告的analyst，只需要更新Analyst Certification，固定文字，如下：
  - I, {analyst_name}, certify that (i) the views expressed in this research report accurately reflect my personal views about any or all of the subject companies or issuers referred to in this research and (ii) no part of my compensation was, is or will be directly or indirectly related to the specific recommendations or views expressed in this research report; and that I (including members of my household) have no financial interest in the security or securities of the subject companies discussed.
  - 只需要根据分析师名字，替换{analyst_name}占位符，多个分析师填充多行，最终效果如下：

![image.png](image.png)

- 股价推荐图，表格[Table_RecommendationChart]，第2行1列，无需保存到报告表，查询这个报告所关联的Coverage的历史Rating和target price，画一个股价走势图和最近3年内的Rating和TP记录，示例如下：

![29cf110d8c348f3d4be7fff38f39516b.png](29cf110d8c348f3d4be7fff38f39516b.png)

- 生成报告后自动上传neolyst。

### 报告提交

- 提交前做前置检查，包括RQC是否已经通过。首席是否通过，coverage是否存在，等等。
- 发起提交报告，工作台检查通过后，自动在neolyst将报告状态设为提交。



## 重要业务规则

### 报告标题生成

- **首次覆盖**：`{公司名} ({Ticker}): 首次覆盖: {标题}`
- **评级变动，目标价不变**：`{公司名} ({Ticker}): {标题}—{行动}{评级}`
- **评级 + 目标价变动**：`{公司名} ({Ticker}): {标题}—{行动}{评级}; {TP_行动}{TP_变动}%`
- **仅目标价变动**：`{公司名} ({Ticker}): {标题}—维持{评级}; {TP_行动}{TP_变动}%`

### 文件相似度检查

- 算法：`1 - (莱文斯坦距离 / 最大字符串长度)`
- 阈值：与上一版相比相似度 < 60% 时警告

### SFC 验证

- 分析师在提交报告前必须持有有效的 SFC 执照
- 查询来源：https://apps.sfc.hk/publicregWeb/searchByName

### RQC（研究质量委员会）触发条件

- 首次覆盖
- 评级变动
- 目标价变动 ≥ 30%
