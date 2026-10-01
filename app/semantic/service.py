from __future__ import annotations

from difflib import SequenceMatcher
import re

from .repository import MetadataRepository
from .resolver import (
    MetadataResolver,
    ResolvedQuery,
)
from .models import DimensionFilterCondition
from .context import (
    LiteralDimensionFilter,
    LiteralPredicate,
    SemanticContext,
    build_semantic_context,
)
from .value_resolver import resolve_literal_dimension_filters


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
        question: str | None = None,
        literal_filters: list[LiteralPredicate] | None = None,
    ) -> SemanticContext:
        """Build a compact, self-contained context for a SQL agent."""

        resolved_literal_filters = resolve_literal_dimension_filters(question)
        for literal_filter in literal_filters or []:
            resolved_literal_filters.extend(
                self._resolve_literal_predicate(literal_filter)
            )
        semantic_filters: list[str] = []
        for filter_term in filters or []:
            resolved_literals = resolve_literal_dimension_filters(filter_term)
            if not resolved_literals:
                if any(
                    filter_term.casefold() == literal.value.casefold()
                    for literal in resolved_literal_filters
                ):
                    continue
                semantic_filters.append(filter_term)
                continue
            for literal_filter in resolved_literals:
                if literal_filter not in resolved_literal_filters:
                    resolved_literal_filters.append(literal_filter)
        requested_dimensions = list(dimensions or [])
        for literal_filter in resolved_literal_filters:
            if literal_filter.business_name not in requested_dimensions:
                requested_dimensions.append(literal_filter.business_name)
        resolved = self.resolve_terms(
            metrics=metrics,
            dimensions=requested_dimensions,
            filters=semantic_filters,
            analysis=analysis,
            patterns=patterns,
        )
        context = build_semantic_context(resolved)
        context.literal_dimension_filters = [
            self._compile_literal_filter(item)
            for item in self._deduplicate_literal_filters(resolved_literal_filters)
        ]
        return context

    def _resolve_literal_predicate(
        self, predicate: LiteralPredicate
    ) -> list[LiteralDimensionFilter]:
        dimension = self.resolver.resolve_dimension_term(predicate.dimension)
        filters = [LiteralDimensionFilter(
            dimension=dimension.dimension_id,
            business_name=dimension.business_name,
            operator=predicate.operator,
            value=predicate.value,
            sql_value=predicate.value,
        )]
        if dimension.dimension_id == "request_error_reason":
            result_dimension = self.resolver.resolve_dimension("request_result")
            filters.insert(0, LiteralDimensionFilter(
                dimension=result_dimension.dimension_id,
                business_name=result_dimension.business_name,
                value="FAIL",
                sql_value="FAIL",
            ))
        return filters

    def _compile_literal_filter(
        self, literal_filter: LiteralDimensionFilter
    ) -> LiteralDimensionFilter:
        dimension = self.resolver.resolve_dimension(literal_filter.dimension)
        mappings = [mapping for mapping in dimension.mappings or [] if mapping.column]
        if len(mappings) != 1:
            raise ValueError(
                f"Literal dimension '{dimension.dimension_id}' must have exactly one "
                "column mapping."
            )
        mapping = mappings[0]
        prefix = mapping.pattern.prefix if mapping.pattern else None
        sql_value = literal_filter.value
        if prefix and not sql_value.upper().startswith(prefix.upper()):
            sql_value = f"{prefix}{sql_value}"
        escaped_value = sql_value.replace("'", "''")
        return literal_filter.model_copy(update={
            "business_name": dimension.business_name,
            "sql_value": sql_value,
            "table": mapping.table,
            "column": mapping.column,
            "sql_expression": (
                f'{{alias}}."{mapping.column}" '
                f"{literal_filter.operator} '{escaped_value}'"
            ),
        })

    @staticmethod
    def _deduplicate_literal_filters(
        literal_filters: list[LiteralDimensionFilter],
    ) -> list[LiteralDimensionFilter]:
        result: list[LiteralDimensionFilter] = []
        seen: set[tuple[str, str, str]] = set()
        for item in literal_filters:
            key = (item.dimension, item.operator, item.value)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

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
