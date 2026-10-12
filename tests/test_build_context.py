from app.semantic import create_service
from app.semantic.models import DimensionModel
from app.semantic.value_resolver import resolve_literal_dimension_filters
from mcp_server.models import BuildContextRequest, SearchGlossaryRequest
from mcp_server.tools import build_context, search_glossary


def _literal_summary(result: dict) -> list[tuple[str, str, str, str]]:
    return [
        (item["dimension"], item["value"], item["table"], item["column"])
        for item in result["literal_dimension_filters"]
    ]


def test_literal_resolver_uses_dimension_metadata_without_code_changes() -> None:
    dimensions = {
        "campaign": DimensionModel.model_validate({
            "dimension_id": "campaign",
            "business_name": "캠페인",
            "literal_patterns": [{
                "regex": r"캠페인\s+([A-Za-z0-9_-]+)",
            }],
        }),
    }

    result = resolve_literal_dimension_filters("캠페인 autumn_2026", dimensions)

    assert [(item.dimension, item.value) for item in result] == [
        ("campaign", "autumn_2026")
    ]


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


def test_search_glossary_resolves_yesterday_through_today() -> None:
    result = search_glossary(
        SearchGlossaryRequest(term="어제부터 오늘까지")
    )

    assert result.filters[0] == "날짜 범위"


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


def test_search_glossary_resolves_message_and_notification_id() -> None:
    for term in ("메시지", "메세지", "notification_id"):
        assert search_glossary(
            SearchGlossaryRequest(term=term)
        ).dimensions[0] == "notification_id"


def test_build_context_requires_distinct_notification_id_only() -> None:
    for term in ("메시지", "메세지", "notification_id"):
        result = build_context(BuildContextRequest(dimensions=[term]))

        assert result["metrics"] == []
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0] == {
            "dimension_id": "notification_id",
            "business_name": "notification_id",
            "distinct": True,
            "mappings": [{
                "table": "notification",
                "column": "notification_id",
            }],
            "description": (
                "메시지 또는 notification_id 목록 조회에 사용한다. "
                "결과에는 notification_id 컬럼만 포함하고 반드시 SELECT DISTINCT로 "
                "중복을 제거한다. 다른 컬럼이나 집계값은 반환하지 않는다.\n"
            ),
        }
        assert [table["table_name"] for table in result["tables"]] == [
            "notification"
        ]


def test_build_context_resolves_metric_and_dimension_aliases() -> None:
    result = build_context(BuildContextRequest(
        metrics=["발송 성공한 수"],
        dimensions=["발송 일자"],
        filters=["지난주"],
    ))

    assert result["metrics"][0]["metric_name"] == "send_success_count"
    assert {item["dimension_id"] for item in result["dimensions"]} >= {
        "request_date"
    }
    assert result["filters"][0]["value"] == "previous_week"


def test_build_context_resolves_literal_organization_from_question() -> None:
    result = build_context(BuildContextRequest(
        metrics=["성공수"],
        filters=["어제"],
        question="어제 조직 sample_team_01의 성공수를 알려줘.",
    ))

    assert {item["dimension_id"] for item in result["dimensions"]} >= {
        "organization"
    }
    assert _literal_summary(result) == [(
        "organization", "sample_team_01", "notification_index", "index"
    )]
    assert result["literal_dimension_filters"][0]["sql_expression"] == (
        '{alias}."index" = \'OR#sample_team_01\''
    )


def test_build_context_preserves_literal_source_from_question() -> None:
    result = build_context(BuildContextRequest(
        metrics=["요청수", "성공수"],
        filters=["어제"],
        question="어제 발신지 FLARELANE에서 발송 요청한 요청수 와 성공수를 알려줘.",
    ))

    assert {item["metric_name"] for item in result["metrics"]} >= {
        "request_count",
        "send_success_count",
    }
    assert {item["dimension_id"] for item in result["dimensions"]} >= {
        "source"
    }
    assert {table["table_name"] for table in result["tables"]} >= {
        "notification_index"
    }
    assert _literal_summary(result) == [(
        "source", "FLARELANE", "notification_index", "index"
    )]


def test_build_context_accepts_source_alias_from_question() -> None:
    result = build_context(BuildContextRequest(
        metrics=["요청수", "성공수"],
        filters=["어제"],
        question="어제 발송지 FALRELANE에서 발송한 요청수와 성공수를 알려줘.",
    ))

    assert _literal_summary(result) == [(
        "source", "FALRELANE", "notification_index", "index"
    )]


