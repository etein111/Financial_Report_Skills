
# 平台架构

## 子系统总览

* 企业微信前台
  面向分析师的协作入口，前台Agent负责
* Editor 工作台
  Editor与AI协作生产。自动根据模板生成报告，写入 Neolyst-DB。
* SA 工作台
  SA与AI协作审核。执行合规检查，确认后发布Neolyst-DB中的报告。
* Neolyst-DB
  内部核心数据库。存所有人员、权限、报告和审计信息。
* Neoport-DB
  外部数据库。只存发给客户看的最终版报告供客户查阅，以及其他客户服务数据。
* 独立发布进程
  搬运工。自动把Neolyst-DB中的已发布报告传送到Neoport-DB。
* Neolyst-Web
  内部网站，主要用于审计和辅助手工操作。
* Neoport-Web
  外部网站，Customer Portal,为客户提供查阅报告等服务。

## 子系统关系

```
 [SA]              [分析师]
   |                  |
   |                  v
   |             [企业微信前台]
   |                  |
   v                  v
[SA工作台]    [Editor工作台]
   |                  |
   |                  v
   +---------->[Neolyst-DB]  ------> [Neolyst-Web]
                     |
                     v
               [Neoport-DB] ---------> [Neoport-Web]
```

## 命名规则

* 子系统名称使用 PascalCase：`Neolyst`、`Neoport`、`Neoskills`、`Neospace`。
* 后缀 `DB` 全大写：`Neolyst-DB`、`Neoport-DB`。
* 后缀 `Web` 首字母大写：`Neolyst-Web`、`Neoport-Web`。
* Skill 名称使用 snake_case：`report_maker`、`template_maker`、`compliance`。

## 架构原则

### 内外分离

* 内部用户和外部用户分别管理。
* 内部数据和外部数据严格分离。
* 外部系统依赖内部系统，严禁反向依赖。

### 统一身份认证与权限

* 内部人员身份认证和权限统一由Neolyst-DB管理。
  不管使用网站还是工作台，都统一由Neolyst-DB来做身份验证和权限控制。
* 外部人员身份认证和权限统一由Neoport-DB管理。

## 子系统详述

### Neolyst-DB

* Supabase Auth 承担认证、数据访问与数据权限兜底。
* Supabase PostgREST + RLS
* Supabase Storage（模板/报告文件）

### Neoskills

* 独立 Skills 架构：每个 Skill 保持单一职责，通过事件和消息解耦.
* 自然语言编排流程 ：支持串行、并行、条件分支等执行模式
* 自然语言配置：通过自然语言对话修改配置文件。

#### report_maker skill

* 模板机制。通过自然语言或 YAML 配置即可新增模板或提取字段

#### Neolyst skill

* 一致性逻辑下沉到 Supabase：业务数据一致性、状态流转、关系维护通过Skills接口执行.

### Neospace

* Neospace通过独立可编排的Skills 实现报告的自动化编辑与审核等工作。
* 工作台仓库，Skills 的运行载体，负责人机协作，session流对接。

## 代码库划分

### Neolyst

* Neolyst-Web，主要用于应对监管合规检查。

### Neoport

* 外部发布系统仓库。
* Neoport-Web
* Neoport-DB
* Publish Worker 进程。

### Neoskills

* Neolyst-DB数据库：唯一事实源，所有数据库实例以此为准。
* 各种skills：Neolyst，report_maker, template_maker, compliance.

### Neospace

* Neospace。