"""
test_coverage.py — coverage 接口集成测试。
"""
import uuid
import pytest

_SUFFIX = uuid.uuid4().hex[:8]
TEST_TICKER = f"TEST{_SUFFIX[:4].upper()}"
TEST_ISIN = f"US{_SUFFIX.upper()[:10]}"


@pytest.fixture(scope="module")
def test_sector_id(neolyst_client):
    """获取第一个可用的 sector id（测试用）。"""
    resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    assert resp.data, "需要至少一条 sector 记录，请先运行 supabase db reset"
    return resp.data[0]["id"]


@pytest.fixture(scope="module")
def created_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    """
    创建测试用 coverage，模块结束后删除（coverage_analyst 随 coverage 级联删除）。
    """
    from skills.neolyst.scripts import coverage as cov
    coverage_id = cov.create_coverage(
        neolyst_client,
        ticker=TEST_TICKER,
        english_name="Test Coverage Company",
        sector_id=test_sector_id,
        isin=TEST_ISIN,
        country_of_domicile="China",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield coverage_id
    neolyst_client.table("coverage").delete().eq("id", coverage_id).execute()


class TestCreateCoverage:
    def test_create_success_returns_uuid(self, neolyst_client, created_coverage_id):
        """create_coverage 返回非空的 coverage_id uuid 字符串。"""
        assert created_coverage_id
        uuid.UUID(created_coverage_id)  # 格式校验：合法 UUID 不抛异常

    def test_create_coverage_record_exists(self, neolyst_client, created_coverage_id):
        """coverage 表中有对应记录，核心字段正确。"""
        resp = (
            neolyst_client.table("coverage")
            .select("*")
            .eq("id", created_coverage_id)
            .execute()
        )
        assert resp.data
        record = resp.data[0]
        assert record["english_name"] == "Test Coverage Company"
        assert record["country_of_domicile"] == "China"
        assert record["isin"] == TEST_ISIN.upper()

    def test_create_coverage_analyst_record_exists(self, neolyst_client, created_coverage_id, test_analyst_email):
        """coverage_analyst 表中有对应分析师记录，author_order=1。"""
        resp = (
            neolyst_client.table("coverage_analyst")
            .select("*")
            .eq("coverage_id", created_coverage_id)
            .execute()
        )
        assert len(resp.data) == 1
        assert resp.data[0]["analyst_email"] == test_analyst_email
        assert resp.data[0]["author_order"] == 1

    def test_create_duplicate_ticker_raises(self, neolyst_client, test_sector_id, created_coverage_id, test_analyst_email):
        """ticker 重复时抛出含"已存在"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="已存在"):
            cov.create_coverage(
                neolyst_client,
                ticker=TEST_TICKER,
                english_name="Duplicate Ticker Company",
                sector_id=test_sector_id,
                isin=f"US{uuid.uuid4().hex[:10].upper()}",
                country_of_domicile="China",
                analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
            )

    def test_create_duplicate_isin_raises(self, neolyst_client, test_sector_id, created_coverage_id, test_analyst_email):
        """ISIN 重复时抛出含"已存在"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="已存在"):
            cov.create_coverage(
                neolyst_client,
                ticker=f"DUP{uuid.uuid4().hex[:4].upper()}",
                english_name="Duplicate ISIN Company",
                sector_id=test_sector_id,
                isin=TEST_ISIN,
                country_of_domicile="China",
                analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
            )


class TestResolveCoverage:
    def test_resolve_found(self, neolyst_client, created_coverage_id, test_analyst_email):
        """ticker + 分析师匹配时返回正确的 coverage_id。"""
        from skills.neolyst.scripts import coverage as cov
        result = cov.resolve_coverage(neolyst_client, TEST_TICKER, test_analyst_email)
        assert result == created_coverage_id

    def test_resolve_case_insensitive_ticker(self, neolyst_client, created_coverage_id, test_analyst_email):
        """ticker 大小写不敏感，小写 ticker 同样命中。"""
        from skills.neolyst.scripts import coverage as cov
        result = cov.resolve_coverage(neolyst_client, TEST_TICKER.lower(), test_analyst_email)
        assert result == created_coverage_id

    def test_resolve_case_insensitive_email(self, neolyst_client, created_coverage_id, test_analyst_email):
        """analyst_email 大小写不敏感，大写 email 同样命中。"""
        from skills.neolyst.scripts import coverage as cov
        result = cov.resolve_coverage(neolyst_client, TEST_TICKER, test_analyst_email.upper())
        assert result == created_coverage_id

    def test_resolve_not_found_ticker_raises(self, neolyst_client, test_analyst_email):
        """ticker 不存在时抛出含"未找到"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="未找到"):
            cov.resolve_coverage(neolyst_client, "GHOST_TICKER_99", test_analyst_email)

    def test_resolve_analyst_not_in_coverage_raises(self, neolyst_client, created_coverage_id):
        """ticker 存在但分析师不在 coverage_analyst 列表中时抛出含"未找到"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="未找到"):
            cov.resolve_coverage(neolyst_client, TEST_TICKER, "nobody@example.com")


