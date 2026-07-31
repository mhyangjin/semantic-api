"""
MCP Tools

Semantic Layer Tool 정의
"""

from __future__ import annotations

from fastmcp import FastMCP

from app.semantic import create_service

from .models import (
    ResolveQueryRequest,
    ResolveQueryResponse,
    FilterConditionResponse,
    GetMetricRequest,
    GetDimensionRequest,
    GetTableRequest,
    GetPatternRequest,
)

# ==========================================================
# Service
# ==========================================================

service = create_service("./metadata")

mcp = FastMCP("Semantic Layer")


# ==========================================================
# resolve_semantics
# ==========================================================

@mcp.tool(
    name="resolve_semantics",
    description="""
Resolve business terms into Semantic Layer metadata.

Always call this tool before generating SQL.

Input may contain:

- business metric names
- glossary terms
- analysis names
- patterns
- filter terms

The tool returns resolved metrics,
dimensions,
tables and filters.
"""
)
def resolve_semantics(
    request: ResolveQueryRequest,
) -> ResolveQueryResponse:

    result = service.resolve_terms(
        metrics=request.metrics,
        dimensions=request.dimensions,
        filters=request.filters,
        analysis=request.analysis,
        patterns=request.patterns,
    )

    return ResolveQueryResponse(
        metrics=[
            metric.metric_name
            for metric in result.metrics
        ],
        dimensions=[
            dimension.dimension_id
            for dimension in result.dimensions
        ],
        tables=[
            table.table_name
            for table in result.tables
        ],
        filters=[
            FilterConditionResponse(
                dimension=f.dimension,
                operator=f.operator,
                value=f.value,
            )
            for f in result.filters
        ],
    )


# ==========================================================
# get_metric
# ==========================================================

@mcp.tool(
    description="Return metadata for a metric."
)
def get_metric(
    request: GetMetricRequest,
):
    metric = service.get_metric(
            request.metric
    )

    return metric.model_dump()


# ==========================================================
# get_dimension
# ==========================================================

@mcp.tool(
    description="Return metadata for a dimension."
)
def get_dimension(
    request: GetDimensionRequest,
):

    dimension = service.get_dimension(
        request.dimension
    )

    return dimension.model_dump()


# ==========================================================
# get_table
# ==========================================================

@mcp.tool(
    description="Return metadata for a table."
)
def get_table(
    request: GetTableRequest,
):

    table = service.get_table(
        request.table
    )

    return table.model_dump()


# ==========================================================
# get_pattern
# ==========================================================

@mcp.tool(
    description="Return resolved metadata for an analysis pattern."
)
def get_pattern(
    request: GetPatternRequest,
):

    pattern = service.service.get_pattern(
    request.pattern)

    return {
        "pattern": pattern.pattern.model_dump(),
        "metrics": [
            metric.metric_name
            for metric in pattern.metrics
        ],
        "dimensions": [
            dimension.dimension_id
            for dimension in pattern.dimensions
        ],
        "tables": [
            table.table_name
            for table in pattern.tables
        ],
        "filters": [
            f.model_dump()
            for f in pattern.filters
        ],
    }