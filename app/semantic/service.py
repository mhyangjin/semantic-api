from __future__ import annotations

from .repository import MetadataRepository
from .resolver import (
    MetadataResolver,
    ResolvedQuery,
)
from .models import DimensionFilterCondition
from .context import SemanticContext, build_semantic_context


class SemanticService:
    """
    Semantic Layer의 진입점.

    REST API,
    MCP Tool,
    SageMaker Agent가 모두 이 서비스를 호출한다.
    """

    def __init__(self, repository: MetadataRepository):
        self.repository = repository
        self.resolver = MetadataResolver(repository)

    #
    # =====================================================
    # Metadata ID 기반 조회
    # =====================================================
    #

    def resolve(
        self,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[DimensionFilterCondition] | None = None,
    ) -> ResolvedQuery:
        """
        이미 Metric ID와 Dimension ID가 전달된 경우.
        """

        return self.resolver.resolve(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
        )

    #
    # =====================================================
    # 자연어/Glossary 기반 조회
    # =====================================================
    #

    def resolve_terms(
        self,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[str] | None = None,
        analysis: list[str] | None = None,
        patterns: list[str] | None = None,
    ) -> ResolvedQuery:
        """
        사용자가 입력한 자연어를 해석한다.

        예)

        metrics=["성공률"]

        dimensions=["채널"]

        filters=["지난달"]
        """

        return self.resolver.resolve_terms(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            analysis=analysis,
            patterns=patterns,
        )

    def build_context(
        self,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[str] | None = None,
        analysis: list[str] | None = None,
        patterns: list[str] | None = None,
    ) -> SemanticContext:
        """Build a compact, self-contained context for a SQL agent."""

        resolved = self.resolve_terms(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            analysis=analysis,
            patterns=patterns,
        )
        return build_semantic_context(resolved)

    #
    # =====================================================
    # Pattern
    # =====================================================
    #

    def resolve_pattern(
        self,
        pattern: str,
    ):
        return self.resolver.resolve_pattern_objects(pattern)

    #
    # =====================================================
    # Analysis
    # =====================================================
    #

    def resolve_analysis(
        self,
        analysis: str,
    ):
        return self.resolver.resolve_analysis_objects(analysis)

    def get_metric(self, metric: str) :
        return self.resolver.resolve_metric(metric)

    def get_dimension(self, dimension: str) :
        return self.resolver.resolve_dimension(dimension)

    def get_table(self, table: str) :
        return self.resolver.resolve_table(table)

    def get_pattern(self, pattern: str) :
        return self.resolver.resolve_pattern_objects(pattern)