def test_build_context_accepts_literal_source_passed_as_filter() -> None:
    result = build_context(BuildContextRequest(
        metrics=["요청수", "성공수"],
        filters=["어제", "발신지 FALRELANE"],
        question="어제 발신지 FALRELANE에서 발송한 요청수와 성공수를 알려줘.",
    ))

    assert _literal_summary(result) == [(
        "source", "FALRELANE", "notification_index", "index"
    )]
    assert all(
        condition["value"] != "FALRELANE"
        for condition in result["filters"]
    )


def test_build_context_compiles_request_error_message_on_notification_index() -> None:
    result = build_context(BuildContextRequest(
        metrics=["요청수"],
        dimensions=["고객 번호"],
        filters=["어제", "contact_excluded"],
        question=(
            "어제 발신지 FLARELANE에서 발송한 메세지 중 요청 에러 메세지가 "
            "contact_excluded 인 고객 번호 1건만 알려줘."
        ),
    ))

    dimensions = {
        item["dimension_id"]: item for item in result["dimensions"]
    }
    assert dimensions["request_result"]["mappings"] == [{
        "table": "notification_status",
        "column": "result",
    }]
    assert dimensions["request_error_reason"]["mappings"] == [{
        "table": "notification_status",
        "column": "error_message",
    }]
    assert _literal_summary(result) == [
        ("source", "FLARELANE", "notification_index", "index"),
        ("request_result", "FAIL", "notification_status", "result"),
        (
            "request_error_reason",
            "contact_excluded",
            "notification_status",
            "error_message",
        ),
    ]


def test_build_context_accepts_typed_literal_predicates() -> None:
    result = build_context(BuildContextRequest(
        metrics=["요청수"],
        dimensions=["고객 번호"],
        filters=["어제"],
        literal_filters=[
            {"dimension": "source", "operator": "=", "value": "FLARELANE"},
            {
                "dimension": "request_error_reason",
                "operator": "=",
                "value": "contact_excluded",
            },
        ],
    ))

    assert _literal_summary(result) == [
        ("source", "FLARELANE", "notification_index", "index"),
        ("request_result", "FAIL", "notification_status", "result"),
        (
            "request_error_reason",
            "contact_excluded",
            "notification_status",
            "error_message",
        ),
    ]
    assert [
        item["sql_expression"] for item in result["literal_dimension_filters"]
    ] == [
        '{alias}."index" = \'SOURCE:FLARELANE\'',
        '{alias}."result" = \'FAIL\'',
        '{alias}."error_message" = \'contact_excluded\'',
    ]


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


def test_yesterday_through_today_filter_contains_safe_athena_expression() -> None:
    result = build_context(BuildContextRequest(
        dimensions=["notification_id"],
        filters=["어제부터 오늘까지", "발송 실패"],
        question=(
            "어제부터 오늘까지 발송 실패한 메세지 중에서 "
            "에러코드가 888인 notification_id를 찾아."
        ),
    ))

    filters = {
        item["value"]: item
        for item in result["filters"]
    }
    date_filter = filters["date_range:어제부터 오늘까지"]
    assert date_filter["dimension"] == "request_date"
    assert date_filter["operator"] == "between"
    assert "date_add('day', -1" in date_filter["sql_expression"]
    assert "date_add('day', 1" in date_filter["sql_expression"]
    assert result["dimensions"][0]["dimension_id"] == "notification_id"
    assert result["dimensions"][0]["distinct"] is True
    assert _literal_summary(result) == [(
        "request_error_code", "888", "notification_status", "error_code"
    )]
    assert result["literal_dimension_filters"][0]["sql_expression"] == (
        '{alias}."error_code" = \'888\''
    )


def test_explicit_date_range_contains_safe_athena_expression() -> None:
    result = build_context(BuildContextRequest(
        metrics=["발송 요청 수"],
        filters=["2026-09-01부터 2026-09-07까지"],
    ))

    assert result["filters"][0]["value"] == (
        "date_range:2026-09-01부터 2026-09-07까지"
    )
    assert result["filters"][0]["sql_expression"] == (
        "{alias}.request_kst_date >= CAST(DATE '2026-09-01' AS varchar) "
        "AND {alias}.request_kst_date < "
        "CAST(date_add('day', 1, DATE '2026-09-07') AS varchar)"
    )
