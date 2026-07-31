"""
MCP Tool Models

Semantic Layer MCP Tool의 Request / Response 모델 정의
"""

from typing import Any

from pydantic import BaseModel, Field


# ==========================================================
# Common
# ==========================================================

class FilterConditionResponse(BaseModel):
    dimension: str
    operator: str
    value: Any


# ==========================================================
# resolve_query
# ==========================================================

class ResolveQueryRequest(BaseModel):
    """
    자연어 또는 Glossary 용어를 이용한 Semantic Query 요청
    """

    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)

    analysis: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)


class ResolveQueryResponse(BaseModel):
    """
    Resolver가 해석한 최종 Metadata 결과
    """

    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)

    filters: list[FilterConditionResponse] = Field(
        default_factory=list
    )


# ==========================================================
# get_metric
# ==========================================================

class GetMetricRequest(BaseModel):
    metric: str


# ==========================================================
# get_dimension
# ==========================================================

class GetDimensionRequest(BaseModel):
    dimension: str


# ==========================================================
# get_table
# ==========================================================

class GetTableRequest(BaseModel):
    table: str


# ==========================================================
# get_pattern
# ==========================================================

class GetPatternRequest(BaseModel):
    pattern: str


# ==========================================================
# search_glossary
# ==========================================================

class SearchGlossaryRequest(BaseModel):
    term: str


class SearchGlossaryResponse(BaseModel):
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    analysis: list[str] = Field(default_factory=list)