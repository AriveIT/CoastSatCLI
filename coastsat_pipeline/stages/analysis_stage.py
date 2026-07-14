from __future__ import annotations

from Complete_Analysis import shoreline_analysis  # type: ignore

from ..context import PipelineContext
from ..helpers.analysis import run_shoreline_analysis
from ..stage import PipelineStage
from ..parameters import Parameters

class AnalysisStage(PipelineStage):
    name = "analysis"
    description = "Generate shoreline plots/exports and prepare cross-distance arrays."

    def run(self, context: PipelineContext, params: Parameters) -> None:
        settings = context.global_settings
        output = context.shoreline_output

        if settings is None or output is None:
            raise RuntimeError("AnalysisStage requires shoreline_output and analysis_settings.")

        cross_distance, transects, updated_output = run_shoreline_analysis(
            output,
            settings,
            params.transect_settings,
        )

        context.cross_distance = cross_distance
        context.transects = transects
        context.shoreline_output = updated_output
        context.metadata["analysis"] = {"plots_created": True}