@pytest.fixture(scope="module")
def history_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    suffix = uuid.uuid4().hex[:6].upper()
    coverage_id = cov.create_coverage(
        neolyst_client,
        ticker=f"HIS{suffix}",
        english_name=f"History Coverage {suffix}",
        sector_id=test_sector_id,
        isin=f"US{suffix}{'0' * (10 - len(suffix))}",
        country_of_domicile="United States",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield coverage_id
    neolyst_client.table("coverage").delete().eq("id", coverage_id).execute()


@pytest.fixture(scope="module")
def history_dataset(neolyst_client, history_coverage_id, test_analyst_email):
    user = neolyst_client.auth.get_user().user
    ticker = f"HIS{uuid.uuid4().hex[:6].upper()}"

    neolyst_client.table("coverage").update({"ticker": ticker}).eq("id", history_coverage_id).execute()

    rows = [
        {
            "id": str(uuid.uuid4()),
            "title": "Newest Published Report",
            "report_type": "company",
            "status": "published",
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": ticker,
            "rating": "OUTPERFORM",
            "target_price": 120,
            "report_language": "en",
            "published_by": user.id,
            "published_at": "2026-04-09T08:00:00+00:00",
            "lead_analyst_email": test_analyst_email,
            "analyst_emails": [test_analyst_email],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Older Published Report",
            "report_type": "company",
            "status": "published",
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": ticker,
            "rating": "NEUTRAL",
            "target_price": 98,
            "report_language": "en",
            "published_by": user.id,
            "published_at": "2026-03-31T08:00:00+00:00",
            "lead_analyst_email": test_analyst_email,
            "analyst_emails": [test_analyst_email],
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Submitted Report Should Be Hidden",
            "report_type": "company",
            "status": "submitted",
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": ticker,
            "rating": "UNDERPERFORM",
            "target_price": 80,
            "report_language": "en",
            "published_at": None,
            "lead_analyst_email": test_analyst_email,
            "analyst_emails": [test_analyst_email],
        },
    ]
    neolyst_client.table("report").insert(rows).execute()
    yield {"ticker": ticker, "rows": rows}
    for row in rows:
        neolyst_client.table("report").delete().eq("id", row["id"]).execute()


class TestListCoverageHistory:
    def test_returns_only_published_rows(self, neolyst_client, history_dataset, test_analyst_email):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_dataset["ticker"],
            first_analyst_email=test_analyst_email,
        )
        assert len(result) == 2
        assert [r["title"] for r in result] == [
            "Newest Published Report",
            "Older Published Report",
        ]

    def test_returns_expected_five_fields(self, neolyst_client, history_dataset, test_analyst_email):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_dataset["ticker"],
            first_analyst_email=test_analyst_email,
        )
        assert set(result[0].keys()) == {
            "report_id",
            "title",
            "rating",
            "target_price",
            "published_at",
        }

    def test_case_insensitive_inputs(self, neolyst_client, history_dataset, test_analyst_email):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_dataset["ticker"].lower(),
            first_analyst_email=test_analyst_email.upper(),
        )
        assert result[0]["title"] == "Newest Published Report"

    def test_returns_empty_list_when_no_published_history(self, neolyst_client, created_coverage_id, test_analyst_email):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(neolyst_client, TEST_TICKER, test_analyst_email)
        assert result == []

    def test_missing_coverage_raises(self, neolyst_client, test_analyst_email):
        from skills.neolyst.scripts import coverage as cov

        with pytest.raises(ValueError, match="未找到匹配的 Coverage"):
            cov.list_coverage_history(neolyst_client, "GHOST_TICKER_99", test_analyst_email)
