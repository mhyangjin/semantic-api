"""자연어 질문에서 glossary 밖의 dimension 값을 추출한다."""

from __future__ import annotations

import re

from .context import LiteralDimensionFilter
from .models import DimensionModel


def resolve_literal_dimension_filters(
    question: str | None,
    dimensions: dict[str, DimensionModel],
) -> list[LiteralDimensionFilter]:
    """Dimension metadata의 패턴으로 질문 속 리터럴 값을 추출한다."""

    if not question:
        return []

    matches: list[tuple[int, DimensionModel, str]] = []
    for dimension in dimensions.values():
        for pattern in dimension.literal_patterns or []:
            match = re.search(pattern.regex, question, re.I)
            if not match:
                continue
            try:
                value = match.group(pattern.value_group).strip().rstrip(pattern.strip)
            except IndexError as exc:
                raise ValueError(
                    f"Literal pattern for '{dimension.dimension_id}' has invalid "
                    f"value_group {pattern.value_group}."
                ) from exc
            matches.append((match.start(), dimension, value))
            break
    resolved: list[LiteralDimensionFilter] = []
    for _, dimension, value in sorted(matches, key=lambda item: item[0]):
        resolved.extend(_literal_filters_for_dimension(dimension, value, dimensions))
    return resolved


def _literal_filters_for_dimension(
    dimension: DimensionModel,
    value: str,
    dimensions: dict[str, DimensionModel],
) -> list[LiteralDimensionFilter]:
    filters: list[LiteralDimensionFilter] = []
    for implied in dimension.implied_filters or []:
        implied_dimension = dimensions[implied.dimension]
        filters.append(LiteralDimensionFilter(
            dimension=implied_dimension.dimension_id,
            business_name=implied_dimension.business_name,
            operator=implied.operator,
            value=str(implied.value),
            sql_value=str(implied.value),
        ))
    filters.append(LiteralDimensionFilter(
        dimension=dimension.dimension_id,
        business_name=dimension.business_name,
        value=value,
        sql_value=value,
    ))
    return filters
