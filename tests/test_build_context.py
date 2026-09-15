from app.semantic import create_service
from mcp_server.models import BuildContextRequest, SearchGlossaryRequest
from mcp_server.tools import build_context, search_glossary


def test_service_build_context_is_self_contained_and_compact() -> None:
    service = create_service("./metadata")

    context = service.build_context(
        metrics=["발송 성공률"],
        dimensions=["채널"],
    )

    assert [metric.metric_name for metric in context.metrics] == [
        "send_success_count",
        "request_count",
        "delivery_rate",
    ]
    assert [dimension.dimension_id for dimension in context.dimensions] == [
        "channel"
    ]
    assert {table.table_name for table in context.tables} == {
        "notification_status",
        "recipient",
        "notification_channels",
    }
    assert all(
        join.table in {selected.table_name for selected in context.tables}
        for table in context.tables
        for join in table.joins
    )


def test_mcp_build_context_demo() -> None:
    result = build_context(
        BuildContextRequest(metrics=["발송 성공 건수"], dimensions=["채널"])
    )

    assert result["dialect"] == "athena"
    assert result["metrics"][0]["metric_name"] == "send_success_count"
    assert result["dimensions"][0]["dimension_id"] == "channel"


def test_date_filter_always_uses_notification_request_kst_date() -> None:
    result = build_context(
        BuildContextRequest(
            metrics=["발송 성공 건수"],
            filters=["LMS", "최근 7일"],
        )
    )

    dimensions = {
        dimension["dimension_id"]: dimension
        for dimension in result["dimensions"]
    }
    request_date = dimensions["request_date"]

    assert "YYYY-MM-DD" in request_date["description"]
    assert "CAST(... AS varchar)" in request_date["description"]
    assert request_date["mappings"] == [
        {
            "table": "notification",
            "column": "request_kst_date",
        }
    ]
    assert {table["table_name"] for table in result["tables"]} == {
        "notification_status",
        "notification_channels",
        "notification",
    }
    assert {
        (condition["dimension"], condition["value"])
        for condition in result["filters"]
    } == {
        ("channel", "LMS"),
        ("request_date", "last_7_days"),
    }


def test_search_glossary_returns_canonical_cross_category_candidates() -> None:
    result = search_glossary(
        SearchGlossaryRequest(term="발송 요청 집계", limit=3)
    )

    assert "발송 건수" in result.metrics
    assert "발송 성과 분석" in result.analysis


def test_search_glossary_returns_filter_alias_as_canonical_term() -> None:
    result = search_glossary(SearchGlossaryRequest(term="지난주"))

    assert result.filters[0] == "지난 주"


def test_search_glossary_returns_short_metric_aliases_as_canonical_terms() -> None:
    assert search_glossary(
        SearchGlossaryRequest(term="요청수")
    ).metrics[0] == "발송 건수"
    assert search_glossary(
        SearchGlossaryRequest(term="성공수")
    ).metrics[0] == "발송 성공 건수"


def test_search_glossary_resolves_customer_number_alias() -> None:
    assert search_glossary(
        SearchGlossaryRequest(term="고객번호")
    ).dimensions[0] == "고객"


def test_customer_dimension_context_contains_compiled_athena_expressions() -> None:
    result = build_context(BuildContextRequest(dimensions=["고객"]))
    mappings = result["dimensions"][0]["mappings"]

    assert mappings[0]["sql_expression"] == (
        "from_utf8(from_base64({alias}.customer_id))"
    )
    assert mappings[1]["sql_expression"] == (
        "from_utf8(from_base64(split_part({alias}.custom_message_id, '.', 1)))"
    )


def test_previous_week_and_month_filters_contain_athena_expressions() -> None:
    previous_week = build_context(BuildContextRequest(filters=["지난 주"]))
    previous_month = build_context(BuildContextRequest(filters=["지난 달"]))

    week_sql = previous_week["filters"][0]["sql_expression"]
    month_sql = previous_month["filters"][0]["sql_expression"]
    assert "date_add('week', -1, date_trunc('week'" in week_sql
    assert "{alias}.request_kst_date" in week_sql
    assert "date_add('month', -1, date_trunc('month'" in month_sql
    assert "{alias}.request_kst_date" in month_sql
