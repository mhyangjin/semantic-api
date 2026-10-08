"""Compact Semantic Layer context consumed by SQL generation agents."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import (
    BaseMetricModel,
    DerivedMetricModel,
    DimensionFilterCondition,
    DimensionModel,
    Join,
    TableModel,
)
from .resolver import ResolvedQuery


def _athena_resolver_expression(mapping) -> str | None:
    """Compile a dimension resolver pipeline into an agent-ready Athena expression."""

    resolver = mapping.resolver or {}
    column = resolver.get("column")
    if not column:
        return None
    expression = f"{{alias}}.{column}"
    for step in resolver.get("pipeline") or []:
        if "split" in step:
            options = step["split"] or {}
            delimiter = str(options.get("delimiter", ".")).replace("'", "''")
            index = int(options.get("index", 0)) + 1
            expression = f"split_part({expression}, '{delimiter}', {index})"
        elif "base64_decode" in step:
            expression = f"from_utf8(from_base64({expression}))"
        else:
            return None
    return expression


def _athena_filter_expression(condition: DimensionFilterCondition) -> str | None:
    """Compile semantic relative-date values into complete Athena predicates."""

    if condition.dimension != "request_date":
        return None
    if isinstance(condition.value, str) and condition.value.startswith("date_range:"):
        value = condition.value.removeprefix("date_range:")
        match = re.fullmatch(
            r"(\d{4}-\d{2}-\d{2}|오늘|금일|어제|전일)\s*부터\s*"
            r"(\d{4}-\d{2}-\d{2}|오늘|금일|어제|전일)\s*까지",
            value,
        )
        if not match:
            raise ValueError(f"Invalid date range: {value}")
        start, end = match.groups()
        today = "CAST(current_timestamp AT TIME ZONE 'Asia/Seoul' AS date)"

        def date_expression(token: str) -> str:
            if token in {"오늘", "금일"}:
                return today
            if token in {"어제", "전일"}:
                return f"date_add('day', -1, {today})"
            try:
                date.fromisoformat(token)
            except ValueError as exc:
                raise ValueError(f"Invalid date in range: {token}") from exc
            return f"DATE '{token}'"

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", end
        ) and date.fromisoformat(start) > date.fromisoformat(end):
            raise ValueError(f"Date range start must not be after end: {value}")
        lower = date_expression(start)
        upper = f"date_add('day', 1, {date_expression(end)})"
        return (
            f"{{alias}}.request_kst_date >= CAST({lower} AS varchar) "
            f"AND {{alias}}.request_kst_date < CAST({upper} AS varchar)"
        )
    week_start = (
        "date_trunc('week', current_timestamp AT TIME ZONE 'Asia/Seoul')"
    )
    month_start = (
        "date_trunc('month', current_timestamp AT TIME ZONE 'Asia/Seoul')"
    )
    ranges = {
        "previous_week": (
            f"date_add('week', -1, {week_start})",
            week_start,
        ),
        "previous_month": (
            f"date_add('month', -1, {month_start})",
            month_start,
        ),
    }
    boundaries = ranges.get(condition.value)
    if not boundaries:
        return None
    lower, upper = boundaries
    return (
        f"{{alias}}.request_kst_date >= CAST(CAST({lower} AS date) AS varchar) "
        f"AND {{alias}}.request_kst_date < "
        f"CAST(CAST({upper} AS date) AS varchar)"
    )


class ContextTable(BaseModel):
    table_name: str
    columns: list[dict[str, Any]] = Field(default_factory=list)
    joins: list[Join] = Field(default_factory=list)


class LiteralDimensionFilter(BaseModel):
    dimension: str
    business_name: str
    operator: Literal["="] = "="
    value: str
    sql_value: str
    table: str | None = None
    column: str | None = None
    sql_expression: str | None = None


class LiteralPredicate(BaseModel):
    """Typed raw value that must never pass through glossary resolution."""

    dimension: str
    operator: Literal["="] = "="
    value: str = Field(min_length=1)


class SemanticContext(BaseModel):
    """All metadata required to generate SQL without follow-up lookups."""

    dialect: Literal["athena"] = "athena"
    metrics: list[BaseMetricModel | DerivedMetricModel] = Field(
        default_factory=list
    )
    dimensions: list[DimensionModel] = Field(default_factory=list)
    tables: list[ContextTable] = Field(default_factory=list)
    filters: list[DimensionFilterCondition] = Field(default_factory=list)
    literal_dimension_filters: list[LiteralDimensionFilter] = Field(
        default_factory=list
    )


def build_semantic_context(resolved: ResolvedQuery) -> SemanticContext:
    """Convert resolver output into a compact context with relevant joins only."""

    selected_tables = {table.table_name for table in resolved.tables}
    tables = [
        _compact_table(table, selected_tables)
        for table in resolved.tables
    ]

    dimensions = [dimension.model_copy(deep=True) for dimension in resolved.dimensions]
    for dimension in dimensions:
        for mapping in dimension.mappings or []:
            mapping.sql_expression = _athena_resolver_expression(mapping)

    filters = [condition.model_copy(deep=True) for condition in resolved.filters]
    for condition in filters:
        condition.sql_expression = _athena_filter_expression(condition)

    return SemanticContext(
        metrics=resolved.metrics,
        dimensions=dimensions,
        tables=tables,
        filters=filters,
    )


def _compact_table(
    table: TableModel,
    selected_tables: set[str],
) -> ContextTable:
    joins = [
        join
        for join in table.joins or []
        if join.table in selected_tables
    ]
    columns = [
        column.model_dump(exclude_none=True)
        for column in table.columns or []
    ]
    return ContextTable(
        table_name=table.table_name,
        columns=columns,
        joins=joins,
    )
