from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    AnalysisGlossary,
    AnalysisPatternModel,
    BaseMetricModel,
    DerivedMetricModel,
    DimensionFilterCondition,
    DimensionModel,
    FilterGlossary,
    PatternFilterCondition,
    TableModel,
)
from .repository import MetadataRepository, MetricModel


# ==========================================================
# Resolved Models
# ==========================================================



@dataclass(slots=True, frozen=True)
class ResolvedMetric:
    """
    요청한 Metric과 해당 Metric이 참조하는 모든 하위 Metric.

    dependencies는 하위 Metric부터 상위 Metric 순서로 정렬된다.
    요청한 root metric 자체는 dependencies에 포함하지 않는다.

    예:
        success_rate
          ├─ success_count
          └─ request_count

        dependencies:
            [
                success_count,
                request_count,
            ]
    """

    metric: MetricModel
    dependencies: list[MetricModel]


@dataclass(slots=True, frozen=True)
class ResolvedPattern:
    """
    Analysis Pattern 내부 참조를 모두 해석한 결과.
    """

    pattern: AnalysisPatternModel
    metrics: list[MetricModel]
    dimensions: list[DimensionModel]
    tables: list[TableModel]
    filters: list[DimensionFilterCondition]


@dataclass(slots=True, frozen=True)
class ResolvedQuery:
    """
    REST API, MCP Adapter 또는 SQL 생성 Agent에 전달할
    최종 Semantic Metadata 객체.
    """

    metrics: list[MetricModel]
    dimensions: list[DimensionModel]
    tables: list[TableModel]
    filters: list[DimensionFilterCondition]


# ==========================================================
# Resolver
# ==========================================================


