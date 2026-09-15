from __future__ import annotations

from difflib import SequenceMatcher
import re

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

    def search_glossary(self, term: str, limit: int = 5) -> dict[str, list[str]]:
        """Alias를 포함해 입력과 유사한 canonical glossary 용어를 반환한다."""

        normalized_query = self._normalize_search_text(term)
        if not normalized_query:
            raise ValueError("Search term must not be empty.")

        sources = {
            "metrics": getattr(
                self.repository.get_metric_glossary(), "metrics", []
            ),
            "dimensions": getattr(
                self.repository.get_dimension_glossary(), "dimensions", []
            ),
            "filters": getattr(
                self.repository.get_filter_glossary(), "filters", []
            ),
            "analysis": getattr(
                self.repository.get_analysis_glossary(), "analysis", []
            ),
        }
        result = {
            category: self._rank_glossary_entries(
                normalized_query, entries, limit
            )
            for category, entries in sources.items()
        }
        result["patterns"] = self._rank_patterns(normalized_query, limit)
        return result

    @staticmethod
    def _normalize_search_text(value: str) -> str:
        return re.sub(r"\s+", "", value).casefold()

    @classmethod
    def _similarity(cls, query: str, candidate: str) -> float:
        normalized_candidate = cls._normalize_search_text(candidate)
        if not normalized_candidate:
            return 0.0
        if query == normalized_candidate:
            return 1.0
        ratio = SequenceMatcher(None, query, normalized_candidate).ratio()
        if query in normalized_candidate or normalized_candidate in query:
            ratio = max(ratio, 0.8)
        return ratio

    @classmethod
    def _rank_glossary_entries(
        cls, query: str, entries: list[object], limit: int
    ) -> list[str]:
        ranked: list[tuple[float, str]] = []
        for entry in entries:
            canonical = str(getattr(entry, "term", ""))
            candidates = [canonical, *(getattr(entry, "aliases", []) or [])]
            score = max(cls._similarity(query, value) for value in candidates)
            if score >= 0.35:
                ranked.append((score, canonical))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [canonical for _, canonical in ranked[:limit]]

    def _rank_patterns(self, query: str, limit: int) -> list[str]:
        ranked: list[tuple[float, str]] = []
        for pattern_id, pattern in self.repository.list_patterns().items():
            candidates = [pattern_id, pattern.business_name]
            score = max(self._similarity(query, value) for value in candidates)
            if score >= 0.35:
                ranked.append((score, pattern_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [pattern_id for _, pattern_id in ranked[:limit]]

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
