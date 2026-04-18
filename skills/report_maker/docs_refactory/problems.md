
• 结论
  skills/report_maker 现在不是一个“设计稳定后的小系统”，而是一个正在从“本地模板 + 本地路由”迁向“neolyst 运行时模板 + draft 提
  交”的过渡系统。代码里最危险的不是单点 bug，而是“协议、文档、测试、运行边界”四套事实没有对齐。

  本次结论基于静态阅读 docs/draft、skills/report_maker/scripts、skills/report_maker/tests；未执行全量测试。

  模块图

  - 抽取层：skills/report_maker/scripts/extractor.py、skills/report_maker/scripts/field_extractor.py、skills/report_maker/
    scripts/splitter.py
  - 渲染层：skills/report_maker/scripts/renderer.py 调度 skills/report_maker/scripts/composer.py、skills/report_maker/scripts/
    content_inserter.py、skills/report_maker/scripts/sectpr_manager.py、skills/report_maker/scripts/image_handler.py、skills/
    report_maker/scripts/post_processor.py、skills/report_maker/scripts/chart_generator.py
  - 基础设施层：skills/report_maker/scripts/common.py、skills/report_maker/scripts/docx_reader.py、skills/report_maker/scripts/
    context.py
  - 外部系统边界：skills/report_maker/scripts/neolyst_integration.py、skills/report_maker/scripts/workflow.py

  高风险问题

  1. 分析师字段协议已经断裂。
     当前 schema 明确使用 a1_cn/a1_email/a1_en/a1_sfc 这套槽位，见 templates/company/schema.yaml:1。但
     resolve_analysts_from_elements() 读取的是 a1 到 a8，见 skills/report_maker/scripts/neolyst_integration.py:90。
     workflow.prepare_and_save_draft() 又把它当成硬前置条件，见 skills/report_maker/scripts/workflow.py:81 和 skills/
     report_maker/scripts/workflow.py:83。按当前 schema 走提交流程，极大概率会直接报“未找到有效的分析师”。
  2. investment_thesis 的来源实现是错的。
     elements 初始化时把 abstract 设成文件名 abstract.docx，见 skills/report_maker/scripts/common.py:371 和 skills/
     report_maker/scripts/common.py:385。但 map_elements_to_draft() 直接拿 elements["abstract"] 去压缩生成 investment_thesis，
     见 skills/report_maker/scripts/neolyst_integration.py:233。文档要求它来自“报告摘要文本”，见 docs/draft/
     skills_neolyst_integration.md:92。现在实际保存到 Neolyst 的很可能只是 "abstract.docx" 或它的截断版本。
  3. 运行时模板来源仍然是“双事实源”。
     文档已经明确运行时应只走 resolve_template()，不再依赖 router.yaml，见 docs/draft/skills_neolyst_integration.md:62。但代码
     保留并继续使用 get_template_name()，见 skills/report_maker/scripts/common.py:200，集成测试还在断言这条老路径，见 skills/
     report_maker/tests/integration/test_report_workflow.py:71。这说明迁移没有真正收口，后续任何“模板解析”变更都可能出现文档改
     了、测试还绿、运行却分叉的情况。
  4. “第二阶段刷新 source: market”只存在于设计，不存在于当前主实现。
     设计稿要求这些字段第一阶段允许为空，第二阶段按 ticker 刷新，见 docs/draft/skills_report_maker_design.md:101 和 docs/draft/
     skills_report_maker_design.md:185。但当前代码仍在第一阶段从草稿里直接抽 current_price/current_price_date/...，见 skills/
     report_maker/scripts/field_extractor.py:51、skills/report_maker/scripts/field_extractor.py:155、skills/report_maker/
     scripts/field_extractor.py:168。而渲染阶段并没有 refresh_market_data() 这条业务链，只有图表生成，见 skills/report_maker/
     scripts/renderer.py:45。这不是文档小过期，而是业务口径根本没落地。
  5. 图表方案也处于“设计一套、实现另一套”。
     增量设计说第一版只做 stock_price_chart，不做 recommendation_chart，见 docs/draft/
     skills_report_maker_design_increment_2026-04-02.md:115 和 docs/draft/skills_report_maker_design_increment_2026-04-
     02.md:165。但当前实现明确生成 relative_chart 和 recommendation_chart，见 skills/report_maker/scripts/renderer.py:45、
     skills/report_maker/scripts/renderer.py:46、skills/report_maker/scripts/renderer.py:153，schema 里也已经把它们当正式字段，
     见 templates/company/schema.yaml:93。这会直接误导后续开发和模板制作。

  结构性问题

     skills/report_maker/scripts/extractor.py:14、skills/report_maker/scripts/splitter.py:18、skills/report_maker/scripts/
     renderer.py:21 都在改 sys.path。测试也只能跟着绕，见 skills/report_maker/tests/conftest.py:9 和 skills/report_maker/tests/
     integration/test_report_workflow.py:22。这说明模块不是“可正常导入的包”，而是“在当前仓库布局下勉强能跑”。
  2. renderer.py 还是总编排热点。
     它虽然把细节拆给多个模块，但自己仍负责上下文、临时模板、图表并发、abstract/body/english_summary 插入、后处理、资源清理，见
     skills/report_maker/scripts/renderer.py:86。更关键的是临时文件只在成功路径清理，见 skills/report_maker/scripts/
     renderer.py:130 到 skills/report_maker/scripts/renderer.py:305。异常分支没有 finally，失败时会留下 temp_rendered.docx /
     temp_fixed_template.docx。
  3. 数据模型不统一。
     field_extractor 产出 analysts 的 JSON 字符串，见 skills/report_maker/scripts/field_extractor.py:437 和 skills/
     report_maker/scripts/field_extractor.py:492。context.prepare_context_with_analysts() 却只在它是 Python list 时才做
     analyst_display，见 skills/report_maker/scripts/context.py:125。这类“字段同名、类型不一致”的问题，在 report_maker 里不止一
     处。
  4. splitter.py 维护成本过高。
     当前单文件 1190 行，包含摘要、正文、英文摘要、附录、多种启发式提取、XML 页边距处理和多个辅助提取接口，见 skills/
     report_maker/scripts/splitter.py。它测试不少，但已经明显超出“单一职责模块”的健康边界。

  测试面判断

  - 文档处理内核的测试相对扎实：field_extractor/docx_reader/splitter/content_inserter/sectpr_manager/composer 都有独立测试文
    件。
  - 但 orchestration 边界基本没测到：没有 test_workflow.py，也没有 test_neolyst_integration.py。
  - 文档里写“84 个测试”，见 docs/draft/skills-report.md:142；当前 tests 目录按 def test_ 计数已远高于这个数字，说明文档早就失真
    了。

  优点

  1. 文档格式保真这条主线做得是认真的。
     docx_reader/splitter/composer/sectpr_manager/content_inserter 这一串都围绕 Word XML 真实问题设计，不是表面封装。
  2. 渲染内核已经从“一个大函数全做”迈向“入口 + 子模块”。
     renderer.py 仍大，但至少图表、内容插入、sectPr、图片、后处理都已经拆出独立文件。
  3. 测试重点放在最容易炸格式的地方，这是对的。
     相比很多只测业务字典的代码，这套测试更贴近真实失败面。

  优先级建议

  1. 先统一 elements 协议。
     明确只保留一套分析师字段格式，并同步修正 workflow/neolyst_integration/context/post_processor/field_extractor/schema。
  2. 再统一“运行时模板来源”。
     要么彻底切 resolve_template，删掉运行时 router.yaml 依赖；要么承认还没迁完，把文档改回混合态。
  3. 再决定“市场字段刷新”到底做不做。
     现在最糟的是设计按刷新说、代码按草稿提取写、测试几乎没约束。
  4. 最后再拆 splitter.py 和收掉 sys.path hack。
     这是工程卫生，但它依赖前面三件事先把事实源收口。