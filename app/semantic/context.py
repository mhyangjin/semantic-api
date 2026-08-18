"""Compact Semantic Layer context consumed by SQL generation agents."""

from __future__ import annotations

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


class ContextTable(BaseModel):
    table_name: str
    columns: list[dict[str, Any]] = Field(default_factory=list)
    joins: list[Join] = Field(default_factory=list)


class SemanticContext(BaseModel):
    """All metadata required to generate SQL without follow-up lookups."""

    dialect: Literal["athena"] = "athena"
    metrics: list[BaseMetricModel | DerivedMetricModel] = Field(
        default_factory=list
    )
    dimensions: list[DimensionModel] = Field(default_factory=list)
    tables: list[ContextTable] = Field(default_factory=list)
    filters: list[DimensionFilterCondition] = Field(default_factory=list)


def build_semantic_context(resolved: ResolvedQuery) -> SemanticContext:
    """Convert resolver output into a compact context with relevant joins only."""

    selected_tables = {table.table_name for table in resolved.tables}
    tables = [
        _compact_table(table, selected_tables)
        for table in resolved.tables
    ]

    return SemanticContext(
        metrics=resolved.metrics,
        dimensions=resolved.dimensions,
        tables=tables,
        filters=resolved.filters,
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
