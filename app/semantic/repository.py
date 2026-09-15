from dataclasses import dataclass, field
from pathlib import Path

from .loader import MetadataLoader
from .models import (
    TableModel,
    DimensionModel,
    BaseMetricModel,
    DerivedMetricModel,
    MetricGlossaryFile,
    DimensionGlossaryFile,
    FilterGlossaryFile,
    AnalysisGlossaryFile,
    AnalysisPatternModel,
)


MetricModel = BaseMetricModel | DerivedMetricModel


@dataclass
class MetadataRegistry:
    tables: dict[str, TableModel] = field(default_factory=dict)
    dimensions: dict[str, DimensionModel] = field(default_factory=dict)
    metrics: dict[str, MetricModel] = field(default_factory=dict)
    patterns: dict[str, AnalysisPatternModel] = field(default_factory=dict)

    metric_glossary: MetricGlossaryFile | None = None
    dimension_glossary: DimensionGlossaryFile | None = None
    filter_glossary: FilterGlossaryFile | None = None
    analysis_glossary: AnalysisGlossaryFile | None = None

    @classmethod
    def load(cls, metadata_root: str | Path) -> "MetadataRegistry":
        root = Path(metadata_root)

        def first_existing_dir(*relative_paths: str) -> Path:
            for relative_path in relative_paths:
                candidate = root / relative_path
                if candidate.exists() and candidate.is_dir():
                    return candidate
            return root / relative_paths[0]

        def first_existing_file(*relative_paths: str) -> Path:
            for relative_path in relative_paths:
                candidate = root / relative_path
                if candidate.exists() and candidate.is_file():
                    return candidate
            return root / relative_paths[0]

        registry = cls(
            tables=MetadataLoader.load_tables(first_existing_dir("tables", "table")),
            dimensions=MetadataLoader.load_dimensions(
                first_existing_dir("dimensions", "dimension", "dimemsions")
            ),
            metrics=MetadataLoader.load_metrics(first_existing_dir("metrics", "metric")),
            patterns=MetadataLoader.load_patterns(first_existing_dir("patterns", "pattern")),

            metric_glossary=MetadataLoader.load_metric_glossary(
                first_existing_file("glossary/metrics.yaml", "glossary/metrics.yml")
            ),
            dimension_glossary=MetadataLoader.load_dimension_glossary(
                first_existing_file("glossary/dimensions.yaml", "glossary/dimensions.yml")
            ),
            filter_glossary=MetadataLoader.load_filter_glossary(
                first_existing_file("glossary/filters.yaml", "glossary/filters.yml")
            ),
            analysis_glossary=MetadataLoader.load_analysis_glossary(
                first_existing_file("glossary/analysis.yaml", "glossary/analysis.yml")
            ),
        )
        registry.validate()
        return registry
    #
    # Convenience API
    #

    def table(self, name: str) -> TableModel:
        return self.tables[name]

    def dimension(self, name: str) -> DimensionModel:
        return self.dimensions[name]

    def metric(self, name: str) -> MetricModel:
        return self.metrics[name]

    def pattern(self, name: str) -> AnalysisPatternModel:
        return self.patterns[name]

    def validate(self) -> None :
        errors: list[str] = []

        glossary_filters = {
            filter_glossary.term for filter_glossary in getattr(self.filter_glossary, "filters", [])
        }

        #
        # Dimension -> Table
        #
        for name, dimension in self.dimensions.items() :
            for mapping in getattr(dimension, "mappings", []) or []:
                table = getattr(mapping, "table", None)
                if table and table not in self.tables:
                    errors.append(
                        f"Dimension '{name}' references unknown table '{table}' in mappings."
                    )

            for join_table in getattr(dimension, "joins", []) or []:
                if join_table not in self.tables:
                    errors.append(
                        f"Dimension '{name}' references unknown join table '{join_table}'."
                    )

        #
        # Base Metric -> Table / Dimension
        #
        for name, metric in self.metrics.items():
            if isinstance(metric, BaseMetricModel):
                if metric.table not in self.tables:
                    errors.append(
                        f"Metric '{name}' references unknown table '{metric.table}'."
                    )

            for dimension in getattr(metric, "supported_dimensions", []) or []:
                if dimension not in self.dimensions:
                    errors.append(
                        f"Metric '{name}' references unknown supported dimension '{dimension}'."
                    )

            for dimension in getattr(metric, "default_dimension", []) or []:
                if dimension not in self.dimensions:
                    errors.append(
                        f"Metric '{name}' references unknown default dimension '{dimension}'."
                    )

        #
        # Derived Metric -> Metric
        #
        for name, metric in self.metrics.items() :
            if isinstance(metric, DerivedMetricModel) :
                deps = [
                    metric.formula.numerator.metric,
                    metric.formula.denominator.metric,
                ]

                for dep in deps :
                    if dep not in self.metrics :
                        errors.append(
                                f"Derived metric '{name}' references unknown metric '{dep}'."
                        )

        #
        # Pattern
        #
        for name, pattern in self.patterns.items() :

            for metric in getattr(pattern, "metrics", []) :
                if metric not in self.metrics :
                    errors.append(
                            f"Pattern '{name}' references unknown metric '{metric}'."
                    )

            for dimension in getattr(pattern, "dimensions", []) :
                if dimension not in self.dimensions :
                    errors.append(
                            f"Pattern '{name}' references unknown dimension '{dimension}'."
                    )

            for filter_name in getattr(pattern, "filters", []) :
                if filter_name not in glossary_filters :
                    errors.append(
                            f"Pattern '{name}' references unknown filter '{filter_name}'."
                    )

            for sort in getattr(pattern, "default_sort", []) or []:
                if sort.metric not in self.metrics:
                    errors.append(
                        f"Pattern '{name}' default_sort references unknown metric '{sort.metric}'."
                    )

        #
        # Metric glossary
        #
        if self.metric_glossary :
            for metric in getattr(self.metric_glossary, "metrics", []) :
                if metric.metric not in self.metrics :
                    errors.append(
                            f"Metric glossary references unknown metric '{metric.metric}'."
                    )

        #
        # Dimension glossary
        #
        if self.dimension_glossary :
            for dimension in getattr(self.dimension_glossary, "dimensions", []) :
                if dimension.dimension not in self.dimensions :
                    errors.append(
                            f"Dimension glossary references unknown dimension '{dimension.dimension}'."
                    )

        #
        # Filter glossary -> Dimension
        #
        if self.filter_glossary:
            for filter_glossary in getattr(self.filter_glossary, "filters", []) or []:
                for condition in getattr(filter_glossary, "filters", []) or []:
                    if condition.dimension not in self.dimensions:
                        errors.append(
                            "Filter glossary '"
                            f"{filter_glossary.term}' references unknown dimension "
                            f"'{condition.dimension}'."
                        )

        #
        # Analysis glossary
        #
        if self.analysis_glossary:
            for analysis in getattr(self.analysis_glossary, "analysis", []) or []:
                for metric in getattr(analysis, "metrics", []) or []:
                    if metric not in self.metrics:
                        errors.append(
                            f"Analysis glossary '{analysis.term}' references unknown metric '{metric}'."
                        )

                for dimension in getattr(analysis, "dimensions", []) or []:
                    if dimension not in self.dimensions:
                        errors.append(
                            f"Analysis glossary '{analysis.term}' references unknown dimension '{dimension}'."
                        )

        if errors :
            raise ValueError(
                    "Metadata validation failed:\n\n- "
                    + "\n- ".join(errors)
            )

class MetadataRepository :

    def __init__(self, registry: MetadataRegistry) :
        self._registry = registry

    def get_table(self, name) :
        return self._registry.table(name)

    def get_dimension(self, name) :
        return self._registry.dimension(name)

    def get_metric(self, name) :
        return self._registry.metric(name)

    def get_pattern(self, name) :
        return self._registry.pattern(name)

    def list_patterns(self) -> dict[str, AnalysisPatternModel]:
        return dict(self._registry.patterns)

    def get_metric_glossary(self) :
        return self._registry.metric_glossary

    def get_dimension_glossary(self) :
        return self._registry.dimension_glossary

    def get_filter_glossary(self) :
        return self._registry.filter_glossary

    def get_analysis_glossary(self) :
        return self._registry.analysis_glossary
