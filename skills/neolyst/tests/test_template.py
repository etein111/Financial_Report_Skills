"""
test_template.py — template 接口集成测试。
"""
import uuid
import pytest
from pathlib import Path

_SUFFIX = uuid.uuid4().hex[:8]
TEST_REPORT_TYPE = f"test_{_SUFFIX}"
TEST_LANGUAGE = "en"
TEMPLATE_ID = f"{TEST_REPORT_TYPE}_{TEST_LANGUAGE}"


@pytest.fixture(scope="module")
def tmp_template_files(tmp_path_factory):
    """创建最小化 docx 和 yaml 测试文件。"""
    d = tmp_path_factory.mktemp("template_fixtures")
    from docx import Document
    doc = Document()
    doc.add_paragraph("test template")
    tmpl = d / "template.docx"
    doc.save(str(tmpl))
    schema = d / "schema.yaml"
    schema.write_text("fields: []\n")
    return {"template": str(tmpl), "schema": str(schema)}


@pytest.fixture(scope="module")
def uploaded_template(neolyst_client, tmp_template_files):
    """上传测试模板，模块结束后清理。"""
    from skills.neolyst.scripts import template
    template.upsert_template(
        neolyst_client,
        report_type=TEST_REPORT_TYPE,
        language=TEST_LANGUAGE,
        template_local_path=tmp_template_files["template"],
        schema_local_path=tmp_template_files["schema"],
    )
    yield TEMPLATE_ID
    # 清理 storage
    resp = neolyst_client.rpc("get_template_storage_paths", {
        "p_report_type": TEST_REPORT_TYPE, "p_language": TEST_LANGUAGE,
    }).execute()
    if resp.data:
        paths = resp.data[0]
        for p in [paths["template_file_path"], paths["schema_file_path"]]:
            try:
                # storage_path 含 bucket 前缀，调用 API 前去掉
                neolyst_client.storage.from_("templates").remove([p.removeprefix("templates/")])
            except Exception:
                pass
    neolyst_client.table("report_template").delete().eq("id", TEMPLATE_ID).execute()


class TestUpsertTemplate:
    def test_record_has_server_computed_paths(self, neolyst_client, uploaded_template):
        resp = neolyst_client.table("report_template").select("*").eq("id", TEMPLATE_ID).execute()
        assert resp.data
        record = resp.data[0]
        assert record["template_file_path"] == f"templates/{TEST_REPORT_TYPE}/{TEST_LANGUAGE}/template.docx"
        assert record["schema_file_path"] == f"templates/{TEST_REPORT_TYPE}/{TEST_LANGUAGE}/schema.yaml"

    def test_upsert_is_idempotent(self, neolyst_client, uploaded_template, tmp_template_files):
        from skills.neolyst.scripts import template
        template.upsert_template(
            neolyst_client,
            report_type=TEST_REPORT_TYPE,
            language=TEST_LANGUAGE,
            template_local_path=tmp_template_files["template"],
            schema_local_path=tmp_template_files["schema"],
        )
        resp = neolyst_client.table("report_template").select("*").eq("id", TEMPLATE_ID).execute()
        assert len(resp.data) == 1


class TestReuseTemplate:
    def test_reuse_copies_paths(self, neolyst_client, uploaded_template):
        from skills.neolyst.scripts import template
        reuse_type = f"reuse_{_SUFFIX}"
        reuse_id = f"{reuse_type}_{TEST_LANGUAGE}"
        try:
            template.reuse_template(neolyst_client, reuse_type, TEST_LANGUAGE, TEST_REPORT_TYPE)
            resp = neolyst_client.table("report_template").select("*").eq("id", reuse_id).execute()
            assert resp.data
            assert resp.data[0]["template_file_path"] == f"templates/{TEST_REPORT_TYPE}/{TEST_LANGUAGE}/template.docx"
        finally:
            neolyst_client.table("report_template").delete().eq("id", reuse_id).execute()

    def test_reuse_self_raises(self, neolyst_client, uploaded_template):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="不能复用自身"):
            template.reuse_template(neolyst_client, TEST_REPORT_TYPE, TEST_LANGUAGE, TEST_REPORT_TYPE)

    def test_reuse_nonexistent_source_raises(self, neolyst_client):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="未找到"):
            template.reuse_template(neolyst_client, f"target_{_SUFFIX}", TEST_LANGUAGE, f"ghost_{_SUFFIX}")


class TestResolveTemplate:
    def test_resolve_downloads_files(self, neolyst_client, uploaded_template, tmp_path):
        from skills.neolyst.scripts import template
        result = template.resolve_template(
            neolyst_client, TEST_REPORT_TYPE, TEST_LANGUAGE, dest_dir=str(tmp_path)
        )
        assert Path(result["template_local_path"]).exists()
        assert result["schema_local_path"] and Path(result["schema_local_path"]).exists()

    def test_resolve_local_path_convention(self, neolyst_client, uploaded_template, tmp_path):
        from skills.neolyst.scripts import template
        result = template.resolve_template(
            neolyst_client, TEST_REPORT_TYPE, TEST_LANGUAGE, dest_dir=str(tmp_path)
        )
        expected = tmp_path / "templates" / TEST_REPORT_TYPE / TEST_LANGUAGE / "template.docx"
        assert result["template_local_path"] == str(expected)

    def test_resolve_unpublished_raises(self, neolyst_client):
        from skills.neolyst.scripts import template
        # 插入一条无路径的记录，测试 "not published" 分支
        empty_id = f"empty_{_SUFFIX}_en"
        neolyst_client.table("report_template").upsert({
            "id": empty_id,
            "report_type": f"empty_{_SUFFIX}",
            "language": "en",
            "template_file_path": "",
        }).execute()
        try:
            with pytest.raises(ValueError, match="not published"):
                template.resolve_template(neolyst_client, f"empty_{_SUFFIX}", "en")
        finally:
            neolyst_client.table("report_template").delete().eq("id", empty_id).execute()

    def test_resolve_nonexistent_raises(self, neolyst_client):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="not found"):
            template.resolve_template(neolyst_client, f"ghost_{_SUFFIX}", "en")