class MetadataResolver:
    """
    MetadataRepository에 저장된 메타데이터 참조 관계를 해석한다.

    주요 역할:
    - Metric, Dimension, Table, Pattern 조회
    - Derived Metric 의존성 재귀 해석
    - Dimension Mapping이 참조하는 Table 해석
    - Metric이 참조하는 Table 해석
    - Pattern 내부 Metric, Dimension, Filter 해석
    - Glossary 용어를 실제 Metadata 객체로 변환
    - REST API 및 MCP Adapter용 ResolvedQuery 생성
    """

    def __init__(self, repository: MetadataRepository):
        self.repo = repository

    # ======================================================
    # Basic Resolver
    # ======================================================

    def resolve_metric(self, name: str) -> MetricModel:
        """
        정규화된 metric_name으로 Metric을 조회한다.
        """

        normalized_name = self._normalize_name(name, "Metric")

        try:
            return self.repo.get_metric(normalized_name)
        except KeyError as exc:
            raise KeyError(
                f"Unknown metric: '{normalized_name}'."
            ) from exc

    def resolve_dimension(self, name: str) -> DimensionModel:
        """
        정규화된 dimension_id로 Dimension을 조회한다.
        """

        normalized_name = self._normalize_name(name, "Dimension")

        try:
            return self.repo.get_dimension(normalized_name)
        except KeyError as exc:
            raise KeyError(
                f"Unknown dimension: '{normalized_name}'."
            ) from exc

    def resolve_table(self, name: str) -> TableModel:
        """
        정규화된 table_name으로 Table을 조회한다.
        """

        normalized_name = self._normalize_name(name, "Table")

        try:
            return self.repo.get_table(normalized_name)
        except KeyError as exc:
            raise KeyError(
                f"Unknown table: '{normalized_name}'."
            ) from exc

    def resolve_pattern(self, name: str) -> AnalysisPatternModel:
        """
        정규화된 pattern_id로 Analysis Pattern을 조회한다.
        """

        normalized_name = self._normalize_name(
            name,
            "Analysis pattern",
        )

        try:
            return self.repo.get_pattern(normalized_name)
        except KeyError as exc:
            raise KeyError(
                f"Unknown analysis pattern: '{normalized_name}'."
            ) from exc

    # ======================================================
    # Glossary Resolver
    # ======================================================

    def resolve_metric_term(self, term: str) -> MetricModel:
        """
        사용자의 Metric 표현을 실제 MetricModel로 변환한다.

        다음 두 형식을 모두 지원한다.

        1. 실제 metric_name
           "success_rate"

        2. Glossary term 또는 alias
           "성공률"
           "발송 성공 비율"
        """

        normalized_term = self._normalize_term(term)

        if not normalized_term:
            raise ValueError("Metric term must not be empty.")

        # 실제 metric_name이 전달된 경우 먼저 직접 조회한다.
        try:
            return self.resolve_metric(term)
        except KeyError:
            pass

        glossary = self.repo.get_metric_glossary()

        entry = self._find_glossary_entry(
            term=term,
            glossary=glossary,
            collection_name="metrics",
            entity_name="metric",
        )

        metric_name = getattr(entry, "metric", None)

        if not metric_name:
            raise ValueError(
                f"Metric glossary term '{term}' does not define "
                "a metric target."
            )

        return self.resolve_metric(str(metric_name))

    def resolve_dimension_term(self, term: str) -> DimensionModel:
        """
        사용자의 Dimension 표현을 실제 DimensionModel로 변환한다.

        다음 두 형식을 모두 지원한다.

        1. 실제 dimension_id
           "channel"

        2. Glossary term 또는 alias
           "채널"
           "채널별"
        """

        normalized_term = self._normalize_term(term)

        if not normalized_term:
            raise ValueError("Dimension term must not be empty.")

        # 실제 dimension_id가 전달된 경우 먼저 직접 조회한다.
        try:
            return self.resolve_dimension(term)
        except KeyError:
            pass

        glossary = self.repo.get_dimension_glossary()

        entry = self._find_glossary_entry(
            term=term,
            glossary=glossary,
            collection_name="dimensions",
            entity_name="dimension",
        )

        dimension_name = getattr(entry, "dimension", None)

        if not dimension_name:
            raise ValueError(
                f"Dimension glossary term '{term}' does not define "
                "a dimension target."
            )

        return self.resolve_dimension(str(dimension_name))

    def resolve_filter_glossary(
        self,
        term: str,
    ) -> FilterGlossary:
        """
        사용자의 Filter 표현을 FilterGlossary 객체로 변환한다.

        예:
            "지난달"
            -> FilterGlossary(
                term="지난달",
                filters=[...]
            )
        """

        glossary = self.repo.get_filter_glossary()

        entry = self._find_glossary_entry(
            term=term,
            glossary=glossary,
            collection_name="filters",
            entity_name="filter",
        )

        if not isinstance(entry, FilterGlossary):
            raise TypeError(
                f"Filter glossary term '{term}' resolved to unsupported "
                f"type: {type(entry).__name__}."
            )

        return entry

    def resolve_filter_term(
        self,
        term: str,
    ) -> list[DimensionFilterCondition]:
        """
        사용자의 Filter 표현을 실제 Filter Condition 목록으로 변환한다.

        하나의 FilterGlossary는 여러 조건을 포함할 수 있으므로
        list[DimensionFilterCondition]을 반환한다.

        예:
            "지난달"
            -> [
                DimensionFilterCondition(
                    dimension="request_date",
                    operator="between",
                    value="previous_month",
                )
            ]
        """

        entry = self.resolve_filter_glossary(term)

        matched_pattern, extracted_value = self._match_filter_pattern(term, entry)

        if matched_pattern is None and self._entry_uses_pattern_value(entry):
            raise ValueError(
                f"Filter glossary term '{term}' requires a pattern match to "
                "extract a value, but no pattern matched."
            )

        resolved_filters: list[DimensionFilterCondition] = []

        for condition in entry.filters:
            resolved_value = condition.value

            if extracted_value is not None:
                resolved_value = self._substitute_pattern_value(
                    resolved_value,
                    extracted_value,
                )

            resolved_filters.append(
                condition.model_copy(
                    update={"value": resolved_value},
                    deep=True,
                )
            )

        return resolved_filters

    def resolve_analysis_term(
        self,
        term: str,
    ) -> AnalysisGlossary:
        """
        사용자의 분석 표현을 AnalysisGlossary 객체로 변환한다.

        현재 AnalysisGlossary 모델은 pattern_id를 참조하지 않고,
        분석에 필요한 metrics와 dimensions를 직접 정의한다.

        예:
            "발송 성과 분석"
            -> AnalysisGlossary(
                metrics=["request_count", "success_count"],
                dimensions=["channel"]
            )
        """

        glossary = self.repo.get_analysis_glossary()

        entry = self._find_glossary_entry(
            term=term,
            glossary=glossary,
            collection_name="analysis",
            entity_name="analysis",
        )

        if not isinstance(entry, AnalysisGlossary):
            raise TypeError(
                f"Analysis glossary term '{term}' resolved to unsupported "
                f"type: {type(entry).__name__}."
            )

        return entry

    # ======================================================
    # Metric Dependency Resolver
    # ======================================================

    def resolve_metric_dependencies(
        self,
        metric_name: str,
    ) -> list[MetricModel]:
        """
        Derived Metric이 참조하는 모든 Metric을 재귀적으로 해석한다.

        현재 DerivedMetricModel은 다음 Formula 구조를 사용한다.

            formula:
              numerator:
                metric: success_count
              denominator:
                metric: request_count

        반환 순서는 하위 Metric부터 상위 Metric 순서다.
        요청한 root metric은 결과에 포함되지 않는다.

        순환 참조가 발견되면 ValueError를 발생시킨다.
        """

        root_metric = self.resolve_metric(metric_name)

        if isinstance(root_metric, BaseMetricModel):
            return []

        if not isinstance(root_metric, DerivedMetricModel):
            raise TypeError(
                f"Unsupported metric model type for '{metric_name}': "
                f"{type(root_metric).__name__}."
            )

        resolved: list[MetricModel] = []
        visited: set[str] = set()
        visiting: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return

            if name in visiting:
                cycle_start = visiting.index(name)
                cycle = visiting[cycle_start:] + [name]

                raise ValueError(
                    "Circular metric dependency detected: "
                    + " -> ".join(cycle)
                )

            metric = self.resolve_metric(name)
            visiting.append(name)

            if isinstance(metric, DerivedMetricModel):
                for dependency_name in self._metric_dependency_names(
                    metric
                ):
                    visit(dependency_name)

            elif not isinstance(metric, BaseMetricModel):
                raise TypeError(
                    f"Unsupported metric model type for '{name}': "
                    f"{type(metric).__name__}."
                )

            visiting.pop()

            resolved.append(metric)
            visited.add(name)

        for dependency_name in self._metric_dependency_names(root_metric):
            visit(dependency_name)

        return resolved

    def resolve_metric_object(
        self,
        metric_name: str,
    ) -> ResolvedMetric:
        """
        Metric과 해당 Metric의 전체 의존성을 함께 반환한다.
        """

        return ResolvedMetric(
            metric=self.resolve_metric(metric_name),
            dependencies=self.resolve_metric_dependencies(metric_name),
        )

    # ======================================================
    # Dimension -> Table Resolver
    # ======================================================

    def resolve_dimension_tables(
        self,
        dimension_name: str,
    ) -> list[TableModel]:
        """
        Dimension의 모든 Mapping이 참조하는 Table을 반환한다.

        하나의 Dimension이 여러 테이블에 매핑될 수 있으므로
        list[TableModel]을 반환한다.

        동일한 테이블이 여러 Mapping에 존재해도 결과에는
        한 번만 포함한다.
        """

        dimension = self.resolve_dimension(dimension_name)
        mappings = dimension.mappings or []

        if not mappings:
            raise ValueError(
                f"Dimension '{dimension_name}' does not define mappings."
            )

        tables: list[TableModel] = []
        resolved_table_names: set[str] = set()

        for mapping in mappings:
            table_name = str(mapping.table)

            if table_name in resolved_table_names:
                continue

            table = self.resolve_table(table_name)

            resolved_table_names.add(table_name)
            tables.append(table)

        return tables

    def resolve_dimension_table(
        self,
        dimension_name: str,
    ) -> TableModel:
        """
        Dimension의 첫 번째 Mapping이 참조하는 Table을 반환한다.

        과거 단일 Table 기반 호출과의 호환성을 위한 메서드다.
        복수 Mapping을 처리해야 하는 경우에는
        resolve_dimension_tables()를 사용한다.
        """

        tables = self.resolve_dimension_tables(dimension_name)

        if not tables:
            raise ValueError(
                f"Dimension '{dimension_name}' does not reference a table."
            )

        return tables[0]

    # ======================================================
    # Pattern Resolver
    # ======================================================

    def resolve_pattern_objects(
        self,
        pattern_name: str,
    ) -> ResolvedPattern:
        """
        Analysis Pattern이 참조하는 Metric, Dimension, Table,
        Filter를 모두 실제 객체로 변환한다.
        """

        pattern = self.resolve_pattern(pattern_name)

        metric_names = self._deduplicate_strings(
            list(pattern.metrics)
        )
        dimension_names = self._deduplicate_strings(
            list(pattern.dimensions)
        )

        resolved_metrics = self._resolve_metrics(metric_names)

        dimensions = [
            self.resolve_dimension(dimension_name)
            for dimension_name in dimension_names
        ]

        filters = self._resolve_filter_terms(list(pattern.filters))

        tables = self._resolve_query_tables(
            metric_names=metric_names,
            dimension_names=dimension_names,
        )

        return ResolvedPattern(
            pattern=pattern,
            metrics=resolved_metrics,
            dimensions=dimensions,
            tables=tables,
            filters=filters,
        )

    def resolve_analysis_objects(
        self,
        term: str,
    ) -> ResolvedQuery:
        """
        Analysis Glossary 용어를 해석하고 해당 분석에 필요한
        Metric, Dimension, Table을 모두 반환한다.

        AnalysisGlossary는 Pattern을 참조하지 않고 metrics와
        dimensions를 직접 정의하므로 ResolvedQuery를 반환한다.
        """

        analysis = self.resolve_analysis_term(term)

        return self.resolve(
            metrics=list(analysis.metrics),
            dimensions=list(analysis.dimensions),
        )

    # ======================================================
    # Query Resolver
    # ======================================================

    def resolve(
        self,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[DimensionFilterCondition] | None = None,
    ) -> ResolvedQuery:
        """
        이미 정규화된 Metadata ID를 실제 객체로 변환한다.

        metrics에는 metric_name,
        dimensions에는 dimension_id를 전달한다.

        예:
            resolve(
                metrics=["success_rate"],
                dimensions=["channel"],
            )
        """

        metric_names = self._deduplicate_strings(metrics or [])
        dimension_names = self._deduplicate_strings(
            dimensions or []
        )

        resolved_metrics = self._resolve_metrics(metric_names)

        resolved_dimensions = [
            self.resolve_dimension(dimension_name)
            for dimension_name in dimension_names
        ]

        tables = self._resolve_query_tables(
            metric_names=metric_names,
            dimension_names=dimension_names,
        )

        return ResolvedQuery(
            metrics=resolved_metrics,
            dimensions=resolved_dimensions,
            tables=tables,
            filters=list(filters or []),
        )

    def resolve_terms(
        self,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        filters: list[str] | None = None,
        analysis: list[str] | None = None,
        patterns: list[str] | None = None
    ) -> ResolvedQuery:
        """
        사용자 자연어, Glossary 용어 또는 실제 Metadata ID를
        실제 객체로 변환한다.

        예:
            resolve_terms(
                metrics=["성공률"],
                dimensions=["채널"],
                filters=["지난달"],
            )
        """

        metric_terms = self._deduplicate_strings(metrics or [])
        dimension_terms = self._deduplicate_strings(dimensions or [])
        filter_terms = self._deduplicate_strings(filters or [])
        analysis_terms = self._deduplicate_strings(analysis or [])
        pattern_names = self._deduplicate_strings(patterns or [])

        # Analysis glossary가 참조하는 Metadata ID 추가
        for analysis_term in analysis_terms :
            analysis_object = self.resolve_analysis_term(analysis_term)
            metric_terms.extend(analysis_object.metrics)
            dimension_terms.extend(analysis_object.dimensions)

        # Pattern이 참조하는 Metadata ID와 Filter term 추가
        for pattern_name in pattern_names :
            pattern = self.resolve_pattern(pattern_name)
            metric_terms.extend(pattern.metrics)
            dimension_terms.extend(pattern.dimensions)
            filter_terms.extend(pattern.filters)

        metric_names = self._deduplicate_strings([
            self.resolve_metric_term(term).metric_name
            for term in metric_terms
        ])
        resolved_metrics = self._resolve_metrics(metric_names)

        resolved_dimensions = [
            self.resolve_dimension_term(term)
            for term in dimension_terms
        ]

        deduplicated_dimensions: list[DimensionModel] = []
        seen_dimension_names: set[str] = set()

        for dimension in resolved_dimensions:
            dimension_name = dimension.dimension_id

            if dimension_name in seen_dimension_names:
                continue

            seen_dimension_names.add(dimension_name)
            deduplicated_dimensions.append(dimension)

        resolved_filters = self._resolve_filter_terms(filter_terms)

        metric_names = [
            metric.metric_name
            for metric in resolved_metrics
        ]

        dimension_names = [
            dimension.dimension_id
            for dimension in deduplicated_dimensions
        ]

        tables = self._resolve_query_tables(
            metric_names=metric_names,
            dimension_names=dimension_names,
        )

        return ResolvedQuery(
                metrics=resolved_metrics,
                dimensions=deduplicated_dimensions,
                tables=tables,
                filters=resolved_filters,
        )

    def _resolve_metrics(
            self,
            metric_names: list[str],
    ) -> list[MetricModel] :
        resolved_metrics: list[MetricModel] = []
        seen_metric_names: set[str] = set()

        for metric_name in self._deduplicate_strings(metric_names) :
            metric_objects = [
                *self.resolve_metric_dependencies(metric_name),
                self.resolve_metric(metric_name),
            ]

            for metric in metric_objects :
                if metric.metric_name in seen_metric_names :
                    continue

                seen_metric_names.add(metric.metric_name)
                resolved_metrics.append(metric)

        return resolved_metrics

    def _resolve_filter_terms(
            self,
            filter_terms: list[str],
    ) -> list[DimensionFilterCondition] :
        resolved_filters: list[DimensionFilterCondition] = []
        seen_filters: set[tuple[str, str, str]] = set()

        for term in self._deduplicate_strings(filter_terms) :
            for condition in self.resolve_filter_term(term) :
                key = (
                    condition.dimension,
                    condition.operator,
                    repr(condition.value),
                )

                if key in seen_filters :
                    continue

                seen_filters.add(key)
                resolved_filters.append(condition)

        return resolved_filters
    # ======================================================
    # Internal: Table Resolver
    # ======================================================

    def _resolve_query_tables(
        self,
        metric_names: list[str],
        dimension_names: list[str],
    ) -> list[TableModel]:
        """
        Metric과 Dimension이 참조하는 모든 Table을 반환한다.

        Metric:
        - BaseMetricModel.table
        - DerivedMetricModel의 모든 하위 BaseMetric.table

        Dimension:
        - DimensionModel.mappings[].table

        동일한 Table은 결과에 한 번만 포함한다.
        """

        tables: list[TableModel] = []
        resolved_table_names: set[str] = set()

        def append_table(table_name: str) -> None:
            if table_name in resolved_table_names:
                return

            table = self.resolve_table(table_name)

            resolved_table_names.add(table_name)
            tables.append(table)

        for metric_name in metric_names:
            root_metric = self.resolve_metric(metric_name)

            metric_objects = [
                *self.resolve_metric_dependencies(metric_name),
                root_metric,
            ]

            for metric in metric_objects:
                if not isinstance(metric, BaseMetricModel):
                    continue
                if metric.table :
                    append_table(metric.table)


        for dimension_name in dimension_names:
            dimension = self.resolve_dimension(dimension_name)

            for mapping in dimension.mappings or []:
                if mapping.table :
                    append_table(mapping.table)

        return tables

    # ======================================================
    # Internal: Metric Helper
    # ======================================================

    @staticmethod
    def _metric_dependency_names(
        metric: DerivedMetricModel,
    ) -> list[str]:
        """
        Derived Metric Formula에서 참조 Metric 이름을 추출한다.

        numerator와 denominator가 동일한 Metric을 참조하는 경우
        한 번만 반환한다.
        """

        dependency_names = [
            metric.formula.numerator.metric,
            metric.formula.denominator.metric,
        ]

        return MetadataResolver._deduplicate_strings(
            dependency_names
        )

    # ======================================================
    # Internal: Glossary Helper
    # ======================================================

    def _find_glossary_entry(
        self,
        term: str,
        glossary: object | None,
        collection_name: str,
        entity_name: str,
    ) -> object:
        """
        Glossary에서 term과 일치하는 항목을 찾는다.

        검색 대상:
        - entry.term
        - entry.aliases

        대소문자와 연속 공백은 무시한다.
        """

        normalized_term = self._normalize_term(term)

        if not normalized_term:
            raise ValueError(
                f"{entity_name.capitalize()} term must not be empty."
            )

        if glossary is None:
            raise LookupError(
                f"{entity_name.capitalize()} glossary is not loaded."
            )

        entries = getattr(glossary, collection_name, None)

        if entries is None:
            raise AttributeError(
                f"{type(glossary).__name__} does not define "
                f"'{collection_name}'."
            )

        matched_entries: list[object] = []

        for entry in entries:
            candidates = self._glossary_candidates(entry)

            if any(
                self._normalize_term(candidate) == normalized_term
                for candidate in candidates
            ):
                matched_entries.append(entry)

        if not matched_entries:
            for entry in entries:
                if self._match_filter_pattern(term, entry)[0] is not None:
                    matched_entries.append(entry)

        if not matched_entries:
            raise KeyError(
                f"Unknown {entity_name} glossary term: '{term}'."
            )

        if len(matched_entries) > 1:
            matched_terms = [
                str(getattr(entry, "term", type(entry).__name__))
                for entry in matched_entries
            ]

            raise ValueError(
                f"Ambiguous {entity_name} glossary term '{term}': "
                + ", ".join(matched_terms)
            )

        return matched_entries[0]

    @staticmethod
    def _glossary_candidates(
        entry: object,
    ) -> list[str]:
        """
        Glossary 항목에서 검색 가능한 문자열 목록을 생성한다.
        """

        candidates: list[str] = []

        term = getattr(entry, "term", None)

        if term:
            candidates.append(str(term))

        aliases = getattr(entry, "aliases", None) or []

        if isinstance(aliases, str):
            candidates.append(aliases)
        else:
            candidates.extend(
                str(alias)
                for alias in aliases
                if alias is not None
            )

        return candidates

    @staticmethod
    def _filter_patterns(entry: object) -> list[PatternFilterCondition]:
        patterns = getattr(entry, "patterns", None) or []

        return [
            pattern
            for pattern in patterns
            if isinstance(pattern, PatternFilterCondition)
        ]

    def _match_filter_pattern(
        self,
        term: str,
        entry: object,
    ) -> tuple[PatternFilterCondition | None, str | None]:
        normalized_term = str(term).strip()

        for pattern in self._filter_patterns(entry):
            if not pattern.regex:
                continue

            match = re.search(pattern.regex, normalized_term)

            if not match:
                continue

            try:
                return pattern, match.group(pattern.value_group)
            except IndexError as exc:
                raise ValueError(
                    f"Filter glossary term '{getattr(entry, 'term', term)}' matched "
                    f"regex '{pattern.regex}' but value_group {pattern.value_group} "
                    "is out of range."
                ) from exc

        return None, None

    @staticmethod
    def _entry_uses_pattern_value(entry: object) -> bool:
        for condition in getattr(entry, "filters", []) or []:
            value = getattr(condition, "value", None)

            if isinstance(value, str) and "{value}" in value:
                return True

        return False

    @staticmethod
    def _substitute_pattern_value(
        value: object,
        extracted_value: str,
    ) -> object:
        if isinstance(value, str):
            return value.replace("{value}", extracted_value)

        if isinstance(value, list):
            return [
                MetadataResolver._substitute_pattern_value(item, extracted_value)
                for item in value
            ]

        if isinstance(value, dict):
            return {
                key: MetadataResolver._substitute_pattern_value(
                    item,
                    extracted_value,
                )
                for key, item in value.items()
            }

        return value

    # ======================================================
    # Internal: Common Helper
    # ======================================================

    @staticmethod
    def _normalize_name(
        name: str,
        entity_name: str,
    ) -> str:
        normalized_name = str(name).strip()

        if not normalized_name:
            raise ValueError(
                f"{entity_name} name must not be empty."
            )

        return normalized_name

    @staticmethod
    def _normalize_term(term: str) -> str:
        """
        대소문자와 연속 공백을 제거해 Glossary 비교 문자열을 만든다.
        """

        return " ".join(
            str(term).strip().casefold().split()
        )

    @staticmethod
    def _deduplicate_strings(
        values: list[str],
    ) -> list[str]:
        """
        입력 순서를 유지하면서 중복 문자열을 제거한다.
        """

        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized_value = str(value).strip()

            if not normalized_value:
                continue

            if normalized_value in seen:
                continue

            seen.add(normalized_value)
            result.append(normalized_value)

        return result

    @staticmethod
    def model_name(
        model: object,
    ) -> str:
        """
        Metadata Model 종류에 따라 식별자를 반환한다.

        REST API 또는 MCP 응답 변환 시 사용할 수 있다.
        """

        if isinstance(model, TableModel):
            return model.table_name

        if isinstance(model, DimensionModel):
            return model.dimension_id

        if isinstance(
            model,
            (BaseMetricModel, DerivedMetricModel),
        ):
            return model.metric_name

        if isinstance(model, AnalysisPatternModel):
            return model.pattern_id

        raise TypeError(
            f"Unsupported metadata model type: "
            f"{type(model).__name__}."
        )