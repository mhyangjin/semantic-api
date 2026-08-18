from app.semantic import create_service
from mcp_server.models import BuildContextRequest
from mcp_server.tools import build_context


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
