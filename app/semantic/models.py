"""
Metadata YAML 로딩을 위한 Pydantic 모델 정의
"""
from typing import Any, List, Optional, Literal
from pydantic import BaseModel, model_validator

class DimensionFilterCondition(BaseModel):
    dimension: str
    operator: str
    value: Any

class PatternFilterCondition(BaseModel):
    regex: str
    value_group: int = 1

class ColumnFilterCondition(BaseModel):
    column: str
    operator: str
    value: Any

class MappingPattern(BaseModel):
    format: Optional[str]=None
    prefix: Optional[str]=None
    suffix: Optional[str]=None
    example: Optional[str]=None
    extract: Optional[str]=None

class Mapping(BaseModel):
    """Dimension 매핑 정보"""
    table: str
    column: Optional[str] = None
    business_name: Optional[str] = None
    resolver: Optional[dict[str, Any]] = None
    transform: Optional[dict[str, Any]] = None
    pattern: Optional[MappingPattern] = None

class Parameter(BaseModel):
    name: str
    business_name: str
    required: bool

class JoinCondition(BaseModel):
    """조인 조건"""
    left: str
    operator: str
    right: str
    required: Optional[bool] = False
    use_when: Optional[List[str]] = None


class Join(BaseModel):
    """조인 정보"""
    table: str
    type: Optional[str] = None  # inner, left, right, full
    purpose: Optional[str] = None
    join_cardinality: Optional[str] = None  # one_to_one, one_to_many, many_to_many
    entity_cardinality: Optional[str] = None
    conditions: Optional[List[JoinCondition]] = None


class Column(BaseModel):
    """테이블 컬럼 정보"""
    name: str
    business_name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class DimensionModel(BaseModel):
    """차원(Dimension) 메타데이터 모델"""
    dimension_id: str
    business_name: str
    parameters: Optional[List[Parameter]] = None
    mappings: Optional[List[Mapping]] = None
    joins: Optional[List[str]] = None
    description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_mapping_field(cls, data):
        if isinstance(data, dict) and "mappings" not in data and "mapping" in data:
            data = dict(data)
            data["mappings"] = data.pop("mapping")
        return data

    class Config:
        extra = "allow"  # 추가 필드 허용

class MetricBase(BaseModel):
    metric_name: str
    business_name: str
    description: str | None = None

    supported_dimensions: list[str] = []
    default_dimension: list[str] = []

class BaseMetricModel(MetricBase):
    type: Literal["base"] = "base"

    aggregate: str
    table: str

    filter: list[ColumnFilterCondition] = []

class FormulaRef(BaseModel):
    metric: str


class Formula(BaseModel) :
    numerator: FormulaRef
    denominator: FormulaRef

class DerivedMetricModel(MetricBase):
    type: Literal["derived"] = "derived"
    formula: Formula
    format: str | None = None
    precision: int | None = None
    inherit_dimensions: str = "intersection"
    class Config:
        extra = "allow"


class MetricTerm(BaseModel):
    """용어집의 메트릭 항목"""
    term: str
    metric: str
    aliases: Optional[List[str]] = None
    description: Optional[str] = None

class GlossaryBase(BaseModel):
    """Glossary 공통 모델"""
    term: str
    aliases: list[str] = []
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data):
        if not isinstance(data, dict):
            return data

        data = dict(data)

        aliases = data.get("aliases")

        if aliases is None:
            data["aliases"] = []
        elif isinstance(aliases, str):
            data["aliases"] = [aliases]
        else:
            data["aliases"] = [alias for alias in aliases if alias is not None]

        return data

    class Config:
        extra = "forbid"

class MetricGlossary(GlossaryBase):
    """Metric 용어"""
    metric: str

class DimensionGlossary(GlossaryBase) :
    """Dimension 용어"""
    dimension: str
    values: dict[str, list[str]] | None = None

class FilterGlossary(GlossaryBase):
    patterns: list[PatternFilterCondition] = []
    filters: list[DimensionFilterCondition] = []

    @model_validator(mode="before")
    @classmethod
    def _normalize_filter_field(cls, data):
        if isinstance(data, dict) and "filters" not in data and "filter" in data:
            data = dict(data)
            filter_value = data.pop("filter")
            if filter_value is None:
                data["filters"] = []
            elif isinstance(filter_value, list):
                data["filters"] = filter_value
            else:
                data["filters"] = [filter_value]
        return data

class AnalysisGlossary(GlossaryBase):
    metrics: list[str] = []
    dimensions: list[str] = []


class MetricGlossaryFile(BaseModel):
    version: str | float = "1.0"
    metrics: list[MetricGlossary]

class DimensionGlossaryFile(BaseModel):
    version: str | float = "1.0"
    dimensions: list[DimensionGlossary]


class FilterGlossaryFile(BaseModel):
    version: str | float = "1.0"
    filters: list[FilterGlossary]


class AnalysisGlossaryFile(BaseModel):
    version: str | float = "1.0"
    analysis: list[AnalysisGlossary]


class TableModel(BaseModel):
    """테이블 메타데이터 모델"""
    table_name: str
    business_name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    refresh_cycle: Optional[str] = None
    joins: Optional[List[Join]] = None
    columns: Optional[List[Column]] = None

    class Config:
        extra = "allow"


class Sort(BaseModel):
    """기본 정렬 정보"""
    metric: str
    direction: Literal["asc", "desc"] = "asc"

    class Config:
        extra = "forbid"

class AnalysisPatternModel(BaseModel):
    """
    Analysis Pattern
    """
    pattern_id: str
    business_name: str
    description: str | None = None
    metrics: list[str] = []
    dimensions: list[str] = []
    filters: list[str] = []
    default_sort: list[Sort] = []
    purpose: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _normalize_metric_field(cls, data):
        if not isinstance(data, dict):
            return data

        data = dict(data)

        if "metrics" not in data and "metric" in data:
            data["metrics"] = data.pop("metric")

        for key in ("metrics", "dimensions", "filters", "purpose"):
            value = data.get(key)
            if isinstance(value, str):
                data[key] = [value]

        if isinstance(data.get("default_sort"), dict):
            data["default_sort"] = [data["default_sort"]]

        return data

    class Config:
        extra = "forbid"



