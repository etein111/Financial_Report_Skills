需要做一些设计上的调整：
主要解决所谓版本问题：文件编辑和审批工作分开。

1）report_analyst没必要有两个time，因为report_analyst本质上只是report的一个列表字段。
甚至可以考虑把这个表删了，report上加两个字段，一个是1作email，一个是所有作者email的列表。有助于简化整体结构，包括存储过程
2）report_status_log里要加一个json字段，保存report的元数据（包括分析师，包括文件路径）。

3）文件版本存储：在报告id目录下，文档类型目录report/model，时间目录（区分版本）
4）report_version表删除，代之以report_log表：report_id, word_file_path, pdf_file_path,create_by, created_at
    model_log表：report_id, model_file_path,create_by, created_at
    用file_log表替代？还是索性现在不要log表
    需要保存elements，abstract，body吗？
5）report表，删掉version，直接记录word_path和pdf_path
6）梳理一遍状态和权限。
   原则是只有在draft状态下才能修改report信息。
   文件可以随时保存？
